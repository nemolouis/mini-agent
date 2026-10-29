"""HTTP service around Agent.run (optional: pip install -e '.[serve]'; the agent itself stays dependency-free).

  POST /runs                 {task, workspace, model?, max_steps?}  -> 202 {run_id}
  GET  /runs/{id}            status, final text, token counts, changed files
  GET  /runs/{id}/events     trajectory events as JSON (?after=N to poll for new ones)
  GET  /runs/{id}/stream     the same events as server-sent events until the run ends
  GET  /runs/{id}/patch      unified diff of what the agent changed
  GET  /healthz
  GET  /                        redirects to /docs, the interactive API page

A service that lets a model run commands is a remote-execution surface, so the defaults are conservative:
- a client never names a path: `workspace` is a key into the allow-list the server was started with, and every run
  works on a private COPY of that directory (the original is never touched);
- bash runs in the Docker sandbox; without it (--no-sandbox) bash is refused and only read/edit tools work;
- it listens on 127.0.0.1, and a non-loopback host is refused unless an API key (MINIAGENT_API_KEY) is set;
- task length, step count, model name and the number of queued runs are capped.
"""
from __future__ import annotations

import argparse
import difflib
import hmac
import json
import os
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Query
    from fastapi.responses import PlainTextResponse, RedirectResponse, StreamingResponse
    from pydantic import BaseModel, Field
except ImportError as e:  # pragma: no cover - only without the optional dependency
    raise ImportError("miniagent.server needs FastAPI: pip install -e '.[serve]'") from e

from .agent import Agent
from .tools import Workspace
from .trajectory import Trajectory

DEFAULT_MODEL = "deepseek-chat"
MAX_TASK_CHARS = 20_000
MAX_STEPS = 60
MAX_PATCH_CHARS = 200_000
FINISHED = {"done", "max_steps", "length", "error"}
HIDDEN_FROM_EVENTS = ("system", "tool_specs")      # large and constant: left out of what the API returns


class RunRequest(BaseModel):
    task: str = Field(min_length=1, max_length=MAX_TASK_CHARS)
    workspace: str = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    max_steps: int = Field(default=30, ge=1, le=MAX_STEPS)


@dataclass
class Run:
    id: str
    task: str
    workspace: str
    model: str
    max_steps: int
    dir: Path
    status: str = "queued"                         # queued | running | done | max_steps | length | error
    created: float = field(default_factory=time.time)
    finished: float | None = None
    result: dict | None = None
    changed_files: list[str] = field(default_factory=list)
    error: str | None = None

    def public(self) -> dict:
        return {"run_id": self.id, "status": self.status, "workspace": self.workspace, "model": self.model,
                "max_steps": self.max_steps, "created": self.created, "finished": self.finished,
                "result": self.result, "changed_files": self.changed_files, "error": self.error}


def _snapshot(root: Path) -> dict[str, bytes]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.relative_to(root).parts and "__pycache__" not in p.parts:
            try:
                out[p.relative_to(root).as_posix()] = p.read_bytes()
            except OSError:
                pass
    return out


def _diff(before: dict[str, bytes], after: dict[str, bytes]) -> tuple[list[str], str]:
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    parts = []
    for k in changed:
        try:
            a = before.get(k, b"").decode("utf-8").splitlines(keepends=True)
            b = after.get(k, b"").decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            parts.append(f"Binary file {k} differs\n")
            continue
        parts.extend(difflib.unified_diff(a, b, f"a/{k}", f"b/{k}"))
    return changed, "".join(parts)[:MAX_PATCH_CHARS]


class Service:
    def __init__(self, workspaces: dict[str, Path], client_factory: Callable[[], object], runs_dir: Path, *,
                 sandbox: bool = True, models: tuple[str, ...] = (DEFAULT_MODEL,), max_concurrent: int = 1,
                 max_pending: int = 20, sandbox_factory: Callable | None = None, agent_kwargs: dict | None = None):
        for name, p in workspaces.items():
            if not Path(p).is_dir():
                raise ValueError(f"workspace {name!r} is not a directory: {p}")
        self.workspaces = {k: Path(v).resolve() for k, v in workspaces.items()}
        self.client_factory, self.runs_dir, self.sandbox, self.models = client_factory, Path(runs_dir), sandbox, models
        self.max_pending, self.agent_kwargs = max_pending, agent_kwargs or {}
        self.sandbox_factory = sandbox_factory
        self.runs: dict[str, Run] = {}
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=max_concurrent, thread_name_prefix="miniagent-run")

    # ---- submit / execute
    def submit(self, req: RunRequest) -> Run:
        if req.workspace not in self.workspaces:
            raise HTTPException(404, f"unknown workspace {req.workspace!r}; available: {sorted(self.workspaces)}")
        model = req.model or self.models[0]
        if model not in self.models:
            raise HTTPException(400, f"model not allowed; allowed: {list(self.models)}")
        with self.lock:
            if sum(r.status in ("queued", "running") for r in self.runs.values()) >= self.max_pending:
                raise HTTPException(429, "too many queued runs")
            rid = uuid.uuid4().hex[:12]
            run = Run(rid, req.task, req.workspace, model, req.max_steps, self.runs_dir / rid)
            self.runs[rid] = run
        self.pool.submit(self._execute, run)
        return run

    def _execute(self, run: Run) -> None:
        run.status = "running"
        work = run.dir / "work"
        try:
            run.dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.workspaces[run.workspace], work)
            before = _snapshot(work)
            if self.sandbox:
                if self.sandbox_factory is not None:
                    sb_ctx = self.sandbox_factory(work)
                else:
                    from .sandbox import Sandbox
                    sb_ctx = Sandbox(work)
            else:
                sb_ctx = nullcontext()
            with sb_ctx as sb:
                agent = Agent(client=self.client_factory(), model=run.model, workspace=Workspace(work, sandbox=sb),
                              confirm=(lambda name, args: True) if self.sandbox else (lambda name, args: name != "bash"),
                              trajectory=Trajectory(run.dir), max_steps=run.max_steps,
                              meta={"run_id": run.id, "workspace": run.workspace}, **self.agent_kwargs)
                res = agent.run(run.task)
            changed, patch = _diff(before, _snapshot(work))
            (run.dir / "patch.diff").write_text(patch, encoding="utf-8")
            run.changed_files = changed
            run.result = {"steps": res.steps, "final_text": res.final_text, "input_tokens": res.input_tokens,
                          "output_tokens": res.output_tokens, "error": res.error}
            run.finished = time.time()
            run.status = res.status if res.status in FINISHED else "error"
        except Exception as e:                       # infrastructure fault: report it, never take the service down
            run.error, run.finished, run.status = f"{type(e).__name__}: {e}", time.time(), "error"
        finally:
            shutil.rmtree(work, ignore_errors=True)

    # ---- read side
    def get(self, rid: str) -> Run:
        run = self.runs.get(rid)
        if run is None:
            raise HTTPException(404, "unknown run")
        return run

    def events(self, run: Run, after: int = 0) -> list[dict]:
        path = run.dir / "trajectory.jsonl"
        if not path.is_file():
            return []
        out = []
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < after or not line.endswith("\n"):          # skip the half-written last line, if any
                    continue
                ev = json.loads(line)
                out.append({"index": i, **{k: v for k, v in ev.items() if k not in HIDDEN_FROM_EVENTS}})
        return out


def create_app(service: Service, api_key: str | None = None) -> FastAPI:
    app = FastAPI(title="mini-agent", version="0.1.0")

    def auth(x_api_key: str | None = Header(default=None)) -> None:
        if api_key and not (x_api_key and hmac.compare_digest(x_api_key.encode(), api_key.encode())):
            raise HTTPException(401, "missing or wrong X-API-Key")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/docs")                  # FastAPI's interactive API page

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "sandbox": service.sandbox, "workspaces": sorted(service.workspaces)}

    @app.post("/runs", status_code=202, dependencies=[Depends(auth)])
    def create_run(req: RunRequest) -> dict:
        run = service.submit(req)
        return {"run_id": run.id, "status": run.status}

    @app.get("/runs/{rid}", dependencies=[Depends(auth)])
    def get_run(rid: str) -> dict:
        return service.get(rid).public()

    @app.get("/runs/{rid}/events", dependencies=[Depends(auth)])
    def get_events(rid: str, after: int = Query(default=0, ge=0)) -> dict:
        run = service.get(rid)
        return {"status": run.status, "events": service.events(run, after)}

    @app.get("/runs/{rid}/patch", dependencies=[Depends(auth)], response_class=PlainTextResponse)
    def get_patch(rid: str) -> str:
        run = service.get(rid)
        p = run.dir / "patch.diff"
        if run.status not in FINISHED or not p.is_file():
            raise HTTPException(409, "run has not finished")
        return p.read_text(encoding="utf-8")

    @app.get("/runs/{rid}/stream", dependencies=[Depends(auth)])
    def stream(rid: str, after: int = Query(default=0, ge=0)) -> StreamingResponse:
        run = service.get(rid)

        def gen():
            nxt, deadline = after, time.time() + 3600
            while time.time() < deadline:
                finished = run.status in FINISHED              # read BEFORE the events: nothing can be missed after it
                for ev in service.events(run, nxt):
                    nxt = ev["index"] + 1
                    yield f"id: {ev['index']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                if finished:
                    yield f"event: end\ndata: {json.dumps({'status': run.status})}\n\n"
                    return
                time.sleep(0.2)

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="miniagent-serve", description="HTTP service around the mini-agent loop")
    ap.add_argument("--workspace", action="append", required=True, metavar="NAME=PATH",
                    help="a directory the service may copy and let the agent work on; repeatable")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--model", action="append", help="allowed model name (repeatable; the first is the default)")
    ap.add_argument("--runs-dir", default="runs-service")
    ap.add_argument("--max-concurrent", type=int, default=1)
    ap.add_argument("--no-sandbox", action="store_true", help="run without Docker: bash is refused, only read/edit tools work")
    args = ap.parse_args(argv)

    api_key = os.environ.get("MINIAGENT_API_KEY") or None
    if args.host not in ("127.0.0.1", "localhost", "::1") and not api_key:
        print("error: a non-loopback host needs MINIAGENT_API_KEY to be set", file=sys.stderr)
        return 2
    workspaces = {}
    for item in args.workspace:
        name, sep, path = item.partition("=")
        if not sep or not name or not Path(path).is_dir():
            print(f"error: --workspace expects NAME=PATH with an existing directory, got {item!r}", file=sys.stderr)
            return 2
        workspaces[name] = Path(path)
    if not args.no_sandbox:
        from .sandbox import available
        if not available():
            print("error: the sandbox image is missing or Docker is not running "
                  "(miniagent-eval sandbox-build), or start with --no-sandbox", file=sys.stderr)
            return 2
    from .client import APIError, ChatClient
    try:
        ChatClient()
    except APIError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    import uvicorn
    service = Service(workspaces, ChatClient, Path(args.runs_dir), sandbox=not args.no_sandbox,
                      models=tuple(args.model or [DEFAULT_MODEL]), max_concurrent=args.max_concurrent)
    uvicorn.run(create_app(service, api_key), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
