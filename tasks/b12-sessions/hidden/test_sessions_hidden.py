from datetime import datetime, timedelta, timezone
import pytest
from parse import parse_event, parse_log, parse_timestamp
from report import summarize
from sessions import sessionize


def test_offsets_are_respected():
    a = parse_timestamp("2024-03-10T12:00:00+02:00")
    b = parse_timestamp("2024-03-10T10:00:00Z")
    assert a == b and a.tzinfo is not None
    assert parse_timestamp("2024-03-10T12:00:00-05:00") == datetime(2024, 3, 10, 17, 0, tzinfo=timezone.utc)


def test_missing_offset_rejected():
    with pytest.raises(ValueError):
        parse_timestamp("2024-03-10T12:00:00")
    with pytest.raises(ValueError):
        parse_event("2024-03-10T12:00:00 ann click")


def test_fractional_seconds():
    assert parse_timestamp("2024-03-10T12:00:00.250Z").microsecond == 250000


def test_unsorted_input():
    log = """2024-03-10T12:20:00Z ann c
2024-03-10T12:00:00Z ann a
2024-03-10T12:10:00Z ann b"""
    ss = sessionize(parse_log(log))
    assert len(ss) == 1 and ss[0].count == 3
    assert ss[0].end - ss[0].start == timedelta(minutes=20)


def test_exact_gap_stays_in_session():
    log = "2024-03-10T12:00:00Z ann a\n2024-03-10T12:30:00Z ann b\n2024-03-10T13:00:01Z ann c"
    ss = sessionize(parse_log(log))
    assert [s.count for s in ss] == [2, 1]


def test_custom_gap():
    log = "2024-03-10T12:00:00Z ann a\n2024-03-10T12:06:00Z ann b"
    assert len(sessionize(parse_log(log), gap_minutes=5)) == 2
    assert len(sessionize(parse_log(log), gap_minutes=6)) == 1


def test_users_interleaved_are_independent():
    log = """2024-03-10T12:00:00Z ann a
2024-03-10T12:05:00Z bob a
2024-03-10T12:10:00Z ann b
2024-03-10T12:15:00Z bob b
2024-03-10T14:00:00Z ann c"""
    ss = sessionize(parse_log(log))
    assert [(s.user, s.count) for s in ss] == [("ann", 2), ("bob", 2), ("ann", 1)]


def test_mixed_offsets_ordering():
    log = """2024-03-10T12:00:00+02:00 ann a
2024-03-10T10:20:00Z ann b
2024-03-10T09:50:00Z ann c"""
    ss = sessionize(parse_log(log))
    # instants: 10:00Z, 10:20Z, 09:50Z -> sorted 09:50, 10:00, 10:20 -> one session
    assert len(ss) == 1 and ss[0].count == 3
    assert ss[0].start == datetime(2024, 3, 10, 9, 50, tzinfo=timezone.utc)


def test_sorted_by_start_then_user():
    log = """2024-03-10T12:00:00Z bob a
2024-03-10T12:00:00Z ann a
2024-03-10T11:00:00Z zed a"""
    assert [s.user for s in sessionize(parse_log(log))] == ["zed", "ann", "bob"]


def test_duration_over_a_day():
    start = datetime(2024, 3, 1, 0, 0, tzinfo=timezone.utc)
    lines = [f"{(start + timedelta(minutes=20 * i)).isoformat()} ann tick" for i in range(0, 91)]
    ss = sessionize(parse_log("\n".join(lines)))
    assert len(ss) == 1
    s = summarize(ss)["ann"]
    assert s["total_seconds"] == 90 * 20 * 60 and s["longest_seconds"] == 90 * 20 * 60 and s["events"] == 91


def test_summary_multi_user_sorted():
    log = """2024-03-10T12:00:00Z zed a
2024-03-10T12:10:00Z zed b
2024-03-10T12:00:00Z ann a
2024-03-10T15:00:00Z ann b
2024-03-10T15:05:00Z ann c"""
    s = summarize(sessionize(parse_log(log)))
    assert list(s) == ["ann", "zed"]
    assert s["ann"] == {"sessions": 2, "events": 3, "total_seconds": 300, "longest_seconds": 300}
    assert s["zed"] == {"sessions": 1, "events": 2, "total_seconds": 600, "longest_seconds": 600}


def test_blank_lines_and_action_with_spaces():
    log = "\n2024-03-10T12:00:00Z ann open the door\n\n"
    ev = parse_log(log)
    assert len(ev) == 1 and ev[0].action == "open the door"
