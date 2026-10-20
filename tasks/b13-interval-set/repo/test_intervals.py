from intervals import IntervalSet


def test_add_and_merge_overlap():
    s = IntervalSet()
    s.add(1, 5)
    s.add(3, 8)
    assert s.intervals() == [(1, 8)]


def test_contains_half_open():
    s = IntervalSet([(1, 3)])
    assert 1 in s and 2 in s and 3 not in s


def test_remove_middle():
    s = IntervalSet([(0, 10)])
    s.remove(3, 5)
    assert s.intervals() == [(0, 3), (5, 10)]
