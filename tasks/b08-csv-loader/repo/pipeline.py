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
    for r in rows[1:]:
        cells = [c.strip() for c in r]
        out.append({h: coerce(c, schema.get(h, "str")) for h, c in zip(headers, cells)})
    return out
