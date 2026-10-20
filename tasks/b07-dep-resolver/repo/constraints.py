import operator
import re

_OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt,
        "==": operator.eq, "!=": operator.ne}
_CLAUSE = re.compile(r"^\s*(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+)*)\s*$")


def vtuple(version):
    """'1.10.0' -> (1, 10, 0). Versions compare numerically, component by component."""
    return tuple(int(p) for p in version.split("."))


def satisfies(version, spec):
    """spec is '*' / '' or comma separated clauses like '>=1.0,<2.0'."""
    spec = spec.strip()
    if spec in ("", "*"):
        return True
    v = vtuple(version)
    for clause in spec.split(","):
        m = _CLAUSE.match(clause)
        if not m:
            raise ValueError(f"bad constraint: {clause!r}")
        if not _OPS[m.group(1)](v, vtuple(m.group(2))):
            return False
    return True
