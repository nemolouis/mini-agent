"""Run one (task, config, repeat) and produce a result record."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from contextlib import nullcontext
from pathlib import Path

from ..agent import SYSTEM_PROMPT, Agent
from ..mcp.client import mcp_session
from ..sandbox import Sandbox, SandboxError
from ..tools import Workspace
from ..trajectory import Trajectory
from .grade import add_hidden, classify, copy_repo, restore_tests, run_tests, trajectory_stats
from .tasks import Task


def config_hash(cfg: dict) -> str:
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:10]


def run_one(task: Task, cfg: dict, repeat: int, out_dir: Path, client, keep_workspace: bool = False,
            attempt: int = 0) -> dict:
    """One run. A sandbox fault (Docker or the network down, the container gone) anywhere in it - starting, agent commands
    or grading - is returned as an `api_error` record: infrastructure, not the model's failure, and retried or resumed."""
    run_id = f"{task.id}__r{repeat}" + (f"__try{attempt + 1}" if attempt else "")
    traj_dir = out_dir / "trajectories" / run_id
    if traj_dir.exists():
        # a leftover from an attempt that left no record (it crashed): appending to it would mix two runs in one trajectory
        shutil.rmtree(traj_dir)
    try:
        return _run_one(task, cfg, repeat, out_dir, client, keep_workspace, attempt, run_id, traj_dir)
    except SandboxError as e:
        path = traj_dir / "trajectory.jsonl"
        events = [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
        return {"task_id": task.id, "split": task.split, "repeat": repeat, "attempt": attempt, "passed": False,
                "agent_status": "error", "error": repr(e), "failure_class": "api_error", "tampered_tests": False,
                "changed_files": [], "wall_s": 0.0, "trajectory": str(path), "final_text": "", "test_output_tail": "",
                **trajectory_stats(events)}


def _run_one(task: Task, cfg: dict, repeat: int, out_dir: Path, client, keep_workspace: bool, attempt: int,
             run_id: str, traj_dir: Path) -> dict:
    system = SYSTEM_PROMPT
    if cfg.get("system_prompt_file"):
        system = Path(cfg["system_prompt_file"]).read_text()

    with tempfile.TemporaryDirectory(prefix=f"mini-{task.id}-") as tmp:
        work = Path(tmp) / "repo"
        copy_repo(task.repo, work)
        use_sandbox = bool(cfg.get("sandbox", False))
        with mcp_session(cfg.get("mcp_servers", [])) as mcp_tools, (Sandbox(work) if use_sandbox else nullcontext()) as sb:
            agent = Agent(
                client=client, model=cfg["model"], workspace=Workspace(work, sandbox=sb, edit_hints=bool(cfg.get("edit_hints", False))),
                trajectory=Trajectory(traj_dir), max_steps=cfg.get("max_steps", 30),
                max_tokens=cfg.get("max_tokens", 4096), context_limit=cfg.get("context_limit", 100_000),
                keep_recent=cfg.get("keep_recent", 8), compact_regrowth=cfg.get("compact_regrowth", 1.0), system=system,
                temperature=cfg.get("temperature"), disabled_tools=tuple(cfg.get("disabled_tools", ())),
                extra_tools=mcp_tools, log_reasoning=bool(cfg.get("log_reasoning", False)),
                meta={"task_id": task.id, "split": task.split, "task_hash": task.hash, "repeat": repeat,
                      "config_name": cfg.get("name"), "config_hash": config_hash(cfg)},
            )
            t0 = time.time()
            res = agent.run(task.prompt)
        wall = round(time.time() - t0, 2)

        g = restore_tests(task.repo, work)
        add_hidden(task.hidden, work)
        passed, test_output = run_tests(work, task.test_cmd, sandbox=use_sandbox)
        if keep_workspace:
            shutil.copytree(work, out_dir / "workspaces" / run_id, dirs_exist_ok=True)

    events = [json.loads(l) for l in (traj_dir / "trajectory.jsonl").read_text().splitlines()]
    rec = {
        "task_id": task.id, "split": task.split, "repeat": repeat, "attempt": attempt,
        "passed": passed, "agent_status": res.status, "error": res.error,
        "failure_class": classify(events, passed, g["tampered"], g["changed_files"]),
        "tampered_tests": g["tampered"], "changed_files": g["changed_files"],
        "wall_s": wall, "trajectory": str(traj_dir / "trajectory.jsonl"),
        "final_text": res.final_text[:2000],
        "test_output_tail": "" if passed else test_output[-1500:],
        **trajectory_stats(events),
    }
    return rec
