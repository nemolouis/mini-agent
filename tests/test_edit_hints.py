import pytest

from miniagent.tools import ToolError, Workspace

SRC = "def f(x):\n    if x > 1:\n        return x\n    return 0\n\ndef g(x):\n    if x > 1:\n        return -x\n"


def ws(tmp_path, hints):
    (tmp_path / "a.py").write_text(SRC)
    return Workspace(tmp_path, edit_hints=hints)


def err(w, **a):
    with pytest.raises(ToolError) as e:
        w.edit_file({"path": "a.py", **a})
    return str(e.value)


def test_default_messages_unchanged(tmp_path):
    w = ws(tmp_path, False)
    assert err(w, old_string="zzz", new_string="y") == "old_string not found (must match exactly, including whitespace)"
    assert err(w, old_string="x", new_string="x") == "old_string and new_string are identical"
    assert err(w, old_string="if x > 1:", new_string="y") == "old_string matches 2 places; include more context to make it unique"
    with pytest.raises(ToolError) as e:
        w.edit_file({"path": "b.py", "old_string": "a", "new_string": "b"})
    assert str(e.value) == "not a file: b.py"


def test_not_found_shows_closest_real_lines(tmp_path):
    w = ws(tmp_path, True)
    m = err(w, old_string="def g(x):\n    if x >= 1:\n        return -x", new_string="y")
    assert "closest match" in m and "lines 6-8" in m and "if x > 1:" in m


def test_whitespace_only_difference_is_named(tmp_path):
    w = ws(tmp_path, True)
    m = err(w, old_string="def f(x):\n  if x > 1:\n      return x", new_string="y")
    assert "only in indentation" in m and "lines 1-3" in m


def test_unrelated_text_says_to_read_first(tmp_path):
    assert "read_file it first" in err(ws(tmp_path, True), old_string="qqqq wwww eeee\nrrrr", new_string="y")


def test_ambiguous_lists_line_numbers(tmp_path):
    assert "at lines 2, 7" in err(ws(tmp_path, True), old_string="if x > 1:", new_string="y")


def test_identical_and_missing_file(tmp_path):
    w = ws(tmp_path, True)
    assert "nothing would change" in err(w, old_string="x", new_string="x")
    with pytest.raises(ToolError) as e:
        w.edit_file({"path": "aa.py", "old_string": "a", "new_string": "b"})
    assert "Did you mean: a.py" in str(e.value)


def test_success_unchanged_and_file_untouched_on_error(tmp_path):
    w = ws(tmp_path, True)
    err(w, old_string="nope", new_string="y")
    assert (tmp_path / "a.py").read_text() == SRC
    assert w.edit_file({"path": "a.py", "old_string": "return 0", "new_string": "return 1"}) == "edited a.py"
