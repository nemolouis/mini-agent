# Eval report: 20261011-165208-baseline

- config: `baseline` (hash `a3c57d08e9`), model `deepseek-chat`, temperature 0.0, max_steps 30
- split: **dev**, tasks 9, runs 27 (repeat 3)
- date: 2026-10-11 16:52:08
- hypothesis: baseline, no hypothesis

## Summary

| metric | value |
|---|---|
| pass rate (task-averaged) | 100.0% (95% CI 100.0–100.0%) |
| mean steps | 5.3 |
| mean input tokens (incl. cache) | 8449 |
| mean output tokens | 713 |
| mean cost (USD/run) | n/a |
| mean wall time (s) | 30.9 |
| mean tool errors | 0.00 |
| runs with summary-compaction | 0 |
| runs that modified tests | 0 |

## Failure classes (per run)

| class | runs |
|---|---|
| pass | 27 |

## Per task

| task | pass rate | steps (mean) | classes |
|---|---|---|---|
| 01-moving-average | 1.00 (3/3) | 5.0 | pass×3 |
| 02-shared-default | 1.00 (3/3) | 5.0 | pass×3 |
| 03-parse-duration | 1.00 (3/3) | 6.0 | pass×3 |
| 04-top-words | 1.00 (3/3) | 5.0 | pass×3 |
| 07-utc-epoch | 1.00 (3/3) | 5.7 | pass×3 |
| 08-config-merge | 1.00 (3/3) | 5.0 | pass×3 |
| 10-lru-memo | 1.00 (3/3) | 5.3 | pass×3 |
| 11-token-bucket | 1.00 (3/3) | 6.0 | pass×3 |
| 12-pagination | 1.00 (3/3) | 5.0 | pass×3 |

_Cost is n/a: fill in `configs/prices.json` for this model._
