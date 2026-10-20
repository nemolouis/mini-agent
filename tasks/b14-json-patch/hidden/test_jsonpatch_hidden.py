import copy
import pytest
from errors import PatchError
from jsonpatch import apply_patch


def P(doc, *ops):
    return apply_patch(doc, list(ops))


def test_add_array_inserts():
    assert P({"foo": ["bar", "baz"]}, {"op": "add", "path": "/foo/1", "value": "qux"}) == {"foo": ["bar", "qux", "baz"]}


def test_add_array_append_dash_and_length_index():
    assert P({"foo": ["bar"]}, {"op": "add", "path": "/foo/-", "value": ["abc", "def"]}) == {"foo": ["bar", ["abc", "def"]]}
    assert P([1, 2], {"op": "add", "path": "/2", "value": 3}) == [1, 2, 3]


def test_add_nested_and_missing_parent():
    assert P({"foo": "bar"}, {"op": "add", "path": "/child", "value": {"grandchild": {}}}) == {"foo": "bar", "child": {"grandchild": {}}}
    with pytest.raises(PatchError):
        P({"foo": "bar"}, {"op": "add", "path": "/baz/bat", "value": "qux"})


def test_add_replaces_existing_member_and_root():
    assert P({"a": 1}, {"op": "add", "path": "/a", "value": 2}) == {"a": 2}
    assert P({"a": 1}, {"op": "add", "path": "", "value": [1]}) == [1]
    assert P({"a": 1}, {"op": "replace", "path": "", "value": 5}) == 5


def test_remove_array_element_shifts():
    assert P({"foo": ["bar", "qux", "baz"]}, {"op": "remove", "path": "/foo/1"}) == {"foo": ["bar", "baz"]}


def test_remove_and_replace_require_existing():
    for op in ({"op": "remove", "path": "/x"}, {"op": "replace", "path": "/x", "value": 1}):
        with pytest.raises(PatchError):
            P({"a": 1}, op)
    for path in ("/3", "/-"):
        with pytest.raises(PatchError):
            P([1, 2], {"op": "remove", "path": path})
        with pytest.raises(PatchError):
            P([1, 2], {"op": "replace", "path": path, "value": 0})


def test_move_member_and_array_element():
    assert P({"foo": {"bar": "baz", "waldo": "fred"}, "qux": {"corge": "grault"}},
             {"op": "move", "from": "/foo/waldo", "path": "/qux/thud"}) == \
        {"foo": {"bar": "baz"}, "qux": {"corge": "grault", "thud": "fred"}}
    assert P({"foo": ["all", "grass", "cows", "eat"]}, {"op": "move", "from": "/foo/1", "path": "/foo/3"}) == \
        {"foo": ["all", "cows", "eat", "grass"]}


def test_move_errors():
    with pytest.raises(PatchError):
        P({"a": {"b": 1}}, {"op": "move", "from": "/a", "path": "/a/c"})
    with pytest.raises(PatchError):
        P({"a": 1}, {"op": "move", "from": "/nope", "path": "/b"})
    assert P({"a": 1}, {"op": "move", "from": "/a", "path": "/a"}) == {"a": 1}


def test_copy_is_deep():
    out = P({"a": {"x": [1]}}, {"op": "copy", "from": "/a", "path": "/b"}, {"op": "add", "path": "/b/x/-", "value": 2})
    assert out == {"a": {"x": [1]}, "b": {"x": [1, 2]}}


def test_escapes():
    doc = {"/": 9, "~1": 10, "a~b": 1}
    assert P(doc, {"op": "test", "path": "/~01", "value": 10}) == doc
    assert P(doc, {"op": "test", "path": "/~1", "value": 9}) == doc
    assert P(doc, {"op": "test", "path": "/a~0b", "value": 1}) == doc
    with pytest.raises(PatchError):
        P(doc, {"op": "test", "path": "/~01", "value": "10"})


def test_test_op_json_equality():
    with pytest.raises(PatchError):
        P({"a": True}, {"op": "test", "path": "/a", "value": 1})
    with pytest.raises(PatchError):
        P({"a": 0}, {"op": "test", "path": "/a", "value": False})
    with pytest.raises(PatchError):
        P({"a": [1, True]}, {"op": "test", "path": "/a", "value": [1, 1]})
    assert P({"a": 1}, {"op": "test", "path": "/a", "value": 1.0}) == {"a": 1}
    assert P({"a": {"b": [1, 2]}}, {"op": "test", "path": "/a", "value": {"b": [1, 2]}}) == {"a": {"b": [1, 2]}}


def test_input_never_modified_and_all_or_nothing():
    doc = {"a": [1, 2], "b": {"c": 1}}
    snapshot = copy.deepcopy(doc)
    ops = [{"op": "add", "path": "/a/-", "value": 3}, {"op": "remove", "path": "/b/c"}]
    ops_snapshot = copy.deepcopy(ops)
    out = apply_patch(doc, ops)
    assert doc == snapshot and ops == ops_snapshot
    assert out == {"a": [1, 2, 3], "b": {}}
    bad = ops + [{"op": "remove", "path": "/nope"}]
    with pytest.raises(PatchError):
        apply_patch(doc, bad)
    assert doc == snapshot


def test_returned_doc_does_not_alias_op_values():
    value = {"k": [1]}
    out = apply_patch({}, [{"op": "add", "path": "/x", "value": value}])
    out["x"]["k"].append(2)
    assert value == {"k": [1]}


def test_bad_array_indexes():
    for path in ("/01", "/-1", "/x", "/1.5", "/ 1"):
        with pytest.raises(PatchError):
            P([1, 2, 3], {"op": "replace", "path": path, "value": 0})
    with pytest.raises(PatchError):
        P([1], {"op": "add", "path": "/5", "value": 0})


def test_bad_pointer_and_ops():
    with pytest.raises(PatchError):
        P({"a": 1}, {"op": "replace", "path": "a", "value": 2})
    with pytest.raises(PatchError):
        P({"a": 1}, {"op": "frobnicate", "path": "/a"})
    with pytest.raises(PatchError):
        P({"a": 1}, {"op": "add", "path": "/b"})
    with pytest.raises(PatchError):
        P({"a": 1}, {"op": "move", "path": "/b"})


def test_descend_through_scalar():
    with pytest.raises(PatchError):
        P({"a": 1}, {"op": "replace", "path": "/a/b", "value": 2})
