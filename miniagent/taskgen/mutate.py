"""Mutation operators. Candidates are found with `ast` (for positions and context) and applied as minimal byte-level
text edits, so the rest of the file keeps its formatting, comments and docstrings. A candidate is dropped when the text
around the operator is not exactly what the AST says it should be (comments, line continuations in odd places...)."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

FAMILIES = ("compare", "arith", "boolop", "negate", "const", "loopctl", "delete")


@dataclass(frozen=True)
class Mutant:
    family: str
    line: int
    description: str
    edits: tuple  # ((start_byte, end_byte, replacement_bytes), ...), non-overlapping


class _Src:
    def __init__(self, source: str):
        self.b = source.encode("utf-8")
        self.starts = [0] + [m.end() for m in re.finditer(rb"\n", self.b)]

    def off(self, lineno: int, col: int) -> int:
        return self.starts[lineno - 1] + col

    def span(self, node) -> tuple[int, int]:
        return self.off(node.lineno, node.col_offset), self.off(node.end_lineno, node.end_col_offset)


_GAP = rb"[\s()\\]*"


def _between(src: _Src, a_end: int, b_start: int, token: bytes):
    """Position of `token` in the gap between two operands, if the gap holds nothing else."""
    if b_start < a_end:
        return None
    m = re.fullmatch(_GAP + b"(?P<t>" + token + b")" + _GAP, src.b[a_end:b_start])
    return None if m is None else (a_end + m.start("t"), a_end + m.end("t"))


_CMP = {ast.Lt: (rb"<", b"<="), ast.LtE: (rb"<=", b"<"), ast.Gt: (rb">", b">="), ast.GtE: (rb">=", b">"),
        ast.Eq: (rb"==", b"!="), ast.NotEq: (rb"!=", b"=="), ast.Is: (rb"is", b"is not"),
        ast.IsNot: (rb"is\s+not", b"is"), ast.In: (rb"in", b"not in"), ast.NotIn: (rb"not\s+in", b"in")}
_NEG = {ast.Lt: (rb"<", b">="), ast.LtE: (rb"<=", b">"), ast.Gt: (rb">", b"<="), ast.GtE: (rb">=", b"<"),
        ast.Eq: (rb"==", b"!="), ast.NotEq: (rb"!=", b"=="), ast.Is: (rb"is", b"is not"),
        ast.IsNot: (rb"is\s+not", b"is"), ast.In: (rb"in", b"not in"), ast.NotIn: (rb"not\s+in", b"in")}
_ARITH = {ast.Add: (rb"\+", b"-"), ast.Sub: (rb"-", b"+"), ast.Mult: (rb"\*", b"//"), ast.FloorDiv: (rb"//", b"*"),
          ast.Div: (rb"/", b"//")}


def candidates(source: str) -> list[Mutant]:
    if "\r" in source:
        return []
    tree = ast.parse(source)
    src = _Src(source)
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    out: list[Mutant] = []

    def text(a, b): return src.b[a:b].decode("utf-8", "replace")

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            for i, op in enumerate(node.ops):
                spec = _CMP.get(type(op))
                if spec is None:
                    continue
                pos = _between(src, src.span(operands[i])[1], src.span(operands[i + 1])[0], spec[0])
                if pos:
                    out.append(Mutant("compare", node.lineno, f"`{text(*pos)}` -> `{spec[1].decode()}`", ((*pos, spec[1]),)))
        elif isinstance(node, ast.BinOp):
            spec = _ARITH.get(type(node.op))
            if spec:
                pos = _between(src, src.span(node.left)[1], src.span(node.right)[0], spec[0])
                if pos:
                    out.append(Mutant("arith", node.lineno, f"`{text(*pos)}` -> `{spec[1].decode()}`", ((*pos, spec[1]),)))
        elif isinstance(node, ast.BoolOp):
            word, new = (rb"and", b"or") if isinstance(node.op, ast.And) else (rb"or", b"and")
            edits = []
            for a, b in zip(node.values, node.values[1:]):
                pos = _between(src, src.span(a)[1], src.span(b)[0], word)
                if pos is None:
                    edits = []
                    break
                edits.append((*pos, new))
            if edits:
                out.append(Mutant("boolop", node.lineno, f"`{word.decode()}` -> `{new.decode()}`", tuple(edits)))
        elif isinstance(node, (ast.If, ast.IfExp)):
            t = node.test
            if isinstance(t, ast.Compare) and len(t.ops) == 1 and type(t.ops[0]) in _NEG:
                # negate a plain comparison by inverting its operator, not by wrapping it in `not (...)`: the wrapped form
                # is a giveaway that points straight at the mutation
                token, new = _NEG[type(t.ops[0])]
                pos = _between(src, src.span(t.left)[1], src.span(t.comparators[0])[0], token)
                if pos:
                    out.append(Mutant("negate", node.lineno, f"condition `{text(*src.span(t))[:60]}` negated", ((*pos, new),)))
            elif not (isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not)):
                a, b = src.span(t)
                out.append(Mutant("negate", node.lineno, f"condition `{text(a, b)[:60]}` negated", ((a, a, b"not ("), (b, b, b")"))))
        elif isinstance(node, ast.Constant) and type(node.value) is int:
            a, b = src.span(node)
            v = node.value
            under_neg = isinstance(parents.get(node), ast.UnaryOp) and isinstance(parents[node].op, ast.USub)
            for new in (v + 1, v - 1):
                if abs(v) > 10 ** 6 or new < 0 or (new == 0 and under_neg):
                    continue
                out.append(Mutant("const", node.lineno, f"constant {v} -> {new}", ((a, b, str(new).encode()),)))
        elif isinstance(node, (ast.Break, ast.Continue)):
            a, b = src.span(node)
            new = b"continue" if isinstance(node, ast.Break) else b"break"
            out.append(Mutant("loopctl", node.lineno, f"`{text(a, b)}` -> `{new.decode()}`", ((a, b, new),)))
        elif isinstance(node, (ast.Assign, ast.AugAssign)) or (isinstance(node, ast.AnnAssign) and node.value is not None) \
                or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            a, b = src.span(node)
            out.append(Mutant("delete", node.lineno, f"statement `{text(a, b)[:60]}` removed", ((a, b, b"pass"),)))

    seen, unique = set(), []
    for m in out:
        if m.edits not in seen:
            seen.add(m.edits)
            unique.append(m)
    return unique


def apply(source: str, mutant: Mutant) -> str | None:
    """The mutated source, or None if it does not compile or is unchanged."""
    b = bytearray(source.encode("utf-8"))
    for start, end, new in sorted(mutant.edits, key=lambda e: e[0], reverse=True):
        b[start:end] = new
    try:
        text = bytes(b).decode("utf-8")
        compile(text, "<mutant>", "exec")
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return None
    return None if text == source else text
