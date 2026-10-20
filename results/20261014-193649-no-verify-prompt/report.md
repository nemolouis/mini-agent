# Eval report: 20261014-193649-no-verify-prompt

- config: `no-verify-prompt` (hash `5c99fa5bd6`), model `deepseek-flash`, temperature 0.0, max_steps 50
- model reported by server: unknown
- split: **dev**, tasks 0, valid runs 0 (repeat 3); **39 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-14 19:36:49
- hypothesis: PREDICTION: removing the 'run the tests' sentence changes little (<= 8 points) because the model runs tests by habit; fewer bash calls per run.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | n/a% (95% CI n/a–n/a%) |
| mean steps | n/a |
| mean input tokens (incl. cache) | n/a |
| mean output tokens | n/a |
| mean reasoning tokens (0 = not reported) | n/a |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | n/a |
| mean tool errors | n/a |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | n/a (api_error only) | 0.0 | api_error×3 |
| b05-interpolate | n/a (api_error only) | 0.0 | api_error×3 |
| b08-csv-loader | n/a (api_error only) | 0.0 | api_error×3 |
| b09-sliding-window | n/a (api_error only) | 0.0 | api_error×3 |
| b12-sessions | n/a (api_error only) | 0.0 | api_error×3 |
| b13-interval-set | n/a (api_error only) | 0.0 | api_error×3 |
| b15-cron-next | n/a (api_error only) | 0.0 | api_error×3 |
| b16-text-diff | n/a (api_error only) | 0.0 | api_error×3 |
| b19-regex-engine | n/a (api_error only) | 0.0 | api_error×3 |
| b21-timer-queue | n/a (api_error only) | 0.0 | api_error×3 |
| b23-meeting-slots | n/a (api_error only) | 0.0 | api_error×3 |
| b25-patch-apply-v2 | n/a (api_error only) | 0.0 | api_error×3 |
| b26-linear-solver-v2 | n/a (api_error only) | 0.0 | api_error×3 |

_Cost is n/a: fill in `configs/prices.json` for this model._
