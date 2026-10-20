from normalize import normalize_headers
from reader import read_rows
from schema import coerce


def load(path, schema=None):
    rows = read_rows(path)
    if not rows:
        return []
    headers = normalize_headers(rows[0])
    schema = schema or {}
    out = []
    for n, r in enumerate(rows[1:], 2):
        if len(r) > len(headers):
            raise ValueError(f"row {n} has too many cells")
        cells = [c.strip() for c in r] + [None] * (len(headers) - len(r))
        out.append({h: (None if c is None else coerce(c, schema.get(h, "str")))
                    for h, c in zip(headers, cells)})
    return out
