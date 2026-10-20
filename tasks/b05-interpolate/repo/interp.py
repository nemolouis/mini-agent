import re

from errors import UndefinedVariable

_REF = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")


def expand(template, env):
    """Expand ${NAME} and ${NAME:-default} references. See docs/INTERPOLATION.md."""
    def repl(m):
        name, default = m.group(1), m.group(2)
        value = env.get(name)
        if value is None or value == "":
            if default is not None:
                return default
            raise UndefinedVariable(name)
        return value

    return _REF.sub(repl, template)


def expand_env(env):
    return {k: expand(v, env) for k, v in env.items()}
