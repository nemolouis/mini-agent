# Eval report: 20261011-190827-flash

- config: `flash` (hash `a3a98492f7`), model `deepseek-flash`, temperature 0.0, max_steps 30
- model reported by server: deepseek-flash
- split: **dev**, tasks 6, runs 18 (repeat 3)
- date: 2026-10-11 19:08:27
- hypothesis: model comparison with explicit model id; max_tokens raised 4096 -> 16384 because 4096 truncated thinking-heavy runs (class max_tokens)

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 83.3% (95% CI 61.1–100.0%) |
| mean steps | 9.3 |
| mean input tokens (incl. cache) | 85058 |
| mean output tokens | 8994 |
| mean reasoning tokens (0 = not reported) | 5964 |
| mean cost (USD/run), off-peak price | 0.00612 |
| mean cost (USD/run), peak price | 0.01224 |
| mean wall time (s) | 55.9 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 15 |
| tests_failed_after_edit | 3 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 5.0 | pass×3 |
| b03-patch-apply | 0.33 (1/3) | 22.7 | tests_failed_after_edit×2, pass×1 |
| b05-interpolate | 1.00 (3/3) | 6.7 | pass×3 |
| b08-csv-loader | 1.00 (3/3) | 8.7 | pass×3 |
| b09-sliding-window | 1.00 (3/3) | 6.7 | pass×3 |
| b12-sessions | 0.67 (2/3) | 6.3 | pass×2, tests_failed_after_edit×1 |
