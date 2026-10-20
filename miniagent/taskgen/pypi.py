"""Fetch source distributions from PyPI without running anything from them.

* metadata comes from the JSON API of pypi.org; the archive URL must be https on files.pythonhosted.org;
* the download is size-capped and checked against the sha256 that PyPI publishes;
* extraction refuses links, devices, absolute paths, `..` and archives that are too big, and nothing is imported
  or executed on the host (the packages' tests run later, inside the sandbox).
"""
from __future__ import annotations

import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_HOST = "files.pythonhosted.org"
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_UNPACKED_BYTES = 80 * 1024 * 1024
MAX_FILES = 5000


class UnsafeArchive(Exception):
    pass


def release_info(name: str, version: str) -> dict:
    """{name, version, filename, url, sha256, size, license} of the sdist of one exact release."""
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=30) as r:
        d = json.load(r)
    sdists = [u for u in d["urls"] if u["packagetype"] == "sdist"]
    if not sdists:
        raise ValueError(f"{name}=={version} has no sdist")
    u = sdists[0]
    return {"name": name, "version": version, "filename": u["filename"], "url": u["url"], "sha256": u["digests"]["sha256"],
            "size": u["size"], "license": d["info"].get("license_expression") or d["info"].get("license") or ""}


def download(info: dict, dest_dir: Path) -> Path:
    url = urlparse(info["url"])
    if url.scheme != "https" or url.hostname != ALLOWED_HOST:
        raise UnsafeArchive(f"refusing to download from {info['url']}")
    if info["size"] > MAX_ARCHIVE_BYTES:
        raise UnsafeArchive(f"{info['filename']} is {info['size']} bytes")
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / Path(info["filename"]).name
    h, n = hashlib.sha256(), 0
    with urllib.request.urlopen(info["url"], timeout=60) as r, path.open("wb") as f:
        while chunk := r.read(65536):
            n += len(chunk)
            if n > MAX_ARCHIVE_BYTES:
                raise UnsafeArchive("download is larger than allowed")
            h.update(chunk)
            f.write(chunk)
    if h.hexdigest() != info["sha256"] or n != info["size"]:
        path.unlink()
        raise UnsafeArchive(f"{info['filename']}: sha256/size do not match what PyPI published")
    return path


def safe_extract(archive: Path, dest: Path) -> Path:
    """Unpack a .tar.gz into `dest` and return the single top-level directory."""
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    total, count = 0, 0
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        for m in members:
            count += 1
            total += max(m.size, 0)
            if m.issym() or m.islnk() or m.isdev() or m.isfifo():
                raise UnsafeArchive(f"{m.name}: links and special files are not allowed")
            p = Path(m.name)
            if p.is_absolute() or ".." in p.parts or not (dest / p).resolve().is_relative_to(dest):
                raise UnsafeArchive(f"{m.name}: path leaves the target directory")
        if count > MAX_FILES or total > MAX_UNPACKED_BYTES:
            raise UnsafeArchive(f"archive too large ({count} members, {total} bytes)")
        tar.extractall(dest, members=members, filter="data")
    tops = {Path(m.name).parts[0] for m in members if m.name not in ("", ".")}
    if len(tops) != 1:
        raise UnsafeArchive(f"expected one top-level directory, found {sorted(tops)}")
    return dest / tops.pop()
