# data

Training data exported from teacher trajectories (`miniagent-eval export`). The `.jsonl` files are **not committed**: they
are outputs of a third-party model (DeepSeek) and contain third-party library code. The `.stats.json` files are.

- `sft_train_v2.jsonl`: 510 chat-format examples (system, user, assistant tool calls, tool results), one per passing run of
  the `train`-split tasks; `sft_train_v2_reasoning.jsonl` is the same with the model's thinking text as `reasoning_content`.
  (`sft_train_v1*` was an earlier export from a run that was still incomplete; it is not used and not committed.)
- Rebuild: run `configs/gen-synth-flash.json` (see the main README), then
  `miniagent-eval export results/<run-dir> --out data/sft_train_v2.jsonl --models deepseek-flash`.
  Only the `train` split is exported by default; exporting `dev` or `test` tasks would void their use for evaluation.
