def duration_seconds(session):
    return (session.end - session.start).seconds


def summarize(sessions):
    """Per user: {"sessions": n, "events": total events, "total_seconds": sum of durations,
    "longest_seconds": longest session}. Users appear in sorted order."""
    out = {}
    for s in sessions:
        u = out.setdefault(s.user, {"sessions": 0, "events": 0, "total_seconds": 0, "longest_seconds": 0})
        d = duration_seconds(s)
        u["sessions"] += 1
        u["events"] += s.count
        u["total_seconds"] += d
        u["longest_seconds"] = max(u["longest_seconds"], d)
    return out
