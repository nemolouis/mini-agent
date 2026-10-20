# Eval report: 20261011-171434-flash

- config: `flash` (hash `b61bd458bb`), model `deepseek-flash`, temperature 0.0, max_steps 30
- model reported by server: deepseek-flash
- split: **dev**, tasks 6, runs 18 (repeat 3)
- date: 2026-10-11 17:14:34
- hypothesis: model comparison: same harness settings as baseline, explicit model id

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 61.1% (95% CI 33.3–88.9%) |
| mean steps | 7.9 |
| mean input tokens (incl. cache) | 42648 |
| mean output tokens | 5593 |
| mean cost (USD/run), off-peak price | 0.00391 |
| mean cost (USD/run), peak price | 0.00781 |
| mean wall time (s) | 40.7 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 11 |
| max_tokens | 4 |
| tests_failed_after_edit | 3 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 0.67 (2/3) | 6.0 | pass×2, tests_failed_after_edit×1 |
| b03-patch-apply | 0.33 (1/3) | 13.3 | max_tokens×1, tests_failed_after_edit×1, pass×1 |
| b05-interpolate | 0.00 (0/3) | 3.7 | max_tokens×3 |
| b08-csv-loader | 1.00 (3/3) | 11.3 | pass×3 |
| b09-sliding-window | 1.00 (3/3) | 6.7 | pass×3 |
| b12-sessions | 0.67 (2/3) | 6.7 | pass×2, tests_failed_after_edit×1 |
