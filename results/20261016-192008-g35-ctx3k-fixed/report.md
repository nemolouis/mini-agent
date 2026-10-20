# Eval report: 20261016-192008-g35-ctx3k-fixed

- config: `g35-ctx3k-fixed` (hash `fb2f832cf9`), model `gemini-3.5-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.5-flash-lite
- split: **dev**, tasks 4, valid runs 4 (repeat 1); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-16 19:20:08
- hypothesis: PREDICTION (compaction fix, mechanism check; gemini-3.5-flash-lite, 4 tasks x 1): the 3000-token limit is not reachable by compaction (580 prompt tokens + verbatim recent tool outputs exceed the 2100 threshold), so every run that compacts logs `compaction_floor`. Before the fix this regime gave about 31 summary compactions and 42 steps per run (DeepSeek, results/20261013-205516-ctx3k). Now: <= 8 summary compactions per run, mean steps <= 34 (1.5x the 22.6 of the g35-mid baseline), and no run ends in `max_steps` because of compaction. The pass rate is NOT interpreted (n=4).

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 50.0% (95% CI 0.0–100.0%) |
| mean steps | 29.5 |
| mean input tokens (incl. cache) | 130768 |
| mean output tokens | 6755 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 736.2 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 4 |
| runs that modified tests | 4 |
| failed runs whose own last test run was green (false completion) | 1 / 2 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 2 |
| tests_failed_after_edit | 1 |
| max_steps | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b08-csv-loader | 0.00 (0/1) | 50.0 | max_steps×1 |
| b12-sessions | 1.00 (1/1) | 37.0 | pass×1 |
| b13-interval-set | 0.00 (0/1) | 18.0 | tests_failed_after_edit×1 |
| b16-text-diff | 1.00 (1/1) | 13.0 | pass×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
