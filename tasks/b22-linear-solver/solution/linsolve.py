from collections import namedtuple
from fractions import Fraction

Solution = namedtuple("Solution", "kind particular nullspace")


def solve(A, b):
    """Solve A x = b exactly (rational arithmetic) for x.

    A is a non-empty list of equal-length rows (ints, Fractions or strings accepted by
    Fraction), b a list with one entry per row. Mismatched or ragged input raises ValueError.

    Returns Solution(kind, particular, nullspace) where entries are Fractions:
      kind == "unique":    exactly one solution; particular is it; nullspace == [].
      kind == "none":      the system is inconsistent; particular is None; nullspace == [].
      kind == "infinite":  many solutions. Using Gauss-Jordan elimination to reduced row
                           echelon form (pivots chosen left to right, columns without a
                           pivot are the free variables):
                           * particular: the solution with every free variable = 0;
                           * nullspace: one vector per free variable, in increasing column
                             order; the vector has 1 at its free variable, 0 at every other
                             free variable, and the values of the pivot variables that make
                             A v = 0.
    """
    if not A or not A[0]:
        raise ValueError("empty system")
    n = len(A[0])
    if any(len(row) != n for row in A) or len(b) != len(A):
        raise ValueError("shape mismatch")
    M = [[Fraction(x) for x in row] + [Fraction(bi)] for row, bi in zip(A, b)]
    m = len(M)
    pivots, r = [], 0
    for c in range(n):
        p = next((i for i in range(r, m) if M[i][c] != 0), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]
        inv = M[r][c]
        M[r] = [x / inv for x in M[r]]
        for i in range(m):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [x - f * y for x, y in zip(M[i], M[r])]
        pivots.append(c)
        r += 1
        if r == m:
            break
    for i in range(r, m):
        if M[i][n] != 0:
            return Solution("none", None, [])
    free = [c for c in range(n) if c not in pivots]
    particular = [Fraction(0)] * n
    for row, c in enumerate(pivots):
        particular[c] = M[row][n]
    if not free:
        return Solution("unique", particular, [])
    basis = []
    for fc in free:
        v = [Fraction(0)] * n
        v[fc] = Fraction(1)
        for row, c in enumerate(pivots):
            v[c] = -M[row][fc]
        basis.append(v)
    return Solution("infinite", particular, basis)
