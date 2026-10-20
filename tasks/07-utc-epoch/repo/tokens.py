from timeutil import to_epoch


def issue(now, ttl_seconds):
    return to_epoch(now) + ttl_seconds


def is_expired(expires_at, now):
    return to_epoch(now) >= expires_at
