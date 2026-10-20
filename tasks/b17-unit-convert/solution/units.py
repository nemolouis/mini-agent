class ConversionError(Exception):
    pass


# name -> (factor to SI base units, (length, mass, time) exponents)
UNITS = {
    "1": (1.0, (0, 0, 0)),
    "m": (1.0, (1, 0, 0)), "km": (1000.0, (1, 0, 0)), "cm": (0.01, (1, 0, 0)),
    "mm": (0.001, (1, 0, 0)), "mi": (1609.344, (1, 0, 0)), "ft": (0.3048, (1, 0, 0)),
    "in": (0.0254, (1, 0, 0)),
    "g": (0.001, (0, 1, 0)), "kg": (1.0, (0, 1, 0)), "lb": (0.45359237, (0, 1, 0)),
    "s": (1.0, (0, 0, 1)), "ms": (0.001, (0, 0, 1)), "min": (60.0, (0, 0, 1)),
    "h": (3600.0, (0, 0, 1)), "day": (86400.0, (0, 0, 1)),
    "N": (1.0, (1, 1, -2)), "kN": (1000.0, (1, 1, -2)),
    "J": (1.0, (2, 1, -2)), "kJ": (1000.0, (2, 1, -2)),
    "W": (1.0, (2, 1, -3)), "kW": (1000.0, (2, 1, -3)),
    "Pa": (1.0, (-1, 1, -2)), "kPa": (1000.0, (-1, 1, -2)),
    "L": (0.001, (3, 0, 0)),
}

import re

_TOKEN = re.compile(r"(?:(\d+)|([A-Za-z]+)|(.))")


def _tokens(expr):
    toks = []
    for m in _TOKEN.finditer(expr.replace(" ", "")):
        if m.group(1) is not None:
            toks.append(("int", m.group(1)))
        elif m.group(2) is not None:
            toks.append(("name", m.group(2)))
        else:
            toks.append(("op", m.group(3)))
    return toks


class _P:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("end", "")

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expr(self):
        f, d = self.term()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            f2, d2 = self.term()
            if op == "*":
                f, d = f * f2, tuple(x + y for x, y in zip(d, d2))
            else:
                f, d = f / f2, tuple(x - y for x, y in zip(d, d2))
        return f, d

    def term(self):
        f, d = self.factor()
        if self.peek() == ("op", "^"):
            self.take()
            sign = 1
            if self.peek() == ("op", "-"):
                self.take()
                sign = -1
            kind, val = self.take()
            if kind != "int":
                raise ConversionError("exponent must be an integer")
            n = sign * int(val)
            f, d = f ** n, tuple(x * n for x in d)
        return f, d

    def factor(self):
        kind, val = self.take()
        if kind == "name" or kind == "int":
            if val not in UNITS:
                raise ConversionError(f"unknown unit {val!r}")
            return UNITS[val]
        if (kind, val) == ("op", "("):
            r = self.expr()
            if self.take() != ("op", ")"):
                raise ConversionError("unbalanced parentheses")
            return r
        raise ConversionError(f"unexpected {val!r}")


def _parse(expr):
    p = _P(_tokens(expr))
    r = p.expr()
    if p.peek() != ("end", ""):
        raise ConversionError("unexpected trailing input")
    return r


def convert(value, src, dst):
    fs, ds = _parse(src)
    fd, dd = _parse(dst)
    if ds != dd:
        raise ConversionError(f"cannot convert {src} to {dst}")
    return value * fs / fd
