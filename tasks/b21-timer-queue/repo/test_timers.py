from clock import FakeClock
from timers import TimerQueue


def test_runs_in_order():
    c = FakeClock(); q = TimerQueue(c); log = []
    q.call_later(5, log.append, "b")
    q.call_later(2, log.append, "a")
    assert q.run_until(10) == 2
    assert log == ["a", "b"] and c.now() == 10


def test_not_yet_due():
    c = FakeClock(); q = TimerQueue(c); log = []
    q.call_later(5, log.append, "x")
    assert q.run_until(4) == 0 and log == [] and q.pending() == 1


def test_cancel():
    c = FakeClock(); q = TimerQueue(c); log = []
    h = q.call_later(1, log.append, "x")
    assert q.cancel(h) is True
    q.run_until(5)
    assert log == []
