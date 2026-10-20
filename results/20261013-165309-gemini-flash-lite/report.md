# Eval report: 20261013-165309-gemini-flash-lite

- config: `gemini-flash-lite` (hash `454e8e01d7`), model `gemini-3.5-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.5-flash-lite
- split: **dev**, tasks 1, runs 1 (repeat 1)
- date: 2026-10-13 16:53:09
- hypothesis: smaller/cheaper Gemini tier: expected to sit clearly below gemini-3.8-flash, giving the benchmark some headroom

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 100.0% (95% CI n/a–n/a%) |
| mean steps | 19.0 |
| mean input tokens (incl. cache) | 63476 |
| mean output tokens | 1461 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 74.3 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 1.00 (1/1) | 19.0 | pass×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
