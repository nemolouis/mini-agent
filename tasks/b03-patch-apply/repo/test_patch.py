import difflib
import pytest
from apply import apply_patch
from patch import PatchError


def lines(t):
    return t.split("\n")[:-1] if t.endswith("\n") else t.split("\n")


def diff(a, b, n=1):
    return "\n".join(difflib.unified_diff(lines(a), lines(b), "a", "b", lineterm="", n=n))


def test_single_hunk():
    a, b = "one\ntwo\nthree\n", "one\nTWO\nthree\n"
    assert apply_patch(a, diff(a, b)) == b


def test_two_hunks_same_size():
    a = "\n".join(f"l{i}" for i in range(20)) + "\n"
    b = a.replace("l2\n", "L2\n").replace("l15\n", "L15\n")
    assert apply_patch(a, diff(a, b)) == b
