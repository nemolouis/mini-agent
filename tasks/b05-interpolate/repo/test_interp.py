import pytest
from errors import UndefinedVariable
from interp import expand


def test_simple():
    assert expand("hello ${NAME}!", {"NAME": "world"}) == "hello world!"


def test_default():
    assert expand("${A:-fallback}", {}) == "fallback"
    assert expand("${A:-fallback}", {"A": "x"}) == "x"


def test_multiple():
    assert expand("${A}-${B}", {"A": "1", "B": "2"}) == "1-2"


def test_undefined():
    with pytest.raises(UndefinedVariable):
        expand("${MISSING}", {})
