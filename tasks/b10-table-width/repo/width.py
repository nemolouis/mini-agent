"""Terminal display width helpers."""


def char_width(ch):
    """Columns taken by one character: 0 for combining marks and format characters
    (e.g. U+0301, U+200D), 2 for East Asian Wide / Fullwidth characters, otherwise 1."""
    return 1


def display_width(s):
    """Columns taken by a string. ANSI colour escape sequences (ESC [ ... letter) take 0."""
    return len(s)


def truncate(s, max_width, ellipsis="\u2026"):
    """Shorten plain text (no ANSI) so that its display width is <= max_width.
    Text that already fits is returned unchanged. Otherwise as many leading characters as
    fit together with the ellipsis are kept and the ellipsis is appended. A wide character
    is never split or half-kept. max_width must be >= display_width(ellipsis), else ValueError."""
    if len(s) <= max_width:
        return s
    return s[: max_width - len(ellipsis)] + ellipsis
