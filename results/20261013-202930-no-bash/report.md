# Eval report: 20261013-202930-no-bash

- config: `no-bash` (hash `8332913d41`), model `deepseek-flash`, temperature 0.0, max_steps 50
- model reported by server: deepseek-flash
- split: **dev**, tasks 13, valid runs 39 (repeat 3); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-13 20:29:30
- hypothesis: PREDICTION: without bash the agent cannot run tests. Pass rate drops by 10-25 points, almost entirely as tests_failed_after_edit on tasks that need iteration (b16, b19, b21, b25); easy tasks unaffected.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 97.4% (95% CI 92.3–100.0%) |
| mean steps | 8.6 |
| mean input tokens (incl. cache) | 57374 |
| mean output tokens | 9749 |
| mean reasoning tokens (0 = not reported) | 7669 |
| mean cost (USD/run), off-peak price | 0.00665 |
| mean cost (USD/run), peak price | 0.01329 |
| mean wall time (s) | 79.4 |
| mean tool errors | 1.23 |
| runs with summary-compaction | 0 |
| runs that modified tests | 1 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 38 |
| tests_failed_after_edit | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 8.0 | pass×3 |
| b05-interpolate | 1.00 (3/3) | 9.3 | pass×3 |
| b08-csv-loader | 1.00 (3/3) | 9.7 | pass×3 |
| b09-sliding-window | 1.00 (3/3) | 7.7 | pass×3 |
| b12-sessions | 0.67 (2/3) | 9.0 | pass×2, tests_failed_after_edit×1 |
| b13-interval-set | 1.00 (3/3) | 7.3 | pass×3 |
| b15-cron-next | 1.00 (3/3) | 10.3 | pass×3 |
| b16-text-diff | 1.00 (3/3) | 9.3 | pass×3 |
| b19-regex-engine | 1.00 (3/3) | 12.0 | pass×3 |
| b21-timer-queue | 1.00 (3/3) | 7.0 | pass×3 |
| b23-meeting-slots | 1.00 (3/3) | 6.0 | pass×3 |
| b25-patch-apply-v2 | 1.00 (3/3) | 9.7 | pass×3 |
| b26-linear-solver-v2 | 1.00 (3/3) | 6.7 | pass×3 |
