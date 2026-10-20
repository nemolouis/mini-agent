# Eval report: 20261012-224643-flash

- config: `flash` (hash `818f1f0e69`), model `deepseek-flash`, temperature 0.0, max_steps 50
- model reported by server: deepseek-flash
- split: **dev**, tasks 13, runs 39 (repeat 3)
- date: 2026-10-12 22:46:43
- hypothesis: model comparison with explicit model id; max_tokens 16384 (4096 truncated thinking), max_steps 50 (30 exhausted by slower explorers)

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 87.2% (95% CI 71.8–100.0%) |
| mean steps | 9.3 |
| mean input tokens (incl. cache) | 64355 |
| mean output tokens | 7864 |
| mean reasoning tokens (0 = not reported) | 4576 |
| mean cost (USD/run), off-peak price | 0.00540 |
| mean cost (USD/run), peak price | 0.01081 |
| mean wall time (s) | 61.4 |
| mean tool errors | 0.10 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 34 |
| tests_failed_after_edit | 5 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 5.0 | pass×3 |
| b03-patch-apply | 0.33 (1/3) | 18.3 | tests_failed_after_edit×2, pass×1 |
| b05-interpolate | 1.00 (3/3) | 6.7 | pass×3 |
| b08-csv-loader | 1.00 (3/3) | 8.3 | pass×3 |
| b09-sliding-window | 1.00 (3/3) | 6.7 | pass×3 |
| b12-sessions | 0.67 (2/3) | 9.7 | pass×2, tests_failed_after_edit×1 |
| b13-interval-set | 1.00 (3/3) | 8.7 | pass×3 |
| b15-cron-next | 1.00 (3/3) | 9.0 | pass×3 |
| b16-text-diff | 1.00 (3/3) | 11.7 | pass×3 |
| b19-regex-engine | 1.00 (3/3) | 12.0 | pass×3 |
| b21-timer-queue | 1.00 (3/3) | 11.3 | pass×3 |
| b22-linear-solver | 0.33 (1/3) | 7.0 | tests_failed_after_edit×2, pass×1 |
| b23-meeting-slots | 1.00 (3/3) | 6.3 | pass×3 |
