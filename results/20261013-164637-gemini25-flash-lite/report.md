# Eval report: 20261013-164637-gemini25-flash-lite

- config: `gemini25-flash-lite` (hash `fea114f175`), model `gemini-2.5-flash-lite`, temperature 0.0, max_steps 50
- model reported by server: unknown
- split: **dev**, tasks 1, runs 1 (repeat 1)
- date: 2026-10-13 16:46:37
- hypothesis: Gemini 2.5 Flash-Lite: expected clearly weaker than 2.5 Flash, to give the benchmark headroom

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 0.0% (95% CI n/a–n/a%) |
| mean steps | 0.0 |
| mean input tokens (incl. cache) | 0 |
| mean output tokens | 0 |
| mean reasoning tokens (0 = not reported) | 0 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 1.4 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |
| runs that needed an api_error rerun | 1 |

## Failure classes (per run)

| class | runs |
|---|---|
| api_error | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b02-month-recurrence | 0.00 (0/1) | 0.0 | api_error×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
