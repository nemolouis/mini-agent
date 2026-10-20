import re

from errors import CycleError, InterpolationSyntaxError, UndefinedVariable

_NAME = re.compile(r"[A-Za-z0-9_]+")


def _parse_ref(t, i):
    """t[i] is the first char after '${'. Return (name, default_or_None, index_after_ref)."""
    m = _NAME.match(t, i)
    if not m:
        raise InterpolationSyntaxError("empty or invalid variable name")
    name, j = m.group(0), m.end()
    if t.startswith("}", j):
        return name, None, j + 1
    if not t.startswith(":-", j):
        raise InterpolationSyntaxError(f"unterminated reference near {t[i - 2:j + 1]!r}")
    j += 2
    start, depth = j, 1
    while j < len(t):
        if t.startswith("$$", j):
            j += 2
        elif t.startswith("${", j):
            depth += 1
            j += 2
        elif t[j] == "}":
            depth -= 1
            if depth == 0:
                return name, t[start:j], j + 1
            j += 1
        else:
            j += 1
    raise InterpolationSyntaxError("unterminated reference")


def _expand(template, env, stack):
    out, i, n = [], 0, len(template)
    while i < n:
        c = template[i]
        if c != "$":
            out.append(c)
            i += 1
            continue
        nxt = template[i + 1] if i + 1 < n else ""
        if nxt == "$":
            out.append("$")
            i += 2
        elif nxt == "{":
            name, default, i = _parse_ref(template, i + 2)
            out.append(_resolve(name, default, env, stack))
        else:
            out.append("$")
            i += 1
    return "".join(out)


def _resolve(name, default, env, stack):
    value = env.get(name)
    if value is None or value == "":
        if default is not None:
            return _expand(default, env, stack)
        if value is None:
            raise UndefinedVariable(name)
        return ""
    if name in stack:
        raise CycleError(" -> ".join(stack + (name,)))
    return _expand(value, env, stack + (name,))


def expand(template, env):
    """Expand ${NAME} and ${NAME:-default} references. See docs/INTERPOLATION.md."""
    return _expand(template, env, ())


def expand_env(env):
    return {k: _expand(v, env, (k,)) for k, v in env.items()}
