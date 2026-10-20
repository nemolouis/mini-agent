from lru import LRUCache
from memo import memoize


def test_capacity_respected():
    c = LRUCache(2)
    for i in range(5):
        c.put(i, i)
    assert len(c) == 2


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    assert c.get("a") == 1
    assert c.get("b") is None


def test_put_existing_refreshes_and_does_not_grow():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)
    c.put("c", 3)
    assert c.get("a") == 10
    assert c.get("b") is None
    assert len(c) == 2


def test_memoize_calls():
    calls = []

    @memoize(2)
    def f(x):
        calls.append(x)
        return x * 2

    f(1); f(2); f(1); f(3); f(1)
    assert calls == [1, 2, 3]
