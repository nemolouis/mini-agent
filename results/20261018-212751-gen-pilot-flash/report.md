# Eval report: 20261018-212751-gen-pilot-flash

- config: `gen-pilot-flash` (hash `894811fb7c`), model `deepseek-flash`, temperature 0.0, max_steps 30
- model reported by server: deepseek-flash
- split: **train**, tasks 30, valid runs 30 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-18 21:27:51
- hypothesis: stage-3 pilot: DeepSeek flash as the trajectory teacher on the same 30 train-split generated tasks, for comparison with gen-pilot-g35 (needs account balance)

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 100.0% (95% CI 100.0–100.0%) |
| mean steps | 8.3 |
| mean input tokens (incl. cache) | 44155 |
| mean output tokens | 1444 |
| mean reasoning tokens (0 = not reported) | 621 |
| mean cost (USD/run), off-peak price | 0.00198 |
| mean cost (USD/run), peak price | 0.00396 |
| mean wall time (s) | 31.4 |
| mean tool errors | 0.03 |
| runs with summary-compaction | 0 |
| runs that modified tests | 1 |
| failed runs whose own last test run was green (false completion) | 0 / 0 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 30 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| g-boltons-002-const | 1.00 (1/1) | 8.0 | pass×1 |
| g-boltons-013-loopctl | 1.00 (1/1) | 8.0 | pass×1 |
| g-boltons-023-boolop | 1.00 (1/1) | 8.0 | pass×1 |
| g-cachetools-002-const | 1.00 (1/1) | 7.0 | pass×1 |
| g-cachetools-003-boolop | 1.00 (1/1) | 11.0 | pass×1 |
| g-cachetools-006-compare | 1.00 (1/1) | 8.0 | pass×1 |
| g-decorator-004-compare | 1.00 (1/1) | 9.0 | pass×1 |
| g-decorator-008-arith | 1.00 (1/1) | 9.0 | pass×1 |
| g-decorator-009-negate | 1.00 (1/1) | 13.0 | pass×1 |
| g-inflection-007-arith | 1.00 (1/1) | 7.0 | pass×1 |
| g-inflection-009-const | 1.00 (1/1) | 6.0 | pass×1 |
| g-inflection-011-delete | 1.00 (1/1) | 10.0 | pass×1 |
| g-ordered_set-001-arith | 1.00 (1/1) | 7.0 | pass×1 |
| g-ordered_set-006-boolop | 1.00 (1/1) | 6.0 | pass×1 |
| g-ordered_set-008-const | 1.00 (1/1) | 8.0 | pass×1 |
| g-parse-005-boolop | 1.00 (1/1) | 9.0 | pass×1 |
| g-parse-022-negate | 1.00 (1/1) | 17.0 | pass×1 |
| g-parse-023-arith | 1.00 (1/1) | 9.0 | pass×1 |
| g-seqtools-009-compare | 1.00 (1/1) | 6.0 | pass×1 |
| g-seqtools-019-arith | 1.00 (1/1) | 6.0 | pass×1 |
| g-six-001-negate | 1.00 (1/1) | 7.0 | pass×1 |
| g-six-002-const | 1.00 (1/1) | 7.0 | pass×1 |
| g-tabulate-012-compare | 1.00 (1/1) | 8.0 | pass×1 |
| g-tabulate-015-negate | 1.00 (1/1) | 7.0 | pass×1 |
| g-termcolor-002-delete | 1.00 (1/1) | 10.0 | pass×1 |
| g-termcolor-005-const | 1.00 (1/1) | 9.0 | pass×1 |
| g-textkit-008-boolop | 1.00 (1/1) | 6.0 | pass×1 |
| g-textkit-014-arith | 1.00 (1/1) | 7.0 | pass×1 |
| g-toolz-003-compare | 1.00 (1/1) | 9.0 | pass×1 |
| g-toolz-004-arith | 1.00 (1/1) | 8.0 | pass×1 |
