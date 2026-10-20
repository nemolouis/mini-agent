import random
from intervals import IntervalSet


def runs(ints):
    out, xs = [], sorted(ints)
    for x in xs:
        if out and out[-1][1] == x:
            out[-1] = (out[-1][0], x + 1)
        else:
            out.append((x, x + 1))
    return out


def build(rng, lo=-12, hi=30, n=6):
    ops = []
    for _ in range(n):
        a = rng.randint(lo, hi)
        b = a + rng.randint(-2, 8)
        ops.append((a, b))
    return ops


def test_adjacent_intervals_coalesce():
    s = IntervalSet()
    s.add(1, 3)
    s.add(3, 5)
    assert s.intervals() == [(1, 5)]
    s.add(7, 9)
    s.add(5, 7)
    assert s.intervals() == [(1, 9)]


def test_remove_exact_and_edges_leave_no_empty_pieces():
    s = IntervalSet([(0, 10)])
    s.remove(5, 10)
    assert s.intervals() == [(0, 5)]
    s.remove(0, 2)
    assert s.intervals() == [(2, 5)]
    s.remove(2, 5)
    assert s.intervals() == []


def test_remove_spanning_many():
    s = IntervalSet([(0, 2), (4, 6), (8, 10)])
    s.remove(1, 9)
    assert s.intervals() == [(0, 1), (9, 10)]


def test_empty_ranges_ignored():
    s = IntervalSet([(3, 3), (5, 4)])
    assert s.intervals() == []
    s.add(2, 2)
    s.remove(0, 0)
    assert s.intervals() == []


def test_total_length_is_count_of_integers():
    assert IntervalSet([(0, 3), (10, 12)]).total_length() == 5


def test_operands_unchanged():
    a, b = IntervalSet([(0, 5)]), IntervalSet([(3, 8)])
    a.union(b); a.intersection(b); a.difference(b)
    assert a.intervals() == [(0, 5)] and b.intervals() == [(3, 8)]


def test_complement_includes_trailing_gap_and_clips():
    s = IntervalSet([(2, 4), (6, 8)])
    assert s.complement(0, 10).intervals() == [(0, 2), (4, 6), (8, 10)]
    assert s.complement(3, 7).intervals() == [(4, 6)]
    assert s.complement(10, 12).intervals() == [(10, 12)]
    assert IntervalSet().complement(5, 9).intervals() == [(5, 9)]


def test_equality_semantic():
    a = IntervalSet([(0, 2), (2, 4)])
    b = IntervalSet([(0, 4)])
    assert a == b


def test_randomised_against_python_sets():
    rng = random.Random(2024)
    for _ in range(300):
        s, model = IntervalSet(), set()
        for _ in range(12):
            a = rng.randint(-12, 30)
            b = a + rng.randint(-2, 9)
            if rng.random() < 0.6:
                s.add(a, b); model |= set(range(a, b))
            else:
                s.remove(a, b); model -= set(range(a, b))
            assert s.intervals() == runs(model), (s, sorted(model))
        assert s.total_length() == len(model)
        assert all((x in s) == (x in model) for x in range(-15, 40))


def test_randomised_set_operations():
    rng = random.Random(7)
    for _ in range(300):
        def make():
            s, m = IntervalSet(), set()
            for a, b in build(rng):
                s.add(a, b); m |= set(range(a, b))
            return s, m
        (s1, m1), (s2, m2) = make(), make()
        assert s1.union(s2).intervals() == runs(m1 | m2)
        assert s1.intersection(s2).intervals() == runs(m1 & m2)
        assert s1.difference(s2).intervals() == runs(m1 - m2)
        lo, hi = sorted((rng.randint(-15, 35), rng.randint(-15, 35)))
        assert s1.complement(lo, hi).intervals() == runs(set(range(lo, hi)) - m1)
