from fractions import Fraction as F
from linsolve import solve


def test_unique():
    s = solve([[2, 1], [1, 3]], [5, 10])
    assert s.kind == "unique" and s.particular == [F(1), F(3)]


def test_unique_with_fractions():
    s = solve([[3, 1], [1, 1]], [1, 1])
    assert s.particular == [F(0), F(1)]
