import pytest
from errors import EvalError, ExprError, ParseError
from evaluate import evaluate


@pytest.mark.parametrize("src,expected", [
    ("-2**2", -4), ("2**3**2", 512), ("2**-1", 0.5), ("(-2)**2", 4), ("-(-3)", 3), ("- -3", 3),
    ("2*-3", -6), ("1 - 2 - 3", -4), ("8/2/2", 2.0), ("7 % 4", 3), ("+3", 3), ("1.5+.5", 2.0),
    ("max(1, 5, 3)", 5), ("min(max(1,2),3)", 2), ("max(4)", 4), ("round(2.6)", 3), ("sqrt(9)", 3.0),
    ("2 * (3 + 4) ** 2", 98), ("-x ** 2", -9),
])
def test_values(src, expected):
    assert evaluate(src, {"x": 3}) == expected


@pytest.mark.parametrize("src", ["1/0", "5 % 0", "1 + y", "foo(1)", "abs(1, 2)", "min()", "sqrt(-1)", "abs()"])
def test_eval_errors(src):
    with pytest.raises(EvalError):
        evaluate(src)


@pytest.mark.parametrize("src", ["1 2", "(1", "1 +", "max(1,", "", "   ", "1 + * 2", "2 $ 3", "max(1 2)", "f(,1)", ")"])
def test_parse_errors(src):
    with pytest.raises(ParseError):
        evaluate(src)


def test_error_hierarchy():
    with pytest.raises(ExprError):
        evaluate("1/0")
    with pytest.raises(ExprError):
        evaluate("(")
