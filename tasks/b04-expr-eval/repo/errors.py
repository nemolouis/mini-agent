class ExprError(Exception):
    """Base class for all expression errors."""


class ParseError(ExprError):
    """Input is not a syntactically valid expression."""


class EvalError(ExprError):
    """Input is valid but cannot be evaluated (unknown name, division by zero, ...)."""
