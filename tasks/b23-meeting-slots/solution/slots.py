from datetime import datetime, timedelta


def _ceil5(t):
    t = t.replace(second=0, microsecond=0) if (t.second == 0 and t.microsecond == 0) else \
        t.replace(second=0, microsecond=0) + timedelta(minutes=1)
    if t.minute % 5:
        t += timedelta(minutes=5 - t.minute % 5)
    return t


def find_slot(busy, duration_minutes, after, work_start=9, work_end=17, horizon_days=60):
    if duration_minutes <= 0 or duration_minutes % 5:
        raise ValueError("duration must be a positive multiple of 5 minutes")
    d = timedelta(minutes=duration_minutes)
    ivs = sorted((s, e) for person in busy.values() for s, e in person if s < e)
    first = _ceil5(after)
    last_date = after.date() + timedelta(days=horizon_days)
    day = after.date()
    while day <= last_date:
        if day.weekday() < 5:
            open_t = datetime(day.year, day.month, day.day, work_start, 0)
            close_t = datetime(day.year, day.month, day.day, work_end, 0)
            s = max(open_t, first)
            while s + d <= close_t:
                clash = next(((bs, be) for bs, be in ivs if bs < s + d and s < be), None)
                if clash is None:
                    return s
                s = _ceil5(clash[1])
        day += timedelta(days=1)
    return None
