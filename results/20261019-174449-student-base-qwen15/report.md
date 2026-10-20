# Eval report: 20261019-174449-student-base-qwen15

- config: `student-base-qwen15` (hash `1bc6ea8d06`), model `default_model`, temperature 0.0, max_steps 30
- model reported by server: default_model
- split: **dev**, tasks 48, valid runs 48 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-19 17:44:49
- hypothesis: untrained Qwen2.5-Coder-1.5B-Instruct served by mlx_lm.server on the dev-split generated tasks (unseen libraries colorama, schema): expected near 0%, because it does not use the <tool_call> format the server parses. The model name must stay default_model: any other name makes the server try to fetch that model from Hugging Face.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 0.0% (95% CI 0.0–0.0%) |
| mean steps | 1.0 |
| mean input tokens (incl. cache) | 735 |
| mean output tokens | 374 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 14.0 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| failed runs whose own last test run was green (false completion) | 0 / 48 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| no_edit | 48 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| g-colorama-000-negate | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-001-compare | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-002-const | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-003-boolop | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-004-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-005-boolop | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-006-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-007-const | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-008-const | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-009-compare | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-010-boolop | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-011-negate | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-012-compare | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-013-boolop | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-014-compare | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-015-boolop | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-016-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-017-arith | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-018-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-019-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-020-negate | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-021-const | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-022-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-colorama-023-negate | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-000-arith | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-001-const | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-002-loopctl | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-003-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-004-arith | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-005-boolop | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-006-const | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-007-loopctl | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-008-arith | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-009-boolop | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-010-const | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-011-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-012-negate | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-013-loopctl | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-014-compare | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-015-arith | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-016-boolop | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-017-compare | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-018-const | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-019-compare | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-020-negate | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-021-delete | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-022-arith | 0.00 (0/1) | 1.0 | no_edit×1 |
| g-schema-023-const | 0.00 (0/1) | 1.0 | no_edit×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
