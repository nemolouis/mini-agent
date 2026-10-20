from collections import OrderedDict
from itertools import count


class CacheFull(Exception):
    pass


class _Entry:
    __slots__ = ("value", "weight", "expires", "pinned", "seq")

    def __init__(self, value, weight, expires, pinned, seq):
        self.value, self.weight, self.expires, self.pinned, self.seq = value, weight, expires, pinned, seq


class Cache:
    def __init__(self, max_weight, clock, on_evict=None):
        self.max_weight = max_weight
        self.clock = clock
        self.on_evict = on_evict
        self._d = OrderedDict()      # least recently used first
        self._seq = count()

    def _notify(self, events):
        if self.on_evict:
            for k, v, r in events:
                self.on_evict(k, v, r)

    def _purge(self):
        now = self.clock.now()
        dead = sorted(((e.expires, e.seq, k) for k, e in self._d.items()
                       if e.expires is not None and now >= e.expires))
        events = []
        for _, _, k in dead:
            e = self._d.pop(k)
            events.append((k, e.value, "expired"))
        self._notify(events)

    def put(self, key, value, weight=1, ttl=None, pinned=False):
        if isinstance(weight, bool) or not isinstance(weight, int) or weight < 1 or weight > self.max_weight:
            raise ValueError("weight must be an int in [1, max_weight]")
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be > 0")
        self._purge()
        old = self._d.get(key)
        total = sum(e.weight for e in self._d.values()) - (old.weight if old else 0)
        need = total + weight - self.max_weight
        victims = []
        if need > 0:
            for k, e in self._d.items():
                if k == key or e.pinned:
                    continue
                victims.append(k)
                need -= e.weight
                if need <= 0:
                    break
            if need > 0:
                raise CacheFull(key)
        events = []
        for k in victims:
            e = self._d.pop(k)
            events.append((k, e.value, "capacity"))
        self._d.pop(key, None)
        expires = None if ttl is None else self.clock.now() + ttl
        self._d[key] = _Entry(value, weight, expires, pinned, next(self._seq))
        self._notify(events)

    def get(self, key, default=None):
        self._purge()
        e = self._d.get(key)
        if e is None:
            return default
        self._d.move_to_end(key)
        return e.value

    def delete(self, key):
        self._purge()
        return self._d.pop(key, None) is not None

    def keys(self):
        self._purge()
        return list(self._d)

    def __len__(self):
        self._purge()
        return len(self._d)

    def total_weight(self):
        self._purge()
        return sum(e.weight for e in self._d.values())

    def clear(self):
        self._d.clear()
