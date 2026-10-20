"""Turn seed libraries into bug-fixing tasks by mutation. Every filter exists to exclude one kind of bad task; see
docs/m5_sandbox_taskgen_design.md, section 2. All runs happen in the Docker sandbox; no model is involved."""
from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import tempfile
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..sandbox import Sandbox
from .mutate import FAMILIES, Mutant, apply, candidates
from .testsplit import close_over_calls, find_tests, keep_only, node_key

PROMPT = ("The tests in this repository are failing. There is a bug in the library code (the tests themselves are "
          "correct). Find the bug and fix it so that the whole test suite passes. Do not modify the tests.")
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git")


@dataclass
class GenConfig:
    per_seed: int = 20              # tasks wanted from each seed
    per_signature: int = 1          # at most this many tasks that fail exactly the same set of tests
    min_tests: int = 8              # seeds with fewer tests give no room for a visible/hidden split
    max_fail_abs: int = 8           # a mutant failing more tests than this (or max_fail_frac of all) is a wreck, not a bug
    max_fail_frac: float = 0.4
    visible_frac: float = 0.6       # share of the test functions the agent gets to see
    candidate_factor: int = 12      # examine at most per_seed * this many mutants
    timeout: int = 60               # per test-suite run
    workers: int = 4
    rng: int = 0


@dataclass
class Seed:
    name: str
    root: Path                      # the project tree (sources and tests together)
    mutate: list[str]               # files that may be mutated, relative to root
    tests: list[str]                # test files, relative to root
    test_cmd: str = "python -m pytest -q"
    split: str | None = None        # train | dev | test; derived from the name when absent


def load_seed(d: str | Path) -> Seed:
    d = Path(d)
    meta = json.loads((d / "seed.json").read_text())
    return Seed(meta.get("name", d.name), d / "repo", meta["mutate"], meta["tests"],
                meta.get("test_cmd", "python -m pytest -q"), meta.get("split"))


def seed_split(seed: Seed) -> str:
    if seed.split:
        return seed.split
    r = int(hashlib.sha256(seed.name.encode()).hexdigest()[:8], 16) % 100
    return "train" if r < 70 else "dev" if r < 85 else "test"


# ------------------------------------------------------------------ running the suite
@dataclass
class SuiteRun:
    rc: int | None
    failed: frozenset
    counts: dict
    timed_out: bool
    tail: str = ""

    @property
    def total(self) -> int:
        return sum(self.counts.get(k, 0) for k in ("passed", "failed", "error"))


_COUNT = re.compile(r"(\d+) (failed|passed|errors?)\b")


def parse_suite(rc, stdout: str, timed_out: bool) -> SuiteRun:
    failed = frozenset(m.group(1) for m in re.finditer(r"^(?:FAILED|ERROR) (\S+)", stdout, re.M))
    counts: Counter = Counter()
    last = [l for l in stdout.splitlines() if _COUNT.search(l)]
    if last:
        for n, k in _COUNT.findall(last[-1]):
            counts["error" if k.startswith("error") else k] += int(n)
    return SuiteRun(rc, failed, dict(counts), timed_out, stdout[-600:])


class Runner:
    """One sandbox over a private copy of the seed tree; used by one thread."""

    def __init__(self, seed: Seed, cfg: GenConfig, tree: Path | None = None):
        self._tmp = tempfile.TemporaryDirectory(prefix=f"gen-{seed.name}-")
        self.dir = Path(self._tmp.name) / "repo"
        shutil.copytree(tree or seed.root, self.dir, ignore=IGNORE)
        self.seed, self.cfg = seed, cfg
        self.sb = Sandbox(self.dir).start()

    def run(self) -> SuiteRun:
        r = self.sb.exec(f"{self.seed.test_cmd} --tb=no -rfE -p no:cacheprovider", timeout=self.cfg.timeout)
        return parse_suite(r.returncode, r.stdout + r.stderr, r.timed_out)

    def run_with(self, rel: str, new_text: str) -> SuiteRun:
        p = self.dir / rel
        old = p.read_text()
        p.write_text(new_text)
        try:
            return self.run()
        finally:
            p.write_text(old)

    def close(self):
        self.sb.close()
        self._tmp.cleanup()


# ------------------------------------------------------------------ search
def _interleave(per_family: dict[str, list]) -> list:
    out, lists = [], [per_family[f] for f in FAMILIES if per_family.get(f)]
    while any(lists):
        for l in lists:
            if l:
                out.append(l.pop())
    return out


def _judge(runner: Runner, rel: str, original: str, mutant: Mutant, cfg: GenConfig, keys: set) -> tuple[str, dict | None]:
    new = apply(original, mutant)
    if new is None:
        return "no_compile", None
    a = runner.run_with(rel, new)
    if a.timed_out:
        return "timeout", None
    if a.rc == 0:
        return "undetected_by_tests", None
    if a.rc != 1 or a.counts.get("error"):
        return "broken_collection_or_error", None
    limit = min(cfg.max_fail_abs, max(1, int(cfg.max_fail_frac * a.total)))
    if len(a.failed) > limit:
        return "too_many_failures", None
    fk = {node_key(i) for i in a.failed}
    if None in fk or not fk <= keys:
        return "unmappable_test_id", None
    b = runner.run_with(rel, new)
    if b.rc != 1 or b.failed != a.failed:
        return "flaky", None
    return "ok", {"file": rel, "mutant": mutant, "text": new, "failed": a.failed, "fail_keys": frozenset(fk), "total": a.total}


def _build_task(seed: Seed, cand: dict, task_dir: Path, cfg: GenConfig, rng: random.Random, tests_src: dict, all_keys: list):
    fk = sorted(cand["fail_keys"], key=str)
    picked = {k for k in all_keys if rng.random() < cfg.visible_frac} | {rng.choice(fk)}
    visible = set()
    for rel, src in tests_src.items():
        visible |= {(rel, c, f) for (c, f) in close_over_calls(src, {(c, f) for (r, c, f) in picked if r == rel})}
    shutil.copytree(seed.root, task_dir / "repo", ignore=IGNORE)
    (task_dir / "repo" / cand["file"]).write_text(cand["text"])
    hidden_files = 0
    for rel, src in tests_src.items():
        keep = {(c, f) for (r, c, f) in visible if r == rel}
        vis = keep_only(src, keep)
        if vis != src:
            (task_dir / "repo" / rel).write_text(vis)
            (task_dir / "hidden" / rel).parent.mkdir(parents=True, exist_ok=True)
            (task_dir / "hidden" / rel).write_text(src)
            hidden_files += 1
    (task_dir / "solution" / cand["file"]).parent.mkdir(parents=True, exist_ok=True)
    (task_dir / "solution" / cand["file"]).write_text((seed.root / cand["file"]).read_text())
    m: Mutant = cand["mutant"]
    meta = {"prompt": PROMPT, "test_cmd": seed.test_cmd, "layer": "G",
            "gen": {"seed": seed.name, "family": m.family, "file": cand["file"], "line": m.line, "description": m.description,
                    "failing_tests": sorted(cand["failed"]), "failing_total": len(cand["failed"]), "tests_total": cand["total"], "visible_tests": len(visible),
                    "hidden_only_tests": len(all_keys) - len(visible), "split_files": hidden_files}}
    (task_dir / "task.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return visible


def generate_seed(seed: Seed, out_root: Path, cfg: GenConfig) -> dict:
    rep: dict = {"seed": seed.name, "split": seed_split(seed), "rejected": Counter(), "tasks": []}
    base = Runner(seed, cfg)
    try:
        runs = [base.run(), base.run()]
        if any(r.rc != 0 for r in runs) or runs[0].failed != runs[1].failed:
            rep["skipped"] = f"the seed's own tests do not pass reliably (rc {[r.rc for r in runs]}): {runs[0].tail[-200:]}"
            return rep
        if runs[0].total < cfg.min_tests:
            rep["skipped"] = f"only {runs[0].total} tests (need {cfg.min_tests})"
            return rep
        tests_src = {rel: (seed.root / rel).read_text() for rel in seed.tests}
        all_keys = [(rel, c, f) for rel, s in tests_src.items() for (c, f) in find_tests(s)]
        keys = set(all_keys)
        rng = random.Random(f"{cfg.rng}:{seed.name}")
        per_family: dict[str, list] = {f: [] for f in FAMILIES}
        sources = {rel: (seed.root / rel).read_text() for rel in seed.mutate}
        for rel, src in sources.items():
            for m in candidates(src):
                per_family[m.family].append((rel, m))
        for l in per_family.values():
            rng.shuffle(l)
        cands = _interleave(per_family)[: cfg.per_seed * cfg.candidate_factor]
        rep["candidates"] = len(cands)

        runners = [base] + [Runner(seed, cfg) for _ in range(cfg.workers - 1)]
        free: list[Runner] = list(runners)
        lock = threading.Lock()

        def work(item):
            with lock:
                r = free.pop()
            try:
                rel, m = item
                return _judge(r, rel, sources[rel], m, cfg, keys)
            finally:
                with lock:
                    free.append(r)

        accepted: list[dict] = []
        sigs: Counter = Counter()
        step = cfg.workers * 4
        with ThreadPoolExecutor(cfg.workers) as pool:
            for i in range(0, len(cands), step):
                if len(accepted) >= cfg.per_seed:
                    break
                for verdict, cand in pool.map(work, cands[i:i + step]):      # map keeps the input order: deterministic
                    if len(accepted) >= cfg.per_seed:
                        rep["rejected"]["not_needed"] += 1
                    elif verdict != "ok":
                        rep["rejected"][verdict] += 1
                    elif sigs[cand["fail_keys"]] >= cfg.per_signature:
                        rep["rejected"]["same_failure_as_another_task"] += 1
                    else:
                        sigs[cand["fail_keys"]] += 1
                        accepted.append(cand)
        for r in runners[1:]:
            r.close()

        for n, cand in enumerate(accepted):
            tid = f"g-{seed.name}-{n:03d}-{cand['mutant'].family}"
            d = out_root / tid
            visible = _build_task(seed, cand, d, cfg, random.Random(f"{cfg.rng}:{seed.name}:{n}"), tests_src, all_keys)
            ok, why = _check_built(seed, d, cfg)
            if not ok:
                shutil.rmtree(d)
                rep["rejected"][f"built_task_check:{why}"] += 1
                continue
            rep["tasks"].append({"id": tid, **json.loads((d / "task.json").read_text())["gen"]})
    finally:
        base.close()
    rep["rejected"] = dict(rep["rejected"])
    return rep


def _check_built(seed: Seed, task_dir: Path, cfg: GenConfig) -> tuple[bool, str]:
    """What the agent will see: the visible tests must fail on the buggy code and pass on the original."""
    r = Runner(seed, cfg, tree=task_dir / "repo")
    try:
        buggy = r.run()
        if buggy.rc != 1 or not buggy.failed:
            return False, "visible tests do not fail on the bug"
        for sol in (task_dir / "solution").rglob("*.py"):
            rel = sol.relative_to(task_dir / "solution")
            (r.dir / rel).write_text(sol.read_text())
        fixed = r.run()
        if fixed.rc != 0:
            return False, "visible tests fail on the original code"
        return True, ""
    finally:
        r.close()


def write_split(out_root: Path, seeds: dict[str, Seed]) -> dict:
    """Freeze split labels for new tasks (per seed, never per task). Existing entries are left alone."""
    from ..eval.tasks import load_tasks
    path = out_root / "SPLIT.json"
    data = json.loads(path.read_text()) if path.exists() else {"version": 1, "tasks": {}}
    for t in load_tasks(out_root):
        if t.id not in data["tasks"]:
            seed = seeds[json.loads((t.dir / "task.json").read_text())["gen"]["seed"]]
            data["tasks"][t.id] = {"split": seed_split(seed), "hash": t.hash}
    path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def generate(seed_dirs: list[Path], out_root: str | Path, cfg: GenConfig, force: bool = False) -> dict:
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    seeds = {s.name: s for s in map(load_seed, seed_dirs)}
    prev = out_root / "GEN_REPORT.json"          # keep the entries of seeds not regenerated in this call
    old = {x["seed"]: x for x in json.loads(prev.read_text())["seeds"]} if prev.exists() else {}
    report = {"config": cfg.__dict__, "seeds": []}
    for seed in seeds.values():
        existing = list(out_root.glob(f"g-{seed.name}-*"))
        if existing and not force:
            report["seeds"].append({"seed": seed.name, "skipped": f"{len(existing)} tasks already exist (use --force)"})
            continue
        if existing:                                   # regenerating: forget the frozen split of the tasks being replaced
            sp = out_root / "SPLIT.json"
            if sp.exists():
                data = json.loads(sp.read_text())
                for d in existing:
                    data["tasks"].pop(d.name, None)
                sp.write_text(json.dumps(data, indent=2, sort_keys=True))
        for d in existing:
            shutil.rmtree(d)
        report["seeds"].append(generate_seed(seed, out_root, cfg))
    write_split(out_root, seeds)
    done = {x["seed"] for x in report["seeds"] if "skipped" not in x or "already exist" not in x["skipped"]}
    report["seeds"] = [x for x in report["seeds"] if x["seed"] in done] + [v for k, v in old.items() if k not in done]
    (out_root / "GEN_REPORT.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=list))
    return report
