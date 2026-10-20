# Eval report: 20261013-204351-steps10

- config: `steps10` (hash `8fb022f31b`), model `deepseek-flash`, temperature 0.0, max_steps 10
- model reported by server: deepseek-flash
- split: **dev**, tasks 13, valid runs 39 (repeat 3); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-13 20:43:51
- hypothesis: PREDICTION: tasks whose baseline mean steps >= 10 (b16, b19, b21, b25) shift to max_steps; overall drop 15-30 points; tasks with <= 7 steps unaffected.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 94.9% (95% CI 87.2–100.0%) |
| mean steps | 8.2 |
| mean input tokens (incl. cache) | 49631 |
| mean output tokens | 7917 |
| mean reasoning tokens (0 = not reported) | 5301 |
| mean cost (USD/run), off-peak price | 0.00537 |
| mean cost (USD/run), peak price | 0.01073 |
| mean wall time (s) | 63.1 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 37 |
| max_steps | 2 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 6.3 | pass×3 |
| b05-interpolate | 1.00 (3/3) | 10.0 | pass×3 |
| b08-csv-loader | 1.00 (3/3) | 7.3 | pass×3 |
| b09-sliding-window | 1.00 (3/3) | 7.0 | pass×3 |
| b12-sessions | 1.00 (3/3) | 8.0 | pass×3 |
| b13-interval-set | 1.00 (3/3) | 8.3 | pass×3 |
| b15-cron-next | 1.00 (3/3) | 6.3 | pass×3 |
| b16-text-diff | 0.67 (2/3) | 10.0 | pass×2, max_steps×1 |
| b19-regex-engine | 0.67 (2/3) | 9.3 | max_steps×1, pass×2 |
| b21-timer-queue | 1.00 (3/3) | 9.3 | pass×3 |
| b23-meeting-slots | 1.00 (3/3) | 7.3 | pass×3 |
| b25-patch-apply-v2 | 1.00 (3/3) | 10.0 | pass×3 |
| b26-linear-solver-v2 | 1.00 (3/3) | 7.3 | pass×3 |
