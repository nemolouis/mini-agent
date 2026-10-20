from collections import namedtuple
from datetime import datetime

Event = namedtuple("Event", "user ts action")


def parse_timestamp(text):
    """Parse an ISO-8601 timestamp that carries a UTC offset ('Z' or +HH:MM / -HH:MM) into a
    timezone-aware datetime. Timestamps without an offset raise ValueError."""
    return datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S")


def parse_event(line):
    """Parse '<timestamp> <user> <action>' (single spaces; action may contain spaces)."""
    ts, user, action = line.strip().split(" ", 2)
    return Event(user, parse_timestamp(ts), action)


def parse_log(text):
    return [parse_event(l) for l in text.splitlines() if l.strip()]
