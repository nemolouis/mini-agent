# Eval report: 20261013-194844-flash

- config: `flash` (hash `818f1f0e69`), model `deepseek-flash`, temperature 0.0, max_steps 50
- model reported by server: deepseek-flash
- split: **dev**, tasks 13, valid runs 39 (repeat 3); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-13 19:48:44
- hypothesis: model comparison with explicit model id; max_tokens 16384 (4096 truncated thinking), max_steps 50 (30 exhausted by slower explorers)

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 89.7% (95% CI 76.9–100.0%) |
| mean steps | 8.7 |
| mean input tokens (incl. cache) | 60852 |
| mean output tokens | 8337 |
| mean reasoning tokens (0 = not reported) | 5439 |
| mean cost (USD/run), off-peak price | 0.00564 |
| mean cost (USD/run), peak price | 0.01128 |
| mean wall time (s) | 70.3 |
| mean tool errors | 0.03 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 35 |
| tests_failed_after_edit | 3 |
| max_tokens | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 6.0 | pass×3 |
| b05-interpolate | 1.00 (3/3) | 7.3 | pass×3 |
| b08-csv-loader | 1.00 (3/3) | 9.7 | pass×3 |
| b09-sliding-window | 1.00 (3/3) | 7.0 | pass×3 |
| b12-sessions | 0.33 (1/3) | 9.3 | tests_failed_after_edit×2, pass×1 |
| b13-interval-set | 1.00 (3/3) | 6.3 | pass×3 |
| b15-cron-next | 1.00 (3/3) | 9.3 | pass×3 |
| b16-text-diff | 1.00 (3/3) | 8.3 | pass×3 |
| b19-regex-engine | 0.67 (2/3) | 13.0 | pass×2, tests_failed_after_edit×1 |
| b21-timer-queue | 1.00 (3/3) | 10.3 | pass×3 |
| b23-meeting-slots | 1.00 (3/3) | 6.3 | pass×3 |
| b25-patch-apply-v2 | 0.67 (2/3) | 13.0 | pass×2, max_tokens×1 |
| b26-linear-solver-v2 | 1.00 (3/3) | 7.7 | pass×3 |
