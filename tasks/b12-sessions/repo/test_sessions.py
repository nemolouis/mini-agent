from parse import parse_event, parse_log
from report import summarize
from sessions import sessionize

LOG = """2024-03-10T12:00:00+00:00 ann click
2024-03-10T12:10:00+00:00 ann scroll
2024-03-10T13:00:00+00:00 ann click"""


def test_parse_event():
    e = parse_event("2024-03-10T12:00:00+00:00 ann open page")
    assert e.user == "ann" and e.action == "open page"


def test_sessions_single_user():
    ss = sessionize(parse_log(LOG))
    assert [(s.count) for s in ss] == [2, 1]


def test_summary():
    s = summarize(sessionize(parse_log(LOG)))
    assert s["ann"]["sessions"] == 2 and s["ann"]["total_seconds"] == 600
