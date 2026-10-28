"""HTTP service tests: a scripted fake model, FastAPI's TestClient, no network and no Docker."""
import json
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from miniagent.client import ModelResponse, ToolCall  # noqa: E402
from miniagent.server import Service, create_app, main  # noqa: E402


def call(i, name, **inp):
    return ToolCall(i, name, json.dumps(inp))


class Script:
    """A fake model: each chat() pops the next (text, tool_calls) step; `gate` can hold the first reply."""

    def __init__(self, steps, gate=None):
        self.steps, self.gate = list(steps), gate

    def chat(self, **kw):
        if self.gate is not None:
            self.gate.wait(10)
        text, calls = self.steps.pop(0)
        return ModelResponse(text, calls, "tool_calls" if calls else "stop",
                             {"input_tokens": 100, "output_tokens": 10, "cache_hit_tokens": 0})


EDIT_THEN_DONE = [("", [call("1", "edit_file", path="a.py", old_string="x = 1", new_string="x = 2")]), ("fixed", [])]


@pytest.fixture
def ws(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / "a.py").write_text("x = 1\n")
    return d


def make(tmp_path, ws, steps=EDIT_THEN_DONE, api_key=None, **kw):
    svc = Service({"demo": ws}, lambda: Script(steps), tmp_path / "runs", sandbox=kw.pop("sandbox", False), **kw)
    return svc, TestClient(create_app(svc, api_key))


def wait(client, rid, headers=None):
    for _ in range(200):
        r = client.get(f"/runs/{rid}", headers=headers).json()
        if r["status"] in ("done", "max_steps", "length", "error"):
            return r
        time.sleep(0.02)
    raise AssertionError("run did not finish")


def start(client, **body):
    r = client.post("/runs", json={"task": "fix it", "workspace": "demo", **body})
    return r


def test_run_edits_a_copy_and_reports_the_patch(tmp_path, ws):
    svc, c = make(tmp_path, ws)
    r = start(c)
    assert r.status_code == 202
    rid = r.json()["run_id"]
    res = wait(c, rid)
    assert res["status"] == "done" and res["result"]["final_text"] == "fixed" and res["changed_files"] == ["a.py"]
    assert (ws / "a.py").read_text() == "x = 1\n"                      # the original is never touched
    assert not (tmp_path / "runs" / rid / "work").exists()               # the working copy is removed
    patch = c.get(f"/runs/{rid}/patch").text
    assert "-x = 1" in patch and "+x = 2" in patch
    ev = c.get(f"/runs/{rid}/events").json()["events"]
    assert [e["event"] for e in ev] == ["run_start", "model_call", "tool_result", "model_call", "run_end"]
    assert "system" not in ev[0] and "tool_specs" not in ev[0]
    assert c.get(f"/runs/{rid}/events?after=3").json()["events"][0]["index"] == 3


def test_stream_ends_with_an_end_event(tmp_path, ws):
    svc, c = make(tmp_path, ws)
    rid = start(c).json()["run_id"]
    text = c.get(f"/runs/{rid}/stream").text
    assert text.count("data: ") >= 6 and text.rstrip().endswith('data: {"status": "done"}') and "event: end" in text


@pytest.mark.parametrize("body,code", [
    ({"workspace": "../etc"}, 404), ({"workspace": "/etc"}, 404), ({"model": "gpt-x"}, 400),
    ({"max_steps": 61}, 422), ({"max_steps": 0}, 422), ({"task": ""}, 422), ({"task": "x" * 20001}, 422),
])
def test_bad_requests_are_rejected(tmp_path, ws, body, code):
    svc, c = make(tmp_path, ws)
    assert start(c, **body).status_code == code


def test_unknown_run_is_404(tmp_path, ws):
    svc, c = make(tmp_path, ws)
    assert c.get("/runs/nope").status_code == 404 and c.get("/runs/nope/events").status_code == 404


def test_api_key(tmp_path, ws):
    svc, c = make(tmp_path, ws, api_key="s3cret")
    assert c.get("/healthz").status_code == 200
    assert start(c).status_code == 401
    assert c.post("/runs", json={"task": "t", "workspace": "demo"}, headers={"X-API-Key": "wrong"}).status_code == 401
    ok = c.post("/runs", json={"task": "t", "workspace": "demo"}, headers={"X-API-Key": "s3cret"})
    assert ok.status_code == 202
    assert c.get(f"/runs/{ok.json()['run_id']}").status_code == 401


def test_bash_is_refused_without_the_sandbox(tmp_path, ws):
    steps = [("", [call("1", "bash", command="echo hi > pwned.txt")]), ("ok", [])]
    svc, c = make(tmp_path, ws, steps=steps)
    rid = start(c).json()["run_id"]
    assert wait(c, rid)["status"] == "done"
    tr = [e for e in c.get(f"/runs/{rid}/events").json()["events"] if e["event"] == "tool_result"][0]
    assert tr["is_error"] and "denied" in tr["output"]
    assert not (ws / "pwned.txt").exists() and wait(c, rid)["changed_files"] == []


def test_with_the_sandbox_bash_goes_to_the_container(tmp_path, ws):
    seen = []

    class FakeSandbox:
        def exec(self, cmd, timeout=60):
            seen.append(cmd)
            return SimpleNamespace(returncode=0, stdout="hi\n", stderr="", timed_out=False)

    @contextmanager
    def factory(work):
        assert (work / "a.py").is_file()                                # it is handed the copy, not the original
        yield FakeSandbox()

    steps = [("", [call("1", "bash", command="echo hi")]), ("ok", [])]
    svc, c = make(tmp_path, ws, steps=steps, sandbox=True, sandbox_factory=factory)
    rid = start(c).json()["run_id"]
    assert wait(c, rid)["status"] == "done" and seen == ["echo hi"]


def test_an_infrastructure_fault_ends_that_run_only(tmp_path, ws):
    def broken():
        raise RuntimeError("boom")

    svc = Service({"demo": ws}, broken, tmp_path / "runs", sandbox=False)
    c = TestClient(create_app(svc))
    rid = start(c).json()["run_id"]
    r = wait(c, rid)
    assert r["status"] == "error" and "boom" in r["error"]
    assert c.get("/healthz").status_code == 200


def test_queue_is_capped(tmp_path, ws):
    gate = threading.Event()
    svc = Service({"demo": ws}, lambda: Script(EDIT_THEN_DONE, gate), tmp_path / "runs", sandbox=False, max_pending=1)
    c = TestClient(create_app(svc))
    first = start(c)
    assert first.status_code == 202 and start(c).status_code == 429
    gate.set()
    wait(c, first.json()["run_id"])
    assert start(c).status_code == 202


def test_patch_before_the_run_finishes_is_409(tmp_path, ws):
    gate = threading.Event()
    svc = Service({"demo": ws}, lambda: Script(EDIT_THEN_DONE, gate), tmp_path / "runs", sandbox=False)
    c = TestClient(create_app(svc))
    rid = start(c).json()["run_id"]
    assert c.get(f"/runs/{rid}/patch").status_code == 409
    gate.set()
    wait(c, rid)


def test_a_workspace_that_does_not_exist_is_refused_at_startup(tmp_path):
    with pytest.raises(ValueError):
        Service({"x": tmp_path / "missing"}, lambda: None, tmp_path / "runs")


def test_cli_refuses_a_public_host_without_a_key(tmp_path, ws, monkeypatch, capsys):
    monkeypatch.delenv("MINIAGENT_API_KEY", raising=False)
    assert main(["--workspace", f"demo={ws}", "--host", "0.0.0.0", "--no-sandbox"]) == 2
    assert "MINIAGENT_API_KEY" in capsys.readouterr().err
    assert main(["--workspace", "demo=" + str(tmp_path / "missing"), "--no-sandbox"]) == 2
