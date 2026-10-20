import pytest
from clock import FakeClock
from timers import TimerQueue


def make():
    c = FakeClock()
    return c, TimerQueue(c)


def test_ties_run_in_creation_order_even_with_uncomparable_callbacks():
    c, q = make(); log = []
    for name in "abcd":
        q.call_later(1, lambda n=name: log.append(n))
    q.run_until(1)
    assert log == list("abcd")


def test_clock_is_due_time_inside_callbacks():
    c, q = make(); seen = []
    q.call_later(3, lambda: seen.append(c.now()))
    q.call_later(7, lambda: seen.append(c.now()))
    q.run_until(10)
    assert seen == [3, 7] and c.now() == 10


def test_repeating_does_not_drift():
    c, q = make(); seen = []
    q.call_every(10, lambda: seen.append(c.now()))
    q.run_until(35)
    assert seen == [10, 20, 30] and c.now() == 35
    q.run_until(50)
    assert seen == [10, 20, 30, 40, 50]


def test_first_delay():
    c, q = make(); seen = []
    q.call_every(10, lambda: seen.append(c.now()), first_delay=3)
    q.run_until(25)
    assert seen == [3, 13, 23]


def test_repeating_cancel_between_runs_and_pending_count():
    c, q = make(); seen = []
    h = q.call_every(5, lambda: seen.append(c.now()))
    q.call_later(100, lambda: None)
    assert q.pending() == 2
    q.run_until(12)
    assert seen == [5, 10] and q.pending() == 2
    assert q.cancel(h) is True and q.pending() == 1
    assert q.cancel(h) is False
    q.run_until(30)
    assert seen == [5, 10]


def test_cancel_from_own_callback_stops_repetition():
    c, q = make(); seen = []
    holder = {}

    def tick():
        seen.append(c.now())
        if len(seen) == 3:
            q.cancel(holder["h"])

    holder["h"] = q.call_every(1, tick)
    q.run_until(10)
    assert seen == [1, 2, 3] and q.pending() == 0


def test_cancel_other_timer_from_callback():
    c, q = make(); log = []
    victim = q.call_later(5, log.append, "victim")
    q.call_later(2, lambda: q.cancel(victim))
    q.run_until(10)
    assert log == []


def test_cancel_finished_returns_false():
    c, q = make()
    h = q.call_later(1, lambda: None)
    q.run_until(2)
    assert q.cancel(h) is False and q.pending() == 0


def test_callbacks_schedule_new_timers_in_same_run():
    c, q = make(); log = []

    def first():
        log.append(("first", c.now()))
        q.call_later(0, lambda: log.append(("zero", c.now())))
        q.call_later(2, lambda: log.append(("later", c.now())))

    q.call_later(1, first)
    q.call_later(1, lambda: log.append(("sibling", c.now())))
    q.run_until(5)
    assert log == [("first", 1), ("sibling", 1), ("zero", 1), ("later", 3)]


def test_new_timer_beyond_t_waits_for_next_run():
    c, q = make(); log = []
    q.call_later(1, lambda: q.call_later(10, log.append, "x"))
    q.run_until(5)
    assert log == [] and q.pending() == 1
    q.run_until(11)
    assert log == ["x"]


def test_errors_are_collected_and_do_not_stop_the_loop():
    c, q = make(); log = []

    def boom():
        raise RuntimeError("boom")

    q.call_later(1, boom)
    q.call_later(2, log.append, "after")
    n = q.call_every(3, boom)
    assert q.run_until(7) == 4          # boom@1, after@2, boom@3, boom@6
    assert log == ["after"]
    assert len(q.errors) == 3 and all(isinstance(e, RuntimeError) for e in q.errors)
    assert q.pending() == 1             # the repeating timer is still alive


def test_validation():
    c, q = make()
    with pytest.raises(ValueError):
        q.call_later(-1, lambda: None)
    with pytest.raises(ValueError):
        q.call_every(0, lambda: None)
    c.set(10)
    with pytest.raises(ValueError):
        q.run_until(5)


def test_run_until_now_runs_zero_delay_timers():
    c, q = make(); log = []
    q.call_later(0, log.append, 1)
    assert q.run_until(0) == 1 and log == [1]


def test_args_are_passed():
    c, q = make(); got = []
    q.call_later(1, lambda a, b: got.append((a, b)), 1, 2)
    q.run_until(1)
    assert got == [(1, 2)]
