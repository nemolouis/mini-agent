def compare(a, b):
    """Return -1, 0 or 1 according to semantic version precedence."""
    ka, kb = (a.major, a.minor, a.patch), (b.major, b.minor, b.patch)
    if ka != kb:
        return -1 if ka < kb else 1
    if a.pre == b.pre:
        return 0
    sa, sb = ".".join(a.pre), ".".join(b.pre)
    if not sa:
        return 1
    if not sb:
        return -1
    return -1 if sa < sb else 1
