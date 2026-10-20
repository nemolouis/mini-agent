import random
import time
from difflib_lite import diff


def lcs_len(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def rebuild(ops):
    return [x for o, x in ops if o in "=-"], [x for o, x in ops if o in "=+"]


def runs_ordered(ops):
    i = 0
    while i < len(ops):
        if ops[i][0] == "=":
            i += 1
            continue
        j = i
        while j < len(ops) and ops[j][0] != "=":
            j += 1
        kinds = [o for o, _ in ops[i:j]]
        if "-" in kinds and "+" in kinds:
            if kinds.index("+") < len(kinds) - 1 - kinds[::-1].index("-"):
                return False
        i = j
    return True


def test_classic_non_greedy_case():
    a, b = list("ABCABBA"), list("CBABAC")
    ops = diff(a, b)
    assert rebuild(ops) == (a, b)
    assert sum(1 for o, _ in ops if o == "=") == lcs_len(a, b) == 4


def test_greedy_trap():
    a, b = list("xaaaab"), list("aaaabx")
    ops = diff(a, b)
    assert sum(1 for o, _ in ops if o == "=") == 5


def test_randomised_minimal_and_valid():
    rng = random.Random(5)
    for _ in range(400):
        a = [rng.choice("abcd") for _ in range(rng.randint(0, 22))]
        b = [rng.choice("abcd") for _ in range(rng.randint(0, 22))]
        ops = diff(a, b)
        assert rebuild(ops) == (a, b), (a, b, ops)
        assert sum(1 for o, _ in ops if o == "=") == lcs_len(a, b), (a, b, ops)
        assert runs_ordered(ops), (a, b, ops)
        assert all(o in ("=", "-", "+") for o, _ in ops)


def test_deletions_before_insertions_explicit():
    ops = diff(["x"], ["y"])
    assert ops == [("-", "x"), ("+", "y")]
    ops = diff(list("axb"), list("ayzb"))
    assert ops == [("=", "a"), ("-", "x"), ("+", "y"), ("+", "z"), ("=", "b")]


def test_non_string_items():
    a, b = [(1, 2), (3, 4), None, 5], [(3, 4), 5, (1, 2)]
    ops = diff(a, b)
    assert rebuild(ops) == (a, b)
    assert sum(1 for o, _ in ops if o == "=") == lcs_len(a, b)


def test_large_with_few_changes_is_fast():
    n = 6000
    a = [f"line {i}" for i in range(n)]
    b = a[:]
    b[10] = "changed"
    del b[2000]
    b.insert(3500, "inserted")
    b[5990] = "tail edit"
    t0 = time.perf_counter()
    ops = diff(a, b)
    assert time.perf_counter() - t0 < 2.0
    assert rebuild(ops) == (a, b)
    # three original lines are gone from b (replaced, deleted, replaced) -> 5997 kept
    assert sum(1 for o, _ in ops if o == "=") == 5997


def test_large_completely_different_is_ok():
    a = [f"a{i}" for i in range(500)]
    b = [f"b{i}" for i in range(500)]
    t0 = time.perf_counter()
    ops = diff(a, b)
    assert time.perf_counter() - t0 < 6.0
    assert sum(1 for o, _ in ops if o == "=") == 0 and len(ops) == 1000
