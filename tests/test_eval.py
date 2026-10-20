"""Harness tests with a scripted fake client (no network)."""
import json
import shutil
from pathlib import Path

import pytest

from miniagent.client import ModelResponse, ToolCall
from miniagent.eval import grade, report
from miniagent.eval.runner import run_one
from miniagent.eval.tasks import Task, apply_split, freeze_split, load_tasks, task_hash


def make_task(root: Path, name="t1", bug=True) -> Task:
    d = root / name
    (d / "repo").mkdir(parents=True)
    (d / "repo" / "m.py").write_text("def f():\n    return 1\n" if bug else "def f():\n    return 2\n")
    (d / "repo" / "test_m.py").write_text("from m import f\n\ndef test_f():\n    assert f() == 2\n")
    (d / "task.json").write_text(json.dumps({"prompt": "make f return 2", "test_cmd": "python -m pytest -q"}))
    return load_tasks(root)[0]


def text(t): return t
def call(i, name, **inp): return ToolCall(i, name, json.dumps(inp))


class Fake:
    def __init__(self, script):
        self.script = list(script)

    def chat(self, **kw):
        content, stop = self.script.pop(0)
        calls = [c for c in content if isinstance(c, ToolCall)]
        txt = "".join(c for c in content if isinstance(c, str))
        return ModelResponse(txt, calls, "tool_calls" if stop == "tool_use" else "stop",
                             {"input_tokens": 150, "output_tokens": 10, "cache_hit_tokens": 50})


CFG = {"name": "t", "model": "fake", "temperature": 0.0, "max_steps": 5}


def test_pass(tmp_path):
    t = make_task(tmp_path / "tasks")
    c = Fake([([call("1", "edit_file", path="m.py", old_string="return 1", new_string="return 2")], "tool_use"),
              ([text("done")], "end_turn")])
    r = run_one(t, CFG, 0, tmp_path / "out", c)
    assert r["passed"] and r["failure_class"] == "pass" and r["steps"] == 2
    assert r["cache_read_tokens"] == 100 and r["uncached_input_tokens"] == 200
    assert r["changed_files"] == ["m.py"]


def test_no_edit_failure(tmp_path):
    t = make_task(tmp_path / "tasks")
    r = run_one(t, CFG, 0, tmp_path / "out", Fake([([text("I looked, nothing to do")], "end_turn")]))
    assert not r["passed"] and r["failure_class"] == "no_edit"


def test_tampering_is_restored_and_flagged(tmp_path):
    t = make_task(tmp_path / "tasks")
    cheat = call("1", "write_file", path="test_m.py", content="def test_f():\n    assert True\n")
    r = run_one(t, CFG, 0, tmp_path / "out", Fake([([cheat], "tool_use"), ([text("done")], "end_turn")]))
    assert not r["passed"]                      # pristine test restored -> still fails
    assert r["tampered_tests"] and r["failure_class"] == "no_edit"   # flag, not a class of its own


def test_added_test_file_removed(tmp_path):
    t = make_task(tmp_path / "tasks")
    c = Fake([([call("1", "edit_file", path="m.py", old_string="return 1", new_string="return 2"),
                call("2", "write_file", path="test_extra.py", content="def test_x():\n    assert False\n")], "tool_use"),
              ([text("done")], "end_turn")])
    r = run_one(t, CFG, 0, tmp_path / "out", c)
    assert r["passed"] and r["tampered_tests"]   # extra failing test ignored, but flagged


def test_max_steps_class(tmp_path):
    t = make_task(tmp_path / "tasks")
    loop = ([call("x", "grep", pattern="def")], "tool_use")
    r = run_one(t, {**CFG, "max_steps": 2}, 0, tmp_path / "out", Fake([loop] * 2))
    assert r["failure_class"] == "max_steps"


def test_api_error_class(tmp_path):
    t = make_task(tmp_path / "tasks")

    class Boom:
        def chat(self, **kw): raise RuntimeError("503")
    r = run_one(t, CFG, 0, tmp_path / "out", Boom())
    assert r["failure_class"] == "api_error"


def test_split_frozen_and_hash_guard(tmp_path):
    root = tmp_path / "tasks"
    for n in "abcde":
        make_task_dir = root / n
        (make_task_dir / "repo").mkdir(parents=True)
        (make_task_dir / "repo" / "x.py").write_text(n)
        (make_task_dir / "task.json").write_text(json.dumps({"prompt": n}))
    tasks = load_tasks(root)
    d1 = freeze_split(tasks, root / "SPLIT.json")
    assert sum(v["split"] == "test" for v in d1["tasks"].values()) == 2  # ceil(0.4*5)
    assert freeze_split(tasks, root / "SPLIT.json")["tasks"] == d1["tasks"]   # idempotent
    apply_split(load_tasks(root), root / "SPLIT.json")
    (root / "a" / "repo" / "x.py").write_text("changed")
    with pytest.raises(SystemExit):
        apply_split(load_tasks(root), root / "SPLIT.json")


def test_report_and_compare():
    def rec(task, passed, steps=5, cls=None):
        return {"task_id": task, "passed": passed, "steps": steps, "uncached_input_tokens": 100, "cache_read_tokens": 0,
                "cache_creation_tokens": 0, "output_tokens": 10, "wall_s": 1.0, "tool_errors": 0, "compactions": 0,
                "tampered_tests": False, "failure_class": cls or ("pass" if passed else "no_edit")}
    a = [rec("t1", True), rec("t2", False), rec("t3", False)]
    b = [rec("t1", True), rec("t2", True), rec("t3", False)]
    c = report.compare(a, b)
    assert c["improved"] == ["t2"] and c["regressed"] == [] and c["unchanged"] == 2
    price = {"off_peak": {"input": 1.0, "cache_read": 0.1, "output": 2.0},
             "peak": {"input": 2.0, "cache_read": 0.2, "output": 4.0}}
    s = report.summarize(a, price)
    assert abs(s["pass_rate"] - 1 / 3) < 1e-9
    assert s["mean_cost_usd_off_peak"] == pytest.approx((100 + 20) / 1e6)
    assert s["mean_cost_usd_peak"] == pytest.approx(2 * (100 + 20) / 1e6)
    assert report.summarize(a)["mean_cost_usd_off_peak"] is None
    assert "Per task" in report.markdown_report({"run_id": "x", "config": {"model": "m"}}, a)


def test_hidden_tests_are_grading_only(tmp_path):
    t = make_task(tmp_path / "tasks")
    # visible test passes with f()==2; hidden test additionally requires f() >= 5
    (t.dir / "hidden").mkdir()
    (t.dir / "hidden" / "test_hidden.py").write_text("from m import f\n\ndef test_big():\n    assert f() >= 5\n")
    from miniagent.eval.tasks import load_tasks
    t = load_tasks(tmp_path / "tasks")[0]
    fix = Fake([([call("1", "edit_file", path="m.py", old_string="return 1", new_string="return 2")], "tool_use"),
                ([text("done")], "end_turn")])
    r = run_one(t, CFG, 0, tmp_path / "out", fix)
    assert not r["passed"]                       # visible fix is not enough
    assert "test_hidden" in r["test_output_tail"]
    assert not (tmp_path / "out" / "trajectories").exists() or "test_hidden" not in (
        tmp_path / "out" / "trajectories" / "t1__r0" / "trajectory.jsonl").read_text()


def test_last_test_green_detection():
    def tr(cmd, out, err=False):
        return {"event": "tool_result", "name": "bash", "input": {"command": cmd}, "output": out, "is_error": err}
    assert grade.last_test_green([]) is None
    assert grade.last_test_green([tr("ls", "a.py")]) is None
    assert grade.last_test_green([tr("pytest -q", "....\n4 passed in 0.01s")]) is True
    assert grade.last_test_green([tr("pytest -q", "1 failed, 3 passed in 0.1s")]) is False
    assert grade.last_test_green([tr("pytest -q", "3 passed"), tr("python -m pytest x", "FAILED a::b\n1 failed")]) is False
    assert grade.last_test_green([tr("pytest -q", "1 failed"), tr("pytest -q", "5 passed in 1s")]) is True


def test_out_of_balance_is_a_permanent_api_error():
    from miniagent.eval.cli import _permanent_api_error
    rec = {"failure_class": "api_error", "error": 'APIError(\'HTTP 402: {"error":{"message":"Insufficient Balance"}}\')'}
    assert _permanent_api_error(rec)
    assert not _permanent_api_error({"failure_class": "api_error", "error": "APIError('HTTP 503: busy')"})


def test_git_directory_is_not_an_edit(tmp_path):
    t = make_task(tmp_path / "tasks")
    c = Fake([([call("1", "bash", command="git init -q . && git add -A")], "tool_use"), ([text("done")], "end_turn")])
    r = run_one(t, CFG, 0, tmp_path / "out", c)
    assert r["changed_files"] == [] and r["failure_class"] == "no_edit"


def test_report_excludes_api_errors_and_resume_dedupes(tmp_path):
    import json as _json
    d = tmp_path / "res"
    d.mkdir()
    base = {"uncached_input_tokens": 1, "cache_read_tokens": 0, "cache_creation_tokens": 0, "output_tokens": 1,
            "wall_s": 1.0, "tool_errors": 0, "compactions": 0, "tampered_tests": False, "steps": 3}
    rows = [
        {**base, "task_id": "a", "repeat": 0, "passed": True, "failure_class": "pass"},
        {**base, "task_id": "b", "repeat": 0, "passed": False, "failure_class": "api_error"},
        {**base, "task_id": "b", "repeat": 0, "passed": False, "failure_class": "tests_failed_after_edit"},  # resumed
        {**base, "task_id": "c", "repeat": 0, "passed": False, "failure_class": "api_error"},
    ]
    (d / "runs.jsonl").write_text("\n".join(_json.dumps(r) for r in rows))
    recs = report.load_records(d)
    assert len(recs) == 3                                         # (b, 0) keeps only the newest record
    s = report.summarize(recs)
    assert s["n_runs"] == 2 and s["n_api_error_excluded"] == 1 and abs(s["pass_rate"] - 0.5) < 1e-9
    md = report.markdown_report({"run_id": "x", "config": {"model": "m"}}, recs)
    assert "excluded because the API failed" in md and "n/a (api_error only)" in md


def test_request_budget_counts_summary_requests(monkeypatch, tmp_path):
    from miniagent.eval import cli
    recs = iter([{"steps": 10, "compactions": 3, "failure_class": "pass", "error": None}])
    monkeypatch.setattr(cli, "run_one", lambda *a, **k: next(recs))
    budget = cli._Budget(100)
    cli._run_with_api_retries("task", {}, 0, tmp_path, None, False, 0, budget=budget)
    assert budget.used == 13                                   # 10 loop requests + 3 summarisation requests
    assert cli._run_with_api_retries("task", {}, 0, tmp_path, None, False, 0, budget=cli._Budget(0)) is None


def test_a_sandbox_fault_becomes_an_api_error_record_not_a_lost_run(tmp_path, monkeypatch):
    from miniagent.eval import runner
    from miniagent.sandbox import SandboxError
    t = make_task(tmp_path / "tasks")
    c = Fake([([call("1", "edit_file", path="m.py", old_string="return 1", new_string="return 2")], "tool_use"),
              ([text("done")], "end_turn")])

    def boom(*a, **k): raise SandboxError("docker exec did not return; the container was removed")

    monkeypatch.setattr(runner, "run_tests", boom)               # Docker goes away while grading
    r = run_one(t, {**CFG, "sandbox": False}, 0, tmp_path / "out", c)
    assert r["failure_class"] == "api_error" and "SandboxError" in r["error"] and not r["passed"]
    assert r["steps"] == 2 and r["trajectory"].endswith("trajectory.jsonl")             # what the agent did is still counted
    assert report.summarize([r], None)["n_api_error_excluded"] == 1                      # and it stays out of the pass rate


def test_a_leftover_trajectory_of_a_crashed_attempt_is_not_appended_to(tmp_path):
    t = make_task(tmp_path / "tasks")
    stale = tmp_path / "out" / "trajectories" / "t1__r0"
    stale.mkdir(parents=True)
    (stale / "trajectory.jsonl").write_text(json.dumps({"event": "run_start", "task": "OLD", "ts": 0}) + "\n")
    c = Fake([([call("1", "edit_file", path="m.py", old_string="return 1", new_string="return 2")], "tool_use"),
              ([text("done")], "end_turn")])
    r = run_one(t, CFG, 0, tmp_path / "out", c)
    events = [json.loads(l) for l in open(r["trajectory"])]
    assert [e["event"] for e in events].count("run_start") == 1 and events[0]["task"] != "OLD" and r["passed"]
