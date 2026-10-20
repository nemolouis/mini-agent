import re

UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text):
    if not re.fullmatch(r"(\d+[hms])+", text):
        raise ValueError(f"invalid duration: {text!r}")
    return sum(int(n) * UNITS[u] for n, u in re.findall(r"(\d+)([hms])", text))
