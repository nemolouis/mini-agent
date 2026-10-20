"""A minimal MCP client over stdio, and the glue that exposes MCP tools to the agent loop.

Lifecycle (per the MCP spec): the client launches the server as a subprocess and exchanges one JSON-RPC
message per line. It first probes with `server/discover` (modern protocol); a modern error such as
-32022 also identifies a modern server, anything else (or silence) means a legacy server and the client
falls back to the `initialize` handshake. Shutdown: close stdin, wait, then SIGTERM, then SIGKILL.
"""
from __future__ import annotations

import json
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager

from ..tools import Tool, ToolError

MODERN_VERSION = "2026-07-28"
LEGACY_VERSION = "2025-11-25"
CLIENT_INFO = {"name": "miniagent", "version": "0.1.0"}
_EOF = object()


class McpError(Exception):
    """Local failure: server not running, timeout, malformed reply, unsupported result type."""


class McpRpcError(McpError):
    def __init__(self, code: int, message: str, data=None):
        super().__init__(f"MCP error {code}: {message}")
        self.code, self.message, self.data = code, message, data


class McpTimeout(McpError):
    pass


def _kill_group(proc: subprocess.Popen, sig: int) -> None:
    try:
        os.killpg(proc.pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


class McpClient:
    def __init__(self, command: list[str], *, env: dict | None = None, cwd: str | None = None, timeout: float = 20.0):
        self.command, self.cwd, self.timeout = list(command), cwd, timeout
        # the server gets a minimal environment, not our secrets (API keys live in os.environ)
        self.env = env if env is not None else {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
        self.proc: subprocess.Popen | None = None
        self.era: str | None = None
        self.server_info: dict = {}
        self.instructions: str = ""
        self.stderr_tail: deque = deque(maxlen=200)
        self._pending: dict[int, queue.Queue] = {}
        self._next_id = 0
        self._send_lock = threading.Lock()
        self._id_lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------------ process
    def start(self) -> None:
        self.proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, encoding="utf-8", errors="replace", bufsize=1, cwd=self.cwd, env=self.env,
                                     start_new_session=True)
        for target in (self._read_stdout, self._drain_stderr):       # stderr must be drained or a chatty server blocks
            t = threading.Thread(target=target, daemon=True)
            t.start()
            self._threads.append(t)

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def _read_stdout(self) -> None:
        try:
            for line in self.proc.stdout:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue                                          # not a protocol message: ignore it
                q = self._pending.get(msg.get("id")) if isinstance(msg, dict) else None
                if q is not None and ("result" in msg or "error" in msg):
                    q.put(msg)
        finally:
            for q in list(self._pending.values()):
                q.put(_EOF)                                            # wake every waiter: the server is gone

    def _drain_stderr(self) -> None:
        for line in self.proc.stderr:
            self.stderr_tail.append(line.rstrip("\n")[:500])

    def close(self) -> None:
        proc = self.proc
        if proc is None:
            return
        try:
            proc.stdin.close()                                         # 1. the polite signal: stdin EOF
        except OSError:
            pass
        for sig, wait in ((None, 2.0), (signal.SIGTERM, 2.0), (signal.SIGKILL, 2.0)):
            if sig is not None:
                _kill_group(proc, sig)
            try:
                proc.wait(timeout=wait)
                break
            except subprocess.TimeoutExpired:
                continue
        _kill_group(proc, signal.SIGKILL)                              # reap anything the server left behind
        for t in self._threads:
            t.join(timeout=1.0)
        self.proc = None

    # ------------------------------------------------------------------ JSON-RPC
    def _send(self, msg: dict) -> None:
        if not self.alive:
            raise McpError(f"MCP server is not running (stderr: {' | '.join(list(self.stderr_tail)[-3:])})")
        data = json.dumps(msg, separators=(",", ":"), ensure_ascii=True) + "\n"
        try:
            with self._send_lock:
                self.proc.stdin.write(data)
                self.proc.stdin.flush()
        except (OSError, ValueError) as e:
            raise McpError(f"could not write to the MCP server: {e}")

    def _meta(self) -> dict:
        return {"io.modelcontextprotocol/protocolVersion": MODERN_VERSION,
                "io.modelcontextprotocol/clientCapabilities": {},
                "io.modelcontextprotocol/clientInfo": CLIENT_INFO}

    def request(self, method: str, params: dict | None = None, timeout: float | None = None, *, modern: bool | None = None) -> dict:
        use_meta = (self.era == "modern") if modern is None else modern
        params = dict(params or {})
        if use_meta:
            params["_meta"] = self._meta()
        with self._id_lock:
            self._next_id += 1
            rid = self._next_id
        q: queue.Queue = queue.Queue(maxsize=1)
        self._pending[rid] = q
        try:
            self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
            try:
                resp = q.get(timeout=timeout or self.timeout)
            except queue.Empty:
                try:
                    self._send({"jsonrpc": "2.0", "method": "notifications/cancelled",
                                "params": {"requestId": rid, "reason": "client timeout"}})
                except McpError:
                    pass
                raise McpTimeout(f"{method} timed out after {timeout or self.timeout:.0f}s")
        finally:
            self._pending.pop(rid, None)
        if resp is _EOF:
            raise McpError(f"MCP server exited (stderr: {' | '.join(list(self.stderr_tail)[-3:])})")
        if "error" in resp:
            e = resp["error"] if isinstance(resp["error"], dict) else {}
            raise McpRpcError(e.get("code", -32603), str(e.get("message", "error")), e.get("data"))
        result = resp["result"]
        if not isinstance(result, dict):
            raise McpError("malformed result")
        if result.get("resultType", "complete") != "complete":         # e.g. input_required: not supported here
            raise McpError(f"unsupported resultType {result.get('resultType')!r}")
        return result

    # ------------------------------------------------------------------ handshake
    def initialize(self, probe_timeout: float = 5.0) -> None:
        """Probe the modern protocol; fall back to the legacy handshake. Sets `self.era`."""
        try:
            result = self.request("server/discover", timeout=probe_timeout, modern=True)
            supported = result.get("supportedVersions") or []
            if MODERN_VERSION not in supported:
                raise McpError(f"no common protocol version (server supports {supported})")
            self.era = "modern"
            info = (result.get("_meta") or {}).get("io.modelcontextprotocol/serverInfo")
            self.server_info, self.instructions = info or {}, str(result.get("instructions") or "")
            return
        except McpRpcError as e:
            if e.code == -32022:                                       # modern server, version mismatch: no fallback
                raise McpError(f"server does not support protocol {MODERN_VERSION}: {e.data}")
        except McpTimeout:
            pass
        if not self.alive:
            raise McpError("MCP server exited during startup: " + " | ".join(list(self.stderr_tail)[-3:]))
        result = self.request("initialize", {"protocolVersion": LEGACY_VERSION, "capabilities": {},
                                             "clientInfo": CLIENT_INFO}, modern=False)
        self.era = "legacy"
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.server_info, self.instructions = result.get("serverInfo") or {}, str(result.get("instructions") or "")

    # ------------------------------------------------------------------ tools
    def list_tools(self) -> list[dict]:
        tools, cursor = [], None
        for _ in range(50):                                            # bounded pagination
            result = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools += [t for t in result.get("tools", []) if isinstance(t, dict) and isinstance(t.get("name"), str)]
            cursor = result.get("nextCursor")
            if not cursor:
                return tools
        raise McpError("tools/list pagination did not terminate")

    def call_tool(self, name: str, arguments: dict, timeout: float | None = None) -> tuple[str, bool]:
        result = self.request("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)
        parts = []
        for item in result.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, dict):
                parts.append(f"[{item.get('type', 'unknown')} content omitted]")
        return "\n".join(parts), bool(result.get("isError"))


# ---------------------------------------------------------------------- glue for the agent
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_NAME_BAD = re.compile(r"[^A-Za-z0-9_-]")


def resolve_command(command: list[str]) -> list[str]:
    """`python` in a config means *this* interpreter (so the venv's packages are found)."""
    if command and command[0] in ("python", "python3"):
        return [sys.executable, *command[1:]]
    return list(command)


def mcp_tools_for(client: McpClient, server: str, allow: list[str], trusted: list[str] = ()) -> dict[str, Tool]:
    """Wrap the server's whitelisted tools as agent tools named `mcp__<server>__<tool>`.

    Only names in `allow` are exposed: the model cannot reach any other tool, so a guessed name never even
    gets as far as the server. Tool annotations are untrusted (the spec says so), so every MCP tool asks for
    user confirmation unless it is listed in `trusted`.
    """
    tools: dict[str, Tool] = {}
    listed = {t["name"]: t for t in client.list_tools()}
    for name in allow:
        t = listed.get(name)
        if t is None:
            continue
        schema = {k: v for k, v in (t.get("inputSchema") or {"type": "object", "properties": {}}).items() if k != "$schema"}
        full = f"mcp__{_NAME_BAD.sub('_', server)}__{_NAME_BAD.sub('_', name)}"
        desc = _CTRL.sub("", str(t.get("description") or ""))[:1000]

        def run(args: dict, _name=name) -> str:
            try:
                text, is_error = client.call_tool(_name, args)
            except McpError as e:
                raise ToolError(str(e))
            if is_error:
                raise ToolError(text)
            return text

        tools[full] = Tool(full, f"{desc} (MCP server '{server}')", schema, run, needs_confirm=name not in trusted)
    return tools


@contextmanager
def mcp_session(configs: list[dict]):
    """Start the configured MCP servers, yield their tools (name -> Tool), and always shut them down.

    Each config: {"name", "command": [...], "allow": [tool names], "trusted": [...], "timeout": seconds}.
    """
    clients: list[McpClient] = []
    try:
        tools: dict[str, Tool] = {}
        for cfg in configs or []:
            if not cfg.get("allow"):
                raise ValueError(f"MCP server {cfg.get('name')!r} needs an explicit non-empty 'allow' list")
            c = McpClient(resolve_command(cfg["command"]), timeout=cfg.get("timeout", 20.0))
            clients.append(c)
            c.start()
            c.initialize()
            tools.update(mcp_tools_for(c, cfg["name"], cfg["allow"], cfg.get("trusted", [])))
        yield tools
    finally:
        for c in clients:
            c.close()
