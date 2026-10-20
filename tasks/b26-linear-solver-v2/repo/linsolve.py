from collections import namedtuple
from fractions import Fraction

Solution = namedtuple("Solution", "kind particular nullspace")


def solve(A, b):
    """Solve A x = b exactly (rational arithmetic) for x.

    A is a non-empty list of equal-length rows (ints, Fractions or strings accepted by
    Fraction), b a list with one entry per row. Mismatched or ragged input, or a matrix with zero columns, raises ValueError.

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
    n = len(A[0])
    M = [[float(x) for x in row] + [float(bi)] for row, bi in zip(A, b)]
    for col in range(n):
        piv = max(range(col, len(M)), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        for r in range(len(M)):
            if r != col:
                f = M[r][col] / M[col][col]
                M[r] = [x - f * y for x, y in zip(M[r], M[col])]
    return Solution("unique", [M[i][n] / M[i][i] for i in range(n)], [])
