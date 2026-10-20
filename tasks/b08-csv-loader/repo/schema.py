def coerce(value, typ):
    if typ == "int":
        return int(value)
    if typ == "float":
        return float(value)
    if typ == "bool":
        return bool(value)
    return value
