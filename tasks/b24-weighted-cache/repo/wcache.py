from collections import OrderedDict


class CacheFull(Exception):
    pass


class Cache:
    def __init__(self, max_weight, clock, on_evict=None):
        self.max_weight = max_weight
        self.clock = clock
        self.on_evict = on_evict
        self._d = OrderedDict()   # key -> [value, weight, expires, pinned]

    def put(self, key, value, weight=1, ttl=None, pinned=False):
        if weight > self.max_weight:
            raise ValueError("too heavy")
        expires = None if ttl is None else self.clock.now() + ttl
        while self.total_weight() + weight > self.max_weight:
            victim = next(iter(self._d))
            v = self._d.pop(victim)
            if self.on_evict:
                self.on_evict(victim, v[0], "expired")
        self._d[key] = [value, weight, expires, pinned]

    def get(self, key, default=None):
        e = self._d.get(key)
        if e is None:
            return default
        if e[2] is not None and self.clock.now() > e[2]:
            del self._d[key]
            return default
        return e[0]

    def delete(self, key):
        return self._d.pop(key, None) is not None

    def keys(self):
        return list(self._d)

    def __len__(self):
        return len(self._d)

    def total_weight(self):
        return sum(e[1] for e in self._d.values())

    def clear(self):
        self._d.clear()
