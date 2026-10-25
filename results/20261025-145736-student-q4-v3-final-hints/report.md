# Eval report: 20261025-145736-student-q4-v3-final-hints

- config: `student-q4-v3-final-hints` (hash `b7f85559cc`), model `default_model`, temperature 0.0, max_steps 30
- model reported by server: default_model
- split: **dev**, tasks 48, valid runs 48 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-25 14:57:36
- hypothesis: PAIRED with student-q4-v3-final: same adapter, same 48 dev tasks, temperature 0, same prompt and tool specs; the only change is edit_hints=true (edit_file failures also return the closest real lines / line numbers / file names). Prediction fixed before running: more runs reach a passing edit than the 4/48 baseline; 'no_edit' share (34/48 in the baseline) goes down. Success counts as an effect only if the paired test (McNemar) is significant; with 48 tasks only a large gain can be.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 6.2% (95% CI 0.0–14.6%) |
| mean steps | 6.5 |
| mean input tokens (incl. cache) | 15359 |
| mean output tokens | 608 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 13.8 |
| mean tool errors | 1.88 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| failed runs whose own last test run was green (false completion) | 0 / 45 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| no_edit | 39 |
| pass | 3 |
| tests_failed_after_edit | 3 |
| max_steps | 3 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| g-colorama-000-negate | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-colorama-001-compare | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-colorama-002-const | 1.00 (1/1) | 6.0 | pass×1 |
| g-colorama-003-boolop | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-colorama-004-delete | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-005-boolop | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-colorama-006-delete | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-colorama-007-const | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-colorama-008-const | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-colorama-009-compare | 1.00 (1/1) | 7.0 | pass×1 |
| g-colorama-010-boolop | 0.00 (0/1) | 7.0 | tests_failed_after_edit×1 |
| g-colorama-011-negate | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-colorama-012-compare | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-colorama-013-boolop | 0.00 (0/1) | 5.0 | tests_failed_after_edit×1 |
| g-colorama-014-compare | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-colorama-015-boolop | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-colorama-016-delete | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-017-arith | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-colorama-018-delete | 1.00 (1/1) | 5.0 | pass×1 |
| g-colorama-019-delete | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-colorama-020-negate | 0.00 (0/1) | 10.0 | no_edit×1 |
| g-colorama-021-const | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-colorama-022-delete | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-023-negate | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-000-arith | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-001-const | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-002-loopctl | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-003-delete | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-004-arith | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-005-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-006-const | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-007-loopctl | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-008-arith | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-009-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-010-const | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-011-delete | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-012-negate | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-013-loopctl | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-014-compare | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-015-arith | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-016-boolop | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-017-compare | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-018-const | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-019-compare | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-020-negate | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-schema-021-delete | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-022-arith | 0.00 (0/1) | 6.0 | tests_failed_after_edit×1 |
| g-schema-023-const | 0.00 (0/1) | 7.0 | no_edit×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
