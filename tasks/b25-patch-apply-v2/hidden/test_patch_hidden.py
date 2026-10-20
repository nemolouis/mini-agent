import difflib
import random
import pytest
from apply import apply_patch
from patch import PatchError


def lines(t):
    if t == "":
        return []
    return t.split("\n")[:-1] if t.endswith("\n") else t.split("\n")


def diff(a, b, n=1):
    return "\n".join(difflib.unified_diff(lines(a), lines(b), "a", "b", lineterm="", n=n))


def test_hunks_that_change_line_count():
    a = "\n".join(f"l{i}" for i in range(30)) + "\n"
    al = a.split("\n")[:-1]
    bl = al[:3] + ["new1", "new2", "new3"] + al[3:10] + al[12:20] + ["tail"] + al[20:]
    b = "\n".join(bl) + "\n"
    assert apply_patch(a, diff(a, b)) == b


def test_mismatch_raises():
    a = "one\ntwo\nthree\n"
    d = diff(a, "one\nTWO\nthree\n")
    with pytest.raises(PatchError):
        apply_patch("one\nDIFFERENT\nthree\n", d)


def test_context_mismatch_raises():
    a = "a\nb\nc\nd\n"
    d = diff(a, "a\nb\nX\nd\n")
    with pytest.raises(PatchError):
        apply_patch("a\nQ\nc\nd\n", d)


def test_patch_past_end_raises():
    a = "a\nb\nc\nd\ne\n"
    d = diff(a, "a\nb\nc\nd\nE\n")
    with pytest.raises(PatchError):
        apply_patch("a\nb\n", d)


def test_insert_into_empty():
    assert apply_patch("", diff("", "x\ny\n")) == "x\ny\n"


def test_append_at_end():
    a = "a\nb\n"
    assert apply_patch(a, diff(a, "a\nb\nc\nd\n", n=0)) == "a\nb\nc\nd\n"


def test_insert_at_start_no_context():
    a = "a\nb\n"
    assert apply_patch(a, diff(a, "z\na\nb\n", n=0)) == "z\na\nb\n"


def test_delete_everything():
    a = "a\nb\n"
    assert apply_patch(a, diff(a, "")) == ""


def test_lines_that_look_like_headers():
    a = "keep\n-- sql comment\n++ plus\nend\n"
    b = "keep\nend\n"
    assert apply_patch(a, diff(a, b)) == b
    assert apply_patch(b, diff(b, a)) == a


def test_no_trailing_newline_preserved():
    a = "a\nb\nc"
    b = "a\nB\nc"
    assert apply_patch(a, diff(a, b)) == b


def test_random_roundtrips():
    rng = random.Random(7)
    for _ in range(300):
        n = rng.randint(0, 25)
        al = [f"line {i}" if rng.random() > 0.1 else rng.choice(["-- c", "++ c", "", "  x"]) for i in range(n)]
        bl = []
        for l in al:
            r = rng.random()
            if r < 0.15:
                continue
            bl.append(l if r > 0.3 else l + "!")
            if rng.random() < 0.15:
                bl.extend(f"ins{rng.randint(0, 99)}" for _ in range(rng.randint(1, 3)))
        if rng.random() < 0.2:
            bl.append("end")
        a = "".join(l + "\n" for l in al)
        b = "".join(l + "\n" for l in bl)
        ctx = rng.choice([0, 1, 2, 3])
        assert apply_patch(a, diff(a, b, n=ctx)) == b, (a, b, ctx)
