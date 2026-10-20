# Eval report: 20261013-205516-ctx3k

- config: `ctx3k` (hash `96e26db4e6`), model `deepseek-flash`, temperature 0.0, max_steps 50
- model reported by server: deepseek-flash
- split: **dev**, tasks 13, valid runs 39 (repeat 3); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-13 20:55:16
- hypothesis: PREDICTION: with context_limit=3000 almost every run compacts. Mean steps rises and pass rate drops 10-30 points; failures are tests_failed_after_edit caused by lost details after summarisation.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 76.9% (95% CI 59.0–92.3%) |
| mean steps | 41.8 |
| mean input tokens (incl. cache) | 160897 |
| mean output tokens | 25184 |
| mean reasoning tokens (0 = not reported) | 19759 |
| mean cost (USD/run), off-peak price | 0.02780 |
| mean cost (USD/run), peak price | 0.05561 |
| mean wall time (s) | 2358.6 |
| mean tool errors | 0.51 |
| runs with summary-compaction | 38 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 30 |
| max_steps | 8 |
| max_tokens | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 12.0 | pass×3 |
| b05-interpolate | 1.00 (3/3) | 50.0 | pass×3 |
| b08-csv-loader | 0.67 (2/3) | 50.0 | max_steps×1, pass×2 |
| b09-sliding-window | 1.00 (3/3) | 27.7 | pass×3 |
| b12-sessions | 0.67 (2/3) | 50.0 | pass×2, max_steps×1 |
| b13-interval-set | 1.00 (3/3) | 50.0 | pass×3 |
| b15-cron-next | 0.33 (1/3) | 50.0 | max_steps×2, pass×1 |
| b16-text-diff | 0.67 (2/3) | 30.3 | max_tokens×1, pass×2 |
| b19-regex-engine | 0.00 (0/3) | 50.0 | max_steps×3 |
| b21-timer-queue | 1.00 (3/3) | 50.0 | pass×3 |
| b23-meeting-slots | 1.00 (3/3) | 39.7 | pass×3 |
| b25-patch-apply-v2 | 0.67 (2/3) | 50.0 | pass×2, max_steps×1 |
| b26-linear-solver-v2 | 1.00 (3/3) | 34.0 | pass×3 |
