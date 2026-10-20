from errors import PatchError
from pointer import parse_pointer


def _resolve(doc, tokens):
    cur = doc
    for t in tokens:
        if isinstance(cur, dict):
            cur = cur[t]
        elif isinstance(cur, list):
            cur = cur[int(t)]
        else:
            raise PatchError("cannot descend")
    return cur


def apply_patch(doc, ops):
    for op in ops:
        kind = op["op"]
        tokens = parse_pointer(op["path"])
        if kind in ("add", "replace"):
            if not tokens:
                doc = op["value"]
                continue
            parent = _resolve(doc, tokens[:-1])
            key = tokens[-1]
            if isinstance(parent, list):
                parent[int(key)] = op["value"]
            else:
                parent[key] = op["value"]
        elif kind == "remove":
            parent = _resolve(doc, tokens[:-1])
            if isinstance(parent, list):
                del parent[int(tokens[-1])]
            else:
                del parent[tokens[-1]]
        elif kind == "move":
            src = parse_pointer(op["from"])
            value = _resolve(doc, src)
            parent = _resolve(doc, tokens[:-1])
            parent[tokens[-1]] = value
        elif kind == "copy":
            value = _resolve(doc, parse_pointer(op["from"]))
            parent = _resolve(doc, tokens[:-1])
            parent[tokens[-1]] = value
        elif kind == "test":
            if _resolve(doc, tokens) != op["value"]:
                raise PatchError("test failed")
    return doc
