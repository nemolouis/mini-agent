# Mini regex engine

`fullmatch(pattern, text) -> bool` and `search(pattern, text) -> (start, end) | None`.

## Syntax
| form | meaning |
|---|---|
| `c` | the literal character c (any character that is not special) |
| `.` | any single character (including newline) |
| `X*` `X+` `X?` | zero or more / one or more / zero or one of the atom X, **greedy** |
| `A\|B` | alternation, lowest precedence; either side may be empty |
| `( ... )` | grouping (no capture needed); may be empty |
| `^` `$` | match only at the very start / very end of the text (not multiline) |
| `\c` | the literal character c (to match special characters) |

Special characters: `. * + ? | ( ) ^ $ \`. A quantifier applies to the immediately preceding
atom (a literal, `.`, an escape, or a group). Concatenation binds tighter than `|`.

## Semantics
Backtracking, Perl/Python style: alternatives are tried left to right, greedy quantifiers
try more repetitions first, and `search` returns the span of the first match found when
trying start positions 0, 1, 2, ... (leftmost), using that preference order at each start.
`fullmatch` is true if the pattern can match the entire text.
A repetition whose body matched the empty string stops repeating (no infinite loops).

## Errors
`RegexError` for: unbalanced parentheses, a quantifier with nothing to repeat
(`*a`, `a|*`, `(*a)`), a quantifier applied to a quantifier (`a**`), a trailing backslash.
