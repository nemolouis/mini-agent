# Cron expression subset

`next_after(expr, dt)` returns the earliest datetime **strictly after** `dt` (seconds and
microseconds of `dt` are ignored, i.e. `dt` is first truncated to its minute) that matches
`expr`, as a naive `datetime` with zero seconds. If no matching time exists
(e.g. `0 0 30 2 *`) it raises `ValueError`. It must handle expressions that only match
rarely (`0 0 29 2 *` = every 29 Feb, found within 8 years) and be fast (no minute-by-minute scanning of years).

## Syntax
Five whitespace-separated fields: `minute hour day-of-month month day-of-week`.

| field | range | names |
|---|---|---|
| minute | 0-59 | |
| hour | 0-23 | |
| day-of-month | 1-31 | |
| month | 1-12 | JAN..DEC (case-insensitive) |
| day-of-week | 0-7 (0 and 7 are both Sunday) | SUN..SAT (case-insensitive) |

Each field is a comma-separated list of items; an item is one of
- `*` (all values in range)
- `N` (single value)
- `A-B` (inclusive range, A <= B)
- `*/S` or `A-B/S` (every S-th value of the range, starting at its first value)
- `N/S` (like `N-max/S` where max is the top of the field's range)
Names may be used wherever a number can (`MON-FRI`, `JAN,JUN`). Values outside the range,
`A > B`, `S < 1`, a wrong field count or an unparsable item raise `ValueError`.

## Day matching
A day matches when its month matches AND:
- if **both** day-of-month and day-of-week are restricted (neither field is exactly `*`
  — note `*/2` counts as restricted), the day matches if **either** matches;
- otherwise (at least one of the two fields is `*`) both fields must match, which for a
  `*` field is always true.
