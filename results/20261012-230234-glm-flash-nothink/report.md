# Eval report: 20261012-230234-glm-flash-nothink

- config: `glm-flash-nothink` (hash `4741f73338`), model `glm-4.7-flash`, temperature 0.0, max_steps 50
- model reported by server: glm-4.7-flash
- split: **dev**, tasks 3, runs 3 (repeat 1)
- date: 2026-10-12 23:02:34
- hypothesis: same model with thinking disabled: faster and fewer tokens; does accuracy drop?

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 0.0% (95% CI 0.0–0.0%) |
| mean steps | 15.3 |
| mean input tokens (incl. cache) | 52074 |
| mean output tokens | 3231 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | 0.00000 |
| mean cost (USD/run), peak price | 0.00000 |
| mean wall time (s) | 697.1 |
| mean tool errors | 0.33 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 2 |

## Failure classes (per run)

| class | runs |
|---|---|
| tests_failed_after_edit | 2 |
| api_error | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 0.00 (0/1) | 14.0 | api_error×1 |
| b09-sliding-window | 0.00 (0/1) | 12.0 | tests_failed_after_edit×1 |
| b13-interval-set | 0.00 (0/1) | 20.0 | tests_failed_after_edit×1 |
