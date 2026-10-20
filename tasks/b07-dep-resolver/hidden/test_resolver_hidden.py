import pytest
from index import Index
from resolver import ResolutionError, resolve


def test_numeric_version_order():
    idx = Index({"a": {"1.9.0": {}, "1.10.0": {}, "1.2.0": {}}})
    assert resolve(idx, {"a": "*"}) == {"a": "1.10.0"}


def test_backtrack_on_missing_transitive():
    idx = Index({
        "a": {"1.0.0": {"b": ">=1.0"}},
        "b": {"2.0.0": {"c": ">=2.0"}, "1.0.0": {}},
        "c": {"1.0.0": {}},
    })
    assert resolve(idx, {"a": "*"}) == {"a": "1.0.0", "b": "1.0.0"}


def test_backtrack_across_siblings():
    idx = Index({
        "x": {"2.0.0": {"z": ">=2.0"}, "1.0.0": {"z": "<2.0"}},
        "y": {"1.0.0": {"z": "<2.0"}},
        "z": {"2.0.0": {}, "1.0.0": {}},
    })
    assert resolve(idx, {"x": "*", "y": "*"}) == {"x": "1.0.0", "y": "1.0.0", "z": "1.0.0"}


def test_backtrack_into_already_chosen_conflict():
    idx = Index({
        "app": {"1.0.0": {"lib": ">=1.0", "plugin": "*"}},
        "lib": {"2.0.0": {}, "1.0.0": {}},
        "plugin": {"2.0.0": {"lib": "<2.0"}, "1.0.0": {"lib": ">=1.0"}},
    })
    # lib is decided first (newest, 2.0.0); plugin 2.0.0 then conflicts, so plugin 1.0.0 is used
    r = resolve(idx, {"app": "*"})
    assert r == {"app": "1.0.0", "lib": "2.0.0", "plugin": "1.0.0"}


def test_prefers_newest_when_no_conflict():
    idx = Index({
        "app": {"1.0.0": {"lib": "*", "plugin": "*"}},
        "lib": {"2.0.0": {}, "1.0.0": {}},
        "plugin": {"1.0.0": {"lib": ">=1.0"}},
    })
    assert resolve(idx, {"app": "*"}) == {"app": "1.0.0", "lib": "2.0.0", "plugin": "1.0.0"}


def test_unsatisfiable():
    idx = Index({"a": {"1.0.0": {"b": ">=2.0"}}, "b": {"1.0.0": {}}})
    with pytest.raises(ResolutionError):
        resolve(idx, {"a": "*"})


def test_unsatisfiable_after_exhausting_all_choices():
    idx = Index({
        "x": {"2.0.0": {"z": ">=2.0"}, "1.0.0": {"z": ">=3.0"}},
        "y": {"1.0.0": {"z": "<2.0"}},
        "z": {"2.0.0": {}, "1.0.0": {}},
    })
    with pytest.raises(ResolutionError):
        resolve(idx, {"x": "*", "y": "*"})


def test_missing_dependency_package_backtracks():
    idx = Index({
        "a": {"2.0.0": {"ghost": "*"}, "1.0.0": {}},
    })
    assert resolve(idx, {"a": "*"}) == {"a": "1.0.0"}
