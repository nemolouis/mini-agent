class IntervalSet:
    """A set of integers stored as sorted, disjoint, non-adjacent half-open intervals [lo, hi).

    Invariant: intervals() returns a list of (lo, hi) tuples with lo < hi, sorted ascending,
    where no two intervals overlap or touch (hi of one < lo of the next): [1,3) and [3,5)
    are stored as the single interval [1,5).

    add(lo, hi) / remove(lo, hi): add or remove all integers x with lo <= x < hi.
        An empty range (lo >= hi) is ignored.
    contains(x) / `x in s`: membership of the integer x.
    total_length(): the number of integers in the set (sum of hi - lo).
    union(other), intersection(other), difference(other): new IntervalSets; operands unchanged.
    complement(lo, hi): the integers in [lo, hi) that are NOT in the set, as a new IntervalSet.
    Two IntervalSets are equal when they contain the same integers.
    """

    def __init__(self, intervals=()):
        self._iv = []
        for lo, hi in intervals:
            self.add(lo, hi)

    def intervals(self):
        return list(self._iv)

    def add(self, lo, hi):
        if lo >= hi:
            return
        iv, out, i = self._iv, [], 0
        while i < len(iv) and iv[i][1] < lo:
            out.append(iv[i])
            i += 1
        while i < len(iv) and iv[i][0] <= hi:
            lo, hi = min(lo, iv[i][0]), max(hi, iv[i][1])
            i += 1
        out.append((lo, hi))
        out.extend(iv[i:])
        self._iv = out

    def remove(self, lo, hi):
        if lo >= hi:
            return
        out = []
        for a, b in self._iv:
            if b <= lo or a >= hi:
                out.append((a, b))
                continue
            if a < lo:
                out.append((a, lo))
            if hi < b:
                out.append((hi, b))
        self._iv = out

    def contains(self, x):
        return any(a <= x < b for a, b in self._iv)

    __contains__ = contains

    def total_length(self):
        return sum(b - a for a, b in self._iv)

    def union(self, other):
        r = IntervalSet(self._iv)
        for a, b in other._iv:
            r.add(a, b)
        return r

    def intersection(self, other):
        res, i, j = [], 0, 0
        A, B = self._iv, other._iv
        while i < len(A) and j < len(B):
            lo, hi = max(A[i][0], B[j][0]), min(A[i][1], B[j][1])
            if lo < hi:
                res.append((lo, hi))
            if A[i][1] < B[j][1]:
                i += 1
            else:
                j += 1
        return IntervalSet(res)

    def difference(self, other):
        r = IntervalSet(self._iv)
        for a, b in other._iv:
            r.remove(a, b)
        return r

    def complement(self, lo, hi):
        res, cur = [], lo
        for a, b in self._iv:
            if b <= lo:
                continue
            if a >= hi:
                break
            if a > cur:
                res.append((cur, a))
            cur = max(cur, b)
        if cur < hi:
            res.append((cur, hi))
        return IntervalSet(res)

    def __eq__(self, other):
        return isinstance(other, IntervalSet) and self._iv == other._iv

    def __repr__(self):
        return f"IntervalSet({self._iv!r})"
