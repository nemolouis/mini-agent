"""Aggregate run records into metrics, a markdown report, and paired comparisons.

Statistical unit is the *task*: repeats of the same task are averaged first,
and confidence intervals are bootstrapped over tasks (runs of one task are not
independent samples).
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def load_records(result_dir: str | Path) -> list[dict]:
    p = Path(result_dir) / "runs.jsonl"
    recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    latest = {}                       # a resumed run appends a newer record for the same (task, repeat)
    for r in recs:
        latest[(r["task_id"], r["repeat"])] = r
    return list(latest.values())


def valid(records: list[dict]) -> list[dict]:
    """Runs that tell us something about the model: server-side failures (api_error) do not."""
    return [r for r in records if r["failure_class"] != "api_error"]


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def bootstrap_ci(values: list[float], n: int = 2000, seed: int = 0) -> tuple[float, float]:
    if len(values) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    means = sorted(_mean(rng.choices(values, k=len(values))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def per_task_pass(records: list[dict]) -> dict[str, float]:
    by = defaultdict(list)
    for r in records:
        by[r["task_id"]].append(1.0 if r["passed"] else 0.0)
    return {t: _mean(v) for t, v in by.items()}


def cost_of(rec: dict, price: dict | None, tier: str = "off_peak") -> float | None:
    p = (price or {}).get(tier)
    if not p or any(p.get(k) is None for k in ("input", "cache_read", "output")):
        return None
    price = p
    return (rec["uncached_input_tokens"] * price["input"]
            + rec["cache_creation_tokens"] * price["input"]
            + rec["cache_read_tokens"] * price["cache_read"]
            + rec["output_tokens"] * price["output"]) / 1e6


def summarize(records: list[dict], price: dict | None = None) -> dict:
    n_api_error = len(records) - len(valid(records))
    records = valid(records)
    pt = per_task_pass(records)
    lo, hi = bootstrap_ci(list(pt.values()))
    def mean_cost(tier):
        cs = [cost_of(r, price, tier) for r in records]
        return None if not cs or any(c is None for c in cs) else _mean(cs)
    total_in = [r["uncached_input_tokens"] + r["cache_read_tokens"] + r["cache_creation_tokens"] for r in records]
    return {
        "n_tasks": len(pt), "n_runs": len(records), "n_api_error_excluded": n_api_error,
        "pass_rate": _mean(pt.values()), "pass_rate_ci95": [lo, hi],
        "mean_steps": _mean(r["steps"] for r in records),
        "mean_input_tokens": _mean(total_in),
        "mean_cache_read_tokens": _mean(r["cache_read_tokens"] for r in records),
        "mean_output_tokens": _mean(r["output_tokens"] for r in records),
        "mean_reasoning_tokens": _mean(r.get("reasoning_tokens", 0) for r in records),
        "mean_cost_usd_off_peak": mean_cost("off_peak"),
        "mean_cost_usd_peak": mean_cost("peak"),
        "mean_wall_s": _mean(r["wall_s"] for r in records),
        "mean_tool_errors": _mean(r["tool_errors"] for r in records),
        "runs_with_compaction": sum(1 for r in records if r["compactions"]),
        "tampered_runs": sum(1 for r in records if r["tampered_tests"]),
        "false_completions": sum(1 for r in records if not r["passed"] and r.get("last_test_green") is True),
        "failed_runs": sum(1 for r in records if not r["passed"]),
        "runs_after_api_retry": sum(1 for r in records if r.get("attempt", 0) > 0),
        "failure_classes": dict(Counter(r["failure_class"] for r in records)),
    }


def _fmt(x, nd=2):
    return "n/a" if x is None or x != x else f"{x:.{nd}f}"


def markdown_report(meta: dict, records: list[dict], price: dict | None = None) -> str:
    s = summarize(records, price)
    ci = s["pass_rate_ci95"]
    pt = per_task_pass(valid(records))
    lines = [
        f"# Eval report: {meta.get('run_id')}", "",
        f"- config: `{meta['config'].get('name')}` (hash `{meta.get('config_hash')}`), model `{meta['config']['model']}`, "
        f"temperature {meta['config'].get('temperature')}, max_steps {meta['config'].get('max_steps', 30)}",
        f"- model reported by server: {', '.join(sorted({m for r in records for m in r.get('response_models', [])})) or 'unknown'}",
        f"- split: **{meta.get('split')}**, tasks {s['n_tasks']}, valid runs {s['n_runs']} (repeat {meta.get('repeat')}); "
        f"**{s['n_api_error_excluded']} run(s) excluded because the API failed** (see failure classes)",
        f"- date: {meta.get('date')}",
        *([f"- hypothesis: {meta['config']['hypothesis']}"] if meta["config"].get("hypothesis") else []),
        "", "## Summary", "",
        "| metric | value |", "|---|---|",
        f"| pass rate (task-averaged) | {_fmt(s['pass_rate'] * 100, 1)}% (95% CI {_fmt(ci[0] * 100, 1)}–{_fmt(ci[1] * 100, 1)}%) |",
        f"| mean steps | {_fmt(s['mean_steps'], 1)} |",
        f"| mean input tokens (incl. cache) | {_fmt(s['mean_input_tokens'], 0)} |",
        f"| mean output tokens | {_fmt(s['mean_output_tokens'], 0)} |",
        f"| mean reasoning tokens (0 = not reported) | {_fmt(s['mean_reasoning_tokens'], 0)} |",
        f"| mean cost (USD/run), off-peak price | {_fmt(s['mean_cost_usd_off_peak'], 5)} |",
        f"| mean cost (USD/run), peak price | {_fmt(s['mean_cost_usd_peak'], 5)} |",
        f"| mean wall time (s) | {_fmt(s['mean_wall_s'], 1)} |",
        f"| mean tool errors | {_fmt(s['mean_tool_errors'], 2)} |",
        f"| runs with summary-compaction | {s['runs_with_compaction']} |",
        f"| runs that modified tests | {s['tampered_runs']} |",
        f"| failed runs whose own last test run was green (false completion) | {s['false_completions']} / {s['failed_runs']} |",
        f"| runs that needed an api_error rerun | {s['runs_after_api_retry']} |",
        "", "## Failure classes (per run)", "", "| class | runs |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(s["failure_classes"].items(), key=lambda kv: -kv[1])],
        "", "## Per task", "", "| task | pass rate | steps (mean) | classes |", "|---|---|---|---|",
    ]
    by = defaultdict(list)
    for r in records:
        by[r["task_id"]].append(r)
    for t in sorted(by):
        rs = by[t]
        cls = Counter(r["failure_class"] for r in rs)
        vr = [r for r in rs if r["failure_class"] != "api_error"]
        rate = f"{pt[t]:.2f} ({sum(r['passed'] for r in vr)}/{len(vr)})" if vr else "n/a (api_error only)"
        lines.append(f"| {t} | {rate} | {_mean(r['steps'] for r in rs):.1f} | "
                     f"{', '.join(f'{k}×{v}' for k, v in cls.items())} |")
    if s["mean_cost_usd_off_peak"] is None:
        lines += ["", "_Cost is n/a: fill in `configs/prices.json` for this model._"]
    return "\n".join(lines) + "\n"


def compare(a: list[dict], b: list[dict]) -> dict:
    a, b = valid(a), valid(b)
    pa, pb = per_task_pass(a), per_task_pass(b)
    common = sorted(set(pa) & set(pb))
    diffs = [pb[t] - pa[t] for t in common]
    lo, hi = bootstrap_ci(diffs)
    return {
        "n_common_tasks": len(common),
        "only_in_a": sorted(set(pa) - set(pb)), "only_in_b": sorted(set(pb) - set(pa)),
        "pass_a": _mean(pa[t] for t in common), "pass_b": _mean(pb[t] for t in common),
        "mean_diff": _mean(diffs), "diff_ci95": [lo, hi],
        "improved": [t for t in common if pb[t] > pa[t]],
        "regressed": [t for t in common if pb[t] < pa[t]],
        "unchanged": sum(1 for t in common if pb[t] == pa[t]),
        "steps_a": _mean(r["steps"] for r in a), "steps_b": _mean(r["steps"] for r in b),
    }


def markdown_compare(name_a: str, name_b: str, c: dict) -> str:
    ci = c["diff_ci95"]
    return "\n".join([
        f"# Compare: {name_a} → {name_b}", "",
        f"- common tasks: {c['n_common_tasks']}",
        f"- pass rate: {c['pass_a'] * 100:.1f}% → {c['pass_b'] * 100:.1f}% "
        f"(diff {c['mean_diff'] * 100:+.1f} pts, 95% CI {_fmt(ci[0] * 100, 1)} to {_fmt(ci[1] * 100, 1)})",
        f"- mean steps: {c['steps_a']:.1f} → {c['steps_b']:.1f}",
        f"- improved ({len(c['improved'])}): {', '.join(c['improved']) or '-'}",
        f"- regressed ({len(c['regressed'])}): {', '.join(c['regressed']) or '-'}",
        f"- unchanged: {c['unchanged']}",
        *([f"- only in A: {c['only_in_a']}"] if c["only_in_a"] else []),
        *([f"- only in B: {c['only_in_b']}"] if c["only_in_b"] else []),
        "", "_With few tasks the interval is wide; treat small differences as noise._", "",
    ])
