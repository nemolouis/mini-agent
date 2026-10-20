# Eval report: 20261014-162520-no-grep

- config: `no-grep` (hash `1bd6466c3b`), model `deepseek-flash`, temperature 0.0, max_steps 50
- model reported by server: deepseek-flash
- split: **dev**, tasks 1, valid runs 3 (repeat 3); **36 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-14 16:25:20
- hypothesis: PREDICTION: no change (|diff| <= 5 points). Repos are 2-5 files and read_file is still available; mean steps may rise slightly.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 100.0% (95% CI n/a–n/a%) |
| mean steps | 4.0 |
| mean input tokens (incl. cache) | 6870 |
| mean output tokens | 1506 |
| mean reasoning tokens (0 = not reported) | 779 |
| mean cost (USD/run), off-peak price | 0.00116 |
| mean cost (USD/run), peak price | 0.00233 |
| mean wall time (s) | 4454.2 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 3 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 3 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 4.0 | pass×3 |
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
