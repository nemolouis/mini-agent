"""Confining file access to one directory, for a caller that is an adversary.

Everything the notes server touches goes through this module. The rules (each one has tests):

* A path is a *relative* string. No NUL, no backslash, no `~`, no drive letter, no empty / `.` / `..`
  component, and no component that starts with `.` (so `.git`, `.env`, `.ssh` ... are unreachable).
  No URL-decoding is ever done: `%2e%2e` is just a strange file name.
* Directories are walked with directory file descriptors: every component is opened relative to the
  previous one with `O_NOFOLLOW | O_DIRECTORY`. There is no "check, then open" gap to race against, and
  a symbolic link anywhere on the path makes the open fail instead of being followed.
* The final file is opened with `O_NOFOLLOW | O_NONBLOCK` and then `fstat`ed: it must be a regular file
  (a FIFO would block a reader forever, a device would never end), have exactly one hard link (a hard link
  to a file outside the root cannot be told from a file inside it), and not exceed the size limit.
* Only whitelisted suffixes are readable. "Not found" and "not allowed" produce the same message, so
  the server is not an oracle for what exists outside the root.

This is application-level confinement, not a sandbox: the process still runs with the user's rights.
"""
from __future__ import annotations

import os
import re
import stat
import time
from dataclasses import dataclass

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_DRIVE = re.compile(r"^[A-Za-z]:")
_DENY_PREFIXES = ("id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "authorized_keys", "known_hosts")

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
_APPEND_FLAGS = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC

_before_final_open = None  # test hook: called between opening the parent directory and the final open


class Denied(Exception):
    """Not allowed, or not there. One message for both so the server cannot be used to probe the disk."""


class TooLarge(Denied):
    """The file is allowed but exceeds the size limit (safe to say: the caller already has a legal path)."""


def clean_text(s: str) -> str:
    """Strip ANSI escape sequences and control characters (keeps newline and tab)."""
    return _CTRL.sub("", _ANSI.sub("", s))


def show(rel) -> str:
    """A printable, bounded echo of a caller-supplied path for error messages."""
    return clean_text(str(rel))[:100]


@dataclass(frozen=True)
class Policy:
    root: str                                    # real path of the notes directory
    suffixes: tuple = (".md", ".txt", ".rst")
    max_file_bytes: int = 1 << 20
    max_files: int = 2000
    max_depth: int = 8
    max_path_len: int = 512
    max_components: int = 16


def make_policy(root, **kw) -> Policy:
    real = os.path.realpath(root)
    if not os.path.isdir(real):
        raise ValueError(f"notes root is not a directory: {root}")
    return Policy(real, **kw)


def validate_rel(policy: Policy, rel, *, allow_empty: bool = False) -> list[str]:
    """Return the components of a safe relative path, or raise Denied."""
    if not isinstance(rel, str):
        raise Denied(show(rel))
    if allow_empty and rel in ("", "."):
        return []
    if (not rel or len(rel) > policy.max_path_len or "\x00" in rel or "\\" in rel
            or rel.startswith(("/", "~")) or _DRIVE.match(rel)):
        raise Denied(show(rel))
    parts = rel[:-1].split("/") if rel.endswith("/") else rel.split("/")
    if not parts or len(parts) > policy.max_components:
        raise Denied(show(rel))
    for p in parts:
        if (p in ("", ".", "..") or p.startswith(".") or p.casefold().startswith(_DENY_PREFIXES)
                or any(ord(c) < 32 or ord(c) == 127 for c in p)):
            raise Denied(show(rel))
    return parts


def has_allowed_suffix(policy: Policy, name: str) -> bool:
    return name.lower().endswith(policy.suffixes)


def open_dir(policy: Policy, parts: list[str]) -> int:
    """fd of the directory `parts` under the root. Caller closes. Raises Denied."""
    try:
        fd = os.open(policy.root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError:
        raise Denied("root")
    try:
        for part in parts:
            try:
                nfd = os.open(part, _DIR_FLAGS, dir_fd=fd)
            except OSError:
                raise Denied(part)
            os.close(fd)
            fd = nfd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _check_regular(policy: Policy, fd: int, *, write: bool) -> None:
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise Denied("not a plain file")
    if not write and st.st_size > policy.max_file_bytes:
        raise TooLarge(f"note is larger than {policy.max_file_bytes} bytes")


def open_file(policy: Policy, parts: list[str], *, write: bool = False) -> int:
    """fd of a plain file under the root (read, or append/create when `write`). Caller closes."""
    if not parts or not has_allowed_suffix(policy, parts[-1]):
        raise Denied("suffix")
    dfd = open_dir(policy, parts[:-1])
    try:
        if _before_final_open is not None:
            _before_final_open()
        try:
            fd = os.open(parts[-1], _APPEND_FLAGS if write else _READ_FLAGS, 0o600, dir_fd=dfd)
        except OSError:
            raise Denied(parts[-1])
    finally:
        os.close(dfd)
    try:
        _check_regular(policy, fd, write=write)
    except BaseException:
        os.close(fd)
        raise
    return fd


def read_all(fd: int, limit: int) -> bytes:
    chunks, total = [], 0
    while total <= limit:
        b = os.read(fd, 65536)
        if not b:
            break
        chunks.append(b)
        total += len(b)
    return b"".join(chunks)


class Scan:
    """Depth-first, name-sorted walk of the notes under `parts`; never follows a symlink.

    Iterating yields (relative path, fd or None, size). With `open_files` the fd is already opened
    (and fstat-checked) and the consumer must close it. `truncated` is set when a limit stopped the walk.
    """

    def __init__(self, policy: Policy, parts: list[str], *, open_files: bool = False, deadline: float | None = None):
        self.policy, self.parts, self.open_files, self.deadline = policy, parts, open_files, deadline
        self.truncated = False
        self.count = 0

    def __iter__(self):
        dfd = open_dir(self.policy, self.parts)
        try:
            yield from self._walk(dfd, "/".join(self.parts), 0)
        finally:
            os.close(dfd)

    def _stop(self) -> bool:
        if self.count >= self.policy.max_files or (self.deadline is not None and time.monotonic() > self.deadline):
            self.truncated = True
        return self.truncated

    def _walk(self, dfd: int, prefix: str, depth: int):
        for name in sorted(os.listdir(dfd)):
            if self._stop():
                return
            if name.startswith(".") or name.casefold().startswith(_DENY_PREFIXES):
                continue
            rel = f"{prefix}/{name}" if prefix else name
            try:
                st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
            except OSError:
                continue
            if stat.S_ISDIR(st.st_mode):
                if depth >= self.policy.max_depth:
                    self.truncated = True
                    continue
                try:
                    cfd = os.open(name, _DIR_FLAGS, dir_fd=dfd)
                except OSError:
                    continue
                try:
                    yield from self._walk(cfd, rel, depth + 1)
                finally:
                    os.close(cfd)
            elif (stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and has_allowed_suffix(self.policy, name)
                  and st.st_size <= self.policy.max_file_bytes):
                self.count += 1
                if not self.open_files:
                    yield rel, None, st.st_size
                    continue
                try:
                    fd = os.open(name, _READ_FLAGS, dir_fd=dfd)
                    _check_regular(self.policy, fd, write=False)
                except (OSError, Denied):
                    try:
                        os.close(fd)
                    except (OSError, UnboundLocalError):
                        pass
                    continue
                yield rel, fd, st.st_size
