import re

from errors import ParseError

_TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|([A-Za-z_]\w*)|(\*\*|[-+*/%(),]))")


def tokenize(src):
    """Return a list of (kind, value, position) with kind in num/name/op, ending with
    ('eof', '', len(src)). Unknown characters raise ParseError."""
    tokens, pos = [], 0
    while pos < len(src):
        if src[pos:].strip() == "":
            break
        m = _TOKEN.match(src, pos)
        if not m:
            raise ParseError(f"unexpected character {src[pos]!r} at position {pos}")
        if m.group(1) is not None:
            text = m.group(1)
            tokens.append(("num", float(text) if "." in text else int(text), m.start(1)))
        elif m.group(2) is not None:
            tokens.append(("name", m.group(2), m.start(2)))
        else:
            tokens.append(("op", m.group(3), m.start(3)))
        pos = m.end()
    tokens.append(("eof", "", len(src)))
    return tokens
