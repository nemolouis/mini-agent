# JSON Patch subset

`apply_patch(doc, ops)` applies a list of operations to a JSON-like document (dict, list,
str, int, float, bool, None) and returns the **new** document. The input `doc` and `ops`
are never modified, whether the patch succeeds or fails. If any operation fails,
`PatchError` is raised and nothing is applied (all-or-nothing).

## Pointers (RFC 6901)
- `""` refers to the whole document.
- Otherwise the pointer must start with `/`; the rest is split on `/` into reference tokens.
- In a token, `~1` means `/` and `~0` means `~` (decode `~1` first, then `~0`).
- For arrays a token must be `0` or a positive integer without leading zeros, or `-`
  (only where stated below). Anything else is an error.

## Operations (each op is a dict with `op`, `path`, and `value` / `from` as needed)
- `add`: object parent: set the member (replacing an existing one). Array parent: insert
  before the given index; the index may equal the array length (append); `-` appends;
  larger indexes are an error. The parent must exist. With `path == ""` the document is
  replaced by `value`.
- `remove`: the target must exist; remove it (array elements after it shift down). `-` is invalid.
- `replace`: the target must exist; replace its value. `-` is invalid. `path == ""` replaces the document.
- `move`: remove the value at `from` and add it at `path`. `from` must exist. It is an error
  if `from` is a proper prefix of `path` (moving into one's own child). `from == path` is a no-op.
- `copy`: add a deep copy of the value at `from` at `path`. Later changes to one copy
  must not affect the other.
- `test`: succeed only if the value at `path` equals `value`; otherwise `PatchError`.
  Equality is JSON equality: `True` is not equal to `1`, `False` not equal to `0`
  (also when nested), `1` equals `1.0`, objects compare by members, arrays by order.
- Unknown `op` or missing required members raise `PatchError`.
