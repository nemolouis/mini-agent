from datetime import datetime
from slots import find_slot


def test_empty_calendar_starts_at_work_start():
    assert find_slot({}, 30, datetime(2024, 9, 2, 8, 0)) == datetime(2024, 9, 2, 9, 0)


def test_skips_busy():
    busy = {"a": [(datetime(2024, 9, 2, 9, 0), datetime(2024, 9, 2, 10, 0))]}
    assert find_slot(busy, 30, datetime(2024, 9, 2, 8, 0)) == datetime(2024, 9, 2, 10, 0)
