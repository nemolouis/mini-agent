def read_rows(path):
    """Return the file as a list of rows (lists of strings), blank rows removed."""
    with open(path) as f:
        text = f.read()
    rows = [line.split(",") for line in text.split("\n")]
    return [r for r in rows if any(c.strip() for c in r)]
