# Eval report: 20261018-203600-gen-pilot-g35

- config: `gen-pilot-g35` (hash `7e6e33d8ad`), model `gemini-3.5-flash-lite`, temperature None, max_steps 30
- model reported by server: gemini-3.5-flash-lite
- split: **train**, tasks 30, valid runs 30 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-18 20:36:00
- hypothesis: stage-3 pilot: free Gemini 3.5-flash-lite as the trajectory teacher on 30 train-split generated tasks; the questions are the pass rate (yield per run), steps (requests per run) and whether those requests fit the 500/day quota

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 83.3% (95% CI 70.0–96.7%) |
| mean steps | 15.0 |
| mean input tokens (incl. cache) | 150670 |
| mean output tokens | 545 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 134.1 |
| mean tool errors | 0.20 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| failed runs whose own last test run was green (false completion) | 0 / 5 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 25 |
| max_steps | 5 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| g-boltons-002-const | 1.00 (1/1) | 7.0 | pass×1 |
| g-boltons-013-loopctl | 1.00 (1/1) | 10.0 | pass×1 |
| g-boltons-023-boolop | 1.00 (1/1) | 15.0 | pass×1 |
| g-cachetools-002-const | 1.00 (1/1) | 18.0 | pass×1 |
| g-cachetools-003-boolop | 1.00 (1/1) | 24.0 | pass×1 |
| g-cachetools-006-compare | 1.00 (1/1) | 30.0 | pass×1 |
| g-decorator-004-compare | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-decorator-008-arith | 1.00 (1/1) | 14.0 | pass×1 |
| g-decorator-009-negate | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-inflection-007-arith | 1.00 (1/1) | 8.0 | pass×1 |
| g-inflection-009-const | 1.00 (1/1) | 13.0 | pass×1 |
| g-inflection-011-delete | 1.00 (1/1) | 13.0 | pass×1 |
| g-ordered_set-001-arith | 1.00 (1/1) | 10.0 | pass×1 |
| g-ordered_set-006-boolop | 1.00 (1/1) | 10.0 | pass×1 |
| g-ordered_set-008-const | 1.00 (1/1) | 9.0 | pass×1 |
| g-parse-005-boolop | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-parse-022-negate | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-parse-023-arith | 1.00 (1/1) | 11.0 | pass×1 |
| g-seqtools-009-compare | 1.00 (1/1) | 6.0 | pass×1 |
| g-seqtools-019-arith | 1.00 (1/1) | 7.0 | pass×1 |
| g-six-001-negate | 1.00 (1/1) | 12.0 | pass×1 |
| g-six-002-const | 1.00 (1/1) | 10.0 | pass×1 |
| g-tabulate-012-compare | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-tabulate-015-negate | 1.00 (1/1) | 15.0 | pass×1 |
| g-termcolor-002-delete | 1.00 (1/1) | 12.0 | pass×1 |
| g-termcolor-005-const | 1.00 (1/1) | 11.0 | pass×1 |
| g-textkit-008-boolop | 1.00 (1/1) | 8.0 | pass×1 |
| g-textkit-014-arith | 1.00 (1/1) | 10.0 | pass×1 |
| g-toolz-003-compare | 1.00 (1/1) | 10.0 | pass×1 |
| g-toolz-004-arith | 1.00 (1/1) | 7.0 | pass×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
