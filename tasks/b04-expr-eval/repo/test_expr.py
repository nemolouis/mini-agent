import pytest
from evaluate import evaluate


def test_precedence():
    assert evaluate("1+2*3") == 7
    assert evaluate("(1+2)*3") == 9


def test_variables():
    assert evaluate("x*2 + y", {"x": 4, "y": 1}) == 9


def test_division():
    assert evaluate("10/4") == 2.5


def test_abs():
    assert evaluate("abs(-3)") == 3
