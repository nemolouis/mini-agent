"""Split a test file into a visible part and the full (hidden) one, at the level of test functions."""
from __future__ import annotations

import ast
import re

TestKey = tuple[str, str | None, str]       # (file, class or None, function)


def find_tests(source: str) -> list[tuple[str | None, str]]:
    """(class, name) of every test function: `test*` at module level or directly inside a class."""
    out: list[tuple[str | None, str]] = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            out.append((None, node.name))
        elif isinstance(node, ast.ClassDef):
            out += [(node.name, n.name) for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")]
    return out


def node_key(nodeid: str) -> TestKey | None:
    """'tests/test_a.py::TestX::test_y[param]' -> ('tests/test_a.py', 'TestX', 'test_y')."""
    parts = re.sub(r"\[.*\]$", "", nodeid.strip()).split("::")
    if len(parts) == 2:
        return parts[0], None, parts[1]
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return None


def _span(n) -> tuple[int, int]:
    start = min([n.lineno] + [d.lineno for d in getattr(n, "decorator_list", [])])
    return start, n.end_lineno


def keep_only(source: str, keep: set[tuple[str | None, str]]) -> str:
    """The source with every test function not in `keep` deleted. A class left without anything but removed tests
    is deleted as a whole; a class that keeps other members gets `pass` if it would otherwise be empty."""
    lines = source.splitlines(keepends=True)
    drop: list[tuple[int, int]] = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            if (None, node.name) not in keep:
                drop.append(_span(node))
        elif isinstance(node, ast.ClassDef):
            removed = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and n.name.startswith("test") and (node.name, n.name) not in keep]
            rest = [n for n in node.body if n not in removed and not (
                isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]
            if removed and not rest:
                drop.append(_span(node))
            else:
                drop += [_span(n) for n in removed]
    for a, b in sorted(drop, reverse=True):
        del lines[a - 1:b]
    return "".join(lines)


def close_over_calls(source: str, keep: set[tuple[str | None, str]]) -> set[tuple[str | None, str]]:
    """`keep` plus every test function that a kept one calls (a test calling another test, or `self.test_x()`): deleting the
    callee would turn the caller into a NameError/AttributeError, i.e. a failure that has nothing to do with the bug."""
    tree = ast.parse(source)
    funcs: dict[tuple[str | None, str], ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            funcs[(None, node.name)] = node
        elif isinstance(node, ast.ClassDef):
            for n in node.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
                    funcs[(node.name, n.name)] = n
    module_level = {name for (c, name) in funcs if c is None}
    out, todo = set(keep), list(keep)
    while todo:
        key = todo.pop()
        node = funcs.get(key)
        if node is None:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in module_level:
                dep = (None, sub.id)
            elif isinstance(sub, ast.Attribute) and key[0] is not None and (key[0], sub.attr) in funcs:
                dep = (key[0], sub.attr)
            else:
                continue
            if dep not in out:
                out.add(dep)
                todo.append(dep)
    return out
