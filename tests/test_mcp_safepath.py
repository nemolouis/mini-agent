"""The confinement rules of the notes server: every escape we could think of, against real filesystem objects."""
import os
import subprocess
import sys
import threading

import pytest

from miniagent.mcp import safepath
from miniagent.mcp.safepath import Denied, Scan, TooLarge, clean_text, make_policy, open_dir, open_file, read_all, validate_rel


@pytest.fixture
def box(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    for d in (root / "sub" / "deep", root / ".git", outside):
        d.mkdir(parents=True)
    (root / "a.md").write_text("alpha\n")
    (root / "sub" / "b.md").write_text("bravo\n")
    (root / "sub" / "deep" / "c.txt").write_text("charlie\n")
    (root / ".hidden.md").write_text("hidden\n")
    (root / ".git" / "config.md").write_text("gitconfig\n")
    (root / "data.bin").write_bytes(b"\x00\x01")
    (root / "key.pem").write_text("-----BEGIN PRIVATE KEY-----")
    (root / "big.md").write_text("x" * 500)
    (outside / "secret.md").write_text("TOPSECRET\n")
    os.symlink(outside / "secret.md", root / "link_file.md")
    os.symlink(outside, root / "link_dir")
    os.symlink(root / "l2.md", root / "l1.md")
    os.symlink(outside / "secret.md", root / "l2.md")
    os.link(outside / "secret.md", root / "hard.md")
    os.mkfifo(root / "fifo.md")
    return make_policy(root, max_file_bytes=200), root, outside


def read(policy, rel):
    parts = validate_rel(policy, rel)
    fd = open_file(policy, parts)
    try:
        return read_all(fd, policy.max_file_bytes).decode()
    finally:
        os.close(fd)


def test_legitimate_reads(box):
    p, _, _ = box
    assert read(p, "a.md") == "alpha\n"
    assert read(p, "sub/b.md") == "bravo\n"
    assert read(p, "sub/deep/c.txt") == "charlie\n"
    assert read(p, "SUB/B.MD".lower()) == "bravo\n"


BAD_PATHS = [
    "../outside/secret.md", "sub/../../outside/secret.md", "/etc/passwd", "/abs/a.md", "~/a.md", "~", "", ".", "..",
    "a/../a.md", "sub//b.md", "./a.md", "sub/./b.md", "a.md\x00.txt", "C:\\x.md", "C:/x.md", "..\\x.md", "sub\\b.md",
    ".hidden.md", ".git/config.md", ".GIT/config.md", ".Env", "sub/.secret.md", "id_rsa.md", "ID_RSA.md",
    "known_hosts.md", "x" * 600 + ".md", "/".join(["d"] * 20) + ".md", "a\nb.md", "a\tb.md", "a\x1b[31m.md",
    123, None, ["a.md"], {"p": "a.md"}, b"a.md",
]


@pytest.mark.parametrize("rel", BAD_PATHS, ids=[repr(p)[:30] for p in BAD_PATHS])
def test_bad_paths_are_denied(box, rel):
    p, _, _ = box
    with pytest.raises(Denied):
        validate_rel(p, rel)


def test_empty_subdir_is_allowed_only_where_asked(box):
    p, _, _ = box
    assert validate_rel(p, "", allow_empty=True) == [] and validate_rel(p, ".", allow_empty=True) == []
    with pytest.raises(Denied):
        validate_rel(p, "..", allow_empty=True)


def test_no_url_decoding(box):
    p, root, _ = box
    with pytest.raises(Denied):
        read(p, "%2e%2e/outside/secret.md")           # would be ../ if it were decoded
    (root / "%2e%2e").mkdir()
    (root / "%2e%2e" / "x.md").write_text("literal\n")
    assert read(p, "%2e%2e/x.md") == "literal\n"      # it is simply a directory with an odd name


@pytest.mark.parametrize("rel", ["link_file.md", "l1.md", "link_dir/secret.md", "hard.md", "data.bin",
                                 "key.pem", "nope.md", "sub", "sub/missing.md", "a.md/x.md"])
def test_escapes_and_non_notes_are_denied(box, rel):
    p, _, _ = box
    result = {}

    def attempt():
        try:
            read(p, rel)
            result["ok"] = True
        except Denied:
            result["denied"] = True

    t = threading.Thread(target=attempt, daemon=True)
    t.start()
    t.join(5)
    assert not t.is_alive(), "reading hung (a FIFO must not block the server)"
    assert result == {"denied": True}


def test_fifo_is_denied_and_never_blocks(box):
    """Run in a subprocess with a timeout: a regression here must fail the test, not hang the whole run."""
    _, root, _ = box
    code = ("import sys\nfrom miniagent.mcp import safepath\n"
            "p = safepath.make_policy(sys.argv[1])\n"
            "try:\n    safepath.open_file(p, ['fifo.md'])\nexcept safepath.Denied:\n    print('denied')\n")
    r = subprocess.run([sys.executable, "-c", code, str(root)], capture_output=True, text=True, timeout=15)
    assert r.stdout.strip() == "denied", r.stderr


def test_oversize_note_is_refused_with_a_specific_error(box):
    p, _, _ = box
    with pytest.raises(TooLarge):
        read(p, "big.md")


def test_toctou_file_swapped_for_a_symlink_just_before_open(box):
    p, root, outside = box

    def swap():
        (root / "a.md").unlink()
        os.symlink(outside / "secret.md", root / "a.md")

    safepath._before_final_open = swap
    try:
        with pytest.raises(Denied):
            read(p, "a.md")
    finally:
        safepath._before_final_open = None


def test_toctou_directory_swapped_after_it_was_opened_cannot_redirect(box):
    p, root, outside = box
    (outside / "b.md").write_text("TOPSECRET-B\n")

    def swap():
        os.rename(root / "sub", root / "sub_old")
        os.symlink(outside, root / "sub")                # `sub` now points outside

    safepath._before_final_open = swap
    try:
        assert read(p, "sub/b.md") == "bravo\n"           # we hold the original directory by fd: still the inside file
    finally:
        safepath._before_final_open = None


def test_root_may_itself_be_a_symlink(box, tmp_path):
    p, root, _ = box
    os.symlink(root, tmp_path / "rootlink")
    q = make_policy(tmp_path / "rootlink", max_file_bytes=200)
    assert read(q, "a.md") == "alpha\n"
    with pytest.raises(Denied):
        read(q, "link_file.md")


def test_append_creates_inside_and_refuses_symlinks(box):
    p, root, outside = box
    fd = open_file(p, ["fresh.md"], write=True)
    os.write(fd, b"hello\n")
    os.close(fd)
    assert (root / "fresh.md").read_text() == "hello\n"
    with pytest.raises(Denied):
        open_file(p, ["link_file.md"], write=True)
    assert (outside / "secret.md").read_text() == "TOPSECRET\n"          # untouched
    os.symlink(outside / "new_target.md", root / "dangling.md")
    with pytest.raises(Denied):
        open_file(p, ["dangling.md"], write=True)                          # O_CREAT must not follow it
    assert not (outside / "new_target.md").exists()
    with pytest.raises(Denied):
        open_file(p, ["no_such_dir", "x.md"], write=True)                  # directories are never created
    with pytest.raises(Denied):
        open_file(p, ["fifo.md"], write=True)


def test_scan_lists_only_real_notes_sorted(box):
    p, _, _ = box
    got = [rel for rel, fd, size in Scan(p, [])]
    assert got == ["a.md", "sub/b.md", "sub/deep/c.txt"]      # no hidden, symlink, hard link, fifo, .bin, .pem, oversize
    assert [rel for rel, _, _ in Scan(p, ["sub"])] == ["sub/b.md", "sub/deep/c.txt"]


def test_scan_with_open_files_gives_closable_fds(box):
    p, _, _ = box
    seen = {}
    for rel, fd, size in Scan(p, [], open_files=True):
        try:
            seen[rel] = read_all(fd, 1000)
        finally:
            os.close(fd)
    assert seen == {"a.md": b"alpha\n", "sub/b.md": b"bravo\n", "sub/deep/c.txt": b"charlie\n"}


def test_scan_limits(box):
    p, root, _ = box
    s = Scan(make_policy(root, max_file_bytes=200, max_files=2), [])
    assert len(list(s)) == 2 and s.truncated
    s = Scan(make_policy(root, max_file_bytes=200, max_depth=1), [])
    assert [r for r, _, _ in s] == ["a.md", "sub/b.md"] and s.truncated       # sub/deep is too deep
    s = Scan(p, [], deadline=0.0)
    assert list(s) == [] and s.truncated


def test_scan_does_not_descend_into_symlinked_directories(box):
    p, root, outside = box
    (outside / "x.md").write_text("outside\n")
    assert all(not rel.startswith("link_dir") for rel, _, _ in Scan(p, []))
    with pytest.raises(Denied):
        list(Scan(p, ["link_dir"]))


def test_clean_text():
    assert clean_text("a\x1b[31mred\x1b[0m\x00b\x07c\n\td") == "aredbc\n\td"
