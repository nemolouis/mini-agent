# Weighted cache

`Cache(max_weight, clock, on_evict=None)`; the clock has `now()`.

## Operations
- `put(key, value, weight=1, ttl=None, pinned=False)`
  - `weight` must be an int >= 1 and `<= max_weight`, `ttl` None or > 0, otherwise `ValueError`
    (nothing changes).
  - If `key` already exists the old entry is replaced: its weight is released, no callback
    is made, and the new entry gets the given `weight` / `ttl` / `pinned` (nothing is inherited).
  - After the put, the total weight of all entries is `<= max_weight`. Room is made by
    evicting **unpinned** entries, least recently used first, calling
    `on_evict(key, value, "capacity")` for each. If room cannot be made without evicting a
    pinned entry, `CacheFull` is raised and the cache is left completely unchanged
    (no evictions, the old entry of `key`, if any, is kept).
  - The new entry becomes the most recently used.
- `get(key, default=None)`: returns the value, or `default` if absent or expired.
  A hit makes the entry the most recently used.
- `delete(key)` -> `True` if it existed (and was not expired), else `False`. No callback.
- `keys()` -> list of keys, least recently used first. `len(cache)` -> number of entries.
  `total_weight()` -> sum of the weights of the entries. `clear()` removes everything, no callbacks.

## Expiry
An entry put at time `p` with `ttl` is expired when `clock.now() >= p + ttl` (exactly at
`p + ttl` it is already expired). At the start of EVERY public operation (including
`len`, `keys`, `total_weight`, `get`, `delete`, `put`) all expired entries are removed first,
in order of their expiry time (ties: the one put earlier first), calling
`on_evict(key, value, "expired")` for each. Expired entries never count toward weight.
Pinned entries still expire normally.
