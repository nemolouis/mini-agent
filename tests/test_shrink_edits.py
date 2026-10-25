import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("shrink_edits", Path(__file__).parent.parent / "scripts" / "shrink_edits.py")
se = importlib.util.module_from_spec(spec)
spec.loader.exec_module(se)

T = "def f(x):\n    if x > 1:\n        return x\n    return 0\n\ndef g(x):\n    if x > 1:\n        return -x\n    return 1\n"


def apply(text, o, n):
    assert text.count(o) == 1
    return text.replace(o, n, 1)


def test_keeps_only_changed_line_when_unique():
    old = "    return 0\n\ndef g(x):\n    if x > 1:"
    new = "    return 0\n\ndef g(x):\n    if x >= 1:"
    o, n = se.shrink(T, old, new)
    assert (o, n) == ("    if x > 1:", "    if x >= 1:") or T.count(o) == 1
    assert apply(T, o, n) == apply(T, old, new)


def test_adds_context_until_unique_and_stays_inside_original():
    old = "def f(x):\n    if x > 1:\n        return x"
    new = "def f(x):\n    if x >= 1:\n        return x"
    o, n = se.shrink(T, old, new)
    assert o == "def f(x):\n    if x > 1:" and old.startswith(o)
    assert apply(T, o, n) == apply(T, old, new)


def test_pure_insertion_keeps_an_anchor_line():
    old, new = "    return 0\n", "    return 0\n    # note\n"
    o, n = se.shrink(T, old, new)
    assert o and apply(T, o, n) == apply(T, old, new)


def test_cannot_shrink_below_original():
    old, new = "    if x > 1:\n        return x", "    if x > 1:\n        return x + 1"
    o, n = se.shrink(T, old, new)
    assert T.count(o) == 1 and apply(T, o, n) == apply(T, old, new)


def test_the_equality_check_catches_a_non_unique_snippet():
    # what the script's check compares: a non-unique shrink would NOT reproduce the teacher's edit
    old, new = "def g(x):\n    if x > 1:", "def g(x):\n    if x >= 1:"
    bad_o, bad_n = "    if x > 1:", "    if x >= 1:"
    assert T.count(bad_o) == 2
    o, n = se.shrink(T, old, new)
    assert T.count(o) == 1 and o != bad_o
