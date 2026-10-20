def _cmp_ident(a, b):
    an, bn = a.isdigit(), b.isdigit()
    if an and bn:
        return (int(a) > int(b)) - (int(a) < int(b))
    if an:
        return -1
    if bn:
        return 1
    return (a > b) - (a < b)


def compare(a, b):
    """Return -1, 0 or 1 according to semantic version precedence."""
    ka, kb = (a.major, a.minor, a.patch), (b.major, b.minor, b.patch)
    if ka != kb:
        return -1 if ka < kb else 1
    if not a.pre and not b.pre:
        return 0
    if not a.pre:
        return 1
    if not b.pre:
        return -1
    for x, y in zip(a.pre, b.pre):
        c = _cmp_ident(x, y)
        if c:
            return c
    return (len(a.pre) > len(b.pre)) - (len(a.pre) < len(b.pre))
