# Eval report: 20261018-221427-gen-synth-flash

- config: `gen-synth-flash` (hash `1a79e21e0e`), model `deepseek-flash`, temperature 0.7, max_steps 30
- model reported by server: deepseek-flash
- split: **train**, tasks 257, valid runs 514 (repeat 2); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-18 22:14:27
- hypothesis: stage-3 synthesis: DeepSeek flash as the teacher on all train-split generated tasks, 2 samples each at temperature 0.7 (at 0.0 a repeat would be a near-copy and be deduplicated); keep thinking text for the with/without-reasoning SFT ablation. Pilot: 30/30 pass, 8.3 steps, about 0.002-0.004 USD per run, so about 514 runs should cost a few USD and take about an hour at 4 workers.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 99.8% (95% CI 99.4–100.0%) |
| mean steps | 8.5 |
| mean input tokens (incl. cache) | 46981 |
| mean output tokens | 1718 |
| mean reasoning tokens (0 = not reported) | 874 |
| mean cost (USD/run), off-peak price | 0.00209 |
| mean cost (USD/run), peak price | 0.00419 |
| mean wall time (s) | 29.5 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 3 |
| failed runs whose own last test run was green (false completion) | 1 / 1 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 513 |
| tests_failed_after_edit | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| g-boltons-000-arith | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-001-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-boltons-002-const | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-003-loopctl | 1.00 (2/2) | 9.0 | pass×2 |
| g-boltons-004-boolop | 1.00 (2/2) | 12.0 | pass×2 |
| g-boltons-005-const | 1.00 (2/2) | 12.0 | pass×2 |
| g-boltons-006-delete | 1.00 (2/2) | 8.0 | pass×2 |
| g-boltons-007-arith | 1.00 (2/2) | 9.0 | pass×2 |
| g-boltons-008-negate | 1.00 (2/2) | 6.5 | pass×2 |
| g-boltons-009-compare | 1.00 (2/2) | 9.0 | pass×2 |
| g-boltons-010-arith | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-011-boolop | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-012-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-013-loopctl | 1.00 (2/2) | 9.0 | pass×2 |
| g-boltons-014-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-015-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-016-const | 1.00 (2/2) | 8.5 | pass×2 |
| g-boltons-017-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-018-boolop | 1.00 (2/2) | 8.0 | pass×2 |
| g-boltons-019-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-020-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-boltons-021-compare | 1.00 (2/2) | 6.0 | pass×2 |
| g-boltons-022-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-boltons-023-boolop | 1.00 (2/2) | 9.0 | pass×2 |
| g-cachetools-000-arith | 1.00 (2/2) | 7.5 | pass×2 |
| g-cachetools-001-boolop | 1.00 (2/2) | 8.0 | pass×2 |
| g-cachetools-002-const | 1.00 (2/2) | 9.0 | pass×2 |
| g-cachetools-003-boolop | 1.00 (2/2) | 9.5 | pass×2 |
| g-cachetools-004-compare | 0.50 (1/2) | 12.0 | pass×1, tests_failed_after_edit×1 |
| g-cachetools-005-const | 1.00 (2/2) | 8.5 | pass×2 |
| g-cachetools-006-compare | 1.00 (2/2) | 11.5 | pass×2 |
| g-cachetools-007-compare | 1.00 (2/2) | 7.0 | pass×2 |
| g-cachetools-008-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-cachetools-009-const | 1.00 (2/2) | 8.0 | pass×2 |
| g-cachetools-010-delete | 1.00 (2/2) | 8.0 | pass×2 |
| g-cachetools-011-arith | 1.00 (2/2) | 7.0 | pass×2 |
| g-cachetools-012-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-cachetools-013-delete | 1.00 (2/2) | 7.0 | pass×2 |
| g-cachetools-014-negate | 1.00 (2/2) | 12.5 | pass×2 |
| g-cachetools-015-compare | 1.00 (2/2) | 10.5 | pass×2 |
| g-cachetools-016-compare | 1.00 (2/2) | 10.0 | pass×2 |
| g-cachetools-017-const | 1.00 (2/2) | 8.5 | pass×2 |
| g-cachetools-018-compare | 1.00 (2/2) | 10.0 | pass×2 |
| g-cachetools-019-const | 1.00 (2/2) | 10.5 | pass×2 |
| g-cachetools-020-delete | 1.00 (2/2) | 19.0 | pass×2 |
| g-cachetools-021-compare | 1.00 (2/2) | 9.0 | pass×2 |
| g-cachetools-022-compare | 1.00 (2/2) | 10.0 | pass×2 |
| g-cachetools-023-compare | 1.00 (2/2) | 8.5 | pass×2 |
| g-decorator-000-arith | 1.00 (2/2) | 8.0 | pass×2 |
| g-decorator-001-const | 1.00 (2/2) | 13.5 | pass×2 |
| g-decorator-002-compare | 1.00 (2/2) | 9.5 | pass×2 |
| g-decorator-003-negate | 1.00 (2/2) | 9.5 | pass×2 |
| g-decorator-004-compare | 1.00 (2/2) | 17.0 | pass×2 |
| g-decorator-005-const | 1.00 (2/2) | 15.5 | pass×2 |
| g-decorator-006-compare | 1.00 (2/2) | 9.5 | pass×2 |
| g-decorator-007-negate | 1.00 (2/2) | 10.5 | pass×2 |
| g-decorator-008-arith | 1.00 (2/2) | 9.5 | pass×2 |
| g-decorator-009-negate | 1.00 (2/2) | 11.5 | pass×2 |
| g-decorator-010-negate | 1.00 (2/2) | 8.5 | pass×2 |
| g-decorator-011-const | 1.00 (2/2) | 9.5 | pass×2 |
| g-decorator-012-const | 1.00 (2/2) | 11.5 | pass×2 |
| g-decorator-013-negate | 1.00 (2/2) | 10.0 | pass×2 |
| g-decorator-014-delete | 1.00 (2/2) | 14.5 | pass×2 |
| g-decorator-015-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-decorator-016-delete | 1.00 (2/2) | 12.5 | pass×2 |
| g-decorator-017-delete | 1.00 (2/2) | 10.0 | pass×2 |
| g-decorator-018-delete | 1.00 (2/2) | 18.0 | pass×2 |
| g-decorator-019-delete | 1.00 (2/2) | 9.5 | pass×2 |
| g-decorator-020-delete | 1.00 (2/2) | 13.0 | pass×2 |
| g-decorator-021-delete | 1.00 (2/2) | 10.5 | pass×2 |
| g-decorator-022-delete | 1.00 (2/2) | 11.5 | pass×2 |
| g-decorator-023-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-inflection-000-const | 1.00 (2/2) | 7.0 | pass×2 |
| g-inflection-001-const | 1.00 (2/2) | 8.0 | pass×2 |
| g-inflection-002-delete | 1.00 (2/2) | 6.5 | pass×2 |
| g-inflection-003-negate | 1.00 (2/2) | 14.5 | pass×2 |
| g-inflection-004-delete | 1.00 (2/2) | 9.0 | pass×2 |
| g-inflection-005-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-inflection-006-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-inflection-007-arith | 1.00 (2/2) | 7.0 | pass×2 |
| g-inflection-008-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-inflection-009-const | 1.00 (2/2) | 8.0 | pass×2 |
| g-inflection-010-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-inflection-011-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-inflection-012-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-inflection-013-const | 1.00 (2/2) | 5.5 | pass×2 |
| g-ordered_set-000-compare | 1.00 (2/2) | 6.5 | pass×2 |
| g-ordered_set-001-arith | 1.00 (2/2) | 7.5 | pass×2 |
| g-ordered_set-002-boolop | 1.00 (2/2) | 9.5 | pass×2 |
| g-ordered_set-003-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-ordered_set-004-const | 1.00 (2/2) | 8.5 | pass×2 |
| g-ordered_set-005-compare | 1.00 (2/2) | 7.0 | pass×2 |
| g-ordered_set-006-boolop | 1.00 (2/2) | 7.0 | pass×2 |
| g-ordered_set-007-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-ordered_set-008-const | 1.00 (2/2) | 7.5 | pass×2 |
| g-ordered_set-009-negate | 1.00 (2/2) | 8.5 | pass×2 |
| g-ordered_set-010-negate | 1.00 (2/2) | 6.5 | pass×2 |
| g-ordered_set-011-compare | 1.00 (2/2) | 6.5 | pass×2 |
| g-ordered_set-012-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-ordered_set-013-negate | 1.00 (2/2) | 8.5 | pass×2 |
| g-ordered_set-014-compare | 1.00 (2/2) | 7.5 | pass×2 |
| g-ordered_set-015-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-ordered_set-016-delete | 1.00 (2/2) | 6.5 | pass×2 |
| g-ordered_set-017-negate | 1.00 (2/2) | 6.5 | pass×2 |
| g-ordered_set-018-delete | 1.00 (2/2) | 8.0 | pass×2 |
| g-ordered_set-019-compare | 1.00 (2/2) | 8.0 | pass×2 |
| g-ordered_set-020-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-ordered_set-021-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-ordered_set-022-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-ordered_set-023-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-parse-000-compare | 1.00 (2/2) | 8.5 | pass×2 |
| g-parse-001-arith | 1.00 (2/2) | 14.5 | pass×2 |
| g-parse-002-arith | 1.00 (2/2) | 7.5 | pass×2 |
| g-parse-003-const | 1.00 (2/2) | 9.5 | pass×2 |
| g-parse-004-delete | 1.00 (2/2) | 9.5 | pass×2 |
| g-parse-005-boolop | 1.00 (2/2) | 10.0 | pass×2 |
| g-parse-006-negate | 1.00 (2/2) | 9.5 | pass×2 |
| g-parse-007-negate | 1.00 (2/2) | 13.5 | pass×2 |
| g-parse-008-delete | 1.00 (2/2) | 9.0 | pass×2 |
| g-parse-009-arith | 1.00 (2/2) | 9.5 | pass×2 |
| g-parse-010-boolop | 1.00 (2/2) | 8.0 | pass×2 |
| g-parse-011-compare | 1.00 (2/2) | 8.5 | pass×2 |
| g-parse-012-const | 1.00 (2/2) | 15.5 | pass×2 |
| g-parse-013-boolop | 1.00 (2/2) | 8.0 | pass×2 |
| g-parse-014-const | 1.00 (2/2) | 11.5 | pass×2 |
| g-parse-015-boolop | 1.00 (2/2) | 8.0 | pass×2 |
| g-parse-016-const | 1.00 (2/2) | 14.5 | pass×2 |
| g-parse-017-compare | 1.00 (2/2) | 10.0 | pass×2 |
| g-parse-018-delete | 1.00 (2/2) | 9.0 | pass×2 |
| g-parse-019-boolop | 1.00 (2/2) | 6.5 | pass×2 |
| g-parse-020-negate | 1.00 (2/2) | 6.5 | pass×2 |
| g-parse-021-const | 1.00 (2/2) | 12.5 | pass×2 |
| g-parse-022-negate | 1.00 (2/2) | 20.5 | pass×2 |
| g-parse-023-arith | 1.00 (2/2) | 10.0 | pass×2 |
| g-seqtools-000-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-001-boolop | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-002-negate | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-003-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-004-delete | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-005-negate | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-006-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-007-negate | 1.00 (2/2) | 6.5 | pass×2 |
| g-seqtools-008-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-009-compare | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-010-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-011-negate | 1.00 (2/2) | 5.0 | pass×2 |
| g-seqtools-012-delete | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-013-negate | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-014-delete | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-015-negate | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-016-arith | 1.00 (2/2) | 6.5 | pass×2 |
| g-seqtools-017-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-018-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-019-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-020-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-seqtools-021-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-six-000-delete | 1.00 (2/2) | 7.0 | pass×2 |
| g-six-001-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-six-002-const | 1.00 (2/2) | 7.0 | pass×2 |
| g-six-003-delete | 1.00 (2/2) | 6.5 | pass×2 |
| g-six-004-negate | 1.00 (2/2) | 6.5 | pass×2 |
| g-six-005-compare | 1.00 (2/2) | 7.0 | pass×2 |
| g-six-006-const | 1.00 (2/2) | 9.0 | pass×2 |
| g-six-007-delete | 1.00 (2/2) | 10.0 | pass×2 |
| g-six-008-delete | 1.00 (2/2) | 7.0 | pass×2 |
| g-six-009-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-six-010-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-six-011-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-six-012-negate | 1.00 (2/2) | 9.5 | pass×2 |
| g-six-013-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-six-014-negate | 1.00 (2/2) | 10.5 | pass×2 |
| g-six-015-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-six-016-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-six-017-delete | 1.00 (2/2) | 6.5 | pass×2 |
| g-six-018-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-six-019-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-six-020-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-six-021-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-six-022-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-six-023-negate | 1.00 (2/2) | 6.0 | pass×2 |
| g-tabulate-000-const | 1.00 (2/2) | 9.0 | pass×2 |
| g-tabulate-001-delete | 1.00 (2/2) | 10.0 | pass×2 |
| g-tabulate-002-arith | 1.00 (2/2) | 7.0 | pass×2 |
| g-tabulate-003-boolop | 1.00 (2/2) | 8.5 | pass×2 |
| g-tabulate-004-const | 1.00 (2/2) | 14.5 | pass×2 |
| g-tabulate-005-delete | 1.00 (2/2) | 9.0 | pass×2 |
| g-tabulate-006-compare | 1.00 (2/2) | 7.0 | pass×2 |
| g-tabulate-007-arith | 1.00 (2/2) | 8.0 | pass×2 |
| g-tabulate-008-const | 1.00 (2/2) | 9.5 | pass×2 |
| g-tabulate-009-loopctl | 1.00 (2/2) | 10.0 | pass×2 |
| g-tabulate-010-arith | 1.00 (2/2) | 8.5 | pass×2 |
| g-tabulate-011-negate | 1.00 (2/2) | 10.0 | pass×2 |
| g-tabulate-012-compare | 1.00 (2/2) | 11.5 | pass×2 |
| g-tabulate-013-arith | 1.00 (2/2) | 7.5 | pass×2 |
| g-tabulate-014-boolop | 1.00 (2/2) | 13.5 | pass×2 |
| g-tabulate-015-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-tabulate-016-const | 1.00 (2/2) | 8.5 | pass×2 |
| g-tabulate-017-negate | 1.00 (2/2) | 9.5 | pass×2 |
| g-tabulate-018-delete | 1.00 (2/2) | 15.5 | pass×2 |
| g-tabulate-019-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-tabulate-020-negate | 1.00 (2/2) | 9.5 | pass×2 |
| g-tabulate-021-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-tabulate-022-arith | 1.00 (2/2) | 7.5 | pass×2 |
| g-tabulate-023-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-termcolor-000-compare | 1.00 (2/2) | 8.0 | pass×2 |
| g-termcolor-001-const | 1.00 (2/2) | 7.0 | pass×2 |
| g-termcolor-002-delete | 1.00 (2/2) | 9.0 | pass×2 |
| g-termcolor-003-compare | 1.00 (2/2) | 7.0 | pass×2 |
| g-termcolor-004-const | 1.00 (2/2) | 7.0 | pass×2 |
| g-termcolor-005-const | 1.00 (2/2) | 7.0 | pass×2 |
| g-textkit-000-compare | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-001-arith | 1.00 (2/2) | 7.0 | pass×2 |
| g-textkit-002-boolop | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-003-negate | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-004-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-005-delete | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-006-compare | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-007-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-008-boolop | 1.00 (2/2) | 7.0 | pass×2 |
| g-textkit-009-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-textkit-010-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-011-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-012-arith | 1.00 (2/2) | 5.5 | pass×2 |
| g-textkit-013-negate | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-014-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-015-delete | 1.00 (2/2) | 6.5 | pass×2 |
| g-textkit-016-compare | 1.00 (2/2) | 7.0 | pass×2 |
| g-textkit-017-negate | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-018-compare | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-019-arith | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-020-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-021-delete | 1.00 (2/2) | 6.0 | pass×2 |
| g-textkit-022-const | 1.00 (2/2) | 6.0 | pass×2 |
| g-toolz-000-negate | 1.00 (2/2) | 9.5 | pass×2 |
| g-toolz-001-const | 1.00 (2/2) | 8.0 | pass×2 |
| g-toolz-002-loopctl | 1.00 (2/2) | 9.5 | pass×2 |
| g-toolz-003-compare | 1.00 (2/2) | 7.0 | pass×2 |
| g-toolz-004-arith | 1.00 (2/2) | 7.0 | pass×2 |
| g-toolz-005-negate | 1.00 (2/2) | 9.5 | pass×2 |
| g-toolz-006-loopctl | 1.00 (2/2) | 8.5 | pass×2 |
| g-toolz-007-delete | 1.00 (2/2) | 7.5 | pass×2 |
| g-toolz-008-compare | 1.00 (2/2) | 13.0 | pass×2 |
| g-toolz-009-boolop | 1.00 (2/2) | 14.0 | pass×2 |
| g-toolz-010-negate | 1.00 (2/2) | 10.5 | pass×2 |
| g-toolz-011-delete | 1.00 (2/2) | 9.5 | pass×2 |
| g-toolz-012-arith | 1.00 (2/2) | 8.5 | pass×2 |
| g-toolz-013-boolop | 1.00 (2/2) | 9.5 | pass×2 |
| g-toolz-014-loopctl | 1.00 (2/2) | 12.0 | pass×2 |
| g-toolz-015-delete | 1.00 (2/2) | 8.0 | pass×2 |
| g-toolz-016-boolop | 1.00 (2/2) | 21.0 | pass×2 |
| g-toolz-017-negate | 1.00 (2/2) | 7.0 | pass×2 |
| g-toolz-018-const | 1.00 (2/2) | 10.5 | pass×2 |
| g-toolz-019-delete | 1.00 (2/2) | 8.5 | pass×2 |
| g-toolz-020-compare | 1.00 (2/2) | 7.0 | pass×2 |
| g-toolz-021-boolop | 1.00 (2/2) | 8.0 | pass×2 |
| g-toolz-022-negate | 1.00 (2/2) | 7.5 | pass×2 |
| g-toolz-023-delete | 1.00 (2/2) | 7.5 | pass×2 |
