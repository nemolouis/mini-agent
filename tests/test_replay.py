"""Record/replay tests (no network, no model)."""
import json
import threading

import pytest

from miniagent.agent import Agent
from miniagent.client import ModelResponse, ToolCall
from miniagent.eval.replay import replay_run, signature
from miniagent.eval.runner import run_one
from miniagent.eval.tasks import load_tasks
from miniagent.replay import (CassetteClient, ReplayMiss, TrajectoryReplayClient, request_key, response_from_dict,
                              response_to_dict)
from miniagent.tools import Workspace
from miniagent.trajectory import Trajectory


def call(i, name, **inp): return ToolCall(i, name, json.dumps(inp))


def usage(n=10): return {"input_tokens": n, "output_tokens": 5, "cache_hit_tokens": 0}


class Script:
    """Answers from a list of (text, [ToolCall], input_tokens); counts calls."""

    def __init__(self, script):
        self.script, self.n = list(script), 0

    def chat(self, **kw):
        self.n += 1
        text, calls, tok = self.script.pop(0)
        return ModelResponse(text, calls, "tool_calls" if calls else "stop", usage(tok), model="m")


def events(d):
    return [json.loads(l) for l in (d / "trajectory.jsonl").read_text().splitlines()]


REQ = dict(model="m", messages=[{"role": "user", "content": "hi"}], system="s", tools=[{"a": 1}], max_tokens=100, temperature=0.0)


# ------------------------------------------------------------------ request key
def test_key_is_stable_and_sensitive_to_every_input():
    k = request_key(**REQ)
    assert request_key(**{**REQ, "tools": [{"a": 1}]}) == k
    for field, other in [("model", "n"), ("system", "t"), ("tools", [{"a": 2}]), ("max_tokens", 101), ("temperature", 0.5),
                         ("messages", [{"role": "user", "content": "ho"}])]:
        assert request_key(**{**REQ, field: other}) != k, field
    assert request_key(**REQ, fingerprint="cfg-b") != k
    assert request_key(**{**REQ, "tools": [{"b": 1, "a": 1}]}) == request_key(**{**REQ, "tools": [{"a": 1, "b": 1}]})


def test_response_roundtrip_keeps_extra_and_reasoning():
    r = ModelResponse("t", [ToolCall("1", "bash", '{"command": "ls"}', {"thought_signature": "SIG"})], "tool_calls",
                      usage(7), model="srv", reasoning="because")
    assert response_from_dict(json.loads(json.dumps(response_to_dict(r)))) == r


# ------------------------------------------------------------------ cassette
def test_record_then_replay_without_the_real_client(tmp_path):
    path = tmp_path / "c.jsonl"
    inner = Script([("one", [], 1), ("two", [call("1", "grep", pattern="x")], 2)])
    rec = CassetteClient(path, inner=inner, mode="record")
    a = rec.chat(**REQ)
    b = rec.chat(**{**REQ, "model": "other"})
    assert (a.text, b.text, inner.n) == ("one", "two", 2)

    rep = CassetteClient(path, mode="replay")
    assert rep.chat(**REQ) == a and rep.chat(**{**REQ, "model": "other"}) == b
    assert rep.hits == 2
    with pytest.raises(ReplayMiss):
        rep.chat(**{**REQ, "model": "never recorded"})
    assert rep.misses == 1 and len(path.read_text().splitlines()) == 2        # replay never writes


def test_auto_mode_calls_the_model_once_per_distinct_request(tmp_path):
    inner = Script([("one", [], 1), ("two", [], 1)])
    c = CassetteClient(tmp_path / "c.jsonl", inner=inner, mode="auto")
    assert c.chat(**REQ).text == c.chat(**REQ).text == "one" and inner.n == 1
    assert c.chat(**{**REQ, "system": "other"}).text == "two" and inner.n == 2
    again = CassetteClient(tmp_path / "c.jsonl", inner=Script([]), mode="auto")          # survives a restart
    assert again.chat(**REQ).text == "one"


def test_fingerprint_separates_configs(tmp_path):
    p = tmp_path / "c.jsonl"
    CassetteClient(p, inner=Script([("a", [], 1)]), fingerprint="cfg-a").chat(**REQ)
    with pytest.raises(ReplayMiss):
        CassetteClient(p, mode="replay", fingerprint="cfg-b").chat(**REQ)


def test_hits_are_fresh_objects(tmp_path):
    p = tmp_path / "c.jsonl"
    CassetteClient(p, inner=Script([("a", [call("1", "bash", command="ls")], 1)]), mode="record").chat(**REQ)
    c = CassetteClient(p, mode="replay")
    first = c.chat(**REQ)
    first.tool_calls[0].extra["poison"] = 1
    first.usage["input_tokens"] = 999
    second = c.chat(**REQ)
    assert second.tool_calls[0].extra == {} and second.usage["input_tokens"] == 1


def test_modes_are_validated(tmp_path):
    with pytest.raises(ValueError):
        CassetteClient(tmp_path / "c", mode="record")                  # needs a real client
    with pytest.raises(ValueError):
        CassetteClient(tmp_path / "c", inner=Script([]), mode="nope")


def test_concurrent_recording_keeps_the_file_intact(tmp_path):
    p = tmp_path / "c.jsonl"

    class Echo:
        def chat(self, **kw): return ModelResponse(kw["messages"][0]["content"], [], "stop", usage())

    c = CassetteClient(p, inner=Echo(), mode="record")
    ts = [threading.Thread(target=lambda i=i: c.chat(**{**REQ, "messages": [{"role": "user", "content": f"q{i}"}]})) for i in range(30)]
    [t.start() for t in ts]; [t.join() for t in ts]
    lines = [json.loads(l) for l in p.read_text().splitlines()]
    assert len(lines) == 30
    rep = CassetteClient(p, mode="replay")
    assert rep.chat(**{**REQ, "messages": [{"role": "user", "content": "q7"}]}).text == "q7"


# ------------------------------------------------------------------ what the loop writes
def test_run_start_has_system_and_tools_and_model_call_has_extra(tmp_path):
    (tmp_path / "f.txt").write_text("hello")
    sig = ToolCall("1", "read_file", '{"path": "f.txt"}', {"thought_signature": "SIG"})
    client = Script([("", [sig], 10), ("ok", [], 10)])
    Agent(client, "m", Workspace(tmp_path), trajectory=Trajectory(tmp_path / "run"), system="MY SYSTEM").run("t")
    ev = events(tmp_path / "run")
    assert ev[0]["system"] == "MY SYSTEM"
    assert {s["function"]["name"] for s in ev[0]["tool_specs"]} == {"read_file", "write_file", "edit_file", "bash", "grep"}
    assert ev[1]["tool_calls"][0]["extra"] == {"thought_signature": "SIG"}


def test_reasoning_is_logged_only_when_asked(tmp_path):
    for flag in (False, True):
        d = tmp_path / str(flag)
        d.mkdir()
        c = Script([("", [], 10)])
        orig = c.chat
        c.chat = lambda **kw: (lambda r: (setattr(r, "reasoning", "thinking..."), r)[1])(orig(**kw))
        Agent(c, "m", Workspace(d), trajectory=Trajectory(d / "run"), log_reasoning=flag).run("t")
        mc = [e for e in events(d / "run") if e["event"] == "model_call"][0]
        assert ("reasoning" in mc) == flag
        assert not flag or mc["reasoning"] == "thinking..."


# ------------------------------------------------------------------ trajectory replay
def compaction_run(root, name):
    """Same scenario as the loop's compaction test: elide, then summarise."""
    ws = root / name
    ws.mkdir()
    (ws / "big.txt").write_text("x" * 5000)
    steps = [("", [call(str(i), "read_file", path="big.txt")], 10) for i in range(6)]
    steps.append(("", [call("7", "read_file", path="big.txt")], 90_000))
    steps += [("SUMMARY", [], 5), ("fin", [], 20)]
    return ws, steps


def make_agent(client, ws, d):
    return Agent(client, "m", Workspace(ws), trajectory=Trajectory(d), keep_recent=2, context_limit=1000, max_steps=20)


def test_replay_of_a_run_with_compaction_is_identical(tmp_path):
    ws, steps = compaction_run(tmp_path, "orig")
    make_agent(Script(steps), ws, tmp_path / "t1").run("task")
    old = events(tmp_path / "t1")
    assert [e["kind"] for e in old if e["event"] == "compaction"] == ["elide", "summary"]

    ws2, _ = compaction_run(tmp_path, "again")
    client = TrajectoryReplayClient(old)
    make_agent(client, ws2, tmp_path / "t2").run("task")
    assert client.remaining == 0
    assert signature(events(tmp_path / "t2")) == signature(old)


def test_replay_detects_a_loop_that_behaves_differently(tmp_path):
    ws, steps = compaction_run(tmp_path, "orig")
    make_agent(Script(steps), ws, tmp_path / "t1").run("task")
    old = events(tmp_path / "t1")
    ws2, _ = compaction_run(tmp_path, "again")
    # a loop with a different context limit never compacts: it asks for a main answer where a summary is recorded
    Agent(TrajectoryReplayClient(old), "m", Workspace(ws2), trajectory=Trajectory(tmp_path / "t2"), keep_recent=2,
          context_limit=10_000_000, max_steps=20).run("task")
    new = events(tmp_path / "t2")
    assert signature(new) != signature(old)
    assert [e for e in new if e["event"] == "run_end"][0]["status"] == "error"        # ReplayMiss surfaced, not hidden


def test_replay_client_ran_out_and_out_of_step_errors():
    ev = [{"event": "model_call", "step": 1, "text": "a", "tool_calls": [], "finish_reason": "stop", "usage": usage()}]
    c = TrajectoryReplayClient(ev)
    with pytest.raises(ReplayMiss):
        c.chat(model="m", messages=[], system=None)              # a summary request, but a main answer is next
    assert c.chat(model="m", messages=[], system="s").text == "a"
    with pytest.raises(ReplayMiss):
        c.chat(model="m", messages=[], system="s")


def test_unparseable_arguments_are_replayed_as_the_raw_string():
    ev = [{"event": "model_call", "step": 1, "text": "", "finish_reason": "tool_calls", "usage": usage(),
           "tool_calls": [{"id": "1", "name": "read_file", "input": {"_raw_arguments": "{not json"}}]}]
    r = TrajectoryReplayClient(ev).chat(model="m", messages=[], system="s")
    assert r.tool_calls[0].arguments == "{not json"


def test_replay_run_end_to_end(tmp_path):
    root = tmp_path / "tasks"
    d = root / "t1"
    (d / "repo").mkdir(parents=True)
    (d / "repo" / "m.py").write_text("def f():\n    return 1\n")
    (d / "repo" / "test_m.py").write_text("from m import f\n\ndef test_f():\n    assert f() == 2\n")
    (d / "task.json").write_text(json.dumps({"prompt": "make f return 2", "test_cmd": "python -m pytest -q"}))
    task = load_tasks(root)[0]
    script = [("", [call("1", "edit_file", path="m.py", old_string="return 1", new_string="return 2")], 100),
              ("", [call("2", "bash", command="python -m pytest -q")], 120), ("done", [], 140)]
    cfg = {"name": "t", "model": "m", "temperature": 0.0, "max_steps": 5}
    rec = run_one(task, cfg, 0, tmp_path / "out", Script(script))
    assert rec["passed"]

    r = replay_run(rec["trajectory"], root)
    assert r["status"] == "ok", r

    d.joinpath("repo", "m.py").write_text("def f():\n    return 1  # changed\n")        # the task changes after recording
    assert replay_run(rec["trajectory"], root)["status"] == "skipped"


def test_replay_restores_tool_call_extras():
    ev = [{"event": "model_call", "step": 1, "text": "", "finish_reason": "tool_calls", "usage": usage(),
           "tool_calls": [{"id": "1", "name": "bash", "input": {"command": "ls"}, "extra": {"thought_signature": "SIG"}}]}]
    assert TrajectoryReplayClient(ev).chat(model="m", messages=[], system="s").tool_calls[0].extra == {"thought_signature": "SIG"}


def test_signature_separates_compaction_behaviour():
    base = [{"event": "run_end", "status": "done", "steps": 3}]
    summary = {"event": "compaction", "kind": "summary"}
    assert signature([summary] + base) != signature(base)
    assert signature([summary] + base) != signature([{"event": "compaction", "kind": "elide"}] + base)
    assert signature([{**summary, "ts": 1, "summary": "text A"}] + base) == signature([{**summary, "ts": 2, "summary": "text B"}] + base)


def test_an_interrupted_recording_is_skipped_not_reported_as_a_difference(tmp_path):
    p = tmp_path / "trajectory.jsonl"
    p.write_text(json.dumps({"event": "run_start", "task": "t", "model": "m", "config": {"tools": []}, "meta": {}}) + "\n")
    r = replay_run(p, tmp_path)
    assert r["status"] == "skipped" and "interrupted" in r["reason"]
