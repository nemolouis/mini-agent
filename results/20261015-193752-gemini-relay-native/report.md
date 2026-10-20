# Eval report: 20261015-193752-gemini-relay-native

- config: `gemini-relay-native` (hash `8ac84b8fd6`), model `gemini-3.1-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.1-flash-lite
- split: **dev**, tasks 13, valid runs 39 (repeat 3); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-15 19:37:52
- hypothesis: gemini-3.1-flash-lite over the Gemini-native protocol through a forwarding relay (thought signatures handled by us)

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 25.6% (95% CI 7.7–43.6%) |
| mean steps | 24.1 |
| mean input tokens (incl. cache) | 138610 |
| mean output tokens | 4203 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 161.4 |
| mean tool errors | 0.46 |
| runs with summary-compaction | 0 |
| runs that modified tests | 9 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| tests_failed_after_edit | 29 |
| pass | 10 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 0.33 (1/3) | 21.3 | pass×1, tests_failed_after_edit×2 |
| b05-interpolate | 0.67 (2/3) | 22.0 | pass×2, tests_failed_after_edit×1 |
| b08-csv-loader | 0.33 (1/3) | 35.7 | tests_failed_after_edit×2, pass×1 |
| b09-sliding-window | 1.00 (3/3) | 20.3 | pass×3 |
| b12-sessions | 0.00 (0/3) | 14.3 | tests_failed_after_edit×3 |
| b13-interval-set | 0.67 (2/3) | 23.3 | tests_failed_after_edit×1, pass×2 |
| b15-cron-next | 0.00 (0/3) | 22.3 | tests_failed_after_edit×3 |
| b16-text-diff | 0.33 (1/3) | 40.0 | tests_failed_after_edit×2, pass×1 |
| b19-regex-engine | 0.00 (0/3) | 32.0 | tests_failed_after_edit×3 |
| b21-timer-queue | 0.00 (0/3) | 18.7 | tests_failed_after_edit×3 |
| b23-meeting-slots | 0.00 (0/3) | 21.7 | tests_failed_after_edit×3 |
| b25-patch-apply-v2 | 0.00 (0/3) | 26.7 | tests_failed_after_edit×3 |
| b26-linear-solver-v2 | 0.00 (0/3) | 14.7 | tests_failed_after_edit×3 |

_Cost is n/a: fill in `configs/prices.json` for this model._
