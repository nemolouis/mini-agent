"""The viewer server: listing, serving trajectories, and refusing anything outside the given directories."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from miniagent.eval.view import make_server


def get(url, host=None):
    req = urllib.request.Request(url)
    if host:
        req.add_header("Host", host)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


@pytest.fixture
def server(tmp_path):
    res = tmp_path / "res"
    (res / "trajectories" / "t1__r0").mkdir(parents=True)
    (res / "trajectories" / "t1__r0" / "trajectory.jsonl").write_text('{"event": "run_start"}\n{"event": "run_end", "status": "done"}\n')
    rec = {"task_id": "t1", "repeat": 0, "passed": True, "failure_class": "pass", "steps": 3, "uncached_input_tokens": 6,
           "output_tokens": 5, "cache_read_tokens": 4, "cache_creation_tokens": 0, "wall_s": 1.5, "compactions": 0, "trajectory": str(res / "trajectories" / "t1__r0" / "trajectory.jsonl")}
    (res / "runs.jsonl").write_text(json.dumps(rec) + "\n")
    (res / "meta.json").write_text(json.dumps({"config": {"name": "c", "model": "m"}, "split": "dev", "date": "d"}))
    (tmp_path / "secret.txt").write_text("do not serve")
    runs = tmp_path / "runs"
    (runs / "20260101-000000").mkdir(parents=True)
    (runs / "20260101-000000" / "trajectory.jsonl").write_text('{"event": "run_start"}\n{"event": "run_end", "status": "max_steps", "steps": 7}\n')
    httpd = make_server([res, runs], port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_page_and_sources(server):
    code, body = get(server + "/")
    assert code == 200 and b"<title>miniagent trajectory viewer</title>" in body
    code, body = get(server + "/api/sources")
    srcs = json.loads(body)
    assert [s["kind"] for s in srcs] == ["results", "runs"] and srcs[0]["meta"]["config"] == "c" and srcs[0]["n"] == 1


def test_runs_listing_and_trajectory(server):
    runs = json.loads(get(server + "/api/runs?source=res")[1])
    assert runs[0]["id"] == "t1__r0" and runs[0]["passed"] is True and "trajectory" not in runs[0]   # no server paths leaked
    assert runs[0]["input_tokens"] == 10                                  # uncached 6 + cache read 4
    code, body = get(server + "/api/traj?source=res&id=t1__r0")
    assert code == 200 and body.startswith(b'{"event": "run_start"}')
    plain = json.loads(get(server + "/api/runs?source=runs")[1])
    assert plain[0]["failure_class"] == "max_steps" and plain[0]["steps"] == 7
    assert get(server + "/api/traj?source=runs&id=20260101-000000")[0] == 200


@pytest.mark.parametrize("bad", ["..", "../..", "../secret.txt", "t1__r0/../../secret.txt", "%2e%2e%2f", "a/b", ".", ""])
def test_path_traversal_is_refused(server, bad):
    assert get(server + "/api/traj?source=res&id=" + bad)[0] == 404


def test_unknown_source_and_paths_and_foreign_host(server):
    assert get(server + "/api/runs?source=nope")[0] == 404
    assert get(server + "/api/traj?source=nope&id=x")[0] == 404
    assert get(server + "/etc/passwd")[0] == 404
    assert get(server + "/api/sources", host="evil.example")[0] == 403          # DNS-rebinding guard
