# Eval report: 20261016-113644-g35-lite-relay

- config: `g35-lite-relay` (hash `4bca5c6a9f`), model `gemini-3.5-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.5-flash-lite
- split: **dev**, tasks 13, valid runs 13 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-16 11:36:44
- hypothesis: gemini-3.5-flash-lite over the native protocol via the relay: expected to sit between 3.1-flash-lite (26%) and DeepSeek flash (~90%+), i.e. a baseline with room in both directions; free quota 500 requests/day/project

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 53.8% (95% CI 30.8–76.9%) |
| mean steps | 22.2 |
| mean input tokens (incl. cache) | 155258 |
| mean output tokens | 5409 |
| mean reasoning tokens (0 = not reported) | 607 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 200.7 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 11 |
| failed runs whose own last test run was green (false completion) | 4 / 6 |
| runs that needed an api_error rerun | 1 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 7 |
| tests_failed_after_edit | 4 |
| max_steps | 2 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (1/1) | 21.0 | pass×1 |
| b05-interpolate | 1.00 (1/1) | 16.0 | pass×1 |
| b08-csv-loader | 0.00 (0/1) | 50.0 | max_steps×1 |
| b09-sliding-window | 1.00 (1/1) | 11.0 | pass×1 |
| b12-sessions | 0.00 (0/1) | 17.0 | tests_failed_after_edit×1 |
| b13-interval-set | 0.00 (0/1) | 19.0 | tests_failed_after_edit×1 |
| b15-cron-next | 0.00 (0/1) | 17.0 | tests_failed_after_edit×1 |
| b16-text-diff | 1.00 (1/1) | 19.0 | pass×1 |
| b19-regex-engine | 0.00 (0/1) | 27.0 | tests_failed_after_edit×1 |
| b21-timer-queue | 1.00 (1/1) | 15.0 | pass×1 |
| b23-meeting-slots | 1.00 (1/1) | 14.0 | pass×1 |
| b25-patch-apply-v2 | 0.00 (0/1) | 50.0 | max_steps×1 |
| b26-linear-solver-v2 | 1.00 (1/1) | 12.0 | pass×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
