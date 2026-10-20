"""SFT export tests (no network)."""
import json

from miniagent.agent import SYSTEM_PROMPT
from miniagent.client import ModelResponse, ToolCall
from miniagent.eval.export import _well_formed, build_messages, export_sft
from miniagent.eval.runner import run_one
from miniagent.eval.tasks import load_tasks


def call(i, name, **inp): return ToolCall(i, name, json.dumps(inp))


class Script:
    def __init__(self, script): self.script = list(script)

    def chat(self, **kw):
        text, calls, tok = self.script.pop(0)
        return ModelResponse(text, calls, "tool_calls" if calls else "stop",
                             {"input_tokens": tok, "output_tokens": 5, "cache_hit_tokens": 0}, model="fake")


EDIT = ("", [call("1", "edit_file", path="m.py", old_string="return 1", new_string="return 2")], 100)
GOOD = [EDIT, ("all fixed", [], 120)]
CFG = {"name": "t", "model": "fake", "temperature": 0.0, "max_steps": 5}


def make_task(root, name="t1"):
    d = root / name
    (d / "repo").mkdir(parents=True)
    (d / "repo" / "m.py").write_text("def f():\n    return 1\n")
    (d / "repo" / "test_m.py").write_text("from m import f\n\ndef test_f():\n    assert f() == 2\n")
    (d / "task.json").write_text(json.dumps({"prompt": "make f return 2", "test_cmd": "python -m pytest -q"}))
    return [t for t in load_tasks(root) if t.id == name][0]


def results(tmp_path, runs, split="train", cfg=CFG, name="res"):
    """runs: list of (script, repeat). Returns the results dir with runs.jsonl as the harness writes it."""
    root = tmp_path / "tasks"
    task = make_task(root) if not (root / "t1").exists() else load_tasks(root)[0]
    task.split = split
    out = tmp_path / name
    recs = [run_one(task, cfg, r, out, Script(script)) for script, r in runs]
    (out / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    return out


def rows(path): return [json.loads(l) for l in open(path)]


def test_a_passing_run_becomes_a_well_formed_example(tmp_path):
    out = results(tmp_path, [(GOOD, 0)])
    stats = export_sft([out], tmp_path / "sft.jsonl")
    (ex,) = rows(tmp_path / "sft.jsonl")
    assert stats["kept"] == 1 and stats["skipped"] == {}
    roles = [m["role"] for m in ex["messages"]]
    assert roles == ["system", "user", "assistant", "tool", "assistant"]
    assert ex["messages"][0]["content"] == SYSTEM_PROMPT and ex["messages"][1]["content"] == "make f return 2"
    tc = ex["messages"][2]["tool_calls"][0]
    assert tc["function"]["name"] == "edit_file" and json.loads(tc["function"]["arguments"])["path"] == "m.py"
    assert ex["messages"][3]["tool_call_id"] == tc["id"] and ex["messages"][4] == {"role": "assistant", "content": "all fixed"}
    assert {t["function"]["name"] for t in ex["tools"]} == {"read_file", "write_file", "edit_file", "bash", "grep"}
    assert ex["meta"]["system_logged"] and ex["meta"]["tools_logged"]


def test_runs_that_must_not_be_training_data_are_skipped_with_a_reason(tmp_path):
    bad_edit = ("", [call("1", "edit_file", path="m.py", old_string="return 1", new_string="return 3")], 100)
    cheat = ("", [call("2", "write_file", path="test_m.py", content="def test_f():\n    assert True\n")], 100)
    loop = [("", [call(str(i), "grep", pattern="a")], 10) for i in range(5)]
    out = results(tmp_path, [([bad_edit, ("done", [], 1)], 0), ([EDIT, cheat, ("done", [], 1)], 1), (loop, 2),
                             ([("I changed nothing", [], 1)], 3), (GOOD, 4)])
    stats = export_sft([out], tmp_path / "sft.jsonl")
    assert stats["kept"] == 1
    assert stats["skipped"]["not_passed"] == 3          # the wrong fix, the run that ran out of steps, the one that changed nothing
    assert stats["skipped"]["touched_tests"] == 1


def test_a_run_that_passed_but_ran_out_of_steps_is_skipped(tmp_path):
    fix_then_loop = [EDIT] + [("", [call(str(i + 2), "grep", pattern="a")], 10) for i in range(5)]
    out = results(tmp_path, [(fix_then_loop, 0)])
    stats = export_sft([out], tmp_path / "sft.jsonl")
    assert stats["kept"] == 0 and stats["skipped"] == {"did_not_finish_by_itself": 1}


def test_only_the_train_split_is_exported_unless_asked(tmp_path):
    for split in ("test", "dev", None):
        out = results(tmp_path, [(GOOD, 0)], split=split, name=f"res_{split}")
        skipped = export_sft([out], tmp_path / f"a_{split}.jsonl")["skipped"]
        assert skipped == {f"split_{split or 'none'}_not_exported": 1}
        assert export_sft([out], tmp_path / f"b_{split}.jsonl", splits={split or "none"})["kept"] == 1


def test_compacted_runs_are_skipped(tmp_path):
    big = [("", [call(str(i), "read_file", path="m.py")], 10) for i in range(6)]
    big.append(("", [call("7", "read_file", path="m.py")], 90_000))
    big += [("SUMMARY", [], 5), ("", [call("9", "edit_file", path="m.py", old_string="return 1", new_string="return 2")], 20), ("fin", [], 20)]
    out = results(tmp_path, [(big, 0)], cfg={**CFG, "context_limit": 1000, "keep_recent": 2, "max_steps": 20})
    stats = export_sft([out], tmp_path / "sft.jsonl")
    assert stats["skipped"] == {"compacted": 1}


def test_duplicates_and_model_filter(tmp_path):
    out = results(tmp_path, [(GOOD, 0), (GOOD, 1)])
    stats = export_sft([out], tmp_path / "sft.jsonl")
    assert stats["kept"] == 1 and stats["skipped"] == {"duplicate": 1}
    assert export_sft([out], tmp_path / "o.jsonl", models={"someone-else"})["skipped"] == {"other_model": 2}


def test_invalid_tool_arguments_are_skipped(tmp_path):
    bad = ("", [ToolCall("0", "read_file", "{not json")], 10)
    out = results(tmp_path, [([bad] + GOOD, 0)])
    assert export_sft([out], tmp_path / "sft.jsonl")["skipped"] == {"invalid_tool_arguments": 1}


def test_old_trajectories_without_logged_system_resolve_by_hash(tmp_path):
    out = results(tmp_path, [(GOOD, 0)])
    traj = next(out.glob("trajectories/*/trajectory.jsonl"))
    ev = [json.loads(l) for l in traj.read_text().splitlines()]
    ev[0].pop("system"); ev[0].pop("tool_specs")                                  # the format before this change
    traj.write_text("".join(json.dumps(e) + "\n" for e in ev))
    export_sft([out], tmp_path / "sft.jsonl")
    (ex,) = rows(tmp_path / "sft.jsonl")
    assert ex["messages"][0]["content"] == SYSTEM_PROMPT and len(ex["tools"]) == 5
    assert not ex["meta"]["system_logged"] and not ex["meta"]["tools_logged"]
    ev[0]["config"]["system_sha1"] = "000000000000"                               # a prompt we cannot identify
    traj.write_text("".join(json.dumps(e) + "\n" for e in ev))
    assert export_sft([out], tmp_path / "x.jsonl")["skipped"] == {"unknown_system_prompt": 1}


def test_reasoning_is_included_only_on_request():
    ev = [{"event": "run_start", "task": "t"},
          {"event": "model_call", "step": 1, "text": "ok", "tool_calls": [], "reasoning": "hmm"}]
    assert "reasoning_content" not in build_messages(ev)[1]
    assert build_messages(ev, with_reasoning=True)[1]["reasoning_content"] == "hmm"


def test_well_formed_checks_call_result_pairing_and_the_ending():
    sysm, user = {"role": "system", "content": "s"}, {"role": "user", "content": "t"}
    tc = {"role": "assistant", "content": None, "tool_calls": [{"id": "1", "type": "function", "function": {"name": "bash", "arguments": "{}"}}]}
    res, end = {"role": "tool", "tool_call_id": "1", "content": "ok"}, {"role": "assistant", "content": "done"}
    assert _well_formed([sysm, user, tc, res, end])
    assert not _well_formed([sysm, user, tc, end])                                 # call never answered
    assert not _well_formed([sysm, user, tc, {**res, "tool_call_id": "9"}, end])   # answer to a call that was not made
    assert not _well_formed([sysm, user, tc, res])                                 # ends on a tool message
    assert not _well_formed([sysm, user, tc, res, tc])                             # ends on a tool call


def test_export_skips_a_trajectory_whose_log_is_missing_a_tool_result(tmp_path):
    out = results(tmp_path, [(GOOD, 0)])
    traj = next(out.glob("trajectories/*/trajectory.jsonl"))
    ev = [json.loads(l) for l in traj.read_text().splitlines() if '"tool_result"' not in l]
    traj.write_text("".join(json.dumps(e) + "\n" for e in ev))
    assert export_sft([out], tmp_path / "sft.jsonl")["skipped"] == {"malformed_transcript": 1}
