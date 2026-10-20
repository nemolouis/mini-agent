import time


def to_epoch(dt):
    """Convert a naive datetime that represents UTC to Unix seconds."""
    return int(time.mktime(dt.timetuple()))
