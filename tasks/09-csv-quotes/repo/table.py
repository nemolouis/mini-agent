from rows import parse_line


def load(text, types=None):
    lines = [l for l in text.splitlines() if l.strip()]
    header = parse_line(lines[0])
    types = types or {}
    out = []
    for line in lines[1:]:
        vals = parse_line(line)
        out.append({h: types.get(h, str)(v) for h, v in zip(header, vals)})
    return out
