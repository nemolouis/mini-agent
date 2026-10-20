"""miniagent-eval: split | verify | run | report | view | replay | export | compare | gen | sandbox-build | sandbox-clean"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .grade import add_hidden, copy_repo, run_tests
from .report import (compare, load_records, markdown_compare, markdown_report, summarize)
from .runner import config_hash, run_one
from .tasks import apply_split, freeze_split, load_tasks


def _load_price(path: str, model: str):
    p = Path(path)
    return json.loads(p.read_text()).get(model) if p.exists() else None


def cmd_gen(a):
    from ..sandbox import available
    from ..taskgen.generate import GenConfig, generate
    if not available():
        raise SystemExit("error: the sandbox image is missing or Docker is not running (miniagent-eval sandbox-build)")
    root = Path(a.seeds)
    dirs = sorted(d for d in root.iterdir() if (d / "seed.json").exists())
    if a.only:
        dirs = [d for d in dirs if d.name in set(a.only.split(","))]
    if not dirs:
        raise SystemExit(f"no seeds found in {root}")
    cfg = GenConfig(per_seed=a.per_seed, workers=a.workers, rng=a.rng, per_signature=a.per_signature)
    rep = generate(dirs, a.out, cfg, force=a.force)
    for s in rep["seeds"]:
        print(f"{s['seed']:20} " + (f"SKIPPED: {s['skipped']}" if s.get("skipped") else
              f"{len(s['tasks'])} tasks from {s['candidates']} candidates  split={s['split']}  rejected={s['rejected']}"))
    print(f"report: {Path(a.out) / 'GEN_REPORT.json'}   next: miniagent-eval --tasks-root {a.out} verify --sandbox")


def cmd_sandbox_build(a):
    import subprocess
    from ..sandbox import IMAGE
    return subprocess.call(["docker", "build", "-t", IMAGE, str(Path(__file__).resolve().parents[2] / "sandbox")])


def cmd_sandbox_clean(a):
    from ..sandbox import cleanup_orphans
    print(f"removed {cleanup_orphans()} container(s)")


def cmd_split(a):
    tasks = load_tasks(a.tasks_root)
    data = freeze_split(tasks, Path(a.tasks_root) / "SPLIT.json")
    from collections import Counter
    print(dict(Counter(v["split"] for v in data["tasks"].values())), "tasks in", Path(a.tasks_root) / "SPLIT.json")


def cmd_verify(a):
    """Each task must fail as shipped and pass (twice, to catch flakiness) with its reference solution."""
    import shutil, tempfile

    def check(t):
        if not t.solution.exists():
            return t, None
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp) / "r"; copy_repo(t.repo, w); add_hidden(t.hidden, w)
            before, _ = run_tests(w, t.test_cmd, sandbox=a.sandbox)
            for f in t.solution.rglob("*"):
                if f.is_file():
                    dst = w / f.relative_to(t.solution); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy(f, dst)
            after = [run_tests(w, t.test_cmd, sandbox=a.sandbox) for _ in range(2)]
        why = next((out for ok, out in after if not ok), "")
        return t, (not before, all(ok for ok, _ in after), why)

    bad = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for t, res in ex.map(check, load_tasks(a.tasks_root)):
            if res is None:
                print(f"{t.id}: no solution/ (skipped)"); continue
            fails, passes, why = res
            ok = fails and passes
            bad += not ok
            print(f"{t.id}: initial_fails={fails} solution_passes={passes} {'OK' if ok else 'PROBLEM'}", flush=True)
            if not passes:
                print("    " + why[-600:].replace("\n", "\n    "), flush=True)
    return 1 if bad else 0


_PERMANENT = re.compile(r"HTTP (400|401|402|403|404|422)\b")


def _quota_exhausted(rec):
    return rec.get("failure_class") == "api_error" and "QuotaExhausted" in (rec.get("error") or "")


def _permanent_api_error(rec):
    """A request the server rejects as invalid (bad model name, bad key, unsupported field) will
    fail the same way every time: retrying or continuing the batch only wastes time."""
    return (rec.get("failure_class") == "api_error" and bool(_PERMANENT.search(rec.get("error") or ""))) \
        or _quota_exhausted(rec)


class _Budget:
    """Stops launching new runs once the model-call budget is spent (free tiers count requests)."""

    def __init__(self, limit):
        import threading
        self.limit, self.used, self._lock = limit, 0, threading.Lock()

    def exhausted(self):
        return self.limit is not None and self.used >= self.limit

    def add(self, n):
        with self._lock:
            self.used += n


def _run_with_api_retries(task, cfg, r, out, client, keep, max_retries, pause=30.0, budget=None):
    """Server-side failures (api_error) are not evidence about the model: rerun the same
    (task, repeat) up to `max_retries` times. Every attempt keeps its own trajectory."""
    if budget is not None and budget.exhausted():
        return None                              # not started: picked up later by --resume
    rec = run_one(task, cfg, r, out, client, keep, attempt=0)
    if budget is not None:
        budget.add(rec["steps"] + rec.get("compactions", 0))      # a summary compaction is one more real request
    attempt = 0
    while rec["failure_class"] == "api_error" and not _permanent_api_error(rec) and attempt < max_retries:
        attempt += 1
        print(f"  api_error on {task.id} r{r} ({rec['error'][:80]}); retry {attempt}/{max_retries} in {pause:.0f}s")
        time.sleep(pause)
        rec = run_one(task, cfg, r, out, client, keep, attempt=attempt)
        if budget is not None:
            budget.add(rec["steps"] + rec.get("compactions", 0))
    return rec


def cmd_run(a):
    from ..client import APIError, ChatClient

    resume_dir = Path(a.resume) if a.resume else None
    if resume_dir:
        prev_meta = json.loads((resume_dir / "meta.json").read_text())
        cfg = prev_meta["config"]
    else:
        if not a.config:
            raise SystemExit("error: --config is required (or --resume <results dir>)")
        cfg = json.loads(Path(a.config).read_text())
        if a.sandbox:
            cfg["sandbox"] = True
    tasks = apply_split(load_tasks(a.tasks_root), Path(a.tasks_root) / "SPLIT.json")
    if resume_dir:
        keep_ids = set(prev_meta["tasks"])
        tasks = [t for t in tasks if t.id in keep_ids]
        for t in tasks:
            if prev_meta["task_hashes"][t.id] != t.hash:
                raise SystemExit(f"task {t.id} changed since the run being resumed was started")
    elif a.subset:
        sets = json.loads((Path(a.tasks_root) / "SUBSETS.json").read_text())
        if a.subset not in sets or a.subset.startswith("_"):
            raise SystemExit(f"unknown subset {a.subset!r}; available: {[k for k in sets if not k.startswith('_')]}")
        want = set(sets[a.subset]["tasks"])
        tasks = [t for t in tasks if t.id in want]
    elif a.tasks:
        want = set(a.tasks.split(","))
        tasks = [t for t in tasks if any(t.id == w or t.id.startswith(w) for w in want)]
    if a.split != "all" and not resume_dir:
        tasks = [t for t in tasks if t.split == a.split]
    retired = json.loads((Path(a.tasks_root) / "SPLIT.json").read_text()).get("retired", {})
    if not a.include_retired and not resume_dir:
        skipped = [t.id for t in tasks if t.id in retired]
        if skipped:
            print(f"skipping retired tasks: {', '.join(skipped)} (use --include-retired to run them)")
        tasks = [t for t in tasks if t.id not in retired]
    if any(t.split == "test" for t in tasks) and not a.final:
        raise SystemExit("refusing to run test-split tasks without --final "
                         "(test is reserved for one report run per finalized version)")
    if not tasks:
        raise SystemExit("no tasks selected")

    replay_only = bool(a.cassette) and a.cassette_mode == "replay"
    key = None
    if cfg.get("api_key_env") and not replay_only:
        key = os.environ.get(cfg["api_key_env"])
        if not key:
            raise SystemExit(f"error: {cfg['api_key_env']} is not set (required by config {cfg.get('name')!r})")
    base_url = cfg.get("base_url")
    if not base_url and cfg.get("base_url_env") and not replay_only:
        base_url = os.environ.get(cfg["base_url_env"])
        if not base_url:
            raise SystemExit(f"error: {cfg['base_url_env']} is not set (required by config {cfg.get('name')!r})")
    try:
        client = None if replay_only else ChatClient(api_key=key, base_url=base_url, extra_body=cfg.get("extra_body"),
                            timeout=cfg.get("api_timeout", 120.0), retries=cfg.get("api_retries", 3),
                            tool_result_json=bool(cfg.get("tool_result_json", False)),
                            api_style=cfg.get("api_style", "openai"),
                            text_tool_calls=bool(cfg.get("text_tool_calls", False)))
    except APIError as e:
        raise SystemExit(f"error: {e}")
    if a.cassette:
        from ..replay import CassetteClient
        client = CassetteClient(a.cassette, inner=client, mode=a.cassette_mode, fingerprint=config_hash(cfg))

    if resume_dir:
        out, meta = resume_dir, prev_meta
        run_id = meta["run_id"]
        repeat = meta["repeat"]
        if a.repeat > repeat:          # extend an existing run with more repeats (same tasks, same config)
            repeat = meta["repeat"] = a.repeat
            (out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
            print(f"extending {run_id} to {repeat} repeats")
        done = {(r["task_id"], r["repeat"]) for r in load_records(out) if r["failure_class"] != "api_error"}
        print(f"resuming {run_id}: {len(done)} runs already have a valid result")
    else:
        run_id = a.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-{cfg.get('name', 'run')}"
        out = Path(a.out_root) / run_id
        out.mkdir(parents=True, exist_ok=False)
        repeat = a.repeat
        done = set()
        meta = {"run_id": run_id, "config": cfg, "config_hash": config_hash(cfg), "split": a.split,
                "repeat": a.repeat, "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tasks": [t.id for t in tasks], "task_hashes": {t.id: t.hash for t in tasks}}
        (out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    jobs = [(t, r) for t in tasks for r in range(repeat) if (t.id, r) not in done]
    budget = _Budget(a.max_requests)
    print(f"{run_id}: {len(jobs)} runs to execute, {a.workers} workers"
          + (f", request budget {a.max_requests}" if a.max_requests else ""))
    recs = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex, (out / "runs.jsonl").open("a") as sink:
        futs = {ex.submit(_run_with_api_retries, t, cfg, r, out, client, a.keep_workspaces, a.api_error_retries,
                          30.0, budget): (t, r) for t, r in jobs}
        for f in as_completed(futs):
            t, r = futs[f]
            try:
                rec = f.result()
            except Exception as e:  # harness bug, not an agent failure; surface loudly
                print(f"  HARNESS ERROR {t.id} r{r}: {e!r}", file=sys.stderr)
                continue
            if rec is None:               # skipped: request budget spent
                continue
            recs.append(rec)
            sink.write(json.dumps(rec, ensure_ascii=False) + "\n"); sink.flush()
            if _quota_exhausted(rec):
                ex.shutdown(wait=False, cancel_futures=True)
                print(f"\nSTOPPING: API quota exhausted ({rec['error'][:200]}).\n"
                      f"Results so far are saved. Continue later with:\n"
                      f"  miniagent-eval run --resume {out}", file=sys.stderr)
                return 3
            if _permanent_api_error(rec):
                ex.shutdown(wait=False, cancel_futures=True)
                print(f"\nSTOPPING: permanent API error, the remaining runs would fail identically.\n  {rec['error']}\n"
                      f"Check the model id, the API key and the config's base_url / extra_body.", file=sys.stderr)
                return 2
            print(f"  {'PASS' if rec['passed'] else 'FAIL'} {t.id} r{r}  {rec['failure_class']}  "
                  f"steps={rec['steps']} wall={rec['wall_s']}s")
    price = _load_price(a.prices, cfg["model"])
    allrecs = load_records(out)
    (out / "report.md").write_text(markdown_report(meta, allrecs, price))
    (out / "summary.json").write_text(json.dumps(summarize(allrecs, price), indent=2))
    s = summarize(allrecs, price)
    total_jobs = len(meta["tasks"]) * meta["repeat"]
    pending = total_jobs - len({(r["task_id"], r["repeat"]) for r in allrecs if r["failure_class"] != "api_error"})
    print(f"pass rate {s['pass_rate'] * 100:.1f}% over {s['n_runs']} valid runs  mean steps {s['mean_steps']:.1f}  "
          f"report: {out / 'report.md'}")
    if pending:
        print(f"{pending} run(s) still without a valid result (budget/quota/api errors). "
              f"Continue with: miniagent-eval run --resume {out}")
    return 0


def cmd_report(a):
    d = Path(a.result_dir)
    meta = json.loads((d / "meta.json").read_text())
    price = _load_price(a.prices, meta["config"]["model"])
    text = markdown_report(meta, load_records(d), price)
    (d / "report.md").write_text(text)
    print(text)


def cmd_view(a):
    from .view import serve
    return serve([Path(d) for d in a.dirs], a.port, not a.no_open)


def cmd_replay(a):
    """Replay recorded trajectories through the current loop; exit 1 if any behaves differently."""
    from .replay import collect, replay_run
    paths = collect(a.paths)
    if not paths:
        raise SystemExit("no trajectory.jsonl found")
    counts = {"ok": 0, "diff": 0, "skipped": 0}
    for p in paths:
        r = replay_run(p, a.tasks_root)
        counts[r["status"]] += 1
        if r["status"] == "ok" and not a.verbose:
            continue
        note = r.get("reason") or "; ".join(r.get("diffs", [])) or ""
        extra = f"  (tool outputs differing: {r['output_mismatches']})" if r["status"] != "skipped" else ""
        print(f"{r['status'].upper():7} {p}{extra}" + (f"\n          {note}" if note else ""))
    print(f"{counts['ok']} identical, {counts['diff']} different, {counts['skipped']} skipped of {len(paths)}")
    return 1 if counts["diff"] else 0


def cmd_export(a):
    from .export import export_sft
    stats = export_sft(a.dirs, a.out, models=set(a.models.split(",")) if a.models else None,
                       with_reasoning=a.with_reasoning, splits=set(a.splits.split(",")))
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"wrote {stats['kept']} examples to {a.out}")


def cmd_compare(a):
    ra, rb = load_records(a.a), load_records(a.b)
    ma, mb = (json.loads((Path(x) / "meta.json").read_text()) for x in (a.a, a.b))
    if ma.get("split") != mb.get("split"):
        print(f"WARNING: different splits ({ma.get('split')} vs {mb.get('split')})", file=sys.stderr)
    for t, ha in ma["task_hashes"].items():
        if t in mb["task_hashes"] and mb["task_hashes"][t] != ha:
            print(f"WARNING: task {t} differs between runs", file=sys.stderr)
    print(markdown_compare(ma["config"].get("name", a.a), mb["config"].get("name", a.b), compare(ra, rb)))


def main(argv=None) -> int:
    # Make the venv's tools (pytest) visible to the agent's bash tool and to grading.
    os.environ["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}"
    ap = argparse.ArgumentParser(prog="miniagent-eval")
    ap.add_argument("--tasks-root", default="tasks")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("split", help="freeze dev/test split for tasks not yet in SPLIT.json").set_defaults(fn=cmd_split)
    vf = sub.add_parser("verify", help="check each task fails initially and passes with its reference solution")
    vf.add_argument("--sandbox", action="store_true", help="run the tests in the Docker sandbox")
    vf.add_argument("--workers", type=int, default=1, help="tasks checked in parallel")
    vf.set_defaults(fn=cmd_verify)
    g = sub.add_parser("gen", help="generate bug-fixing tasks from seed libraries by mutation (needs the Docker sandbox)")
    g.add_argument("--seeds", default="seeds", help="directory with one subdirectory per seed (seed.json + repo/)")
    g.add_argument("--out", default="gen_tasks")
    g.add_argument("--only", help="comma-separated seed names")
    g.add_argument("--per-seed", type=int, default=20)
    g.add_argument("--per-signature", type=int, default=1, help="max tasks that fail exactly the same tests")
    g.add_argument("--workers", type=int, default=4)
    g.add_argument("--rng", type=int, default=0)
    g.add_argument("--force", action="store_true", help="regenerate seeds that already have tasks in --out")
    g.set_defaults(fn=cmd_gen)
    sub.add_parser("sandbox-build", help="build the sandbox image (needs Docker)").set_defaults(fn=cmd_sandbox_build)
    sub.add_parser("sandbox-clean", help="remove sandbox containers left behind by a crashed run").set_defaults(fn=cmd_sandbox_clean)
    r = sub.add_parser("run", help="run a config over a split")
    r.add_argument("--config")
    r.add_argument("--resume", help="results dir of an interrupted run: only runs without a valid result are executed; "
                        "add --repeat N (N larger than before) to extend it with more repeats")
    r.add_argument("--max-requests", type=int, default=None,
                   help="stop starting new runs after this many model calls (free tiers meter requests per day)")
    r.add_argument("--split", choices=["train", "dev", "test", "all"], default="dev")
    r.add_argument("--tasks", help="comma-separated task ids or prefixes")
    r.add_argument("--subset", help="named task subset from tasks/SUBSETS.json (see its 'why' field)")
    r.add_argument("--repeat", type=int, default=1)
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--include-retired", action="store_true", help="also run tasks listed under 'retired' in SPLIT.json")
    r.add_argument("--final", action="store_true", help="allow running test-split tasks")
    r.add_argument("--out-root", default="results")
    r.add_argument("--run-id")
    r.add_argument("--prices", default="configs/prices.json")
    r.add_argument("--api-error-retries", type=int, default=2,
                   help="rerun a run that ended in api_error up to N times (server trouble, not a model failure)")
    r.add_argument("--cassette", help="file that stores model responses by request hash (see miniagent/replay.py)")
    r.add_argument("--cassette-mode", choices=["auto", "record", "replay"], default="auto",
                   help="auto: reuse a stored response, else call the model and store it; record: always call and store; "
                        "replay: stored responses only (no API key needed, a missing one is an error)")
    r.add_argument("--sandbox", action="store_true", help="run bash and the grading tests in the Docker sandbox (sets config key sandbox)")
    r.add_argument("--keep-workspaces", action="store_true", help="keep final workspaces for inspection")
    r.set_defaults(fn=cmd_run)
    p = sub.add_parser("report"); p.add_argument("result_dir"); p.add_argument("--prices", default="configs/prices.json"); p.set_defaults(fn=cmd_report)
    v = sub.add_parser("view", help="browse and compare trajectories in a local web page")
    v.add_argument("dirs", nargs="+", help="results directories (or a runs/ directory)")
    v.add_argument("--port", type=int, default=8765)
    v.add_argument("--no-open", action="store_true")
    v.set_defaults(fn=cmd_view)
    rp = sub.add_parser("replay", help="replay recorded trajectories through the current loop and report differences")
    rp.add_argument("paths", nargs="+", help="trajectory.jsonl files or directories containing them")
    rp.add_argument("--verbose", action="store_true", help="also list the identical ones")
    rp.set_defaults(fn=cmd_replay)
    ex = sub.add_parser("export", help="write passing runs as chat-format training examples (JSONL)")
    ex.add_argument("dirs", nargs="+", help="results directories")
    ex.add_argument("--out", required=True)
    ex.add_argument("--models", help="comma-separated model names to keep (as in run_start.model, e.g. deepseek-flash)")
    ex.add_argument("--with-reasoning", action="store_true", help="include logged thinking as reasoning_content")
    ex.add_argument("--splits", default="train", help="comma-separated splits to export (default: train; tasks without a split are 'none'). "
                    "Exporting dev or test tasks as training data voids the evaluation on them")
    ex.set_defaults(fn=cmd_export)
    c = sub.add_parser("compare"); c.add_argument("a"); c.add_argument("b"); c.set_defaults(fn=cmd_compare)
    a = ap.parse_args(argv)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
