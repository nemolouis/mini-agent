from width import display_width, truncate


def pad(text, width, align="left"):
    """Pad `text` with spaces to `width` display columns. align: left, right or center
    (center puts the extra space, if any, on the right)."""
    gap = max(width - len(text), 0)
    if align == "right":
        return " " * gap + text
    if align == "center":
        return " " * (gap // 2) + text + " " * (gap - gap // 2)
    return text + " " * gap


def render_table(headers, rows, align=None, max_col_width=None):
    """Render an ASCII grid:

        +-------+-----+
        | name  | qty |
        +-------+-----+
        | apple | 12  |
        +-------+-----+

    Column width is the widest cell (header included) in display columns. `align` is an
    optional list of 'left'/'right'/'center' per column. With `max_col_width`, every cell
    and header is passed through truncate(..., max_col_width) first. Cell values are str()'d.
    A row whose length differs from the header raises ValueError."""
    cols = len(headers)
    body = []
    for r in rows:
        if len(r) != cols:
            raise ValueError("row length does not match headers")
        body.append([str(c) for c in r])
    head = [str(h) for h in headers]
    if max_col_width:
        head = [truncate(h, max_col_width) for h in head]
        body = [[truncate(c, max_col_width) for c in r] for r in body]
    widths = [max(len(x) for x in col) for col in zip(head, *body)]
    aligns = align or ["left"] * cols

    def line(cells):
        return "| " + " | ".join(pad(c, w, a) for c, w, a in zip(cells, widths, aligns)) + " |"

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    return "\n".join([sep, line(head), sep, *[line(r) for r in body], sep])
