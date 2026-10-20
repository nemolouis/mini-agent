"""Turn finished runs into chat-format training examples (the data side of SFT).

Which runs are kept, and why each rule exists:
* the hidden tests passed and the agent ended by itself (`done`): a run that edited correctly but ran out of steps or
  errored has no closing answer, and teaching "stop on a tool call" is wrong;
* the agent did not touch the tests (`tampered_tests`);
* no compaction happened: compaction rewrites the history, so the transcript rebuilt from the event log is not what
  the model actually saw at the later steps. (Splitting such runs into several examples is future work.)
* no tool call with unparseable JSON arguments (training on malformed calls teaches them);
* the task is in the `train` split, unless other splits are asked for: dev and test tasks (and tasks without a split, like the
  hand-written ones) are for evaluation, training on them voids the result.
Exact duplicates are dropped. Every skipped run is counted by reason.

Output, one JSON object per line: {id, task_id, model, split, messages, tools, meta}. `messages` starts with the
system prompt; assistant tool calls use the OpenAI shape (`arguments` is a JSON string); `tools` are the specs the
model was given.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from ..agent import SYSTEM_PROMPT
from ..tools import Workspace, build_tools
from .report import load_records


def _sha(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def _known_systems() -> dict[str, str]:
    known = {_sha(SYSTEM_PROMPT): SYSTEM_PROMPT}
    for f in Path("prompts").glob("*.txt"):
        text = f.read_text()
        known[_sha(text)] = text
    return known


def build_messages(events: list[dict], *, with_reasoning: bool = False) -> list[dict]:
    """Rebuild the conversation (without the system prompt) from the event log of an uncompacted run."""
    msgs = [{"role": "user", "content": events[0]["task"]}]
    for e in events:
        if e["event"] == "model_call":
            m: dict = {"role": "assistant", "content": e["text"] or None}
            if e["tool_calls"]:
                m["tool_calls"] = [{"id": c["id"], "type": "function",
                                    "function": {"name": c["name"], "arguments": json.dumps(c["input"], ensure_ascii=False)}}
                                   for c in e["tool_calls"]]
            if with_reasoning and e.get("reasoning"):
                m["reasoning_content"] = e["reasoning"]
            msgs.append(m)
        elif e["event"] == "tool_result":
            msgs.append({"role": "tool", "tool_call_id": e["tool_call_id"], "content": e["output"]})
    return msgs


def _well_formed(msgs: list[dict]) -> bool:
    """Every assistant tool call is answered by exactly one tool message, in order, and the run ends on plain text."""
    pending: list[str] = []
    for m in msgs[1:]:
        if m["role"] == "assistant":
            if pending:
                return False
            pending = [c["id"] for c in m.get("tool_calls", [])]
        elif m["role"] == "tool":
            if m["tool_call_id"] not in pending:
                return False
            pending.remove(m["tool_call_id"])
    last = msgs[-1]
    return not pending and last["role"] == "assistant" and not last.get("tool_calls")


def export_sft(result_dirs: list[str | Path], out_path: str | Path, *, models: set[str] | None = None,
               with_reasoning: bool = False, splits: set[str] | None = None) -> dict:
    """`splits`: which task splits may be exported (default: only "train"); a task without a split is never exported
    unless "none" is listed."""
    splits = splits or {"train"}
    systems = _known_systems()
    builtin = build_tools(Workspace("."))
    seen: set[str] = set()
    skipped: Counter = Counter()
    kept: Counter = Counter()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as sink:
        for d in map(Path, result_dirs):
            for rec in load_records(d):
                if not rec.get("passed"):
                    skipped["not_passed"] += 1; continue
                if rec.get("agent_status") != "done":
                    skipped["did_not_finish_by_itself"] += 1; continue
                if rec.get("tampered_tests"):
                    skipped["touched_tests"] += 1; continue
                if (rec.get("split") or "none") not in splits:
                    skipped[f"split_{rec.get('split') or 'none'}_not_exported"] += 1; continue
                path = Path(rec["trajectory"])
                if not path.exists():
                    skipped["trajectory_missing"] += 1; continue
                events = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
                start = events[0]
                if models and start["model"] not in models:
                    skipped["other_model"] += 1; continue
                if any(e["event"] == "compaction" for e in events):
                    skipped["compacted"] += 1; continue
                if any("_raw_arguments" in c["input"] for e in events if e["event"] == "model_call" for c in e["tool_calls"]):
                    skipped["invalid_tool_arguments"] += 1; continue
                system = start.get("system") or systems.get(start["config"]["system_sha1"])
                if system is None:
                    skipped["unknown_system_prompt"] += 1; continue
                tools = start.get("tool_specs") or [builtin[n].spec() for n in start["config"]["tools"] if n in builtin]
                msgs = build_messages(events, with_reasoning=with_reasoning)
                if not _well_formed(msgs):
                    skipped["malformed_transcript"] += 1; continue
                full = [{"role": "system", "content": system}] + msgs
                digest = hashlib.sha256(json.dumps(full, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                if digest in seen:
                    skipped["duplicate"] += 1; continue
                seen.add(digest)
                ex = {"id": f"{d.name}/{path.parent.name}", "task_id": rec["task_id"], "model": start["model"],
                      "split": rec.get("split"), "messages": full, "tools": tools,
                      "meta": {"steps": rec["steps"], "system_logged": "system" in start, "tools_logged": "tool_specs" in start,
                               "has_reasoning": any(m.get("reasoning_content") for m in msgs)}}
                sink.write(json.dumps(ex, ensure_ascii=False) + "\n")
                kept[start["model"]] += 1
    stats = {"kept": sum(kept.values()), "kept_by_model": dict(kept), "skipped": dict(skipped)}
    out_path.with_suffix(".stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    return stats
