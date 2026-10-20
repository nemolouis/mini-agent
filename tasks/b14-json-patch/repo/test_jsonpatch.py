import pytest
from errors import PatchError
from jsonpatch import apply_patch


def test_add_member():
    assert apply_patch({"foo": "bar"}, [{"op": "add", "path": "/baz", "value": "qux"}]) == {"foo": "bar", "baz": "qux"}


def test_replace():
    assert apply_patch({"a": 1}, [{"op": "replace", "path": "/a", "value": 2}]) == {"a": 2}


def test_remove_member():
    assert apply_patch({"a": 1, "b": 2}, [{"op": "remove", "path": "/a"}]) == {"b": 2}


def test_test_failure():
    with pytest.raises(PatchError):
        apply_patch({"a": 1}, [{"op": "test", "path": "/a", "value": 2}])
