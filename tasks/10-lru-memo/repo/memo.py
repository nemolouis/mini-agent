from lru import LRUCache

_MISS = object()


def memoize(capacity):
    def deco(fn):
        cache = LRUCache(capacity)

        def wrapper(*args):
            v = cache.get(args, _MISS)
            if v is _MISS:
                v = fn(*args)
                cache.put(args, v)
            return v

        return wrapper

    return deco
