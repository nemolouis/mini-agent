"""Archive handling tests: a hostile sdist must be refused before anything is written outside the target."""
import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from miniagent.taskgen import pypi
from miniagent.taskgen.pypi import UnsafeArchive, download, safe_extract


def make_tar(path: Path, members):
    """members: list of (name, bytes | ('link', target) | ('sym', target))"""
    with tarfile.open(path, "w:gz") as t:
        for name, body in members:
            info = tarfile.TarInfo(name)
            if isinstance(body, tuple):
                info.type = tarfile.SYMTYPE if body[0] == "sym" else tarfile.LNKTYPE
                info.linkname = body[1]
                t.addfile(info)
            else:
                info.size = len(body)
                t.addfile(info, io.BytesIO(body))
    return path


def test_a_normal_archive_is_unpacked(tmp_path):
    a = make_tar(tmp_path / "p.tar.gz", [("p-1.0/p.py", b"x = 1\n"), ("p-1.0/tests/test_p.py", b"")])
    root = safe_extract(a, tmp_path / "out")
    assert root.name == "p-1.0" and (root / "p.py").read_text() == "x = 1\n"


@pytest.mark.parametrize("members", [
    [("p-1.0/ok.py", b""), ("../escape.py", b"boom")],
    [("/etc/escape.py", b"boom")],
    [("p-1.0/a/../../escape.py", b"boom")],
    [("p-1.0/link", ("sym", "/etc/passwd"))],
    [("p-1.0/link", ("link", "p-1.0/ok.py")), ("p-1.0/ok.py", b"")],
    [("a/x.py", b""), ("b/y.py", b"")],                                           # two top-level directories
], ids=["dotdot", "absolute", "inner-dotdot", "symlink", "hardlink", "two-roots"])
def test_hostile_archives_are_refused_and_write_nothing(tmp_path, members):
    a = make_tar(tmp_path / "p.tar.gz", members)
    out = tmp_path / "out"
    with pytest.raises(UnsafeArchive):
        safe_extract(a, out)
    assert not (tmp_path / "escape.py").exists() and not Path("/etc/escape.py").exists()


def test_archives_that_are_too_big_are_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(pypi, "MAX_FILES", 3)
    a = make_tar(tmp_path / "p.tar.gz", [(f"p/{i}.py", b"") for i in range(5)])
    with pytest.raises(UnsafeArchive):
        safe_extract(a, tmp_path / "out")
    monkeypatch.setattr(pypi, "MAX_FILES", 5000)
    monkeypatch.setattr(pypi, "MAX_UNPACKED_BYTES", 10)
    with pytest.raises(UnsafeArchive):
        safe_extract(make_tar(tmp_path / "q.tar.gz", [("q/big.py", b"x" * 100)]), tmp_path / "out2")


def info(**kw):
    base = {"filename": "p-1.0.tar.gz", "url": "https://files.pythonhosted.org/packages/x/p-1.0.tar.gz", "sha256": "0" * 64, "size": 5}
    return {**base, **kw}


@pytest.mark.parametrize("url", ["http://files.pythonhosted.org/p.tar.gz", "https://evil.example/p.tar.gz",
                                 "https://files.pythonhosted.org.evil.example/p.tar.gz", "file:///etc/passwd"])
def test_only_https_pythonhosted_is_accepted(tmp_path, url):
    with pytest.raises(UnsafeArchive):
        download(info(url=url), tmp_path)


def test_oversized_declared_archives_are_refused(tmp_path):
    with pytest.raises(UnsafeArchive):
        download(info(size=pypi.MAX_ARCHIVE_BYTES + 1), tmp_path)


def test_a_wrong_checksum_deletes_the_download(tmp_path, monkeypatch):
    body = b"hello"

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(pypi.urllib.request, "urlopen", lambda *a, **k: Resp(body))
    with pytest.raises(UnsafeArchive):
        download(info(sha256="1" * 64), tmp_path)
    assert not list(tmp_path.glob("*.tar.gz"))
    path = download(info(sha256=hashlib.sha256(body).hexdigest()), tmp_path)
    assert path.read_bytes() == body
