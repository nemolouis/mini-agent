import copy
import re

from errors import PatchError
from pointer import parse_pointer

_INDEX = re.compile(r"^(0|[1-9][0-9]*)$")


def _index(token, length, allow_end=False, allow_dash=False):
    if token == "-":
        if allow_dash:
            return length
        raise PatchError("'-' is not valid here")
    if not _INDEX.match(token):
        raise PatchError(f"invalid array index {token!r}")
    i = int(token)
    if i > length or (i == length and not allow_end):
        raise PatchError(f"array index {i} out of range")
    return i


def _get(doc, tokens):
    cur = doc
    for t in tokens:
        if isinstance(cur, dict):
            if t not in cur:
                raise PatchError(f"missing member {t!r}")
            cur = cur[t]
        elif isinstance(cur, list):
            cur = cur[_index(t, len(cur))]
        else:
            raise PatchError("cannot descend into a scalar")
    return cur


def _equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, (dict, list)) or isinstance(b, (dict, list)):
        return False
    return a == b


def _add(doc, tokens, value):
    if not tokens:
        return value
    parent = _get(doc, tokens[:-1])
    key = tokens[-1]
    if isinstance(parent, dict):
        parent[key] = value
    elif isinstance(parent, list):
        parent.insert(_index(key, len(parent), allow_end=True, allow_dash=True), value)
    else:
        raise PatchError("cannot add into a scalar")
    return doc


def _remove(doc, tokens):
    if not tokens:
        raise PatchError("cannot remove the whole document")
    parent = _get(doc, tokens[:-1])
    key = tokens[-1]
    if isinstance(parent, dict):
        if key not in parent:
            raise PatchError(f"missing member {key!r}")
        del parent[key]
    elif isinstance(parent, list):
        del parent[_index(key, len(parent))]
    else:
        raise PatchError("cannot remove from a scalar")
    return doc


def _need(op, name):
    if name not in op:
        raise PatchError(f"{op.get('op')!r} requires {name!r}")
    return op[name]


def apply_patch(doc, ops):
    doc = copy.deepcopy(doc)
    for op in ops:
        if not isinstance(op, dict) or "op" not in op:
            raise PatchError("operation must be an object with 'op'")
        kind = op["op"]
        tokens = parse_pointer(_need(op, "path"))
        if kind == "add":
            doc = _add(doc, tokens, copy.deepcopy(_need(op, "value")))
        elif kind == "remove":
            doc = _remove(doc, tokens)
        elif kind == "replace":
            value = copy.deepcopy(_need(op, "value"))
            if not tokens:
                doc = value
            else:
                _get(doc, tokens)
                parent = _get(doc, tokens[:-1])
                if isinstance(parent, dict):
                    parent[tokens[-1]] = value
                else:
                    parent[_index(tokens[-1], len(parent))] = value
        elif kind in ("move", "copy"):
            src = parse_pointer(_need(op, "from"))
            if kind == "move":
                if src == tokens:
                    _get(doc, src)
                    continue
                if tokens[:len(src)] == src and len(tokens) > len(src):
                    raise PatchError("cannot move a value into its own child")
            value = copy.deepcopy(_get(doc, src))
            if kind == "move":
                doc = _remove(doc, src)
            doc = _add(doc, tokens, value)
        elif kind == "test":
            if not _equal(_get(doc, tokens), _need(op, "value")):
                raise PatchError("test failed")
        else:
            raise PatchError(f"unknown op {kind!r}")
    return doc
