class InterpolationError(Exception):
    pass


class UndefinedVariable(InterpolationError):
    pass


class CycleError(InterpolationError):
    pass


class InterpolationSyntaxError(InterpolationError):
    pass
