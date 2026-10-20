def shift_for_insert(marks, pos, n):
    """Return new marks after inserting n characters at pos: marks at or after pos move right by n."""
    return {k: (v + n if v >= pos else v) for k, v in marks.items()}


def shift_for_delete(marks, pos, n):
    """Return new marks after deleting [pos, pos+n): marks inside the range move to pos,
    marks after the range move left by n, earlier marks are unchanged."""
    out = {}
    for k, v in marks.items():
        if v >= pos + n:
            out[k] = v - n
        elif v > pos:
            out[k] = pos
        else:
            out[k] = v
    return out
