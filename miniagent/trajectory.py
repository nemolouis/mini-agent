"""Append-only JSONL trajectory log. One line per event.

This is the shared data format for M2 (eval harness reads run_end), M3
(replay UI reads everything) and later L1 (SFT data is built from it).

Events (all carry `ts` and `event`):
  run_start    task, model, config
  model_call   step, latency_s, finish_reason, text, tool_calls[{id,name,input}],
               usage{input_tokens,output_tokens,cache_hit_tokens}
  tool_result  step, tool_call_id, name, input, output, is_error, approved, duration_s
  compaction   kind ("elide"|"summary"), est_tokens_before, est_tokens_after, summary?
  run_end      status, steps, usage totals, final_text

The message list is append-only apart from `compaction`, so a reader can
rebuild the exact model input at any step by replaying events in order.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


class Trajectory:
    def __init__(self, run_dir: str | Path | None):
        self.path: Path | None = None
        if run_dir is not None:
            d = Path(run_dir)
            d.mkdir(parents=True, exist_ok=True)
            self.path = d / "trajectory.jsonl"

    def log(self, event: str, **data) -> None:
        if self.path is None:
            return
        rec = {"ts": round(time.time(), 3), "event": event, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
