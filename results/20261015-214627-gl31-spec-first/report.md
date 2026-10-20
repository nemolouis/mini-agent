# Eval report: 20261015-214627-gl31-spec-first

- config: `gl31-spec-first` (hash `d554b66974`), model `gemini-3.1-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.1-flash-lite
- split: **dev**, tasks 13, valid runs 13 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-15 21:46:27
- hypothesis: PREDICTION (baseline gemini-3.1-flash-lite 25.6%, 21/29 failures ended with a green own test run): a prompt that forces a spec-derived verification pass cuts false completions by at least a third and lifts pass rate by 10-20 points; steps rise by 20-40%; tasks whose failing tests are documented edge cases (b02, b21, b25, b26) gain most.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 30.8% (95% CI 7.7–61.5%) |
| mean steps | 27.2 |
| mean input tokens (incl. cache) | 155340 |
| mean output tokens | 4901 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 209.1 |
| mean tool errors | 0.23 |
| runs with summary-compaction | 0 |
| runs that modified tests | 1 |
| failed runs whose own last test run was green (false completion) | 5 / 9 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| tests_failed_after_edit | 9 |
| pass | 4 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (1/1) | 24.0 | pass×1 |
| b05-interpolate | 0.00 (0/1) | 18.0 | tests_failed_after_edit×1 |
| b08-csv-loader | 0.00 (0/1) | 20.0 | tests_failed_after_edit×1 |
| b09-sliding-window | 1.00 (1/1) | 17.0 | pass×1 |
| b12-sessions | 0.00 (0/1) | 43.0 | tests_failed_after_edit×1 |
| b13-interval-set | 0.00 (0/1) | 23.0 | tests_failed_after_edit×1 |
| b15-cron-next | 0.00 (0/1) | 31.0 | tests_failed_after_edit×1 |
| b16-text-diff | 1.00 (1/1) | 50.0 | pass×1 |
| b19-regex-engine | 0.00 (0/1) | 33.0 | tests_failed_after_edit×1 |
| b21-timer-queue | 0.00 (0/1) | 20.0 | tests_failed_after_edit×1 |
| b23-meeting-slots | 0.00 (0/1) | 37.0 | tests_failed_after_edit×1 |
| b25-patch-apply-v2 | 0.00 (0/1) | 22.0 | tests_failed_after_edit×1 |
| b26-linear-solver-v2 | 1.00 (1/1) | 15.0 | pass×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
