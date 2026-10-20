"""Helpers for sequences of numbers."""


def mean(xs):
    if not xs:
        raise ValueError("empty")
    return sum(xs) / len(xs)


def median(xs):
    if not xs:
        raise ValueError("empty")
    s = sorted(xs)
    mid = len(s) // 2
    if len(s) % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def mode(xs):
    """Most frequent value; ties go to the smallest value."""
    if not xs:
        raise ValueError("empty")
    counts = {}
    for x in xs:
        counts[x] = counts.get(x, 0) + 1
    best = max(counts.values())
    return min(x for x, c in counts.items() if c == best)


def percentile(xs, p):
    """Linear interpolation between closest ranks, p in [0, 100]."""
    if not xs:
        raise ValueError("empty")
    if not 0 <= p <= 100:
        raise ValueError("p out of range")
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def moving_average(xs, window):
    """Averages of every full window; empty if the sequence is shorter than the window."""
    if window < 1:
        raise ValueError("window must be positive")
    return [sum(xs[i:i + window]) / window for i in range(len(xs) - window + 1)]


def run_length_encode(xs):
    out = []
    for x in xs:
        if out and out[-1][0] == x:
            out[-1][1] += 1
        else:
            out.append([x, 1])
    return [(v, n) for v, n in out]


def run_length_decode(pairs):
    out = []
    for v, n in pairs:
        out.extend([v] * n)
    return out


def chunked(xs, size):
    """Consecutive pieces of at most `size` items."""
    if size < 1:
        raise ValueError("size must be positive")
    return [xs[i:i + size] for i in range(0, len(xs), size)]


def flatten(xs):
    """Flatten arbitrarily nested lists and tuples; strings are atoms."""
    out = []
    for x in xs:
        if isinstance(x, (list, tuple)):
            out.extend(flatten(x))
        else:
            out.append(x)
    return out


def rolling_max(xs, window):
    """Maximum of each window of size `window` (windows shorter than `window` at the start are included)."""
    if window < 1:
        raise ValueError("window must be positive")
    return [max(xs[max(0, i - window + 1): i + 1]) for i in range(len(xs))]


def clamp(x, lo, hi):
    if lo > hi:
        raise ValueError("lo > hi")
    return max(lo, min(hi, x))


def normalise(xs):
    """Scale to [0, 1]; a constant sequence becomes all zeros."""
    lo, hi = min(xs), max(xs)
    if hi == lo:
        return [0.0 for _ in xs]
    return [(x - lo) / (hi - lo) for x in xs]
