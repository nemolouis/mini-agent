from datetime import date

from calendar_utils import days_in_month


def add_months(d, n):
    """Return d shifted by n months, clamping the day to the end of the target month."""
    total = d.year * 12 + (d.month - 1) + n
    y, m = divmod(total, 12)
    m += 1
    return date(y, m, min(d.day, days_in_month(y, m)))


def monthly(start, count, every=1):
    """Return `count` dates. The i-th date is `start` plus i*`every` months, keeping the
    day-of-month of `start`; when that day does not exist in the target month the last
    day of the month is used. The day-of-month of `start` is never lost: Jan 31 monthly
    gives Jan 31, Feb 28, Mar 31 (not Mar 28). count <= 0 returns an empty list."""
    out = [start]
    cur = start
    for _ in range(count - 1):
        cur = add_months(cur, every)
        out.append(cur)
    return out
