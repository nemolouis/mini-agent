_TRUE = {"true", "yes", "y", "1"}
_FALSE = {"false", "no", "n", "0"}


def coerce(value, typ):
    if typ == "str":
        return value
    if value == "":
        return None
    if typ == "int":
        return int(value)
    if typ == "float":
        return float(value)
    if typ == "bool":
        v = value.lower()
        if v in _TRUE:
            return True
        if v in _FALSE:
            return False
        raise ValueError(f"not a boolean: {value!r}")
    raise ValueError(f"unknown type: {typ!r}")
