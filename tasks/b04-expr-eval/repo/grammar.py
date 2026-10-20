"""Recursive-descent parser.

Grammar (lowest to highest precedence):
    expr   := term (('+' | '-') term)*
    term   := unary (('*' | '/' | '%') unary)*
    unary  := ('-' | '+') unary | power
    power  := atom ('**' unary)?          # right associative: 2**3**2 == 2**(3**2)
    atom   := NUMBER | NAME | NAME '(' [expr (',' expr)*] ')' | '(' expr ')'

Consequences: -2**2 == -4 (unary minus binds looser than **), 2**-1 == 0.5.
The whole input must be consumed; trailing tokens raise ParseError.
AST nodes: ("num", v) ("name", n) ("neg", e) ("bin", op, l, r) ("call", name, [args]).
"""
from errors import ParseError
from lexer import tokenize


class Parser:
    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i]

    def next(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def at_op(self, *ops):
        k, v, _ = self.peek()
        return k == "op" and v in ops

    def expect(self, op):
        k, v, pos = self.next()
        if not (k == "op" and v == op):
            raise ParseError(f"expected {op!r} at position {pos}")

    def expr(self):
        left = self.term()
        while self.at_op("+", "-"):
            op = self.next()[1]
            left = ("bin", op, left, self.term())
        return left

    def term(self):
        left = self.power()
        while self.at_op("*", "/", "%"):
            op = self.next()[1]
            left = ("bin", op, left, self.power())
        return left

    def power(self):
        left = self.atom()
        while self.at_op("**"):
            self.next()
            left = ("bin", "**", left, self.atom())
        return left

    def atom(self):
        kind, val, pos = self.next()
        if kind == "num":
            return ("num", val)
        if kind == "op" and val == "-":
            return ("neg", self.atom())
        if kind == "op" and val == "(":
            e = self.expr()
            self.expect(")")
            return e
        if kind == "name":
            if self.at_op("("):
                self.next()
                arg = self.expr()
                self.expect(")")
                return ("call", val, [arg])
            return ("name", val)
        raise ParseError(f"unexpected token {val!r} at position {pos}")


def parse(src):
    return Parser(tokenize(src)).expr()
