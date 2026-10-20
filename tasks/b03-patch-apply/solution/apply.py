from patch import PatchError, parse


def _split(text):
    if text == "":
        return []
    ls = text.split("\n")
    if text.endswith("\n"):
        ls.pop()
    return ls


def apply_patch(text, diff):
    """Apply a unified diff to `text` and return the new text.

    Line numbers in hunk headers refer to the ORIGINAL text. For a hunk with old_len == 0
    the header number is the line AFTER which new lines are inserted (0 = at the start).
    Every context and removed line must match the original exactly, otherwise PatchError
    is raised. The result ends with a newline iff the original did, or the original was
    empty and the result is not."""
    lines = _split(text)
    offset = 0
    for h in parse(diff):
        start = (h.old_start - 1 if h.old_len > 0 else h.old_start) + offset
        if start < 0 or start > len(lines):
            raise PatchError(f"hunk at line {h.old_start} is out of range")
        pos, new = start, []
        for op, s in h.lines:
            if op in (" ", "-"):
                if pos >= len(lines) or lines[pos] != s:
                    raise PatchError(f"hunk at line {h.old_start} does not match at line {pos + 1}")
                pos += 1
                if op == " ":
                    new.append(s)
            elif op == "+":
                new.append(s)
        lines[start:pos] = new
        offset += len(new) - (pos - start)
    out = "\n".join(lines)
    if lines and (text == "" or text.endswith("\n")):
        out += "\n"
    return out
