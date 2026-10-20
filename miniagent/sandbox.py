"""Run shell commands inside a locked-down Docker container. Design and threat model: docs/m5_sandbox_taskgen_design.md.

One container per agent run (a `sleep` under `--init`), one `docker exec` per command. The workspace directory is
bind-mounted at /work; nothing else of the host is visible. No network, read-only root file system, no capabilities,
non-root user, no environment variables, limits on processes, memory and CPU. The container shares the host kernel:
this is a strong application-level boundary, not a virtual machine.
"""
from __future__ import annotations

import atexit
import os
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .proc import ShellResult

IMAGE = "miniagent-sandbox:py312"
LABEL = "miniagent-sandbox=1"
SYNC_SECONDS = 10.0             # how long a command waits for the container to see the host's version of the workspace
OUTPUT_CAP = 2_000_000          # bytes kept per stream; the rest is read and dropped so a flood cannot fill host memory
_live: set[str] = set()


class SandboxError(Exception):
    """The sandbox itself failed (Docker down, container died). An infrastructure fault, never the model's fault."""


@dataclass(frozen=True)
class SandboxConfig:
    image: str = IMAGE
    memory: str = "1g"
    cpus: float = 1.0
    pids: int = 256
    tmp_size: str = "256m"
    network: bool = False


def docker_run_args(name: str, workdir: Path, cfg: SandboxConfig, uid: int, gid: int) -> list[str]:
    """The `docker run` command line. A pure function so that every security option can be tested without Docker."""
    args = ["docker", "run", "-d", "--init", "--name", name, "--label", LABEL,
            "--read-only", f"--tmpfs=/tmp:rw,exec,nosuid,size={cfg.tmp_size}",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", str(cfg.pids), "--memory", cfg.memory, "--memory-swap", cfg.memory, "--cpus", str(cfg.cpus),
            "--user", f"{uid}:{gid}", "-e", "HOME=/tmp",
            "-v", f"{workdir}:/work:rw", "-w", "/work"]
    if not cfg.network:
        args += ["--network", "none"]
    return args + [cfg.image, "sleep", "infinity"]


# Files changed on the host reach the container with a delay (the Docker VM learns of host changes asynchronously; measured:
# about 8% of "overwrite a file, start a command at once" saw the old file under load). Before each command the container
# therefore waits until its view of the workspace (path, size, mtime in seconds of every regular file) equals the host's,
# which is sent on stdin. If it does not converge the command is not run (SandboxError): better a run that ends as an
# infrastructure error than a transcript in which the agent's edit seems to have had no effect. Writes made inside the
# container are visible to the host at once (measured: 0 of 600 late). The delay is also long-lived (10 s and more) for a
# file that an EARLIER container read and the host then replaced, so a fresh container must not be started over such a
# directory (grading mounts a fresh copy instead, see eval/grade.run_tests).
_SYNC_SCRIPT = r"""
exp=$(mktemp /tmp/manifest.XXXXXX); cat > "$exp"
i=0
while ! find . -type f -not -path '*/__pycache__/*' -not -path './.pytest_cache/*' -printf '%P\t%s\t%Ts\n' | LC_ALL=C sort | cmp -s - "$exp"; do
  i=$((i+1))
  if [ "$i" -ge "$3" ]; then echo "miniagent-sandbox: workspace view did not converge" >&2; exit 97; fi
  sleep 0.05
done
rm -f "$exp"
exec timeout -k 2 "$1" bash -c "$2"
"""
_SKIP_DIRS = {"__pycache__"}


def workspace_manifest(root: Path) -> bytes:
    """The lines `find . -type f -printf '%P\t%s\t%Ts\n' | LC_ALL=C sort` prints inside the container for the same tree."""
    lines: list[bytes] = []
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            if e.is_dir(follow_symlinks=False):
                if e.name in _SKIP_DIRS or (d == root and e.name == ".pytest_cache"):
                    continue
                stack.append(Path(e.path))
            elif e.is_file(follow_symlinks=False):
                st = e.stat(follow_symlinks=False)
                rel = os.fsencode(os.path.relpath(e.path, root))
                lines.append(rel + b"\t%d\t%d\n" % (st.st_size, int(st.st_mtime)))
    return b"".join(sorted(lines))


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _run_capped(argv: list[str], timeout: float, cap: int = OUTPUT_CAP,
                stdin: bytes = b"") -> tuple[int | None, str, str, bool]:
    """Run `argv` (feeding it `stdin`, then EOF), keep at most `cap` bytes of each stream, give up after `timeout`.
    -> (rc, stdout, stderr, timed_out)."""
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        p.stdin.write(stdin)
        p.stdin.close()
    except BrokenPipeError:
        pass
    bufs, dropped = [bytearray(), bytearray()], [0, 0]

    def pump(stream, i):
        while True:
            chunk = stream.read1(65536)
            if not chunk:
                return
            room = max(cap - len(bufs[i]), 0)
            bufs[i] += chunk[:room]
            dropped[i] += len(chunk) - min(len(chunk), room)

    threads = [threading.Thread(target=pump, args=(s, i), daemon=True) for i, s in enumerate((p.stdout, p.stderr))]
    [t.start() for t in threads]
    timed_out = False
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(p.pid)
        p.wait()
    finally:
        _kill_group(p.pid)
    [t.join(5) for t in threads]
    out = []
    for i in range(2):
        text = bytes(bufs[i]).decode("utf-8", "replace")
        out.append(text + (f"\n[... {dropped[i]} more bytes dropped]" if dropped[i] else ""))
    return (None if timed_out else p.returncode), out[0], out[1], timed_out


def _docker(*args: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def available(image: str = IMAGE) -> bool:
    """Docker answers and the sandbox image exists."""
    try:
        return _docker("image", "inspect", image, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def cleanup_orphans() -> int:
    """Remove sandbox containers left behind by a crashed process. Returns how many."""
    ids = _docker("ps", "-aq", "--filter", f"label={LABEL}").stdout.split()
    if ids:
        _docker("rm", "-f", *ids)
    return len(ids)


@atexit.register
def _cleanup_live() -> None:
    for name in list(_live):
        try:
            _docker("rm", "-f", name, timeout=30)
        except Exception:
            pass
    _live.clear()


class Sandbox:
    def __init__(self, workdir: str | Path, config: SandboxConfig | None = None):
        self.workdir = Path(workdir).resolve()
        self.config = config or SandboxConfig()
        self.name = f"mini-{uuid.uuid4().hex[:12]}"
        self.started = False

    def start(self) -> "Sandbox":
        args = docker_run_args(self.name, self.workdir, self.config, os.getuid(), os.getgid())
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise SandboxError(f"cannot start the sandbox: {e}") from e
        if r.returncode != 0:
            raise SandboxError(f"docker run failed: {r.stderr.strip()[:500]}")
        self.started = True
        _live.add(self.name)
        return self

    def exec(self, command: str, timeout: float = 60, _retry: bool = True) -> ShellResult:
        if not self.started:
            raise SandboxError("sandbox is not running")
        t = max(int(timeout), 1)
        argv = ["docker", "exec", "-i", "-w", "/work", self.name, "bash", "-c", _SYNC_SCRIPT, "_", str(t), command, str(int(SYNC_SECONDS / 0.05))]
        t0 = time.time()
        rc, out, err, host_timeout = _run_capped(argv, timeout=t + 30, stdin=workspace_manifest(self.workdir))
        if host_timeout:                               # the in-container timeout should have fired long before
            self.close()
            raise SandboxError("docker exec did not return; the container was removed")
        if rc == 97 and "did not converge" in err:
            raise SandboxError("the container does not see the current files of the workspace (host/VM file sharing lag)")
        if "OCI runtime exec failed" in err + out[:300] or rc == 125 or (rc == 1 and "No such container" in err):
            # typically the process table is full (a fork bomb left debris): start over once, then give up
            if _retry:
                self._restart()
                return self.exec(command, timeout, _retry=False)
            raise SandboxError(f"docker exec failed: {(err or out).strip()[:300]}")
        elapsed = time.time() - t0
        if rc in (124, 137) and elapsed >= t - 0.5:
            self._restart()          # kills anything the command left running (setsid daemons, a half-dead fork bomb)
            return ShellResult(None, out, err, True)
        return ShellResult(rc, out, err, False)

    def _restart(self) -> None:
        """Replace the container by a fresh one over the same workspace directory (the workspace files are kept)."""
        _docker("rm", "-f", self.name, timeout=30)
        _live.discard(self.name)
        self.started = False
        self.name = f"mini-{uuid.uuid4().hex[:12]}"
        self.start()

    def close(self) -> None:
        if self.started:
            self.started = False
            try:
                _docker("rm", "-f", self.name, timeout=30)
            except Exception:
                pass
            _live.discard(self.name)

    def __enter__(self) -> "Sandbox":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.close()
