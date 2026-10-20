import pytest
from index import Index
from resolver import ResolutionError, resolve


def test_picks_newest():
    idx = Index({"a": {"1.0.0": {}, "1.2.0": {}, "1.5.0": {}}})
    assert resolve(idx, {"a": ">=1.0"}) == {"a": "1.5.0"}


def test_respects_constraint():
    idx = Index({"a": {"1.0.0": {}, "2.0.0": {}}})
    assert resolve(idx, {"a": "<2.0"}) == {"a": "1.0.0"}


def test_transitive():
    idx = Index({"app": {"1.0.0": {"lib": ">=1.0"}}, "lib": {"1.0.0": {}, "1.1.0": {}}})
    assert resolve(idx, {"app": "*"}) == {"app": "1.0.0", "lib": "1.1.0"}


def test_missing_package():
    with pytest.raises(ResolutionError):
        resolve(Index({}), {"nope": "*"})
