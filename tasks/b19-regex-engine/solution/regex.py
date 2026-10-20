class RegexError(Exception):
    pass


SPECIAL = set(".*+?|()^$\\")


# AST: ("lit", c) ("any",) ("bol",) ("eol",) ("cat", [nodes]) ("alt", [nodes])
#      ("star", node) ("plus", node) ("opt", node)

class _Parser:
    def __init__(self, p):
        self.p, self.i = p, 0

    def peek(self):
        return self.p[self.i] if self.i < len(self.p) else None

    def alt(self):
        branches = [self.cat()]
        while self.peek() == "|":
            self.i += 1
            branches.append(self.cat())
        return branches[0] if len(branches) == 1 else ("alt", branches)

    def cat(self):
        items = []
        while self.peek() is not None and self.peek() not in "|)":
            items.append(self.piece())
        return ("cat", items)

    def piece(self):
        c = self.peek()
        if c in "*+?":
            raise RegexError("nothing to repeat")
        node = self.atom()
        while self.peek() is not None and self.peek() in "*+?":
            q = self.p[self.i]
            self.i += 1
            node = ({"*": "star", "+": "plus", "?": "opt"}[q], node)
            if self.peek() is not None and self.peek() in "*+?":
                raise RegexError("multiple repeat")
        return node

    def atom(self):
        c = self.p[self.i]
        self.i += 1
        if c == "(":
            node = self.alt()
            if self.peek() != ")":
                raise RegexError("unbalanced parenthesis")
            self.i += 1
            return node
        if c == ")":
            raise RegexError("unbalanced parenthesis")
        if c == "\\":
            if self.peek() is None:
                raise RegexError("trailing backslash")
            lit = self.p[self.i]
            self.i += 1
            return ("lit", lit)
        if c == ".":
            return ("any",)
        if c == "^":
            return ("bol",)
        if c == "$":
            return ("eol",)
        return ("lit", c)


def _parse(pattern):
    p = _Parser(pattern)
    node = p.alt()
    if p.peek() is not None:
        raise RegexError("unbalanced parenthesis")
    return node


def _m(node, text, i):
    """Yield end positions of matches of `node` starting at i, in preference order."""
    k = node[0]
    if k == "lit":
        if i < len(text) and text[i] == node[1]:
            yield i + 1
    elif k == "any":
        if i < len(text):
            yield i + 1
    elif k == "bol":
        if i == 0:
            yield i
    elif k == "eol":
        if i == len(text):
            yield i
    elif k == "cat":
        yield from _cat(node[1], 0, text, i)
    elif k == "alt":
        for b in node[1]:
            yield from _m(b, text, i)
    elif k == "opt":
        yield from _m(node[1], text, i)
        yield i
    elif k == "star":
        yield from _star(node[1], text, i)
    elif k == "plus":
        for j in _m(node[1], text, i):
            if j > i:
                yield from _star(node[1], text, j)
            else:
                yield j
        
    else:
        raise AssertionError(k)


def _cat(items, idx, text, i):
    if idx == len(items):
        yield i
        return
    for j in _m(items[idx], text, i):
        yield from _cat(items, idx + 1, text, j)


def _star(node, text, i):
    for j in _m(node, text, i):
        if j > i:
            yield from _star(node, text, j)
        else:
            yield i          # an empty iteration ends the loop; continue with what follows
    yield i


def fullmatch(pattern, text):
    ast = _parse(pattern)
    return any(j == len(text) for j in _m(ast, text, 0))


def search(pattern, text):
    ast = _parse(pattern)
    for s in range(len(text) + 1):
        for e in _m(ast, text, s):
            return (s, e)
    return None
