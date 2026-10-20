# Failure cases

A catalogue of problems found while building and evaluating the agent. Each case says what happened, the
evidence, the root cause, and its status. The point is to separate **defects in our own system** (loop, harness,
tasks, provider integration) from **behaviour of a particular model**, because only the first kind can be fixed
and tested.

How to read it
- Category: **S** agent loop / tools, **H** evaluation harness, **T** task design, **P** provider integration,
  **M** model behaviour.
- Cases of kind S/H/T/P do not depend on which model produced them. Cases of kind M are **observations about one
  model on one task set** and are labelled with the model and the sample size; they are not claims about LLMs in
  general.
- Evidence paths (`results/...`, `runs/...`) are local run directories (not committed). Each contains the
  `trajectory.jsonl` of every run, `runs.jsonl` and `report.md`.

| # | Case | Cat. | Status |
|---|---|---|---|
| 1 | Compaction summary built from an already-elided transcript | S | fixed, tested |
| 2 | Compaction runs on every step ("thrash") | S | fixed (cost bounded), tested; re-run pending |
| 3 | Timed-out pipelines leave orphan processes at 100% CPU | S | fixed, tested |
| 4 | Agent cds into a path it guessed | S | fixed (prompt) |
| 5 | Editing test files hid the real failure class | H | fixed, tested |
| 6 | `.git/` metadata counted as an edit | H | fixed, tested |
| 7 | Server-side failures counted as model failures | H | fixed, tested |
| 8 | Batch kept running after unrecoverable errors | H | fixed, tested |
| 9 | Too small `max_tokens` made a thinking model look weak | H | fixed (config) |
| 10 | Hidden tests that the spec does not imply | T | fixed (new task ids) |
| 11 | Benchmark saturated; headroom only appeared with a weaker model | T | addressed (model ladder) |
| 12 | Relay translation layer broke Gemini 3 tool calls | P | fixed (native protocol), tested |
| 13 | False completion: stops after a green *visible* test run | M | **open** |
| 14 | Runaway thinking uses the whole output budget | M | observation |
| 15 | A test for a blocking hazard blocked the test run | T | fixed |

---

## 1. Compaction summary built from an already-elided transcript  (S)
- **Evidence**: `runs/20261011-160732`, `runs/20261011-161226` (`--context-limit 3000`, DeepSeek).
- **What happened**: after compaction the agent's own summary said "`test_order.py`: read but contents elided in
  transcript - not yet summarized" and, in the other run, "Task: Unknown (not stated in transcript)". In one run
  the "compacted" history was not smaller than before (est. 1997 -> 2006 tokens).
- **Root cause**: compaction has two stages. Stage 1 replaces old tool outputs with `[elided N chars]`; stage 2
  asked the model to summarise the middle of the history - but it was handed the already-elided messages, so the
  information the summary was supposed to preserve had been deleted one step earlier. The task statement was also
  not passed to the summariser.
- **Fix**: stage 2 summarises the original messages and receives the task text. Regression test
  `test_summary_sees_unelided_tool_output`.
- **Lesson**: in a multi-stage context pipeline each stage must read from the source of truth, not from the
  previous stage's lossy output.

## 2. Compaction runs on every step ("thrash")  (S)
- **Evidence**: `results/20261013-205516-ctx3k` (DeepSeek flash, `context_limit=3000`, 13 tasks x 3), baseline
  `results/20261013-194844-flash`.
- **What happened**: pass rate 90% -> 77%, but mean steps 8.7 -> **41.8**, output tokens 8.3k -> 25k per run,
  **1,199 summary compactions in 39 runs** (about 31 per run; 38 of 39 runs compacted). Failures are
  `max_steps` (8) and `max_tokens` (1); none is "edited but wrong".
- **Root cause**: the trigger was "last reported input tokens > 70% of the limit". When a compaction *cannot* get the
  next request below that threshold, the very next step triggers another one, indefinitely. In the ctx3k runs the
  fixed part of the request (system prompt + tool definitions + task) is only **828 tokens (28% of the limit)**; what
  keeps the input above the 2,100-token threshold is the **verbatim recent window**: the last `keep_recent=4`
  messages hold whole tool outputs (file contents, test logs of 1-2k tokens each). Elision and summarisation
  skip exactly those messages, so compaction cannot go below them, and the loop never reaches a stable working
  context. (An earlier version of this entry blamed the prompt and tool definitions; measuring the step-1 input
  showed that was wrong.)
- **Fix**: `Agent.compact_regrowth` (default 1.0) and `_compact_trigger`. The loop records the input size measured on
  the first request after each compaction (the "floor"). If the floor is below the 70% threshold the compaction worked
  and the trigger is unchanged (identical behaviour, tested). If the floor is at or above the threshold, the next
  compaction waits until the input has grown by `compact_regrowth` times the floor, and a `compaction_floor` event
  records that this limit is not reachable by compaction. Compaction events also record `trigger_input_tokens`.
- **Evidence for the fix (simulation, deterministic)**: with a 3,000-token limit, 2,000-token fixed prompt, 4 verbatim
  messages and ~800-token tool outputs, the old trigger made **22 summaries in 25 steps**; the new one makes **3**
  (1,600-token outputs: 22 -> 4). Tests: `test_the_old_trigger_thrashes_...`, `test_compaction_waits_for_regrowth_...`,
  `test_when_compaction_works_the_trigger_is_unchanged`; three mutations of the fix are each caught by the tests.
- **Evidence for the fix (real runs, Gemini 3.5-flash-lite, `g35-mid` = 4 tasks)**: the pre-registered predictions are in
  `configs/g35-ctx3k-fixed.json` and `configs/g35-ctx12k.json`.
  - `results/20261016-192008-g35-ctx3k-fixed` (limit 3,000, 4 runs): summaries per run 6 / 3 / 5 / 1 (before the fix about 31),
    mean steps 29.5 (before about 42), 10 `compaction_floor` events (every run that compacted). Predictions met.
    One run (b08) ended in `max_steps` with 5 summaries; the same task also reached 50 steps once in the uncompacted
    baseline, so this run cannot be attributed to compaction either way.
  - `results/20261018-113044-g35-ctx12k` (limit 12,000, 12 runs): at most 1 summary per run, mean steps 23.7
    (baseline 22.6), pass rate 41.7% (5/12) vs 33% baseline. **One prediction missed**: I predicted compaction would
    always get below the 8,400-token threshold; in 2 of 12 runs (both b16-text-diff) the input after compaction was
    9,441 and 8,857 tokens, because the verbatim window held large tool outputs that summarising does not touch. The
    regrowth rule handled both (1 summary each, no loop), so the *fix* holds, but my model of "feasible limit" was
    incomplete: feasibility depends on the size of the last `keep_recent` messages, not only on the limit.
  - Pass rates are not evidence about summary quality: n=4 and n=12, 8 compacted runs passed 4 and 4 uncompacted runs
    passed 1, which is inside the noise. `tampered_tests` is true in almost every run here and in the baseline (the
    model edits test files; the harness restores them before grading), so it does not separate the conditions.
  - Not run: the DeepSeek versions `configs/abl-ctx3k-fixed.json` and `configs/abl-ctx10k.json` (no balance). The
    old DeepSeek ctx3k table row is still the pre-fix code.
- **Lesson**: the experiment was meant to test summary quality and instead measured a control-loop bug. Check that
  the *class* of failure matches the mechanism the experiment targets before interpreting the pass rate. Also measure
  before explaining: the first diagnosis of the cause here was plausible and wrong.

## 3. Timed-out pipelines leave orphan processes at 100% CPU  (S)
- **Evidence**: reproduced locally with `python3 -c "while True: pass" 2>&1 | tail -5` and a 1 s timeout: after the
  tool reported "timed out", a Python process with PPID 1 kept running at 100% CPU. A single command did *not*
  reproduce it (the shell `exec`s it), which is why it was intermittent.
- **Root cause**: `subprocess.run(cmd, shell=True, timeout=...)` kills only the shell. With a pipeline or
  `cd x && pytest`, the grandchild survives. The agent writes such commands all the time, and the code under test
  sometimes contains an infinite loop. Grading ran tests the same way.
- **Fix**: `miniagent/proc.py` runs each command in its own process group and kills the group on timeout and after
  exit; used by the `bash` tool and by grading. Test `test_timeout_kills_whole_process_group`.
- **Lesson**: a timeout has to kill the process *tree*.
- **Note**: some CPU load seen at the same time was legitimate (the b15 hidden tests take 36 s of CPU even with
  the correct solution). Orphans are recognised by PPID 1 with no parent evaluator.

## 4. Agent cds into a path it guessed  (S)
- **Evidence**: 4 bash calls found by scanning `runs/` (`cd /workspace`, `cd /Users/<user>`), all from the first sessions.
- **Root cause**: the system prompt never said that commands already run in the workspace root.
- **Fix**: one sentence in the system prompt. Minor, but it wasted steps and is a typical prompt-vs-environment gap.

## 5. Editing test files hid the real failure class  (H)
- **Evidence**: `results/20261013-165840-gemini-flash-lite` (Gemini 3.5-flash-lite): 20 of 33 records had edited
  test files; 4 failed runs were classified `tampered_tests`, e.g. b13 r1, b15 r0.
- **What happened**: the model habitually rewrites the visible test file to add its own tests. Grading restores the
  pristine tests first, so this cannot change the outcome - but `tampered_tests` took priority in the failure
  classes and replaced the real reason (the code was simply wrong).
- **Fix**: "edited tests" is a flag (and a report row), not a failure class. Updated tests.
- **Lesson**: do not give a diagnostic flag priority over the cause in a mutually exclusive classification.

## 6. `.git/` metadata counted as an edit  (H)
- **Evidence**: same run, b08 r1 and b09 r0: `changed_files` listed 20+ `.git/...` files because the agent ran
  `git init`.
- **Effect**: a run that changed no source file would be classified `tests_failed_after_edit` instead of
  `no_edit`.
- **Fix**: `.git`, `__pycache__`, `.pytest_cache` are ignored when diffing. Test `test_git_directory_is_not_an_edit`.

## 7. Server-side failures counted as model failures  (H)
- **Evidence**: `results/20261012-173624-glm-flash` (GLM-4.7-Flash, free tier), interrupted after 17 runs and
  4.9 hours of wall time: 6 of 17 records were `api_error` (HTTP 429, "model currently overloaded"), 6 `max_tokens`,
  4 `tests_failed_after_edit`, 1 `no_edit`; 61 of 71 calls slower than 60 s produced fewer than 2,000 tokens, i.e.
  they were queueing/backoff, not generation.
- **Root cause**: pass rates treated an `api_error` as a failed attempt, so the provider's load looked like the
  model's weakness (0 passes even before excluding them).
- **Fix**: pass rates and comparisons use only *valid* runs; the report states how many were excluded; the harness
  reruns a run that ended in `api_error`; the client backs off patiently on 429 (and honours the server's
  suggested delay). Tests in `tests/test_client.py` and `tests/test_eval.py`.
- **Lesson**: separate "the system under test failed" from "the measurement infrastructure failed".

## 8. Batch kept running after unrecoverable errors  (H)
Three variants of the same defect, each wasting a batch:
- **Unavailable model** - `results/20261013-164637-gemini25-flash-lite`: HTTP 404 "no longer available to new
  users" (the model is still listed by `/models`); each run was retried twice before giving up.
- **Daily quota** - `results/20261013-165840-gemini-flash-lite`: "limit: 500 ... retry in 14h"; 10 runs each waited
  about 330 s and then failed.
- **Out of balance** - `results/20261014-162520-no-grep` and `results/20261014-193649-no-verify-prompt`:
  HTTP 402; 36 + 39 = 75 doomed runs were executed one by one. (This also left two of the five planned ablations
  unevaluated.)
- **Fix**: HTTP 400/401/402/403/404/422 stop the batch immediately; a 429 that asks for more than 10 minutes is
  treated as quota exhaustion; runs save progress and can be continued with `--resume`; `--max-requests` stops
  before a metered budget is spent.
- **Lesson**: classify errors as retryable or permanent, and stop a batch on the first permanent one.

## 9. Too small `max_tokens` made a thinking model look weak  (H)
- **Evidence**: `results/20261011-171434-flash` and `results/20261011-172740-pro`, both with `max_tokens=4096`:
  4 of 18 flash runs and 7 of 18 pro runs ended `max_tokens`; the last call produced exactly 4,096 tokens, empty
  text, no tool call (the thinking used the whole budget). b05 failed 3/3 for both.
- **Effect**: the first flash-vs-pro comparison showed "no difference" (61% vs 61%) purely because pro thinks longer
  and was truncated more.
- **Fix**: `max_tokens=16384`; the reruns gave 83% vs 89%, and b05 went to 3/3 for both. The report also gained a
  reasoning-token row.
- **Lesson**: when a failure class depends on a configuration limit, check it before reading the comparison.

## 10. Hidden tests that the spec does not imply  (T)
- **Evidence**: `results/20261012-224643-flash`: of the 5 failing runs, 4 were task defects:
  - **b03-patch-apply**: the docstring said the result "ends with a newline iff the original did", which literally
    requires `"\n"` for an empty result; the hidden test expected `""`. Two runs followed the docstring and failed.
  - **b22-linear-solver**: the hidden test required `ValueError` for `solve([[]], [1])`, but the docstring only
    asked for a non-empty list of equal-length rows; "no solution" is a defensible answer. Two runs failed on that
    single test.
  - The fifth failure (b12: a regex rejecting fractional seconds) was a genuine model miss.
  The first-pass 87% was really about 97%.
- **Fix**: both tasks retired in `tasks/SPLIT.json` (with the reason) and replaced by `b25-patch-apply-v2` and
  `b26-linear-solver-v2` with the spec stated explicitly; the harness skips retired tasks by default. Tasks that a
  model has already run are never edited in place (the content hash guards this).
- **Lesson**: every assertion in a hidden test must be derivable from the visible specification. Review hidden
  tests like code, and treat a failure that every run shares as evidence about the task first.

## 11. Benchmark saturated; headroom appeared only with a weaker model  (T)
- **Evidence**: all 15 first-round tasks passed with DeepSeek flash in 5-8 steps; 24 harder, spec-driven tasks with
  hidden tests still gave 87-97% (`results/20261013-194844-flash`: 90%). Other models on the same tasks:
  Gemini 3.5-flash-lite about 54% (`results/20261016-113644-g35-lite-relay`, 13 tasks x 1), Gemini 3.1-flash-lite
  26% (`results/20261015-193752-gemini-relay-native`, 13 x 3).
- **Lesson**: difficulty is relative to a model. Making tasks harder is expensive and unreliable (case 10 is a
  by-product); a **model ladder** over a fixed task set gives the headroom for free.

## 12. Relay translation layer broke Gemini 3 tool calls  (P)
- **Evidence**: `results/20261015-165454-gemini-relay-3.1-flash-lite` (HTTP 400 "Invalid function response") and
  `results/20261015-165911-gemini-relay-3.1-flash-lite` (HTTP 400 "Function call is missing a thought_signature").
- **Root cause** (confirmed by reading the relay's source, `gemini-balance-lite`): any path ending in
  `/chat/completions` is handed to the relay's own OpenAI-to-Gemini translator; every other path is forwarded to
  Google unchanged. The translator (a) passes a plain-text tool result into Gemini's `functionResponse`, which
  must be a JSON object, and (b) emits function calls without the thought signature Gemini 3 requires. A path such
  as `/v1beta/openai/chat/completions` also ends in `/chat/completions`, so the obvious workaround is intercepted
  too.
- **Fix**: a Gemini-native mode in the client (`api_style: "gemini"`): requests go to
  `/models/<m>:generateContent`, which the relay forwards untouched; tool results are merged into one user content;
  thought signatures are stored from each response and replayed. Tests cover request building, signature replay,
  usage and finish-reason mapping. First success: `results/20261015-173936-gemini-relay-native`; then 39 of 39
  valid runs in `results/20261015-193752-gemini-relay-native`.
- **Security note**: that relay logs the selected API key in full for every forwarded request; only use a
  deployment you control and a dedicated key. The client also no longer falls back to `DEEPSEEK_API_KEY` for a
  non-DeepSeek host, so a key cannot be sent to a third party by accident.
- **Lesson**: an "OpenAI-compatible" endpoint is a claim about the wire format, not about every feature; when a
  proxy translates, test the multi-turn tool-calling path first.

## 13. False completion: stops after a green visible test run  (M)
- **Evidence** (single model, small sample): Gemini 3.1-flash-lite, `results/20261015-193752-gemini-relay-native`:
  **21 of 29** failing runs ended with the agent's own last test run green, and 16 of 29 final messages claimed
  success. The same shape on DeepSeek flash, `results/20261013-194844-flash`: 3 of 4 failing runs.
- **Pattern**: the failing hidden tests were usually rules stated in the docstring or `docs/` but not covered by
  the visible tests (b12 timezone offsets in all 3 runs; b21 "`cancel` of a finished timer returns False" in all 3).
  The model verified against the tests it could see and stopped.
- **Interventions tried** (13 tasks x 1 each, so differences below about 35 points are not detectable):
  a prompt demanding a spec-derived verification pass (`gl31-spec-first`, 31% vs 23% for the same repeat of the
  baseline) barely changed behaviour - scratch-check calls per run 6.0 -> 7.5; enabling thinking
  (`gl31-think-high`, 31%) cut such checks to 0.3 per run and did not reduce false completions (6 of 9).
- **Status**: **open**. Hypothesis not yet tested: the cure is a mechanism, not wording - generate the checks from
  the specification in a separate step, independently of the model that writes the fix.
- **Related**: with DeepSeek flash, removing `bash` entirely (no test execution) did not lower the pass rate
  (see `docs/ablations.md`), consistent with running the visible tests being a weak signal on these tasks.

## 14. Runaway thinking uses the whole output budget  (M)
- **Evidence**: GLM-4.7-Flash, `results/20261012-173624-glm-flash`: 6 of 17 runs ended `max_tokens`, each with
  exactly 16,384 reasoning tokens and no visible output, about 11 minutes at roughly 25 tokens/s.
  Gemini 3.5-flash-lite on b15-cron-next: 2 of 3 runs ended `max_tokens`
  (`results/20261013-165840-gemini-flash-lite`).
- **Status**: observation of model behaviour; the harness classifies it correctly (`max_tokens`) and the
  reasoning-token column makes it visible. A lower token cap would fail faster but would also change what is being
  measured (case 9).

## 15. A test for a blocking hazard blocked the test run  (T)
- **Evidence**: while mutation-checking the MCP path-confinement tests (remove one defence at a time and expect a
  failure). Removing `O_NONBLOCK` from the file open made the FIFO test **hang the whole pytest process** instead of
  failing; the run had to be killed, and the mutated source file was left in place until it was restored by hand.
- **Root cause**: opening a FIFO for reading blocks until a writer appears. The test ran the open in a thread, so a
  regression turned into a hang rather than a red test. The mutation script also restored the file only after the
  test run finished, so it was not exception-safe.
- **Fix**: the FIFO test now runs in a subprocess with a timeout (a regression fails after about 15 s); the
  mutation script restores the file in a `finally` block and verifies it is byte-identical afterwards.
- **Lesson**: a test for "this can block forever" must be able to fail without blocking; and any script that
  edits source in place has to restore it in `finally`.

---

## Open items
1. Case 2: the trigger fix is verified on Gemini 3.5-flash-lite (see above). Whether summaries lose information is
   still unmeasured: the sample is too small to see a pass-rate effect. The DeepSeek configs were never run.
2. Case 13: test a spec-derived verification step with a model that has headroom (a mid-strength Gemini baseline
   is being measured; the quota allows only a few conditions).
3. `no-grep` and `no-verify-prompt` ablations were never evaluated (out of balance) and are reported as such.
