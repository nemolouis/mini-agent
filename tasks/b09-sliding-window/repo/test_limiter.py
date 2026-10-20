from clock import FakeClock
from limiter import SlidingWindowLimiter


def test_limit():
    c = FakeClock()
    lim = SlidingWindowLimiter(3, 10.0, c)
    assert [lim.allow("k") for _ in range(4)] == [True, True, True, False]


def test_window_slides():
    c = FakeClock()
    lim = SlidingWindowLimiter(2, 10.0, c)
    assert lim.allow("k") and lim.allow("k") and not lim.allow("k")
    c.advance(10.5)
    assert lim.allow("k")


def test_keys_independent():
    c = FakeClock()
    lim = SlidingWindowLimiter(1, 10.0, c)
    assert lim.allow("a") and lim.allow("b") and not lim.allow("a")
