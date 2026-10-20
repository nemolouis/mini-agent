from collections import namedtuple

MergeResult = namedtuple("MergeResult", "lines conflicts")


def _matching(a, b):
    """Map index in a -> index in b along one longest common subsequence."""
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            L[i][j] = L[i + 1][j + 1] + 1 if a[i] == b[j] else max(L[i + 1][j], L[i][j + 1])
    match, i, j = {}, 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            match[i] = j
            i += 1
            j += 1
        elif L[i + 1][j] >= L[i][j + 1]:
            i += 1
        else:
            j += 1
    return match


def merge3(base, ours, theirs):
    base, ours, theirs = list(base), list(ours), list(theirs)
    mo, mt = _matching(base, ours), _matching(base, theirs)
    sync = [i for i in range(len(base)) if i in mo and i in mt]
    out, conflicts = [], 0
    pb = po = pt = 0
    for i in sync + [None]:
        if i is None:
            b1, o1, t1 = len(base), len(ours), len(theirs)
        else:
            b1, o1, t1 = i, mo[i], mt[i]
        b, o, t = base[pb:b1], ours[po:o1], theirs[pt:t1]
        if o == b:
            out.extend(t)
        elif t == b:
            out.extend(o)
        elif o == t:
            out.extend(o)
        else:
            conflicts += 1
            out.extend(["<<<<<<< ours", *o, "=======", *t, ">>>>>>> theirs"])
        if i is not None:
            out.append(base[i])
            pb, po, pt = i + 1, mo[i] + 1, mt[i] + 1
    return MergeResult(out, conflicts)
