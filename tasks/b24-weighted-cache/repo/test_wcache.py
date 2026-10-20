import pytest
from clock import FakeClock
from wcache import Cache


def test_put_get():
    c = Cache(10, FakeClock())
    c.put("a", 1)
    assert c.get("a") == 1 and c.get("b", "x") == "x"


def test_capacity_eviction_lru():
    c = Cache(2, FakeClock())
    c.put("a", 1); c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert c.keys() == ["a", "c"]


def test_too_heavy():
    with pytest.raises(ValueError):
        Cache(2, FakeClock()).put("a", 1, weight=3)
