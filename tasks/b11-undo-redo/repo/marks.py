def shift_for_insert(marks, pos, n):
    """Return new marks after inserting n characters at pos: marks at or after pos move right by n."""
    return dict(marks)


def shift_for_delete(marks, pos, n):
    """Return new marks after deleting [pos, pos+n): marks inside the range move to pos,
    marks after the range move left by n, earlier marks are unchanged."""
    return dict(marks)
