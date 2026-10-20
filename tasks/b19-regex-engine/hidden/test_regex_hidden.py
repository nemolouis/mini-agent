import random
import re
import pytest
from regex import RegexError, fullmatch, search


def test_alternation_and_groups():
    assert fullmatch("a|b", "b") and not fullmatch("a|b", "ab")
    assert fullmatch("(ab)+c", "ababc") and not fullmatch("(ab)+c", "abac")
    assert fullmatch("(a|b)*c", "abbac")
    assert fullmatch("a(b|)c", "ac") and fullmatch("a(b|)c", "abc")
    assert fullmatch("", "") and not fullmatch("", "a")
    assert fullmatch("()", "") and fullmatch("a||b", "")


def test_search_preference_order():
    assert search("a|ab", "xab") == (1, 2)          # first alternative wins, not the longest
    assert search("a*", "baaa") == (0, 0)           # leftmost match is the empty match at 0
    assert search("a+", "baaa") == (1, 4)
    assert search("(a|ab)(c|bcd)", "abcd") == (0, 4)


def test_anchors():
    assert search("^b", "ab") is None and search("^a", "ab") == (0, 1)
    assert search("b$", "ab") == (1, 2) and search("a$", "ab") is None
    assert fullmatch("^ab$", "ab")
    assert search("^$", "") == (0, 0)
    assert search("a|^b", "cb") is None


def test_escapes():
    assert fullmatch("a\\.b", "a.b") and not fullmatch("a\\.b", "axb")
    assert fullmatch("\\(x\\)", "(x)")
    assert fullmatch("a\\*", "a*") and fullmatch("\\\\", "\\")
    assert fullmatch("\\|", "|")


def test_dot_matches_newline():
    assert fullmatch("a.b", "a\nb")


def test_empty_body_repetition_terminates():
    assert fullmatch("(a*)*", "aaa")
    assert fullmatch("(a*)+b", "aab")
    assert search("(|a)+", "aa") is not None


@pytest.mark.parametrize("bad", ["(", ")", "a)", "(a", "*a", "a|*", "(*a)", "a**", "a+*", "a\\", "+", "?a"])
def test_errors(bad):
    with pytest.raises(RegexError):
        fullmatch(bad, "a")
    with pytest.raises(RegexError):
        search(bad, "a")


# ---- differential testing against Python's re (same leftmost / preference semantics) ----

def gen(rng, depth=0):
    def atom():
        r = rng.random()
        if r < 0.55 or depth >= 3:
            return rng.choice(["a", "b", "."])
        return "(" + gen(rng, depth + 1) + ")"

    def piece():
        a = atom()
        r = rng.random()
        if r < 0.2:
            return a + "*"
        if r < 0.32:
            return a + "+"
        if r < 0.42:
            return a + "?"
        return a

    def branch():
        return "".join(piece() for _ in range(rng.randint(0, 4)))

    return "|".join(branch() for _ in range(rng.choice([1, 1, 1, 2, 3])))


def oracle_pattern(p):
    return p.replace("$", "\\Z")


def test_differential_search_and_fullmatch_against_re():
    rng = random.Random(1234)
    texts = ["", "a", "b", "ab", "ba", "aab", "abab", "bbb", "aaaa", "abba", "babab", "aabbaa"]
    n = 0
    for _ in range(500):
        p = gen(rng)
        if rng.random() < 0.15:
            p = "^" + p
        if rng.random() < 0.15:
            p = p + "$"
        try:
            rx = re.compile(oracle_pattern(p), re.DOTALL)
        except re.error:
            continue
        for t in texts:
            m = rx.search(t)
            want = None if m is None else m.span()
            assert search(p, t) == want, (p, t, search(p, t), want)
            assert fullmatch(p, t) == (rx.fullmatch(t) is not None), (p, t)
            n += 1
    assert n > 3000
