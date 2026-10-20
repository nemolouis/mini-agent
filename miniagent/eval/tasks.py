"""Task loading and the frozen dev/test split.

tasks/<id>/task.json   {"prompt": ..., "test_cmd": ...}
tasks/<id>/repo/       what the agent sees (copied to a temp dir per run)
tasks/<id>/solution/   reference fix files, used only by `verify`
tasks/SPLIT.json       {"tasks": {id: {"split": "dev"|"test", "hash": ...}}}

The hash covers task.json and repo/. If a task changes after it was split, every
command refuses to run: silently editing a task would invalidate comparisons.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

TEST_FRACTION = 0.4


@dataclass
class Task:
    id: str
    prompt: str
    test_cmd: str
    dir: Path
    hash: str
    split: str | None = None

    @property
    def repo(self) -> Path:
        return self.dir / "repo"

    @property
    def solution(self) -> Path:
        return self.dir / "solution"

    @property
    def hidden(self) -> Path:
        """Extra test files copied in only at grading time; the agent never sees them."""
        return self.dir / "hidden"


def task_hash(d: Path) -> str:
    h = hashlib.sha256()
    files = [d / "task.json"] + sorted(
        p for sub in ("repo", "hidden") if (d / sub).exists()
        for p in (d / sub).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for p in files:
        h.update(str(p.relative_to(d)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _id_digest(task_id: str) -> int:
    return int(hashlib.sha256(task_id.encode()).hexdigest()[:8], 16)


def load_tasks(root: str | Path) -> list[Task]:
    root = Path(root)
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir() and (p / "task.json").exists()):
        meta = json.loads((d / "task.json").read_text())
        out.append(Task(d.name, meta["prompt"], meta.get("test_cmd", "pytest -q"), d, task_hash(d)))
    return out


def freeze_split(tasks: list[Task], split_path: str | Path) -> dict:
    """Assign dev/test to tasks not yet in SPLIT.json. Existing entries are never changed."""
    split_path = Path(split_path)
    data = json.loads(split_path.read_text()) if split_path.exists() else {"version": 1, "tasks": {}}
    new = [t for t in tasks if t.id not in data["tasks"]]
    if new and not data["tasks"]:
        # first freeze: rank by hash so the fraction is exact for a small set
        ranked = sorted(new, key=lambda t: _id_digest(t.id))
        n_test = math.ceil(len(ranked) * TEST_FRACTION)
        assign = {t.id: ("test" if i < n_test else "dev") for i, t in enumerate(ranked)}
    else:
        assign = {t.id: ("test" if _id_digest(t.id) % 100 < TEST_FRACTION * 100 else "dev") for t in new}
    for t in new:
        data["tasks"][t.id] = {"split": assign[t.id], "hash": t.hash}
    split_path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def apply_split(tasks: list[Task], split_path: str | Path) -> list[Task]:
    """Attach split labels; raise if a task is unsplit or changed since it was split."""
    data = json.loads(Path(split_path).read_text())["tasks"]
    for t in tasks:
        e = data.get(t.id)
        if e is None:
            raise SystemExit(f"task {t.id} is not in SPLIT.json; run `miniagent-eval split`")
        if e["hash"] != t.hash:
            raise SystemExit(f"task {t.id} changed since the split was frozen "
                             f"({e['hash']} -> {t.hash}); create a new task id instead of editing")
        t.split = e["split"]
    return tasks
