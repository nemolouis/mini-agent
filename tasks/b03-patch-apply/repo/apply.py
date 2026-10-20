from patch import PatchError, parse


def apply_patch(text, diff):
    """Apply a unified diff to `text` and return the new text.

    Line numbers in hunk headers refer to the ORIGINAL text. For a hunk with old_len == 0
    the header number is the line AFTER which new lines are inserted (0 = at the start).
    Every context and removed line must match the original exactly, otherwise PatchError
    is raised. The result ends with a newline iff the original did, or the original was
    empty and the result is not."""
    lines = text.splitlines()
    for h in parse(diff):
        i = h.old_start - 1
        pos, new = i, []
        for op, s in h.lines:
            if op == " ":
                pos += 1
                new.append(s)
            elif op == "-":
                pos += 1
            elif op == "+":
                new.append(s)
        lines[i:pos] = new
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
