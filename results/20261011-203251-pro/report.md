# Eval report: 20261011-203251-pro

- config: `pro` (hash `a43c691338`), model `deepseek-v4-pro`, temperature 0.0, max_steps 30
- model reported by server: deepseek-v4-pro
- split: **dev**, tasks 6, runs 18 (repeat 3)
- date: 2026-10-11 20:32:51
- hypothesis: model comparison with explicit model id; max_tokens raised 4096 -> 16384 because 4096 truncated thinking-heavy runs (class max_tokens)

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 88.9% (95% CI 66.7–100.0%) |
| mean steps | 20.1 |
| mean input tokens (incl. cache) | 297672 |
| mean output tokens | 17884 |
| mean reasoning tokens (0 = not reported) | 13927 |
| mean cost (USD/run), off-peak price | 0.04534 |
| mean cost (USD/run), peak price | 0.09069 |
| mean wall time (s) | 235.9 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 16 |
| max_steps | 2 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (3/3) | 6.3 | pass×3 |
| b03-patch-apply | 0.33 (1/3) | 30.0 | pass×1, max_steps×2 |
| b05-interpolate | 1.00 (3/3) | 27.3 | pass×3 |
| b08-csv-loader | 1.00 (3/3) | 26.3 | pass×3 |
| b09-sliding-window | 1.00 (3/3) | 12.3 | pass×3 |
| b12-sessions | 1.00 (3/3) | 18.0 | pass×3 |
