from datetime import timedelta

from recur import monthly


def adjust_to_business_day(d):
    """Saturdays and Sundays move to the preceding Friday; other days are unchanged."""
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def business_schedule(start, count, every=1):
    """Monthly schedule (see recur.monthly), each date adjusted to a business day.
    Adjustment is applied to each date independently and never changes later dates."""
    return [adjust_to_business_day(d) for d in monthly(start, count, every)]
