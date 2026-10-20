from version import Version


def caret_bounds(v):
    if v.major > 0:
        return v, Version(v.major + 1, 0, 0)
    if v.minor > 0:
        return v, Version(0, v.minor + 1, 0)
    return v, Version(0, 0, v.patch + 1)


def tilde_bounds(v):
    return v, Version(v.major, v.minor + 1, 0)


def satisfies(version, spec):
    """spec is '^X.Y.Z' or '~X.Y.Z'."""
    if spec[:1] not in ("^", "~"):
        raise ValueError(f"unsupported range: {spec!r}")
    if version.pre:
        return False
    base = Version.parse(spec[1:])
    lo, hi = (caret_bounds if spec[0] == "^" else tilde_bounds)(base)
    return lo <= version < hi
