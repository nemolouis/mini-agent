import pytest
from clock import FakeClock
from wcache import Cache, CacheFull


def make(max_weight=10):
    c = FakeClock()
    log = []
    return c, Cache(max_weight, c, lambda k, v, r: log.append((k, v, r))), log


def test_weight_accounting_and_multi_eviction_order():
    c, cache, log = make(10)
    cache.put("a", 1, weight=4)
    cache.put("b", 2, weight=3)
    cache.put("c", 3, weight=3)
    assert cache.total_weight() == 10 and log == []
    cache.get("a")                                   # LRU order now b, c, a
    cache.put("d", 4, weight=5)                      # needs 5 free: evict b (3) then c (3)
    assert log == [("b", 2, "capacity"), ("c", 3, "capacity")]
    assert cache.keys() == ["a", "d"] and cache.total_weight() == 9


def test_exact_fit_does_not_evict():
    c, cache, log = make(5)
    cache.put("a", 1, weight=2)
    cache.put("b", 2, weight=3)
    assert log == [] and len(cache) == 2


def test_ttl_boundary_is_expired_at_exactly_ttl():
    c, cache, log = make()
    cache.put("a", 1, ttl=10)
    c.advance(9.99)
    assert cache.get("a") == 1
    c.advance(0.01)
    assert cache.get("a", "gone") == "gone"
    assert log == [("a", 1, "expired")]


def test_expired_do_not_count_and_are_purged_in_expiry_order():
    c, cache, log = make(4)
    cache.put("x", 1, weight=2, ttl=5)
    c.advance(1)
    cache.put("y", 2, weight=1, ttl=2)
    cache.put("z", 3, weight=1, ttl=2)
    c.advance(5)                                     # x expired at 5, y and z at 3
    assert len(cache) == 0 and cache.total_weight() == 0
    assert log == [("y", 2, "expired"), ("z", 3, "expired"), ("x", 1, "expired")]


def test_expiry_purged_by_every_public_operation():
    for op in (lambda k: k.keys(), lambda k: len(k), lambda k: k.total_weight(), lambda k: k.delete("nope"),
               lambda k: k.get("nope")):
        c, cache, log = make()
        cache.put("a", 1, ttl=1)
        c.advance(1)
        op(cache)
        assert log == [("a", 1, "expired")]


def test_put_purges_expired_before_making_room():
    c, cache, log = make(3)
    cache.put("a", 1, weight=2, ttl=1)
    cache.put("b", 2, weight=1)
    c.advance(1)
    cache.put("c", 3, weight=2)                      # a is expired -> no capacity eviction of b
    assert log == [("a", 1, "expired")]
    assert cache.keys() == ["b", "c"]


def test_pinned_never_evicted_for_space():
    c, cache, log = make(4)
    cache.put("p", 1, weight=2, pinned=True)
    cache.put("a", 2, weight=1)
    cache.put("b", 3, weight=1)
    cache.put("c", 4, weight=1)                      # evicts a, not p
    assert cache.keys() == ["p", "b", "c"] and log == [("a", 2, "capacity")]


def test_cachefull_leaves_everything_unchanged():
    c, cache, log = make(4)
    cache.put("p", 1, weight=3, pinned=True)
    cache.put("a", 2, weight=1)
    before = (cache.keys(), cache.total_weight())
    with pytest.raises(CacheFull):
        cache.put("big", 9, weight=2)
    assert (cache.keys(), cache.total_weight()) == before and log == []


def test_cachefull_on_replace_keeps_old_entry():
    c, cache, log = make(4)
    cache.put("p", 1, weight=3, pinned=True)
    cache.put("a", "old", weight=1)
    with pytest.raises(CacheFull):
        cache.put("a", "new", weight=2)
    assert cache.get("a") == "old" and cache.total_weight() == 4


def test_replace_releases_old_weight_without_callback():
    c, cache, log = make(5)
    cache.put("a", 1, weight=5)
    cache.put("a", 2, weight=5)                      # fits because the old entry is released
    assert cache.get("a") == 2 and log == [] and len(cache) == 1


def test_replace_does_not_inherit_ttl_or_pin():
    c, cache, log = make(2)
    cache.put("a", 1, ttl=1, pinned=True)
    cache.put("a", 2)
    c.advance(5)
    assert cache.get("a") == 2
    cache.put("b", 3)
    cache.put("c", 4)                                # a is unpinned now -> evictable
    assert "a" not in cache.keys()


def test_recency_from_get_and_put():
    c, cache, log = make(3)
    cache.put("a", 1); cache.put("b", 2); cache.put("c", 3)
    cache.get("a")
    assert cache.keys() == ["b", "c", "a"]
    cache.put("b", 20)
    assert cache.keys() == ["c", "a", "b"]


def test_delete_and_clear_make_no_callbacks():
    c, cache, log = make()
    cache.put("a", 1); cache.put("b", 2)
    assert cache.delete("a") is True and cache.delete("a") is False
    cache.clear()
    assert len(cache) == 0 and log == []


def test_delete_of_expired_entry_reports_false_after_purge():
    c, cache, log = make()
    cache.put("a", 1, ttl=1)
    c.advance(1)
    assert cache.delete("a") is False
    assert log == [("a", 1, "expired")]


def test_validation_changes_nothing():
    c, cache, log = make(3)
    cache.put("a", 1)
    for kw in ({"weight": 0}, {"weight": 4}, {"weight": 1.5}, {"ttl": 0}, {"ttl": -1}):
        with pytest.raises(ValueError):
            cache.put("b", 2, **kw)
    assert cache.keys() == ["a"] and log == []


def test_pinned_entries_still_expire():
    c, cache, log = make()
    cache.put("a", 1, ttl=2, pinned=True)
    c.advance(2)
    assert len(cache) == 0 and log == [("a", 1, "expired")]
