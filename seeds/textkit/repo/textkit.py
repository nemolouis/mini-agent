"""Small text helpers."""
import re

_SMALL = {"a", "an", "the", "and", "or", "of", "in", "on", "to", "for"}
_ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def slugify(text):
    """Lower-case ASCII slug: runs of non-alphanumerics become one '-', no leading or trailing '-'."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return s.strip("-")


def truncate(text, limit, suffix="..."):
    """At most `limit` characters; if it had to be cut the result ends with `suffix`."""
    if len(text) <= limit:
        return text
    if limit <= len(suffix):
        return suffix[:limit]
    return text[: limit - len(suffix)] + suffix


def wrap(text, width):
    """Greedy word wrap; a word longer than `width` stays on its own line."""
    lines, cur = [], ""
    for word in text.split():
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= width:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def camel_to_snake(name):
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()


def snake_to_camel(name):
    first, *rest = name.split("_")
    return first + "".join(p.capitalize() for p in rest if p)


def title_case(text):
    """Capitalise words; small words stay lower-case unless first or last."""
    words = text.split()
    out = []
    for i, w in enumerate(words):
        if 0 < i < len(words) - 1 and w.lower() in _SMALL:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


def is_palindrome(text):
    """Ignores case and everything that is not a letter or digit."""
    chars = [c.lower() for c in text if c.isalnum()]
    return chars == chars[::-1]


def to_roman(n):
    if not 1 <= n <= 3999:
        raise ValueError("out of range")
    out = []
    for value, sym in _ROMAN:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def from_roman(s):
    total, i = 0, 0
    for value, sym in _ROMAN:
        while s.startswith(sym, i):
            total += value
            i += len(sym)
    if i != len(s) or total == 0 or to_roman(total) != s:
        raise ValueError("not a roman numeral")
    return total


def count_words(text):
    """Word frequencies, case-insensitive, words are runs of letters and apostrophes."""
    counts = {}
    for w in re.findall(r"[A-Za-z']+", text.lower()):
        counts[w] = counts.get(w, 0) + 1
    return counts
