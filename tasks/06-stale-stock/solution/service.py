from store import read, write
from cache import Cache

_cache = Cache()


def stock(sku):
    return _cache.get(sku, read)


def restock(sku, n):
    write(sku, read(sku) + n)
    _cache.invalidate(sku)


def sell(sku, n):
    have = read(sku)
    if n > have:
        raise ValueError("insufficient stock")
    write(sku, have - n)
    _cache.invalidate(sku)


def reset():
    _cache.invalidate()
