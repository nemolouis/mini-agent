class RegexError(Exception):
    pass


SPECIAL = set(".*+?|()^$\\")


def _atoms(pattern):
    """Very small matcher: sequence of single-character atoms with optional * + ?."""
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        i += 1
        q = ""
        if i < len(pattern) and pattern[i] in "*+?":
            q = pattern[i]
            i += 1
        out.append((c, q))
    return out


def _match_here(atoms, text, ai, ti):
    if ai == len(atoms):
        return ti
    c, q = atoms[ai]
    ok = lambda k: k < len(text) and (c == "." or text[k] == c)
    if q == "*":
        n = 0
        while ok(ti + n):
            n += 1
        while n >= 0:
            r = _match_here(atoms, text, ai + 1, ti + n)
            if r is not None:
                return r
            n -= 1
        return None
    if q == "+":
        if not ok(ti):
            return None
        return _match_here([(c, "*")] + atoms[ai + 1:], text, 0, ti + 1)
    if q == "?":
        if ok(ti):
            r = _match_here(atoms, text, ai + 1, ti + 1)
            if r is not None:
                return r
        return _match_here(atoms, text, ai + 1, ti)
    return _match_here(atoms, text, ai + 1, ti + 1) if ok(ti) else None


def fullmatch(pattern, text):
    atoms = _atoms(pattern)
    r = _match_here(atoms, text, 0, 0)
    return r == len(text)


def search(pattern, text):
    atoms = _atoms(pattern)
    for s in range(len(text) + 1):
        r = _match_here(atoms, text, 0, s)
        if r is not None:
            return (s, r)
    return None
