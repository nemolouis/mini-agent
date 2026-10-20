import calendar
from datetime import datetime, timedelta

_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]


def _parse_field(text, lo, hi):
    values = set()
    for item in text.split(","):
        step = 1
        if "/" in item:
            item, s = item.split("/")
            step = int(s)
        if item == "*":
            a, b = lo, hi
        elif "-" in item:
            a, b = (int(x) for x in item.split("-"))
        else:
            a = b = int(item)
        values.update(range(a, b + 1, step))
    return values


def parse(expr):
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError("expected 5 fields")
    return [_parse_field(f, lo, hi) for f, (lo, hi) in zip(fields, _RANGES)]


def next_after(expr, dt):
    minutes, hours, doms, months, dows = parse(expr)
    t = dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit = t + timedelta(days=366)
    while t < limit:
        if (t.month in months and t.day in doms and (t.weekday() + 1) % 7 in dows
                and t.hour in hours and t.minute in minutes):
            return t
        t += timedelta(minutes=1)
    raise ValueError("no match")
