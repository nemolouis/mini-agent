# Eval report: 20261016-145525-g35-lite-relay

- config: `g35-lite-relay` (hash `4bca5c6a9f`), model `gemini-3.5-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.5-flash-lite
- split: **dev**, tasks 4, valid runs 12 (repeat 3); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-16 14:55:25
- hypothesis: gemini-3.5-flash-lite over the native protocol via the relay: expected to sit between 3.1-flash-lite (26%) and DeepSeek flash (~90%+), i.e. a baseline with room in both directions; free quota 500 requests/day/project

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 33.3% (95% CI 8.3–58.3%) |
| mean steps | 22.6 |
| mean input tokens (incl. cache) | 174484 |
| mean output tokens | 6762 |
| mean reasoning tokens (0 = not reported) | 165 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 460.8 |
| mean tool errors | 0.42 |
| runs with summary-compaction | 0 |
| runs that modified tests | 12 |
| failed runs whose own last test run was green (false completion) | 8 / 8 |
| runs that needed an api_error rerun | 1 |

## Failure classes (per run)

| class | runs |
|---|---|
| tests_failed_after_edit | 7 |
| pass | 4 |
| no_edit | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b08-csv-loader | 0.67 (2/3) | 31.7 | tests_failed_after_edit×1, pass×2 |
| b12-sessions | 0.33 (1/3) | 22.3 | tests_failed_after_edit×2, pass×1 |
| b13-interval-set | 0.00 (0/3) | 17.7 | tests_failed_after_edit×3 |
| b16-text-diff | 0.33 (1/3) | 18.7 | pass×1, tests_failed_after_edit×1, no_edit×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
