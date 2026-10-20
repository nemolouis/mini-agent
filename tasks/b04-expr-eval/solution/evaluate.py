"""Evaluation.

evaluate(src, env=None) parses and evaluates `src`. Functions: abs(x), min(a, ...),
max(a, ...) (at least one argument), round(x), sqrt(x).

Errors: syntax problems raise errors.ParseError. Everything that goes wrong while
evaluating raises errors.EvalError and never a bare Python exception: unknown variable,
unknown function, wrong number of arguments, division or modulo by zero, sqrt of a
negative number.
"""
import math

from errors import EvalError
from grammar import parse

FUNCS = {"abs": (abs, 1, 1), "min": (lambda *a: min(a), 1, None), "max": (lambda *a: max(a), 1, None),
         "round": (round, 1, 1), "sqrt": (math.sqrt, 1, 1)}


def run(node, env):
    k = node[0]
    if k == "num":
        return node[1]
    if k == "name":
        if node[1] not in env:
            raise EvalError(f"unknown variable {node[1]!r}")
        return env[node[1]]
    if k == "neg":
        return -run(node[1], env)
    if k == "bin":
        op, l, r = node[1], run(node[2], env), run(node[3], env)
        try:
            if op == "+":
                return l + r
            if op == "-":
                return l - r
            if op == "*":
                return l * r
            if op == "/":
                return l / r
            if op == "%":
                return l % r
            return l ** r
        except ZeroDivisionError:
            raise EvalError("division by zero")
        except OverflowError as e:
            raise EvalError(str(e))
    name = node[1]
    if name not in FUNCS:
        raise EvalError(f"unknown function {name!r}")
    fn, lo, hi = FUNCS[name]
    args = [run(a, env) for a in node[2]]
    if len(args) < lo or (hi is not None and len(args) > hi):
        raise EvalError(f"wrong number of arguments for {name}")
    try:
        return fn(*args)
    except (ValueError, TypeError) as e:
        raise EvalError(str(e))


def evaluate(src, env=None):
    return run(parse(src), env or {})
