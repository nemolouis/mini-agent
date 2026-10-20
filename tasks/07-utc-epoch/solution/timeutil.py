import calendar


def to_epoch(dt):
    """Convert a naive datetime that represents UTC to Unix seconds."""
    return calendar.timegm(dt.timetuple())
