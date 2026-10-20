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
    ops, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            ops.append(("=", a[i]))
            i += 1
            j += 1
        elif a[i] not in b[j:]:
            ops.append(("-", a[i]))
            i += 1
        else:
            ops.append(("+", b[j]))
            j += 1
    ops.extend(("-", x) for x in a[i:])
    ops.extend(("+", x) for x in b[j:])
    return ops
