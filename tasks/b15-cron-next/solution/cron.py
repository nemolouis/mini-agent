import calendar
from datetime import datetime, timedelta

_NAMES_MONTH = {n: i + 1 for i, n in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
_NAMES_DOW = {n: i for i, n in enumerate(["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"])}
# (low, high, names)
_FIELDS = [(0, 59, {}), (0, 23, {}), (1, 31, {}), (1, 12, _NAMES_MONTH), (0, 7, _NAMES_DOW)]


def _value(tok, lo, hi, names):
    t = tok.strip().upper()
    if t in names:
        return names[t]
    if not t.isdigit():
        raise ValueError(f"bad value {tok!r}")
    v = int(t)
    if not lo <= v <= hi:
        raise ValueError(f"value {v} out of range {lo}-{hi}")
    return v


def _parse_field(text, lo, hi, names):
    values = set()
    if text == "":
        raise ValueError("empty field")
    for item in text.split(","):
        if item == "":
            raise ValueError("empty list item")
        step = None
        if "/" in item:
            item, s = item.split("/", 1)
            if not s.isdigit() or int(s) < 1:
                raise ValueError(f"bad step {s!r}")
            step = int(s)
        if item == "*":
            a, b = lo, hi
        elif "-" in item:
            x, y = item.split("-", 1)
            a, b = _value(x, lo, hi, names), _value(y, lo, hi, names)
            if a > b:
                raise ValueError("descending range")
        else:
            a = _value(item, lo, hi, names)
            b = hi if step is not None else a
        values.update(range(a, b + 1, step or 1))
    return values


def parse(expr):
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError("expected 5 fields")
    parsed = [_parse_field(f, lo, hi, nm) for f, (lo, hi, nm) in zip(fields, _FIELDS)]
    parsed[4] = {d % 7 for d in parsed[4]}
    return parsed, fields[2] == "*", fields[4] == "*"


def _day_matches(d, doms, months, dows, dom_star, dow_star):
    if d.month not in months:
        return False
    d_ok = d.day in doms
    w_ok = (d.weekday() + 1) % 7 in dows
    if not dom_star and not dow_star:
        return d_ok or w_ok
    return d_ok and w_ok


def next_after(expr, dt):
    (minutes, hours, doms, months, dows), dom_star, dow_star = parse(expr)
    t = dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    day = t.replace(hour=0, minute=0)
    last_day = day + timedelta(days=366 * 9)
    sm, sh = sorted(minutes), sorted(hours)
    first = True
    while day <= last_day:
        if _day_matches(day, doms, months, dows, dom_star, dow_star):
            for h in sh:
                if first and (h < t.hour):
                    continue
                for m in sm:
                    cand = day.replace(hour=h, minute=m)
                    if cand >= t:
                        return cand
        day += timedelta(days=1)
        first = False
    raise ValueError("no matching time")
