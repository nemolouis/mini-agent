# data

Training data exported from teacher trajectories (`miniagent-eval export`). The `.jsonl` files are **not committed**: they
are outputs of a third-party model (DeepSeek) and contain third-party library code. The `.stats.json` files are.

- `sft_train_v2.jsonl`: 510 chat-format examples (system, user, assistant tool calls, tool results), one per passing run of
  the `train`-split tasks; `sft_train_v2_reasoning.jsonl` is the same with the model's thinking text as `reasoning_content`.
- `sft_train_v3.jsonl`: the same 510 examples with the teacher's `old_string` of every `edit_file` call shortened to the
  shortest unique snippet (`python scripts/shrink_edits.py data/sft_train_v2.jsonl data/sft_train_v3.jsonl`; each rewrite is
  checked by replaying it on the task's starting files). It was used for one retraining that produced no tool calls (see
  `docs/next_phase_plan.md`), so treat it as an experiment, not as the main dataset.
- The tool calls in these files are stored as chat messages; how they are rendered into training text depends on the chat
  template: the model's own (`<tool_call>` special tokens, untrained in this model) or `prompts/chat_template_plain.jinja`
  (plain-text `[TOOL_CALL]`), chosen with `scripts/sft_mlx.py --chat-template`.
  (`sft_train_v1*` was an earlier export from a run that was still incomplete; it is not used and not committed.)
- Rebuild: run `configs/gen-synth-flash.json` (see the main README), then
  `miniagent-eval export results/<run-dir> --out data/sft_train_v2.jsonl --models deepseek-flash`.
  Only the `train` split is exported by default; exporting `dev` or `test` tasks would void their use for evaluation.
