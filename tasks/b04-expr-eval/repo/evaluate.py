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

FUNCS = {"abs": abs, "min": min, "max": max, "round": round, "sqrt": math.sqrt}


def run(node, env):
    k = node[0]
    if k == "num":
        return node[1]
    if k == "name":
        return env[node[1]]
    if k == "neg":
        return -run(node[1], env)
    if k == "bin":
        op, l, r = node[1], run(node[2], env), run(node[3], env)
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
    args = [run(a, env) for a in node[2]]
    return FUNCS[node[1]](*args)


def evaluate(src, env=None):
    return run(parse(src), env or {})
