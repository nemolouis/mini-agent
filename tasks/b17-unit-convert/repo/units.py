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


def _parse(expr):
    """Return (factor, dims). Naive: the first '/' sends everything after it to the denominator."""
    num, _, den = expr.replace(" ", "").partition("/")
    factor, dims = 1.0, [0, 0, 0]
    for part, sign in ((num, 1), (den, -1)):
        if not part:
            continue
        for tok in part.split("*"):
            name, _, exp = tok.partition("^")
            e = int(exp) if exp else 1
            f, d = UNITS[name]
            factor *= f ** (e * sign)
            dims = [x + y * e * sign for x, y in zip(dims, d)]
    return factor, tuple(dims)


def convert(value, src, dst):
    fs, ds = _parse(src)
    fd, dd = _parse(dst)
    if ds != dd:
        raise ConversionError(f"cannot convert {src} to {dst}")
    return value * fs / fd
