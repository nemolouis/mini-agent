# Eval report: 20261021-012056-student-q4-v3-final

- config: `student-q4-v3-final` (hash `b05297cd89`), model `default_model`, temperature 0.0, max_steps 30
- model reported by server: default_model
- split: **dev**, tasks 48, valid runs 48 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-21 01:20:56
- hypothesis: the final adapter (step 456) of the third QLoRA run (Adam bias correction on, lr 1e-4), on the dev split of the generated tasks (48 tasks, unseen libraries colorama and schema). Checkpoint choice was fixed BEFORE looking at any dev result: the final adapter is the primary result, step 300 the secondary; both are reported. Untrained 4-bit base: 0/48 (no tool calls). Tool calls are read from the reply text (text_tool_calls): the model learned the format, but <tool_call> / </tool_call> have untrained embeddings in this model and it emits token 124 for both.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 8.3% (95% CI 2.1–16.7%) |
| mean steps | 5.9 |
| mean input tokens (incl. cache) | 11704 |
| mean output tokens | 667 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 15.9 |
| mean tool errors | 1.77 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| failed runs whose own last test run was green (false completion) | 0 / 44 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| no_edit | 34 |
| pass | 4 |
| max_tokens | 4 |
| tests_failed_after_edit | 4 |
| max_steps | 2 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| g-colorama-000-negate | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-001-compare | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-colorama-002-const | 1.00 (1/1) | 6.0 | pass×1 |
| g-colorama-003-boolop | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-colorama-004-delete | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-005-boolop | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-colorama-006-delete | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-colorama-007-const | 0.00 (0/1) | 4.0 | max_tokens×1 |
| g-colorama-008-const | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-colorama-009-compare | 1.00 (1/1) | 5.0 | pass×1 |
| g-colorama-010-boolop | 0.00 (0/1) | 3.0 | max_tokens×1 |
| g-colorama-011-negate | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-012-compare | 0.00 (0/1) | 8.0 | no_edit×1 |
| g-colorama-013-boolop | 0.00 (0/1) | 5.0 | tests_failed_after_edit×1 |
| g-colorama-014-compare | 0.00 (0/1) | 4.0 | max_tokens×1 |
| g-colorama-015-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-016-delete | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-colorama-017-arith | 1.00 (1/1) | 5.0 | pass×1 |
| g-colorama-018-delete | 1.00 (1/1) | 5.0 | pass×1 |
| g-colorama-019-delete | 0.00 (0/1) | 6.0 | max_tokens×1 |
| g-colorama-020-negate | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-021-const | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-colorama-022-delete | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-colorama-023-negate | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-000-arith | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-001-const | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-002-loopctl | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-003-delete | 0.00 (0/1) | 5.0 | tests_failed_after_edit×1 |
| g-schema-004-arith | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-005-boolop | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-006-const | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-007-loopctl | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-008-arith | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-009-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-010-const | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-011-delete | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-012-negate | 0.00 (0/1) | 9.0 | no_edit×1 |
| g-schema-013-loopctl | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-014-compare | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-015-arith | 0.00 (0/1) | 3.0 | no_edit×1 |
| g-schema-016-boolop | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-schema-017-compare | 0.00 (0/1) | 5.0 | tests_failed_after_edit×1 |
| g-schema-018-const | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-019-compare | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-020-negate | 0.00 (0/1) | 4.0 | no_edit×1 |
| g-schema-021-delete | 0.00 (0/1) | 12.0 | no_edit×1 |
| g-schema-022-arith | 0.00 (0/1) | 5.0 | tests_failed_after_edit×1 |
| g-schema-023-const | 0.00 (0/1) | 4.0 | no_edit×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
