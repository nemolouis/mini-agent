import pytest
from errors import CycleError, InterpolationError, InterpolationSyntaxError, UndefinedVariable
from interp import expand, expand_env


def test_nested_default():
    assert expand("${A:-${B:-x}}", {}) == "x"
    assert expand("${A:-${B:-x}}", {"B": "b"}) == "b"
    assert expand("${A:-${B}-${C:-c}}", {"B": "b"}) == "b-c"


def test_default_followed_by_text():
    assert expand("[${A:-x}]", {}) == "[x]"
    assert expand("[${A:-${B:-y}}]!", {}) == "[y]!"


def test_escape():
    assert expand("cost: $$5", {}) == "cost: $5"
    assert expand("$${NAME}", {"NAME": "x"}) == "${NAME}"
    assert expand("$$$${A}", {"A": "1"}) == "$${A}"


def test_literal_dollar():
    assert expand("a $ b", {}) == "a $ b"
    assert expand("100$", {}) == "100$"
    assert expand("$x", {"x": "1"}) == "$x"


def test_empty_value_uses_default_or_empty():
    assert expand("${A:-d}", {"A": ""}) == "d"
    assert expand("[${A}]", {"A": ""}) == "[]"


def test_values_expanded_recursively():
    assert expand("${A}", {"A": "${B}/x", "B": "${C}", "C": "root"}) == "root/x"


def test_escape_in_value_is_resolved_once():
    assert expand("${A}", {"A": "$$B"}) == "$B"


def test_cycles():
    with pytest.raises(CycleError):
        expand("${A}", {"A": "${B}", "B": "${A}"})
    with pytest.raises(CycleError):
        expand("${A}", {"A": "x${A}"})


def test_repeated_reference_is_not_a_cycle():
    assert expand("${A}${A}", {"A": "${B}", "B": "v"}) == "vv"
    assert expand("${A}", {"A": "${B}${B}", "B": "v"}) == "vv"


def test_syntax_errors():
    for t in ["${A", "${}", "x ${A:-b", "${A:-${B}"]:
        with pytest.raises(InterpolationSyntaxError):
            expand(t, {"A": "1", "B": "2"})


def test_hierarchy_and_undefined_in_default():
    with pytest.raises(InterpolationError):
        expand("${A}", {})
    with pytest.raises(UndefinedVariable):
        expand("${A:-${B}}", {})


def test_expand_env():
    env = {"HOME": "/h", "BIN": "${HOME}/bin", "PATH": "${BIN}:${EXTRA:-/usr/bin}"}
    assert expand_env(env) == {"HOME": "/h", "BIN": "/h/bin", "PATH": "/h/bin:/usr/bin"}


def test_expand_env_cycle():
    with pytest.raises(CycleError):
        expand_env({"A": "${B}", "B": "${A}"})
    with pytest.raises(CycleError):
        expand_env({"A": "${A}"})
