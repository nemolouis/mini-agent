# Eval report: 20261026-175205-student-q4-v5-plain-final

- config: `student-q4-v5-plain-final` (hash `e0e7b88c64`), model `default_model`, temperature 0.0, max_steps 30
- model reported by server: default_model
- split: **dev**, tasks 48, valid runs 48 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-26 17:52:05
- hypothesis: Tests the FORMAT alone: tool calls written as plain-text [TOOL_CALL] JSON [/TOOL_CALL] (prompts/chat_template_plain.jinja) instead of Qwen's untrained <tool_call> special tokens. Same data as the v3 run (sft_train_v2.jsonl, original old_string), same hyper-parameters, final step, same 48 dev tasks, temperature 0, one run each. Differences from the v3 run to keep in mind: 151 examples fit 4096 tokens (not 159), so slightly fewer steps. Prediction fixed before running: 48/48 runs make tool calls (v4 and step-300 made none), and passes exceed 4/48. If tool calls are made but passes stay at or below 4/48, the format fixed the instability but not the editing skill.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 0.0% (95% CI 0.0–0.0%) |
| mean steps | 13.7 |
| mean input tokens (incl. cache) | 88589 |
| mean output tokens | 825 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 35.9 |
| mean tool errors | 0.02 |
| runs with summary-compaction | 1 |
| runs that modified tests | 0 |
| failed runs whose own last test run was green (false completion) | 0 / 48 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| no_edit | 31 |
| max_steps | 15 |
| max_tokens | 2 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| g-colorama-000-negate | 0.00 (0/1) | 8.0 | no_edit×1 |
| g-colorama-001-compare | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-002-const | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-003-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-004-delete | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-005-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-006-delete | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-007-const | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-008-const | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-009-compare | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-010-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-011-negate | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-012-compare | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-013-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-014-compare | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-015-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-016-delete | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-017-arith | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-018-delete | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-019-delete | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-colorama-020-negate | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-colorama-021-const | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-colorama-022-delete | 0.00 (0/1) | 4.0 | max_tokens×1 |
| g-colorama-023-negate | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-000-arith | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-schema-001-const | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-002-loopctl | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-schema-003-delete | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-004-arith | 0.00 (0/1) | 6.0 | max_tokens×1 |
| g-schema-005-boolop | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-006-const | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-007-loopctl | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-008-arith | 0.00 (0/1) | 9.0 | no_edit×1 |
| g-schema-009-boolop | 0.00 (0/1) | 5.0 | no_edit×1 |
| g-schema-010-const | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-011-delete | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-012-negate | 0.00 (0/1) | 9.0 | no_edit×1 |
| g-schema-013-loopctl | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-014-compare | 0.00 (0/1) | 11.0 | no_edit×1 |
| g-schema-015-arith | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-016-boolop | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-017-compare | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-018-const | 0.00 (0/1) | 7.0 | no_edit×1 |
| g-schema-019-compare | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-020-negate | 0.00 (0/1) | 14.0 | no_edit×1 |
| g-schema-021-delete | 0.00 (0/1) | 6.0 | no_edit×1 |
| g-schema-022-arith | 0.00 (0/1) | 30.0 | max_steps×1 |
| g-schema-023-const | 0.00 (0/1) | 6.0 | no_edit×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
