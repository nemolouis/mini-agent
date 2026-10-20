def diff(a, b):
    """Return an edit script turning sequence `a` into sequence `b`.

    The script is a list of (op, item) tuples where op is one of
        "="  item present in both (kept)
        "-"  item deleted from a
        "+"  item inserted from b
    Requirements:
    1. Applying the script reproduces both inputs: the items of "=" and "-" ops, in order,
       are exactly `a`; the items of "=" and "+" ops, in order, are exactly `b`.
    2. The script is minimal: the number of "=" ops equals the length of a longest common
       subsequence of a and b (equivalently, the fewest possible insertions + deletions).
    3. Ordering: inside every maximal run of consecutive non-"=" ops, all "-" ops come
       before all "+" ops (each group keeps the order of its items in a / b).
    4. Performance: two ~6000-element sequences that differ in a handful of places must be
       diffed in well under 2 seconds. Items only need to support ==.
    """
    a, b = list(a), list(b)
    lo = 0
    while lo < len(a) and lo < len(b) and a[lo] == b[lo]:
        lo += 1
    ha, hb = len(a), len(b)
    while ha > lo and hb > lo and a[ha - 1] == b[hb - 1]:
        ha -= 1
        hb -= 1
    mid = _middle(a[lo:ha], b[lo:hb])
    ops = [("=", x) for x in a[:lo]] + mid + [("=", x) for x in a[ha:]]
    return _canonical(ops)


def _middle(a, b):
    n, m = len(a), len(b)
    if n == 0:
        return [("+", x) for x in b]
    if m == 0:
        return [("-", x) for x in a]
    # Myers' O(ND) greedy algorithm; D is the (small) number of edits.
    v = {1: 0}
    trace = []
    for d in range(n + m + 1):
        trace.append(dict(v))
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v[k - 1] < v[k + 1]):
                x = v[k + 1]
            else:
                x = v[k - 1] + 1
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[k] = x
            if x >= n and y >= m:
                return _backtrack(trace, a, b, d)
    raise AssertionError("unreachable")


def _backtrack(trace, a, b, d_final):
    x, y = len(a), len(b)
    ops = []
    for d in range(d_final, 0, -1):
        v = trace[d]
        k = x - y
        down = k == -d or (k != d and v[k - 1] < v[k + 1])
        prev_k = k + 1 if down else k - 1
        prev_x = v[prev_k]
        prev_y = prev_x - prev_k
        mid_x = prev_x if down else prev_x + 1
        mid_y = mid_x - k
        while x > mid_x and y > mid_y:
            ops.append(("=", a[x - 1]))
            x -= 1
            y -= 1
        ops.append(("+", b[prev_y]) if down else ("-", a[prev_x]))
        x, y = prev_x, prev_y
    while x > 0 and y > 0:
        ops.append(("=", a[x - 1]))
        x -= 1
        y -= 1
    ops.reverse()
    return ops


def _canonical(ops):
    out, i = [], 0
    while i < len(ops):
        if ops[i][0] == "=":
            out.append(ops[i])
            i += 1
            continue
        j = i
        while j < len(ops) and ops[j][0] != "=":
            j += 1
        run = ops[i:j]
        out.extend([o for o in run if o[0] == "-"] + [o for o in run if o[0] == "+"])
        i = j
    return out
