import random
from datetime import datetime, timedelta
import pytest
from cron import next_after

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]


def N(expr, *dt):
    return next_after(expr, datetime(*dt))


def test_dom_or_dow_when_both_restricted():
    # the 13th OR any Friday
    assert N("0 0 13 * 5", 2024, 9, 1) == datetime(2024, 9, 6)       # Friday
    assert N("0 0 13 * 5", 2024, 9, 7) == datetime(2024, 9, 13)      # 13th (also a Friday)
    assert N("0 0 13 * 5", 2024, 9, 14) == datetime(2024, 9, 20)     # Friday
    assert N("0 0 13 * 1", 2024, 9, 9) == datetime(2024, 9, 13)      # 13th beats next Monday (16th)


def test_only_one_restricted_means_and():
    assert N("0 0 * * 1", 2024, 9, 2) == datetime(2024, 9, 9)
    assert N("0 0 15 * *", 2024, 9, 16) == datetime(2024, 10, 15)


def test_star_step_counts_as_restricted():
    # day-of-month */2 is restricted, day-of-week 1 restricted -> OR
    assert N("0 0 */2 * 1", 2024, 9, 2, 12) == datetime(2024, 9, 3)  # odd dom 3rd matches */2 (1,3,5..)


def test_sunday_zero_and_seven():
    assert N("0 0 * * 0", 2024, 9, 2) == datetime(2024, 9, 8)
    assert N("0 0 * * 7", 2024, 9, 2) == datetime(2024, 9, 8)
    assert N("0 0 * * SUN", 2024, 9, 2) == datetime(2024, 9, 8)
    assert N("0 0 * * 6-7", 2024, 9, 2) == datetime(2024, 9, 7)


def test_names_and_ranges():
    assert N("0 9 * * MON-FRI", 2024, 9, 6, 9, 0) == datetime(2024, 9, 9, 9, 0)
    assert N("0 0 1 jan,JUN *", 2024, 2, 1) == datetime(2024, 6, 1)
    assert N("0 0 1 mar-may *", 2024, 5, 2) == datetime(2025, 3, 1)


def test_steps_on_ranges_and_single_values():
    assert N("10-40/10 * * * *", 2024, 1, 1, 5, 0) == datetime(2024, 1, 1, 5, 10)
    assert N("10-40/10 * * * *", 2024, 1, 1, 5, 40) == datetime(2024, 1, 1, 6, 10)
    assert N("5/20 * * * *", 2024, 1, 1, 5, 6) == datetime(2024, 1, 1, 5, 25)
    assert N("5/20 * * * *", 2024, 1, 1, 5, 46) == datetime(2024, 1, 1, 6, 5)
    assert N("0 0-23/6 * * *", 2024, 1, 1, 7) == datetime(2024, 1, 1, 12)


def test_lists_combined():
    assert N("0,30 8,20 * * *", 2024, 1, 1, 8, 30) == datetime(2024, 1, 1, 20, 0)


def test_leap_day_found_quickly():
    assert N("0 0 29 2 *", 2025, 3, 1) == datetime(2028, 2, 29)
    assert N("0 0 29 2 *", 2096, 3, 1) == datetime(2104, 2, 29)   # 2100 is not a leap year
    assert N("30 4 29 FEB *", 2024, 2, 29, 4, 30) == datetime(2028, 2, 29, 4, 30)


def test_impossible_raises():
    with pytest.raises(ValueError):
        N("0 0 30 2 *", 2024, 1, 1)
    with pytest.raises(ValueError):
        N("0 0 31 4 *", 2024, 1, 1)


@pytest.mark.parametrize("expr", ["60 * * * *", "* 24 * * *", "* * 0 * *", "* * * 13 *", "* * * * 8",
                                  "5-1 * * * *", "*/0 * * * *", "a * * * *", "* * * * * *", "", "1,,2 * * * *",
                                  "* * * FOO *", "-5 * * * *"])
def test_invalid_expressions(expr):
    with pytest.raises(ValueError):
        N(expr, 2024, 1, 1)


def test_seconds_are_ignored_and_truncated():
    assert next_after("* * * * *", datetime(2024, 1, 1, 0, 0, 59, 999)) == datetime(2024, 1, 1, 0, 1)
    assert next_after("30 0 * * *", datetime(2024, 1, 1, 0, 30, 5)) == datetime(2024, 1, 2, 0, 30)


def test_year_and_month_rollover():
    assert N("59 23 31 12 *", 2024, 12, 31, 23, 59) == datetime(2025, 12, 31, 23, 59)
    assert N("0 0 1 1 *", 2024, 12, 31, 23, 59) == datetime(2025, 1, 1)


# ---- differential test against an independent brute-force oracle -------------------------

def _expand(item, lo, hi):
    step = 1
    if "/" in item:
        item, s = item.split("/")
        step = int(s)
    if item == "*":
        a, b = lo, hi
    elif "-" in item:
        a, b = map(int, item.split("-"))
    else:
        a, b = int(item), (hi if step != 1 or False else int(item))
    return set(range(a, b + 1, step))


def _field(text, lo, hi):
    out = set()
    for it in text.split(","):
        if "/" in it and "-" not in it.split("/")[0] and it.split("/")[0] != "*":
            a = int(it.split("/")[0]); s = int(it.split("/")[1])
            out |= set(range(a, hi + 1, s))
        else:
            out |= _expand(it, lo, hi)
    return out


def _oracle_match(expr, t):
    m, h, dom, mon, dow = expr.split()
    ms, hs = _field(m, 0, 59), _field(h, 0, 23)
    doms, mons = _field(dom, 1, 31), _field(mon, 1, 12)
    dows = {d % 7 for d in _field(dow, 0, 7)}
    if t.minute not in ms or t.hour not in hs or t.month not in mons:
        return False
    d_ok, w_ok = t.day in doms, (t.weekday() + 1) % 7 in dows
    return (d_ok or w_ok) if (dom != "*" and dow != "*") else (d_ok and w_ok)


def _rand_field(rng, lo, hi, names=None):
    kind = rng.random()
    if kind < 0.25:
        return "*"
    if kind < 0.4:
        return f"*/{rng.randint(1, max(2, (hi - lo) // 2))}"
    parts = []
    for _ in range(rng.randint(1, 3)):
        r = rng.random()
        a = rng.randint(lo, hi)
        if r < 0.5:
            parts.append(str(a))
        elif r < 0.8:
            b = rng.randint(a, hi)
            parts.append(f"{a}-{b}")
        else:
            parts.append(f"{a}/{rng.randint(1, 10)}")
    return ",".join(parts)


def test_randomised_against_bruteforce():
    rng = random.Random(99)
    checked = 0
    for _ in range(120):
        expr = " ".join([_rand_field(rng, 0, 59), _rand_field(rng, 0, 23), _rand_field(rng, 1, 28),
                         _rand_field(rng, 1, 12), _rand_field(rng, 0, 6)])
        start = datetime(2023, 1, 1) + timedelta(minutes=rng.randint(0, 60 * 24 * 700))
        got = next_after(expr, start)
        t = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
        # brute force, hour by hour for speed is not independent; scan minutes but cap at 4 years
        limit = t + timedelta(days=366 * 4)
        step_fast = timedelta(minutes=1)
        while t < limit and not _oracle_match(expr, t):
            t += step_fast
        assert got == t, (expr, start, got, t)
        checked += 1
    assert checked == 120
