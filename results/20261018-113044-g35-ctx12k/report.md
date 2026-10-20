# Eval report: 20261018-113044-g35-ctx12k

- config: `g35-ctx12k` (hash `6da13ad918`), model `gemini-3.5-flash-lite`, temperature None, max_steps 50
- model reported by server: gemini-3.5-flash-lite
- split: **dev**, tasks 4, valid runs 12 (repeat 3); **0 run(s) excluded because the API failed** (see failure classes)
- date: 2026-10-18 11:30:44
- hypothesis: PREDICTION (feasible limit; baseline peak input per run: median 10.7k tokens, so the 8400-token threshold is crossed in about 10 of 12 runs): <= 3 summary compactions per affected run, compaction always gets below the threshold (no `compaction_floor` events), mean steps within 25% of the baseline's 22.6 (<= 28). Pass rate versus the g35-mid baseline (33%, n=12): within +-25 points; with n=12 only a larger change could be detected, so a smaller drop concentrated in runs that compacted would be a hint about summary information loss, not a finding.

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 41.7% (95% CI 16.7–66.7%) |
| mean steps | 23.7 |
| mean input tokens (incl. cache) | 112281 |
| mean output tokens | 5018 |
| mean reasoning tokens (0 = not reported) | 182 |
| mean cost (USD/run), off-peak price | n/a |
| mean cost (USD/run), peak price | n/a |
| mean wall time (s) | 129.5 |
| mean tool errors | 0.17 |
| runs with summary-compaction | 7 |
| runs that modified tests | 11 |
| failed runs whose own last test run was green (false completion) | 6 / 7 |
| runs that needed an api_error rerun | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| tests_failed_after_edit | 6 |
| pass | 5 |
| stopped_malformed_response | 1 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| b08-csv-loader | 0.67 (2/3) | 22.3 | tests_failed_after_edit×1, pass×2 |
| b12-sessions | 0.33 (1/3) | 25.7 | tests_failed_after_edit×2, pass×1 |
| b13-interval-set | 0.67 (2/3) | 29.7 | pass×2, tests_failed_after_edit×1 |
| b16-text-diff | 0.00 (0/3) | 17.0 | tests_failed_after_edit×2, stopped_malformed_response×1 |

_Cost is n/a: fill in `configs/prices.json` for this model._
