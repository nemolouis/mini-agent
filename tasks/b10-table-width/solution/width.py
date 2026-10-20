"""Terminal display width helpers."""
import re
import unicodedata

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def char_width(ch):
    """Columns taken by one character: 0 for combining marks and format characters
    (e.g. U+0301, U+200D), 2 for East Asian Wide / Fullwidth characters, otherwise 1."""
    if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    """Columns taken by a string. ANSI colour escape sequences (ESC [ ... letter) take 0."""
    return sum(char_width(c) for c in _ANSI.sub("", s))


def truncate(s, max_width, ellipsis="\u2026"):
    """Shorten plain text (no ANSI) so that its display width is <= max_width.
    Text that already fits is returned unchanged. Otherwise as many leading characters as
    fit together with the ellipsis are kept and the ellipsis is appended. A wide character
    is never split or half-kept. max_width must be >= display_width(ellipsis), else ValueError."""
    ew = display_width(ellipsis)
    if max_width < ew:
        raise ValueError("max_width is smaller than the ellipsis")
    if display_width(s) <= max_width:
        return s
    budget, used, out = max_width - ew, 0, []
    for ch in s:
        w = char_width(ch)
        if used + w > budget:
            break
        out.append(ch)
        used += w
    return "".join(out) + ellipsis
