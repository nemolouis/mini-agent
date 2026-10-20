import pytest

from seqtools import (chunked, clamp, flatten, mean, median, mode, moving_average, normalise, percentile,
                      rolling_max, run_length_decode, run_length_encode)


def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_mean_empty():
    with pytest.raises(ValueError):
        mean([])


def test_median_odd():
    assert median([5, 1, 3]) == 3


def test_median_even():
    assert median([4, 1, 3, 2]) == 2.5


def test_median_empty():
    with pytest.raises(ValueError):
        median([])


def test_mode_simple():
    assert mode([1, 2, 2, 3]) == 2


def test_mode_tie_smallest():
    assert mode([3, 1, 3, 1, 2]) == 1


def test_percentile_endpoints():
    assert percentile([10, 20, 30, 40], 0) == 10
    assert percentile([10, 20, 30, 40], 100) == 40


def test_percentile_interpolates():
    assert percentile([10, 20, 30, 40], 50) == 25
    assert percentile([1, 2, 3, 4, 5], 25) == 2


def test_percentile_unsorted_input():
    assert percentile([40, 10, 30, 20], 50) == 25


def test_percentile_bad_p():
    with pytest.raises(ValueError):
        percentile([1], 101)
    with pytest.raises(ValueError):
        percentile([1], -1)


def test_moving_average():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_moving_average_window_equals_length():
    assert moving_average([2, 4, 6], 3) == [4]


def test_moving_average_too_short():
    assert moving_average([1, 2], 3) == []


def test_moving_average_bad_window():
    with pytest.raises(ValueError):
        moving_average([1, 2], 0)


def test_run_length_encode():
    assert run_length_encode("aaabcc") == [("a", 3), ("b", 1), ("c", 2)]
    assert run_length_encode([]) == []


def test_run_length_round_trip():
    data = [1, 1, 2, 3, 3, 3, 1]
    assert run_length_decode(run_length_encode(data)) == data


def test_chunked():
    assert chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunked([], 3) == []


def test_chunked_bad_size():
    with pytest.raises(ValueError):
        chunked([1], 0)


def test_flatten():
    assert flatten([1, [2, (3, [4])], 5]) == [1, 2, 3, 4, 5]
    assert flatten(["ab", ["cd"]]) == ["ab", "cd"]


def test_rolling_max():
    assert rolling_max([1, 3, 2, 5, 4], 2) == [1, 3, 3, 5, 5]
    assert rolling_max([4, 3, 2, 1], 3) == [4, 4, 4, 3]


def test_rolling_max_bad_window():
    with pytest.raises(ValueError):
        rolling_max([1], 0)


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
    with pytest.raises(ValueError):
        clamp(1, 5, 2)


def test_normalise():
    assert normalise([2, 4, 6]) == [0.0, 0.5, 1.0]
    assert normalise([3, 3]) == [0.0, 0.0]
