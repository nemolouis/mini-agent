"""`miniagent-eval view <dir> [<dir> ...]`: serve the trajectory viewer for results or runs directories.

Security: binds to 127.0.0.1 only, rejects requests whose Host header is not local (DNS rebinding), serves
nothing except the viewer page and `trajectory.jsonl` files that live inside the directories given on the
command line (the trajectory id is validated against a strict pattern and the resolved path must stay inside).
"""
from __future__ import annotations

import json
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .report import load_records

VIEWER = Path(__file__).with_name("viewer") / "index.html"
_ID = re.compile(r"^[A-Za-z0-9_.\-]{1,200}$")
_RUN_FIELDS = ("task_id", "repeat", "attempt", "passed", "failure_class", "steps", "output_tokens",
               "wall_s", "compactions", "last_test_green", "tampered_tests", "tool_errors")


def _read_json_line(path: Path, last: bool) -> dict | None:
    try:
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return json.loads(lines[-1 if last else 0]) if lines else None
    except (OSError, ValueError):
        return None


class Source:
    """One directory: a results dir (runs.jsonl + trajectories/) or a runs dir (<ts>/trajectory.jsonl)."""

    def __init__(self, name: str, root: Path):
        self.name, self.root = name, root.resolve()
        self.kind = "results" if (self.root / "runs.jsonl").exists() else "runs"

    def meta(self) -> dict | None:
        try:
            m = json.loads((self.root / "meta.json").read_text())
            return {"config": m["config"].get("name"), "model": m["config"].get("model"),
                    "split": m.get("split"), "date": m.get("date")}
        except (OSError, ValueError, KeyError):
            return None

    def runs(self) -> list[dict]:
        out = []
        if self.kind == "results":
            for r in load_records(self.root):
                rec = {k: r.get(k) for k in _RUN_FIELDS}
                # records store the input split into uncached / cache-read / cache-creation parts
                rec["input_tokens"] = sum(r.get(k) or 0 for k in ("uncached_input_tokens", "cache_read_tokens", "cache_creation_tokens"))
                rec["id"] = Path(r["trajectory"]).parent.name
                out.append(rec)
            return out
        for d in sorted(p for p in self.root.iterdir() if p.is_dir() and (p / "trajectory.jsonl").exists()):
            start, end = _read_json_line(d / "trajectory.jsonl", False), _read_json_line(d / "trajectory.jsonl", True)
            out.append({"id": d.name, "task_id": d.name, "repeat": None, "passed": None,
                        "failure_class": (end or {}).get("status", "incomplete"), "steps": (end or {}).get("steps"),
                        "input_tokens": (end or {}).get("input_tokens"), "output_tokens": (end or {}).get("output_tokens"),
                        "wall_s": None, "compactions": None, "attempt": None})
        return out

    def trajectory(self, run_id: str) -> Path | None:
        if not _ID.match(run_id):
            return None
        sub = Path("trajectories") / run_id if self.kind == "results" else Path(run_id)
        path = (self.root / sub / "trajectory.jsonl").resolve()
        return path if path.is_file() and path.is_relative_to(self.root) else None


def make_server(dirs: list[Path], port: int = 8765) -> ThreadingHTTPServer:
    sources: dict[str, Source] = {}
    for d in dirs:
        name, i = d.resolve().name, 2
        while name in sources:
            name, i = f"{d.resolve().name}#{i}", i + 1
        sources[name] = Source(name, d)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):          # keep the terminal quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str = "text/plain; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200):
            self._send(code, json.dumps(obj).encode(), "application/json")

        def do_GET(self):
            if (self.headers.get("Host") or "").rsplit(":", 1)[0] not in ("127.0.0.1", "localhost"):
                return self._send(403, b"forbidden host")
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path == "/":
                return self._send(200, VIEWER.read_bytes(), "text/html; charset=utf-8")
            if url.path == "/api/sources":
                return self._json([{"name": n, "kind": s.kind, "meta": s.meta(), "n": len(s.runs())} for n, s in sources.items()])
            src = sources.get(q.get("source", ""))
            if url.path in ("/api/runs", "/api/traj") and src is None:
                return self._send(404, b"unknown source")
            if url.path == "/api/runs":
                return self._json(src.runs())
            if url.path == "/api/traj":
                path = src.trajectory(q.get("id", ""))
                if path is None:
                    return self._send(404, b"unknown trajectory")
                return self._send(200, path.read_bytes())
            return self._send(404, b"not found")

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(dirs: list[Path], port: int = 8765, open_browser: bool = True) -> int:
    for d in dirs:
        if not d.is_dir():
            raise SystemExit(f"not a directory: {d}")
    httpd = make_server(dirs, port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"viewer on {url}  (Ctrl-C to stop)")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
