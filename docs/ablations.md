# Ablations on DeepSeek flash (B-layer dev, 13 tasks x 3 repeats)

Model `deepseek-flash`, temperature 0, 13 tasks of the B layer (dev split, retired tasks excluded), 3 repeats per
task. Baseline = `results/20261013-194844-flash`. Every condition changes exactly one thing. Predictions were
written into each config's `hypothesis` field **before** the runs; they are scored below, including the ones
that turned out wrong.

| condition | valid runs | pass rate (95% CI) | mean steps | failure classes | verdict on the prediction |
|---|---|---|---|---|---|
| baseline | 39 | 90% (77-100) | 8.7 | 3 tests_failed_after_edit, 1 max_tokens | - |
| no-bash | 39 | 97% (92-100) | 8.6 | 1 tests_failed_after_edit | **refuted** |
| steps10 | 39 | 95% (87-100) | 8.2 | 2 max_steps | **refuted** (mis-calibrated) |
| ctx3k | 39 | 77% (59-92) | 41.8 | 8 max_steps, 1 max_tokens | direction right, **mechanism wrong** |
| no-grep | 3 | - | - | 36 runs lost to HTTP 402 (out of balance) | not evaluated |
| no-verify-prompt | 0 | - | - | 39 runs lost to HTTP 402 (out of balance) | not evaluated |

## no-bash (cannot run anything, so cannot run tests)
- Predicted: pass rate -10 to -25 points, mostly `tests_failed_after_edit` on tasks that need iteration.
- Observed: **90% -> 97%** (+8 points, paired 95% CI 0 to 15), steps unchanged (8.7 -> 8.6). No run executed a
  test (baseline: 39 of 39 did). The model still *tried* to call `bash` 40 times (about once per run) and got
  "unknown tool" errors.
- The three tasks that moved are exactly the ones the baseline sometimes fails (b12 .33 -> .67, b19 .67 -> 1.0,
  b25 .67 -> 1.0); nothing regressed.
- Reading: for spec-driven tasks this model works as a reader/reasoner, and running the visible tests was not what
  made it succeed. A cautious reading is "running tests did not help here"; the +8 is borderline and I do not claim
  that removing bash helps. A hypothesis worth testing separately: green visible tests give false confidence
  (see the false-completion rate in failure_cases.md).

## steps10 (step budget 10 instead of 50)
- Predicted: tasks that average >= 10 steps in the baseline fall to `max_steps`; overall -15 to -30 points.
- Observed: **95%** (+5, CI -5 to 18). Only 2 of 39 runs hit the cap.
- Why the prediction was wrong: it was calibrated on step counts from an earlier, harder configuration. In this
  baseline the mean is 8.7 steps and 30 of 39 runs finish within 10. A budget of 10 is almost never binding for
  this model, so 30-50 is simply headroom it does not use.

## ctx3k (compact when input exceeds 70% of 3,000 tokens, keep 4 messages)
- Predicted: pass rate -10 to -30 points; failures are `tests_failed_after_edit` caused by details lost in
  summarisation.
- Observed: **90% -> 77%** (-13, CI -28 to +3) - the direction and size match - but the mechanism does not:
  - the failures are `max_steps` (8) and `max_tokens` (1), **none** is `tests_failed_after_edit`;
  - mean steps went from 8.7 to **41.8** and output tokens from 8.3k to 25k per run;
  - 1,199 summary compactions over 39 runs (about 31 per run; 38 of 39 runs compacted).
- Cause (a design flaw in the loop, not a model weakness): after a compaction the next request is again above
  the threshold, so the loop compacts on **every** step. The fixed part of the request is only 828 tokens; what
  stays above the threshold is the verbatim window of the last 4 messages (whole tool outputs), which compaction
  does not touch. It never gets a stable working context and burns its step budget re-summarising.
  This experiment therefore measured a thrashing loop, not the quality of the summaries.
  To see it: `miniagent-eval view results/20261013-194844-flash results/20261013-205516-ctx3k`, open b08 r0 as A from
  the first directory and as B from the second; B shows 33 summary compactions in 50 steps.
- Follow-up: the trigger now waits for regrowth when a compaction cannot get below the threshold
  (`compact_regrowth`, see failure case 2; in simulation 22 -> 3 summaries in 25 steps). The re-run
  `configs/abl-ctx3k-fixed.json` and the feasible-limit experiment `configs/abl-ctx10k.json` are prepared with
  predictions but have **not been run** (DeepSeek has no balance); the numbers in the table above are from the code
  before the fix. The fix was verified on Gemini 3.5-flash-lite instead (`g35-ctx3k-fixed`: 1-6 summaries per run,
  mean 29.5 steps; `g35-ctx12k`: at most 1 summary per run, 23.7 steps, 41.7% vs 33% baseline, within noise). One
  prediction missed (2 of 12 runs still ended above the threshold); details in failure case 2.

## no-grep, no-verify-prompt
Both runs stopped being valid when the DeepSeek account ran out of balance (`HTTP 402 Insufficient Balance`).
no-grep has 3 valid runs (all passed), no-verify-prompt has none. They are reported as **not evaluated**, not as
passes. The harness now treats HTTP 402 as a permanent error and stops the batch instead of running the
remaining jobs.

## Caveats
- 13 tasks x 3 repeats is a small sample and the baseline is near the ceiling (90%): differences of 5-8 points are
  within what a repeat of the same condition could show. Only the ctx3k step/token blow-up is unambiguous.
- There is no replicate of the baseline on this exact task set, so the run-to-run noise of the baseline itself is
  not measured directly.
