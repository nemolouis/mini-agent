from clock import FakeClock
from limiter import TokenBucket


def test_burst_then_deny():
    c = FakeClock()
    b = TokenBucket(2, 1, c)
    assert b.allow() and b.allow()
    assert not b.allow()


def test_refill():
    c = FakeClock()
    b = TokenBucket(1, 1, c)
    assert b.allow()
    assert not b.allow()
    c.advance(1)
    assert b.allow()


def test_idle_does_not_exceed_capacity():
    c = FakeClock()
    b = TokenBucket(2, 1, c)
    c.advance(100)
    assert b.allow() and b.allow()
    assert not b.allow()


def test_denied_calls_do_not_double_credit():
    c = FakeClock()
    b = TokenBucket(1, 1, c)
    assert b.allow()          # t=0, tokens 0
    c.advance(0.5)
    assert not b.allow()      # t=0.5, tokens 0.5
    c.advance(0.5)
    assert b.allow()          # t=1.0, tokens 1.0 -> 0
    c.advance(0.5)
    assert not b.allow()      # t=1.5, tokens 0.5
