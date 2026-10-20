import random
from datetime import datetime, timedelta
import pytest
from slots import find_slot


def D(*a):
    return datetime(*a)


def test_touching_boundaries_allowed():
    busy = {"a": [(D(2024, 9, 2, 9, 0), D(2024, 9, 2, 10, 0)), (D(2024, 9, 2, 10, 30), D(2024, 9, 2, 12, 0))]}
    assert find_slot(busy, 30, D(2024, 9, 2, 8, 0)) == D(2024, 9, 2, 10, 0)
    assert find_slot(busy, 35, D(2024, 9, 2, 8, 0)) == D(2024, 9, 2, 12, 0)


def test_must_end_by_work_end():
    busy = {"a": [(D(2024, 9, 2, 9, 0), D(2024, 9, 2, 16, 30))]}
    assert find_slot(busy, 30, D(2024, 9, 2, 8, 0)) == D(2024, 9, 2, 16, 30)
    assert find_slot(busy, 35, D(2024, 9, 2, 8, 0)) == D(2024, 9, 3, 9, 0)


def test_weekends_skipped():
    assert find_slot({}, 60, D(2024, 9, 6, 16, 30)) == D(2024, 9, 9, 9, 0)     # Friday late -> Monday
    assert find_slot({}, 60, D(2024, 9, 7, 10, 0)) == D(2024, 9, 9, 9, 0)      # Saturday


def test_after_rounds_up_to_grid():
    assert find_slot({}, 30, D(2024, 9, 2, 10, 1)) == D(2024, 9, 2, 10, 5)
    assert find_slot({}, 30, D(2024, 9, 2, 10, 5, 0, 1)) == D(2024, 9, 2, 10, 10)
    assert find_slot({}, 30, D(2024, 9, 2, 10, 5)) == D(2024, 9, 2, 10, 5)


def test_multiple_people_all_must_be_free():
    busy = {"a": [(D(2024, 9, 2, 9, 0), D(2024, 9, 2, 10, 0))],
            "b": [(D(2024, 9, 2, 10, 0), D(2024, 9, 2, 11, 15))],
            "c": []}
    assert find_slot(busy, 60, D(2024, 9, 2, 0, 0)) == D(2024, 9, 2, 11, 15)


def test_busy_spanning_days_and_empty_intervals_ignored():
    busy = {"a": [(D(2024, 9, 2, 12, 0), D(2024, 9, 4, 11, 0)), (D(2024, 9, 5, 9, 0), D(2024, 9, 5, 9, 0))]}
    assert find_slot(busy, 30, D(2024, 9, 2, 9, 0)) == D(2024, 9, 2, 9, 0)
    assert find_slot(busy, 180, D(2024, 9, 2, 9, 0)) == D(2024, 9, 2, 9, 0)      # ends exactly at 12:00
    assert find_slot(busy, 185, D(2024, 9, 2, 9, 0)) == D(2024, 9, 4, 11, 0)


def test_custom_working_hours_and_horizon():
    assert find_slot({}, 60, D(2024, 9, 2, 0, 0), work_start=7, work_end=15) == D(2024, 9, 2, 7, 0)
    full = {"a": [(D(2024, 9, 2), D(2024, 9, 20))]}
    assert find_slot(full, 30, D(2024, 9, 2, 8), horizon_days=7) is None
    assert find_slot(full, 30, D(2024, 9, 2, 8), horizon_days=30) == D(2024, 9, 20, 9, 0)


def test_duration_validation_and_too_long():
    for bad in (0, -5, 7, 12):
        with pytest.raises(ValueError):
            find_slot({}, bad, D(2024, 9, 2))
    assert find_slot({}, 9 * 60, D(2024, 9, 2)) is None        # longer than the working day


def _oracle(busy, dur, after, ws=9, we=17, horizon=60):
    ivs = [iv for v in busy.values() for iv in v if iv[0] < iv[1]]
    t = after.replace(second=0, microsecond=0)
    if t < after or t.minute % 5:
        t += timedelta(minutes=1)
        while t.minute % 5:
            t += timedelta(minutes=1)
    t = t.replace(second=0, microsecond=0)
    end_date = after.date() + timedelta(days=horizon)
    d = timedelta(minutes=dur)
    while t.date() <= end_date:
        day_open = t.replace(hour=ws, minute=0)
        day_close = t.replace(hour=we, minute=0)
        if t.weekday() < 5 and day_open <= t and t + d <= day_close:
            if all(not (s < t + d and t < e) for s, e in ivs):
                return t
        t += timedelta(minutes=5)
    return None


def test_randomised_against_bruteforce():
    rng = random.Random(17)
    for _ in range(80):
        base = D(2024, 9, 2) + timedelta(days=rng.randint(0, 20))
        busy = {}
        for p in range(rng.randint(1, 4)):
            ivs = []
            for _ in range(rng.randint(0, 12)):
                s = D(base.year, base.month, base.day) + timedelta(days=rng.randint(0, 6),
                                                                  minutes=5 * rng.randint(0, 288))
                ivs.append((s, s + timedelta(minutes=5 * rng.randint(0, 40))))
            busy[f"p{p}"] = ivs
        after = base + timedelta(minutes=rng.randint(0, 24 * 60))
        dur = 5 * rng.randint(1, 30)
        got = find_slot(busy, dur, after, horizon_days=30)
        want = _oracle(busy, dur, after, horizon=30)
        assert got == want, (busy, dur, after, got, want)
