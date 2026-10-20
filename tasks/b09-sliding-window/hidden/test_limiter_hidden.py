import time
from clock import FakeClock
from limiter import SlidingWindowLimiter


def test_boundary_event_expires_exactly_at_window():
    c = FakeClock()
    lim = SlidingWindowLimiter(1, 10.0, c)
    assert lim.allow("k")
    c.advance(9.0)
    assert not lim.allow("k")
    c.advance(1.0)
    assert lim.allow("k")


def test_denied_calls_not_recorded():
    c = FakeClock()
    lim = SlidingWindowLimiter(2, 10.0, c)
    lim.allow("k"); lim.allow("k")
    for _ in range(5):
        assert not lim.allow("k")
    assert lim.pending("k") == 2
    c.advance(10.0)
    assert lim.allow("k") and lim.allow("k") and not lim.allow("k")


def test_retry_after():
    c = FakeClock()
    lim = SlidingWindowLimiter(2, 10.0, c)
    assert lim.retry_after("k") == 0.0
    lim.allow("k")
    c.advance(3.0)
    lim.allow("k")
    assert lim.retry_after("k") == 7.0
    c.advance(2.0)
    assert lim.retry_after("k") == 5.0
    c.advance(5.0)
    assert lim.retry_after("k") == 0.0
    assert lim.allow("k")


def test_retry_after_unknown_key_and_not_limited():
    c = FakeClock()
    lim = SlidingWindowLimiter(3, 10.0, c)
    lim.allow("a")
    assert lim.retry_after("a") == 0.0
    assert lim.retry_after("zzz") == 0.0


def test_pending_counts_only_window():
    c = FakeClock()
    lim = SlidingWindowLimiter(5, 10.0, c)
    for _ in range(3):
        lim.allow("k")
        c.advance(4.0)
    assert lim.pending("k") == 2


def test_reset():
    c = FakeClock()
    lim = SlidingWindowLimiter(1, 10.0, c)
    lim.allow("k")
    lim.reset("k")
    assert lim.pending("k") == 0 and lim.allow("k")
    lim.reset("never-seen")


def test_many_requests_fast_and_bounded_memory():
    c = FakeClock()
    lim = SlidingWindowLimiter(100, 1.0, c)
    allowed = 0
    t0 = time.perf_counter()
    for _ in range(60_000):
        c.advance(0.001)
        allowed += lim.allow("k")
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.5, elapsed
    assert lim.pending("k") <= 100
    assert len(lim._events["k"]) <= 100
    assert 5900 <= allowed <= 6100, allowed


def test_many_keys_memory():
    c = FakeClock()
    lim = SlidingWindowLimiter(2, 1.0, c)
    for i in range(2000):
        c.advance(0.01)
        lim.allow(f"k{i % 7}")
    assert all(len(v) <= 2 for v in lim._events.values())
