import re
from dataclasses import dataclass, field

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(Exception):
    """Raised when a patch does not apply cleanly."""


@dataclass
class Hunk:
    old_start: int          # 1-based line number in the original text
    old_len: int            # number of original lines covered (0 for a pure insertion)
    lines: list = field(default_factory=list)  # (op, text); op is ' ', '-' or '+'


def parse(diff):
    """Parse a unified diff into hunks. Lines before the first hunk header (---/+++)
    are ignored. Inside a hunk every line is data: its first character is the operation
    (' ' context, '-' removed, '+' added) and the rest is the line text, even if the
    text itself starts with '--' or '++'. Lines starting with a backslash are ignored."""
    hunks, cur = [], None
    for line in diff.split("\n"):
        m = HUNK.match(line)
        if m:
            old_len = 1 if m.group(2) is None else int(m.group(2))
            cur = Hunk(int(m.group(1)), old_len)
            hunks.append(cur)
            continue
        if cur is None or line.startswith("\\"):
            continue
        if line == "":
            # an empty context line whose single space was stripped; treat as empty context
            cur.lines.append((" ", ""))
            continue
        cur.lines.append((line[0], line[1:]))
    return hunks
