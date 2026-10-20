# Unit conversion

`convert(value, src, dst)` converts `value` from the unit expression `src` to the unit
expression `dst` and returns a float.

## Unit expressions
    expr   := term (('*' | '/') term)*          # operators group LEFT to RIGHT
    term   := factor ('^' INT)?                 # INT may be negative: s^-2
    factor := UNIT | '1' | '(' expr ')'

- Whitespace is ignored. Unit names are case sensitive.
- `a/b*c` means `(a/b)*c`, so `m/s*s` is a length. `a/b/c` means `(a/b)/c`.
- `1` is the dimensionless number one: `1/s` is a frequency.
- `(expr)^n` raises the whole parenthesised expression to the power n.
- The known units are in `UNITS` (name -> (factor to SI, dimension vector)).

## Errors
Every problem raises `ConversionError`: unknown unit, syntax error (empty expression,
`m//s`, unbalanced parentheses, trailing junk, a missing exponent), and dimension mismatch
(converting `m` to `s`, or `N` to `J`).
