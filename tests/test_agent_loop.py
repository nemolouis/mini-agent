"""Loop tests with a scripted fake client (no network)."""
import copy
import json

from miniagent.agent import Agent
from miniagent.client import ModelResponse, ToolCall
from miniagent.tools import Workspace
from miniagent.trajectory import Trajectory


def text(t): return t
def call(i, name, **inp): return ToolCall(i, name, json.dumps(inp))


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def chat(self, **kw):
        self.calls.append(copy.deepcopy(kw))
        content, stop, tok = self.script.pop(0)
        calls = [c for c in content if isinstance(c, ToolCall)]
        txt = "".join(c for c in content if isinstance(c, str))
        finish = "tool_calls" if stop == "tool_use" else "stop"
        return ModelResponse(txt, calls, finish, {"input_tokens": tok, "output_tokens": 10, "cache_hit_tokens": 0})


def make(tmp_path, script, **kw):
    return Agent(FakeClient(script), "fake", Workspace(tmp_path),
                 trajectory=Trajectory(tmp_path / "run"), **kw)


def events(tmp_path):
    return [json.loads(l) for l in (tmp_path / "run" / "trajectory.jsonl").read_text().splitlines()]


def test_tool_then_done(tmp_path):
    (tmp_path / "f.txt").write_text("hello\n")
    a = make(tmp_path, [([call("1", "read_file", path="f.txt")], "tool_use", 100), ([text("done")], "end_turn", 150)])
    r = a.run("look")
    assert r.status == "done" and r.steps == 2 and r.final_text == "done"
    second_input = a.client.calls[1]["messages"]
    assert second_input[-1]["role"] == "tool" and second_input[-1]["tool_call_id"] == "1"
    assert second_input[-2]["tool_calls"][0]["function"]["name"] == "read_file"
    assert [e["event"] for e in events(tmp_path)] == ["run_start", "model_call", "tool_result", "model_call", "run_end"]


def test_max_steps(tmp_path):
    loop = ([call("x", "grep", pattern="a")], "tool_use", 10)
    r = make(tmp_path, [loop] * 3, max_steps=3).run("t")
    assert r.status == "max_steps" and r.steps == 3


def test_denied_and_unknown_tool(tmp_path):
    a = make(tmp_path, [([call("1", "bash", command="ls"), call("2", "nope")], "tool_use", 10), ([text("ok")], "end_turn", 10)],
             confirm=lambda n, args: False)
    a.run("t")
    results = a.client.calls[1]["messages"][-2:]
    assert all(r["role"] == "tool" for r in results)
    assert all(e["is_error"] for e in events(tmp_path) if e["event"] == "tool_result")
    assert "denied" in results[0]["content"] and "unknown tool" in results[1]["content"]


def test_dangerous_command_blocked_even_when_approved(tmp_path):
    a = make(tmp_path, [([call("1", "bash", command="sudo rm -rf /")], "tool_use", 10), ([text("ok")], "end_turn", 10)])
    a.run("t")
    assert "blocked by safety policy" in a.client.calls[1]["messages"][-1]["content"]


def test_invalid_json_arguments_reported_to_model(tmp_path):
    bad = ToolCall("1", "read_file", "{not json")
    a = make(tmp_path, [([bad], "tool_use", 10), ([text("ok")], "end_turn", 10)])
    assert a.run("t").status == "done"
    assert "not valid JSON" in a.client.calls[1]["messages"][-1]["content"]


def test_compaction_elides_then_summarises(tmp_path):
    big = "x" * 5000
    (tmp_path / "big.txt").write_text(big)
    steps = [([call(str(i), "read_file", path="big.txt")], "tool_use", 10) for i in range(6)]
    # step 7: reported input tokens exceed 70% of limit -> compaction before the next call
    steps.append(([call("7", "read_file", path="big.txt")], "tool_use", 90_000))
    summary = ([text("SUMMARY")], "end_turn", 5)  # consumed by the summary call
    steps += [summary, ([text("fin")], "end_turn", 20)]
    a = make(tmp_path, steps, keep_recent=2, context_limit=1000, max_steps=20)
    r = a.run("task")
    assert r.status == "done"
    kinds = [e["kind"] for e in events(tmp_path) if e["event"] == "compaction"]
    assert kinds == ["elide", "summary"]
    final_msgs = a.client.calls[-1]["messages"]
    assert "SUMMARY" in final_msgs[0]["content"] and final_msgs[1]["role"] == "assistant"
    roles = [m["role"] for m in final_msgs]
    assert all(roles[i] != roles[i + 1] for i in range(len(roles) - 1))


def test_summary_sees_unelided_tool_output(tmp_path):
    (tmp_path / "f.txt").write_text("SECRET_MARKER " + "y" * 600)
    steps = [([call(str(i), "read_file", path="f.txt")], "tool_use", 10) for i in range(5)]
    steps += [([call("9", "read_file", path="f.txt")], "tool_use", 90_000), ([text("S")], "end_turn", 5), ([text("fin")], "end_turn", 5)]
    a = make(tmp_path, steps, keep_recent=2, context_limit=1000, max_steps=20)
    a.run("the original task")
    summary_call = [c for c in a.client.calls if "<transcript>" in str(c["messages"][0]["content"])][0]
    prompt = summary_call["messages"][0]["content"]
    assert "SECRET_MARKER" in prompt and "the original task" in prompt


# ---------------------------------------------------------------- compaction hysteresis (failure case 2)
class SizedClient:
    """Reports input tokens like a real API: a fixed prompt (system + tool definitions) plus the history size."""

    def __init__(self, fixed, steps):
        self.fixed, self.steps, self.calls = fixed, steps, 0

    def chat(self, **kw):
        self.calls += 1
        if not kw.get("tools"):                                  # the summarisation request
            return ModelResponse("SUMMARY of earlier work", [], "stop", {"input_tokens": 200, "output_tokens": 20, "cache_hit_tokens": 0})
        used = self.fixed + len(json.dumps(kw["messages"])) // 3
        if self.steps:
            return ModelResponse("", [self.steps.pop(0)], "tool_calls", {"input_tokens": used, "output_tokens": 10, "cache_hit_tokens": 0})
        return ModelResponse("done", [], "stop", {"input_tokens": used, "output_tokens": 10, "cache_hit_tokens": 0})


def thrash_run(tmp_path, n_steps=24, file_chars=2400, **agent_kw):
    """Heavy recent window: each tool output (about file_chars/3 tokens) stays verbatim for the last keep_recent messages."""
    (tmp_path / "f.txt").write_text("y" * file_chars)
    steps = [call(str(i), "read_file", path="f.txt") for i in range(n_steps)]
    a = Agent(SizedClient(fixed=2000, steps=steps), "fake", Workspace(tmp_path), trajectory=Trajectory(tmp_path / "run"),
              context_limit=3000, keep_recent=4, max_steps=n_steps + 2, **agent_kw)
    r = a.run("task")
    summaries = sum(1 for e in events(tmp_path) if e["event"] == "compaction" and e["kind"] == "summary")
    return r, summaries


def old_trigger(self, floor):
    """The trigger before the fix: always 70% of the limit, whatever the previous compaction achieved."""
    return self.context_limit * 0.7


def test_the_old_trigger_thrashes_when_compaction_cannot_reach_the_threshold(tmp_path, monkeypatch):
    """Documents failure case 2: prompt + tools (2000 tokens) plus two verbatim ~800-token tool outputs are above 70% of a
    3000-token limit, so a compacted history is still 'too big' and the old loop re-summarised on almost every step."""
    monkeypatch.setattr(Agent, "_compact_trigger", old_trigger)
    r, summaries = thrash_run(tmp_path)
    assert r.status == "done" and summaries >= 18, summaries


def test_compaction_waits_for_regrowth_when_it_cannot_reach_the_threshold(tmp_path):
    r, summaries = thrash_run(tmp_path)
    assert r.status == "done" and r.steps == 25
    assert summaries <= 4, f"{summaries} summary compactions in 25 steps: still thrashing"
    ev = events(tmp_path)
    floors = [e for e in ev if e["event"] == "compaction_floor"]
    assert floors and floors[0]["input_tokens"] >= floors[0]["threshold"] and floors[0]["next_trigger"] > floors[0]["input_tokens"]
    summaries_ev = [e for e in ev if e["event"] == "compaction" and e["kind"] == "summary"]
    assert all(e["trigger_input_tokens"] > 2100 for e in summaries_ev)           # the trigger input is recorded


def test_more_regrowth_means_fewer_compactions(tmp_path):
    counts = []
    for i, g in enumerate((0.5, 1.0, 2.0)):
        d = tmp_path / f"g{i}"
        d.mkdir()
        counts.append(thrash_run(d, compact_regrowth=g)[1])
    assert counts[0] >= counts[1] >= counts[2] and counts[0] > counts[2]


def test_when_compaction_works_the_trigger_is_unchanged(tmp_path, monkeypatch):
    """A feasible limit (history can be brought well below 70%): old and new triggers give identical behaviour."""
    def run(d, old):
        if old:
            monkeypatch.setattr(Agent, "_compact_trigger", old_trigger)
        (d / "f.txt").write_text("y" * 2400)
        steps = [call(str(i), "read_file", path="f.txt") for i in range(30)]
        a = Agent(SizedClient(fixed=300, steps=steps), "fake", Workspace(d), trajectory=Trajectory(d / "run"),
                  context_limit=4000, keep_recent=4, max_steps=40)
        a.run("task")
        monkeypatch.undo()
        return [(e["kind"], e["trigger_input_tokens"]) for e in events(d) if e["event"] == "compaction"]
    new_dir, old_dir = tmp_path / "new", tmp_path / "old"
    new_dir.mkdir(); old_dir.mkdir()
    new, old = run(new_dir, False), run(old_dir, True)
    assert new == old and any(k == "summary" for k, _ in new)
    assert not [e for e in events(new_dir) if e["event"] == "compaction_floor"]      # compaction always got below the threshold


def test_compact_trigger_rule():
    a = Agent(SizedClient(0, []), "fake", Workspace("."), context_limit=10_000, compact_regrowth=0.5)
    assert a._compact_trigger(None) == 7000
    assert a._compact_trigger(3000) == 7000 and a._compact_trigger(6999) == 7000      # last compaction worked
    assert a._compact_trigger(7000) == 10_500 and a._compact_trigger(9000) == 13_500    # it did not: wait for 50% growth


def test_an_empty_summary_does_not_delete_the_history(tmp_path):
    class EmptySummary(SizedClient):
        last_messages = None

        def chat(self, **kw):
            if not kw.get("tools"):
                self.calls += 1
                return ModelResponse("", [], "length", {"input_tokens": 200, "output_tokens": 1500, "cache_hit_tokens": 0})
            self.last_messages = copy.deepcopy(kw["messages"])        # not a reference: the loop appends to it later
            return super().chat(**kw)

    (tmp_path / "f.txt").write_text("y" * 2400)
    steps = [call(str(i), "read_file", path="f.txt") for i in range(8)]
    client = EmptySummary(fixed=2000, steps=steps)
    a = Agent(client, "fake", Workspace(tmp_path), trajectory=Trajectory(tmp_path / "run"),
              context_limit=3000, keep_recent=4, max_steps=12)
    r = a.run("the original task")
    assert r.status == "done" and r.steps == 9
    kinds = [e["kind"] for e in events(tmp_path) if e["event"] == "compaction"]
    assert "summary_failed" in kinds and "summary" not in kinds
    last = client.last_messages
    assert last[0] == {"role": "user", "content": "the original task"}            # no empty "progress summary" was spliced in
    assert sum(m["role"] == "assistant" for m in last) == 8                        # every earlier turn is still there
