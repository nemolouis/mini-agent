import re
from functools import total_ordering

_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$")


@total_ordering
class Version:
    def __init__(self, major, minor, patch, pre=(), build=()):
        self.major, self.minor, self.patch = major, minor, patch
        self.pre, self.build = tuple(pre), tuple(build)

    @classmethod
    def parse(cls, text):
        m = _RE.match(text)
        if not m:
            raise ValueError(f"invalid version: {text!r}")
        pre = tuple(m.group(4).split(".")) if m.group(4) else ()
        build = tuple(m.group(5).split(".")) if m.group(5) else ()
        return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)), pre, build)

    def _key(self):
        return (self.major, self.minor, self.patch, self.pre, self.build)

    def __eq__(self, other):
        return isinstance(other, Version) and self._key() == other._key()

    def __lt__(self, other):
        from compare import compare
        return compare(self, other) < 0

    def __hash__(self):
        return hash(self._key())

    def __str__(self):
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre:
            s += "-" + ".".join(self.pre)
        if self.build:
            s += "+" + ".".join(self.build)
        return s

    def __repr__(self):
        return f"Version({str(self)!r})"
