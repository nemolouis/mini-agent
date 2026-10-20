from stats import moving_average

def test_basic():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]

def test_full_window():
    assert moving_average([2, 4], 2) == [3.0]

def test_too_short():
    assert moving_average([1], 3) == []
