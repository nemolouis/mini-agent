import csv
import io


def read_rows(path):
    """Return the file as a list of rows (lists of strings), blank rows removed."""
    with open(path, "rb") as f:
        text = f.read().decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    return [r for r in rows if any(c.strip() for c in r)]
