# Eval report: 20261015-173936-gemini-relay-native

- config: `gemini-relay-native` (hash `8ac84b8fd6`), model `gemini-3.1-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.1-flash-lite
- split: **dev**, tasks 1, valid runs 1 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-15 17:39:36
- hypothesis: gemini-3.1-flash-lite over the Gemini-native protocol through a forwarding relay (thought signatures handled by us)

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 0.0% (95% CI n/a–n/a%) |
| mean steps | 24.0 |
| mean input tokens (incl. cache) | 66563 |
| mean output tokens | 1663 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 65.5 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| tests_failed_after_edit | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 0.00 (0/1) | 24.0 | tests_failed_after_edit×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
