def apply_percent(cents, percent):
    """Return cents reduced by percent, rounded half up to a whole cent."""
    return (cents * (100 - percent) + 50) // 100
