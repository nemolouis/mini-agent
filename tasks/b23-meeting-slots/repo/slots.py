from datetime import datetime, timedelta


def find_slot(busy, duration_minutes, after, work_start=9, work_end=17, horizon_days=60):
    if duration_minutes <= 0 or duration_minutes % 5:
        raise ValueError("duration must be a positive multiple of 5 minutes")
    intervals = [iv for ivs in busy.values() for iv in ivs]
    d = timedelta(minutes=duration_minutes)
    t = after
    end = after + timedelta(days=horizon_days)
    while t < end:
        day_start = t.replace(hour=work_start, minute=0, second=0, microsecond=0)
        if t < day_start:
            t = day_start
        if t.hour >= work_end:
            t = (t + timedelta(days=1)).replace(hour=work_start, minute=0, second=0, microsecond=0)
            continue
        if all(not (s <= t + d and t <= e) for s, e in intervals):
            return t
        t += timedelta(minutes=5)
    return None
