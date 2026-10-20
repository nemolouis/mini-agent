# Eval report: 20261012-142646-flash

- config: `flash` (hash `7321289890`), model `deepseek-flash`, temperature 0.0, max_steps 50
- model reported by server: deepseek-flash
- split: **dev**, tasks 13, runs 39 (repeat 3)
- date: 2026-10-12 14:26:46
- hypothesis: model comparison with explicit model id; max_tokens 16384 (4096 truncated thinking), max_steps 50 (30 exhausted by slower explorers)

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 76.9% (95% CI 56.4–92.3%) |
| mean steps | 9.1 |
| mean input tokens (incl. cache) | 63229 |
| mean output tokens | 8475 |
| mean reasoning tokens (0 = not reported) | 5467 |
| mean cost (USD/run), off-peak price | 0.00575 |
| mean cost (USD/run), peak price | 0.01150 |
| mean wall time (s) | 112.4 |
| mean tool errors | 0.08 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 30 |
| tests_failed_after_edit | 9 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 6.0 | pass×3 |
| b03-patch-apply | 1.00 (3/3) | 14.0 | pass×3 |
| b05-interpolate | 1.00 (3/3) | 8.3 | pass×3 |
| b08-csv-loader | 1.00 (3/3) | 8.0 | pass×3 |
| b09-sliding-window | 1.00 (3/3) | 11.0 | pass×3 |
| b12-sessions | 0.33 (1/3) | 6.7 | pass×1, tests_failed_after_edit×2 |
| b13-interval-set | 1.00 (3/3) | 8.3 | pass×3 |
| b15-cron-next | 0.33 (1/3) | 7.7 | tests_failed_after_edit×2, pass×1 |
| b16-text-diff | 1.00 (3/3) | 9.3 | pass×3 |
| b19-regex-engine | 0.67 (2/3) | 13.7 | tests_failed_after_edit×1, pass×2 |
| b21-timer-queue | 1.00 (3/3) | 10.7 | pass×3 |
| b22-linear-solver | 0.00 (0/3) | 7.0 | tests_failed_after_edit×3 |
| b23-meeting-slots | 0.67 (2/3) | 7.7 | tests_failed_after_edit×1, pass×2 |
