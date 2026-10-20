import random
from fractions import Fraction as F
import pytest
from linsolve import Solution, solve


def matvec(A, x):
    return [sum(F(a) * xi for a, xi in zip(row, x)) for row in A]


def rref_pivots(A):
    M = [[F(x) for x in row] for row in A]
    pivots, r = [], 0
    for c in range(len(M[0])):
        p = next((i for i in range(r, len(M)) if M[i][c] != 0), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]
        M[r] = [x / M[r][c] for x in M[r]]
        for i in range(len(M)):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [x - f * y for x, y in zip(M[i], M[r])]
        pivots.append(c)
        r += 1
        if r == len(M):
            break
    return pivots


def test_exactness_not_floats():
    s = solve([[1, 3], [3, 1]], [1, 1])
    assert s.kind == "unique" and s.particular == [F(1, 4), F(1, 4)]
    assert all(isinstance(v, F) for v in s.particular)


def test_needs_row_swap_zero_pivot():
    s = solve([[0, 2, 1], [1, 0, 0], [0, 1, 3]], [5, 2, 5])
    assert s.kind == "unique"
    assert matvec([[0, 2, 1], [1, 0, 0], [0, 1, 3]], s.particular) == [5, 2, 5]


def test_inconsistent():
    s = solve([[1, 1], [2, 2]], [1, 3])
    assert s.kind == "none" and s.particular is None and s.nullspace == []
    s = solve([[0, 0]], [1])
    assert s.kind == "none"
    s = solve([[1], [1], [1]], [1, 1, 2])
    assert s.kind == "none"


def test_infinite_one_free_variable_exact_form():
    # x + y + z = 3 ; y - z = 0  -> pivots x, y ; z free
    s = solve([[1, 1, 1], [0, 1, -1]], [3, 0])
    assert s.kind == "infinite"
    assert s.particular == [F(3), F(0), F(0)]
    assert s.nullspace == [[F(-2), F(1), F(1)]]


def test_infinite_two_free_variables_exact_form():
    s = solve([[1, 2, 0, 1]], [4])
    assert s.kind == "infinite"
    assert s.particular == [F(4), F(0), F(0), F(0)]
    assert s.nullspace == [[F(-2), F(1), F(0), F(0)], [F(0), F(0), F(1), F(0)], [F(-1), F(0), F(0), F(1)]]


def test_zero_matrix():
    s = solve([[0, 0], [0, 0]], [0, 0])
    assert s.kind == "infinite" and s.particular == [0, 0]
    assert s.nullspace == [[1, 0], [0, 1]]


def test_overdetermined_consistent_is_unique():
    s = solve([[1, 0], [0, 1], [1, 1]], [1, 2, 3])
    assert s.kind == "unique" and s.particular == [F(1), F(2)]


def test_underdetermined_with_dependent_rows():
    s = solve([[1, 1, 0], [2, 2, 0], [0, 0, 1]], [1, 2, 5])
    assert s.kind == "infinite"
    assert s.particular == [F(1), F(0), F(5)]
    assert s.nullspace == [[F(-1), F(1), F(0)]]


def test_input_variants():
    s = solve([["1/2", 1], [1, "1/3"]], ["1", 2])
    assert s.kind == "unique"
    assert matvec([[F(1, 2), 1], [1, F(1, 3)]], s.particular) == [1, 2]


@pytest.mark.parametrize("A,b", [([], []), ([[1, 2], [3]], [1, 2]), ([[1, 2]], [1, 2]), ([[]], [1])])
def test_bad_shapes(A, b):
    with pytest.raises(ValueError):
        solve(A, b)


def test_random_unique_roundtrip():
    rng = random.Random(8)
    done = 0
    while done < 150:
        n = rng.randint(1, 5)
        A = [[rng.randint(-6, 6) for _ in range(n)] for _ in range(n)]
        if len(rref_pivots(A)) < n:
            continue
        x = [F(rng.randint(-9, 9), rng.randint(1, 5)) for _ in range(n)]
        b = matvec(A, x)
        s = solve(A, b)
        assert s.kind == "unique" and s.particular == x
        done += 1


def test_random_rank_deficient_systems():
    rng = random.Random(9)
    for _ in range(200):
        n = rng.randint(2, 5)
        m = rng.randint(1, 5)
        r = rng.randint(1, min(m, n))
        B = [[rng.randint(-3, 3) for _ in range(r)] for _ in range(m)]
        C = [[rng.randint(-3, 3) for _ in range(n)] for _ in range(r)]
        A = [[sum(B[i][k] * C[k][j] for k in range(r)) for j in range(n)] for i in range(m)]
        x0 = [F(rng.randint(-5, 5)) for _ in range(n)]
        b = matvec(A, x0)                       # consistent by construction
        s = solve(A, b)
        pivots = rref_pivots(A)
        free = [c for c in range(n) if c not in pivots]
        if free:
            assert s.kind == "infinite"
            assert matvec(A, s.particular) == b
            assert all(s.particular[c] == 0 for c in free)
            assert len(s.nullspace) == len(free)
            for v, fc in zip(s.nullspace, free):
                assert matvec(A, v) == [0] * m
                assert v[fc] == 1 and all(v[o] == 0 for o in free if o != fc)
        else:
            assert s.kind == "unique" and s.particular == x0
        # make it inconsistent when a dependent row exists
        if len(pivots) < m:
            dep = next(i for i in range(m) if True)
            A2 = [row[:] for row in A] + [[2 * v for v in A[0]]]
            b2 = b + [2 * b[0] + 1]
            assert solve(A2, b2).kind == "none"
