# Eval report: 20261011-172740-pro

- config: `pro` (hash `6d418e0725`), model `deepseek-v4-pro`, temperature 0.0, max_steps 30
- model reported by server: deepseek-v4-pro
- split: **dev**, tasks 6, runs 18 (repeat 3)
- date: 2026-10-11 17:27:40
- hypothesis: model comparison: same harness settings as baseline, explicit model id

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 61.1% (95% CI 22.2–94.4%) |
| mean steps | 12.1 |
| mean input tokens (incl. cache) | 105774 |
| mean output tokens | 9598 |
| mean cost (USD/run), off-peak price | 0.02376 |
| mean cost (USD/run), peak price | 0.04751 |
| mean wall time (s) | 125.6 |
| mean tool errors | 0.06 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 11 |
| max_tokens | 7 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 5.7 | pass×3 |
| b03-patch-apply | 0.00 (0/3) | 10.0 | max_tokens×3 |
| b05-interpolate | 0.00 (0/3) | 4.3 | max_tokens×3 |
| b08-csv-loader | 0.67 (2/3) | 19.3 | max_tokens×1, pass×2 |
| b09-sliding-window | 1.00 (3/3) | 15.0 | pass×3 |
| b12-sessions | 1.00 (3/3) | 18.0 | pass×3 |
