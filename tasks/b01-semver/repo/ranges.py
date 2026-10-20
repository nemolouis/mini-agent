from version import Version


def caret_bounds(v):
    return v, Version(v.major + 1, 0, 0)


def tilde_bounds(v):
    return v, Version(v.major, v.minor + 1, 0)


def satisfies(version, spec):
    """spec is '^X.Y.Z' or '~X.Y.Z'."""
    if spec[:1] not in ("^", "~"):
        raise ValueError(f"unsupported range: {spec!r}")
    base = Version.parse(spec[1:])
    lo, hi = (caret_bounds if spec[0] == "^" else tilde_bounds)(base)
    return lo <= version < hi
