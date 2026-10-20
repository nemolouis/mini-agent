import pytest
from errors import CycleError
from graph import build_order


def test_simple():
    assert build_order({"a": ["b", "c"], "b": ["c"], "c": []}) == ["c", "b", "a"]


def test_ties_alphabetical():
    assert build_order({"x": [], "a": [], "m": []}) == ["a", "m", "x"]


def test_dependency_only_nodes_included():
    assert build_order({"app": ["lib"]}) == ["lib", "app"]


def test_dependency_order_with_unsorted_input():
    assert build_order({"z": ["a"], "a": []}) == ["a", "z"]


def test_cycle():
    with pytest.raises(CycleError):
        build_order({"a": ["b"], "b": ["a"]})


def test_self_cycle():
    with pytest.raises(CycleError):
        build_order({"a": ["a"]})


def test_diamond_not_a_cycle():
    assert build_order({"top": ["l", "r"], "l": ["base"], "r": ["base"]}) == ["base", "l", "r", "top"]
