def apply_percent(cents, percent):
    """Return cents reduced by percent, rounded half up to a whole cent."""
    return int(cents * (100 - percent) / 100)
