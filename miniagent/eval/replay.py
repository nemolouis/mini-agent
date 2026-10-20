"""Replay a recorded trajectory through the current agent loop and compare the two runs step by step.

The model answers come from the recording (`TrajectoryReplayClient`); the tools run for real in a fresh copy of the
task repository. Two kinds of difference are reported separately:

* structural: different tool calls, different compaction points, different step count or end status. These mean the
  loop (or its tools) now behaves differently from the version that produced the recording.
* output: a tool printed something other than it did originally. Often harmless (pytest timings, temp paths), so it is
  counted, not treated as a failure.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ..agent import SYSTEM_PROMPT, Agent
from ..replay import ReplayMiss, TrajectoryReplayClient
from ..tools import Workspace, build_tools
from ..trajectory import Trajectory
from .grade import copy_repo
from .tasks import load_tasks


def _load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def signature(events: list[dict]) -> list[tuple]:
    """The part of a trajectory that must be identical on replay (no timestamps, latencies or tool outputs)."""
    sig: list[tuple] = []
    for e in events:
        kind = e["event"]
        if kind == "model_call":
            calls = tuple((c["name"], json.dumps(c["input"], sort_keys=True, ensure_ascii=False)) for c in e["tool_calls"])
            sig.append(("model_call", e["step"], e["text"], calls, e["finish_reason"]))
        elif kind == "tool_result":
            sig.append(("tool_result", e["step"], e["name"], json.dumps(e["input"], sort_keys=True, ensure_ascii=False), e["is_error"]))
        elif kind == "compaction":
            sig.append(("compaction", e["kind"]))
        elif kind == "compaction_floor":
            sig.append(("compaction_floor", e["step"]))
        elif kind == "run_end":
            sig.append(("run_end", e["status"], e["steps"]))
    return sig


def replay_run(traj_path: str | Path, tasks_root: str | Path = "tasks") -> dict:
    """Result keys: status ('ok' | 'diff' | 'skipped' | 'error'), reason/diffs, output_mismatches."""
    traj_path = Path(traj_path)
    old = _load(traj_path)
    start = old[0]
    if start.get("event") != "run_start":
        return {"status": "skipped", "reason": "no run_start event"}
    if not any(e["event"] == "run_end" for e in old):
        return {"status": "skipped", "reason": "the recording has no run_end (the run was interrupted), so there is no end to compare"}
    cfg, meta = start["config"], start.get("meta") or {}
    builtin = set(build_tools(Workspace(".")))
    unknown = set(cfg["tools"]) - builtin
    if unknown:
        return {"status": "skipped", "reason": f"uses tools that are not built in ({sorted(unknown)}): MCP runs cannot be replayed"}
    tasks = {t.id: t for t in load_tasks(tasks_root)}
    task = tasks.get(meta.get("task_id"))
    if task is None:
        return {"status": "skipped", "reason": f"task {meta.get('task_id')!r} not found in {tasks_root}"}
    if meta.get("task_hash") and meta["task_hash"] != task.hash:
        return {"status": "skipped", "reason": f"task {task.id} has changed since the recording"}

    calls = [c for e in old if e["event"] == "model_call" for c in e["tool_calls"]]
    if calls and not any("extra" in c for c in calls) and any(
            str(e.get("response_model", "")).lower().startswith("gemini") for e in old if e["event"] == "model_call"):
        return {"status": "skipped", "reason": "Gemini run recorded before tool-call extras (thought signatures) were logged: "
                                               "the history size, and with it the compaction decisions, cannot be reproduced"}
    client = TrajectoryReplayClient(old)
    # Same prefix as the runner: the workspace path appears in pytest output, and the compaction decision depends on a
    # character-count estimate of the history, so a shorter path can flip a decision and make the replay diverge.
    with tempfile.TemporaryDirectory(prefix=f"mini-{task.id}-") as tmp:
        work = Path(tmp) / "repo"
        copy_repo(task.repo, work)
        new_dir = Path(tmp) / "traj"
        agent = Agent(
            client=client, model=start["model"], workspace=Workspace(work), trajectory=Trajectory(new_dir),
            max_steps=cfg["max_steps"], max_tokens=cfg["max_tokens"], context_limit=cfg["context_limit"],
            keep_recent=cfg["keep_recent"], compact_regrowth=cfg.get("compact_regrowth", 1.0),
            temperature=cfg.get("temperature"), disabled_tools=tuple(sorted(builtin - set(cfg["tools"]))),
            system=start.get("system") or SYSTEM_PROMPT)
        try:
            agent.run(start["task"])
        except ReplayMiss as e:                    # not expected: the loop catches exceptions; kept for safety
            return {"status": "diff", "diffs": [f"replay stopped: {e}"], "output_mismatches": 0}
        new = _load(new_dir / "trajectory.jsonl")

    a, b = signature(old), signature(new)
    diffs: list[str] = []
    for i in range(max(len(a), len(b))):
        x, y = (a[i] if i < len(a) else None), (b[i] if i < len(b) else None)
        if x != y:
            diffs.append(f"event {i}: recorded {str(x)[:160]} / now {str(y)[:160]}")
            if len(diffs) >= 5:
                break
    old_end = next((e for e in reversed(old) if e["event"] == "run_end"), {})
    end = next((e for e in reversed(new) if e["event"] == "run_end"), {})
    if end.get("status") == "error" and old_end.get("status") != "error":
        diffs.append(f"replay ended in an error: {end.get('error', '')[:200]}")
    outs_old = [e["output"] for e in old if e["event"] == "tool_result"]
    outs_new = [e["output"] for e in new if e["event"] == "tool_result"]
    mism = sum(1 for p, q in zip(outs_old, outs_new) if p != q) + abs(len(outs_old) - len(outs_new))
    return {"status": "diff" if diffs else "ok", "diffs": diffs, "output_mismatches": mism,
            "events_recorded": len(old), "events_now": len(new)}


def collect(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in map(Path, paths):
        if p.is_file():
            out.append(p)
        else:
            out.extend(sorted(p.rglob("trajectory.jsonl")))
    return out
