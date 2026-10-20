# Eval report: 20261015-220959-gl31-think-high

- config: `gl31-think-high` (hash `5601261c90`), model `gemini-3.1-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.1-flash-lite
- split: **dev**, tasks 13, valid runs 13 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-15 22:09:59
- hypothesis: PREDICTION: the model does not think by default (reasoning tokens ~0). Enabling thinking raises pass rate by 10-25 points and lowers steps (fewer blind edit/test cycles); output tokens rise several-fold. If the provider rejects thinkingLevel for this model the run stops immediately with a 400.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 30.8% (95% CI 7.7–53.8%) |
| mean steps | 18.3 |
| mean input tokens (incl. cache) | 114172 |
| mean output tokens | 7668 |
| mean reasoning tokens (0 = not reported) | 4509 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 146.1 |
| mean tool errors | 0.08 |
| runs with summary-compaction | 0 |
| runs that modified tests | 6 |
| failed runs whose own last test run was green (false completion) | 6 / 9 |
| runs that needed an api_error rerun | 1 |

## Failure classes (per run)

| class | runs |
|---|---|
| tests_failed_after_edit | 9 |
| pass | 4 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (1/1) | 22.0 | pass×1 |
| b05-interpolate | 0.00 (0/1) | 14.0 | tests_failed_after_edit×1 |
| b08-csv-loader | 0.00 (0/1) | 33.0 | tests_failed_after_edit×1 |
| b09-sliding-window | 1.00 (1/1) | 11.0 | pass×1 |
| b12-sessions | 0.00 (0/1) | 12.0 | tests_failed_after_edit×1 |
| b13-interval-set | 0.00 (0/1) | 18.0 | tests_failed_after_edit×1 |
| b15-cron-next | 1.00 (1/1) | 13.0 | pass×1 |
| b16-text-diff | 0.00 (0/1) | 15.0 | tests_failed_after_edit×1 |
| b19-regex-engine | 0.00 (0/1) | 24.0 | tests_failed_after_edit×1 |
| b21-timer-queue | 0.00 (0/1) | 21.0 | tests_failed_after_edit×1 |
| b23-meeting-slots | 0.00 (0/1) | 13.0 | tests_failed_after_edit×1 |
| b25-patch-apply-v2 | 0.00 (0/1) | 26.0 | tests_failed_after_edit×1 |
| b26-linear-solver-v2 | 1.00 (1/1) | 16.0 | pass×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
