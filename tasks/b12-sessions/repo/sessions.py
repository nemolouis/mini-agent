from collections import namedtuple
from datetime import timedelta

Session = namedtuple("Session", "user start end count")


def sessionize(events, gap_minutes=30):
    """Group events into per-user sessions.

    - Events may arrive in any order; they are ordered by timestamp first.
    - A user's session continues while the time since that user's previous event is at most
      `gap_minutes`; a gap strictly greater than that starts a new session. (Exactly 30
      minutes stays in the same session.)
    - Users are independent: one user's events never affect another's sessions.
    - Returns Session(user, start, end, count) sorted by (start, user).
    """
    gap = timedelta(minutes=gap_minutes)
    out = []
    cur = None
    for e in events:
        if cur is not None and e.ts - cur["end"] < gap:
            cur["end"] = e.ts
            cur["count"] += 1
        else:
            cur = {"user": e.user, "start": e.ts, "end": e.ts, "count": 1}
            out.append(cur)
    return [Session(s["user"], s["start"], s["end"], s["count"]) for s in out]
