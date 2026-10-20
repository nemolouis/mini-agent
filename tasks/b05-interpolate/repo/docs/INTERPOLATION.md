# Interpolation

`expand(template, env)` replaces references in `template` using the mapping `env` (str -> str).

| Syntax | Meaning |
|---|---|
| `${NAME}` | the value of NAME |
| `${NAME:-default}` | the value of NAME, or `default` when NAME is unset **or empty** |
| `$$` | a literal `$` |
| a `$` followed by anything else | a literal `$` |

Rules
1. `NAME` consists of letters, digits and `_`.
2. A `default` is itself a template: it may contain `${...}` references and `$$`, and may
   contain nested braces from them (`${A:-${B:-x}}`). The default ends at the `}` that
   closes the reference.
3. Values taken from `env` are themselves templates and are expanded recursively with the
   same rules.
4. An unset NAME without a default raises `UndefinedVariable(NAME)`. An empty NAME with
   no default expands to the empty string.
5. A reference cycle (`A=${B}`, `B=${A}`, or `A=${A}`) raises `CycleError`.
6. An unterminated `${...` or an empty name (`${}`) raises `InterpolationSyntaxError`.
7. `expand_env(env)` returns a new dict in which every value has been expanded against
   `env`.
All three exceptions derive from `InterpolationError`.
