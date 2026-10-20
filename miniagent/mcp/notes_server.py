"""A small MCP server over a directory of notes, speaking JSON-RPC on stdio.

    python -m miniagent.mcp.notes_server --root NOTES_DIR [--allow-write] [--allow-tools a,b]

Protocol (checked against the MCP specification): newline-delimited UTF-8 JSON-RPC on stdin/stdout, logs
on stderr, exit when stdin closes. The server is *dual-era*:

* modern (2026-07-28): no handshake; every request carries `params._meta` with the protocol version and the
  client capabilities; `server/discover` is implemented; results carry `resultType`.
* legacy (<= 2025-11-25): `initialize` / `notifications/initialized` handshake.

Tools: list_notes, read_note, search_notes (read-only) and append_note (only with --allow-write).
Every tool argument is untrusted: all file access goes through `safepath`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from . import safepath
from .safepath import Denied, Scan, TooLarge, clean_text, make_policy, open_file, read_all, show, validate_rel

SERVER_INFO = {"name": "miniagent-notes", "version": "0.1.0"}
MODERN_VERSIONS = ("2026-07-28",)
LEGACY_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPS = "io.modelcontextprotocol/clientCapabilities"
META_SERVER = "io.modelcontextprotocol/serverInfo"
INSTRUCTIONS = ("Read-only access to a folder of Markdown/text notes. Use list_notes to see what exists, "
                "read_note to read one, search_notes to find text. Paths are relative to the notes folder.")

MAX_LINE = 1 << 20                  # largest accepted JSON-RPC message
MAX_OUTPUT_BYTES = 64 * 1024        # largest text a tool returns
MAX_APPEND_BYTES = 32 * 1024
SEARCH_BUDGET_S = 5.0

E_PARSE, E_REQUEST, E_METHOD, E_PARAMS, E_INTERNAL, E_VERSION = -32700, -32600, -32601, -32602, -32603, -32022


class RpcError(Exception):
    def __init__(self, code: int, message: str, data=None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


class ToolFailure(Exception):
    """A tool *execution* error: reported with isError=true so the model can correct itself."""


# ------------------------------------------------------------------ tool definitions
def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


TOOLS = {
    "list_notes": {
        "description": "List the notes (Markdown/text files) in the notes folder, recursively, sorted by path. "
                       "Returns one `path<TAB>size` line per note.",
        "schema": _schema({"subdir": {"type": "string", "description": "optional sub-folder, relative to the notes folder"},
                           "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "description": "max entries (default 200)"}}, []),
        "write": False},
    "read_note": {
        "description": "Read one note by relative path. Returns numbered lines. Use offset/limit to page through long notes.",
        "schema": _schema({"path": {"type": "string", "description": "relative path of the note, e.g. projects/ideas.md"},
                           "offset": {"type": "integer", "minimum": 1, "description": "first line to return (1-based, default 1)"},
                           "limit": {"type": "integer", "minimum": 1, "maximum": 2000, "description": "max lines (default 400)"}}, ["path"]),
        "write": False},
    "search_notes": {
        "description": "Case-insensitive literal text search over all notes (not a regular expression). "
                       "Returns `path:line: text` matches.",
        "schema": _schema({"query": {"type": "string", "minLength": 1, "maxLength": 200},
                           "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "description": "default 20"}}, ["query"]),
        "write": False},
    "append_note": {
        "description": "Append text to a Markdown note (created if it does not exist, in an existing folder). Writes only inside the notes folder.",
        "schema": _schema({"path": {"type": "string", "description": "relative path ending in .md"},
                           "text": {"type": "string", "minLength": 1, "maxLength": MAX_APPEND_BYTES}}, ["path", "text"]),
        "write": True},
}


def validate_args(schema: dict, args) -> str | None:
    """Return an actionable message if `args` does not satisfy `schema` (the small subset we use), else None."""
    if not isinstance(args, dict):
        return "arguments must be an object"
    props = schema["properties"]
    for k in args:
        if k not in props:
            return f"unknown argument {show(k)!r}; allowed: {', '.join(props) or 'none'}"
    for k in schema["required"]:
        if k not in args:
            return f"missing required argument {k!r}"
    for k, v in args.items():
        spec = props[k]
        if spec["type"] == "string":
            if not isinstance(v, str):
                return f"argument {k!r} must be a string"
            if len(v) < spec.get("minLength", 0) or len(v) > spec.get("maxLength", 1 << 20):
                return f"argument {k!r} has a bad length (allowed {spec.get('minLength', 0)}..{spec.get('maxLength', 1 << 20)})"
        elif spec["type"] == "integer":
            if isinstance(v, bool) or not isinstance(v, int):
                return f"argument {k!r} must be an integer"
            if v < spec.get("minimum", -(1 << 53)) or v > spec.get("maximum", 1 << 53):
                return f"argument {k!r} must be between {spec.get('minimum')} and {spec.get('maximum')}"
    return None


# ------------------------------------------------------------------ the server
class NotesServer:
    def __init__(self, root, *, allow_write: bool = False, allow_tools: set[str] | None = None, **policy_kw):
        self.policy = make_policy(root, **policy_kw)
        enabled = [n for n, t in TOOLS.items() if allow_write or not t["write"]]
        if allow_tools is not None:
            enabled = [n for n in enabled if n in allow_tools]
        self.enabled = {n: TOOLS[n] for n in enabled}            # an insertion-ordered, deterministic list
        self.legacy_session = False

    # ---- protocol
    def handle_line(self, line: str) -> str | None:
        try:
            msg = json.loads(line)
        except ValueError:
            return self._dump(self._error(None, E_PARSE, "parse error"))
        resp = self.handle(msg)
        return None if resp is None else self._dump(resp)

    @staticmethod
    def _dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=True, separators=(",", ":"))      # never contains a raw newline

    @staticmethod
    def _error(rid, code: int, message: str, data=None) -> dict:
        err = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return {"jsonrpc": "2.0", "id": rid, "error": err}

    def handle(self, msg) -> dict | None:
        if isinstance(msg, list):
            return self._error(None, E_REQUEST, "batch requests are not supported")
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            return self._error(None, E_REQUEST, "invalid request")
        method = msg["method"]
        if "id" not in msg:                                           # a notification: never answered
            if method == "notifications/initialized":
                self.legacy_session = True
            return None
        rid = msg["id"]
        if isinstance(rid, bool) or not isinstance(rid, (str, int)):
            return self._error(None, E_REQUEST, "id must be a string or an integer")
        params = msg.get("params", {})
        if not isinstance(params, dict):
            return self._error(rid, E_PARAMS, "params must be an object")
        try:
            result, era = self._dispatch(method, params)
        except RpcError as e:
            return self._error(rid, e.code, e.message, e.data)
        except Exception as e:                                         # a server bug must not kill the server
            print(f"internal error in {method}: {type(e).__name__}: {e}", file=sys.stderr)
            return self._error(rid, E_INTERNAL, "internal error")
        if era == "modern":
            result = {"resultType": "complete", **result}
            result.setdefault("_meta", {})[META_SERVER] = SERVER_INFO
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def _era(self, params: dict) -> str:
        meta = params.get("_meta")
        if isinstance(meta, dict) and META_VERSION in meta:
            version = meta[META_VERSION]
            if not isinstance(version, str):
                raise RpcError(E_PARAMS, f"_meta {META_VERSION} must be a string")
            if version not in MODERN_VERSIONS:
                raise RpcError(E_VERSION, "Unsupported protocol version",
                               {"supported": list(MODERN_VERSIONS + LEGACY_VERSIONS), "requested": version})
            if not isinstance(meta.get(META_CAPS), dict):
                raise RpcError(E_PARAMS, f"missing required _meta field {META_CAPS}")
            return "modern"
        if self.legacy_session:
            return "legacy"
        raise RpcError(E_PARAMS, f"missing required _meta field {META_VERSION} "
                                 "(modern clients), or send initialize first (legacy clients)")

    def _dispatch(self, method: str, params: dict):
        if method == "initialize":                                     # legacy handshake
            requested = params.get("protocolVersion")
            if not isinstance(requested, str):
                raise RpcError(E_PARAMS, "protocolVersion is required")
            self.legacy_session = True
            version = requested if requested in LEGACY_VERSIONS else LEGACY_VERSIONS[0]
            return ({"protocolVersion": version, "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO,
                     "instructions": INSTRUCTIONS}, "legacy")
        if method == "ping":
            return {}, "legacy"
        era = self._era(params)
        if method == "server/discover":
            if era != "modern":
                raise RpcError(E_METHOD, "server/discover needs a modern request")
            return {"supportedVersions": list(MODERN_VERSIONS), "capabilities": {"tools": {}},
                    "instructions": INSTRUCTIONS}, era
        if method == "tools/list":
            return {"tools": [{"name": n, "description": t["description"], "inputSchema": t["schema"]}
                              for n, t in self.enabled.items()]}, era
        if method == "tools/call":
            return self._call(params), era
        raise RpcError(E_METHOD, f"method not found: {show(method)}")

    def _call(self, params: dict) -> dict:
        name, args = params.get("name"), params.get("arguments", {})
        if not isinstance(name, str):
            raise RpcError(E_PARAMS, "tool name is required")
        tool = self.enabled.get(name)
        if tool is None:                                               # also covers a disabled write tool
            raise RpcError(E_PARAMS, f"Unknown tool: {show(name)}")
        problem = validate_args(tool["schema"], args)
        if problem:
            return self._result(f"invalid arguments: {problem}", True)
        try:
            return self._result(getattr(self, "tool_" + name)(args), False)
        except ToolFailure as e:
            return self._result(str(e), True)
        except TooLarge as e:
            return self._result(f"note too large: {e}", True)
        except Denied as e:                                            # same text whether it is missing or forbidden
            return self._result(f"no such note, or not allowed: {show(args.get('path', args.get('subdir', '')))!r}. "
                                "Use list_notes to see the available paths.", True)

    @staticmethod
    def _result(text: str, is_error: bool) -> dict:
        data = clean_text(text).encode("utf-8")
        if len(data) > MAX_OUTPUT_BYTES:
            text = data[:MAX_OUTPUT_BYTES].decode("utf-8", "ignore") + "\n[output truncated]"
        return {"content": [{"type": "text", "text": clean_text(text)}], "isError": is_error}

    # ---- tools
    def tool_list_notes(self, a: dict) -> str:
        parts = validate_rel(self.policy, a.get("subdir", ""), allow_empty=True)
        limit = a.get("limit", 200)
        scan, lines = Scan(self.policy, parts, deadline=time.monotonic() + SEARCH_BUDGET_S), []
        for rel, _, size in scan:
            lines.append(f"{rel}\t{size} bytes")
            if len(lines) >= limit:
                scan.truncated = True
                break
        if not lines:
            return "(no notes found)"
        return "\n".join(lines) + ("\n[list truncated]" if scan.truncated else "")

    def tool_read_note(self, a: dict) -> str:
        rel = a["path"]
        parts = validate_rel(self.policy, rel)
        fd = open_file(self.policy, parts)
        try:
            data = read_all(fd, self.policy.max_file_bytes)
        finally:
            os.close(fd)
        if b"\x00" in data[:8192]:
            raise ToolFailure("this file is not a text note")
        lines = data.decode("utf-8", "replace").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        offset, limit = a.get("offset", 1), a.get("limit", 400)
        chunk = lines[offset - 1:offset - 1 + limit]
        body = "\n".join(f"{offset + i:>5}  {line}" for i, line in enumerate(chunk))
        end = offset - 1 + len(chunk)
        footer = f"[lines {offset}-{end} of {len(lines)}]" if chunk else f"[no lines at offset {offset}; the note has {len(lines)} lines]"
        if end < len(lines):
            footer += f" - continue with offset={end + 1}"
        return f"[note: {'/'.join(parts)}]\n{body}\n{footer}"

    def tool_search_notes(self, a: dict) -> str:
        needle, cap = a["query"].casefold(), a.get("max_results", 20)
        scan = Scan(self.policy, [], open_files=True, deadline=time.monotonic() + SEARCH_BUDGET_S)
        hits, truncated = [], False
        for rel, fd, _ in scan:
            try:
                text = read_all(fd, self.policy.max_file_bytes).decode("utf-8", "replace")
            finally:
                os.close(fd)
            if "\x00" in text[:8192]:
                continue
            for n, line in enumerate(text.split("\n"), 1):
                if needle in line.casefold():
                    hits.append(f"{rel}:{n}: {line.strip()[:200]}")
                    if len(hits) >= cap:
                        truncated = True
                        break
            if truncated:
                break
        truncated = truncated or scan.truncated
        if not hits:
            return "no matches" + (" (search stopped early: limit reached)" if scan.truncated else "")
        return "\n".join(hits) + ("\n[more results may exist: narrow the query]" if truncated else "")

    def tool_append_note(self, a: dict) -> str:
        parts = validate_rel(self.policy, a["path"])
        if not parts[-1].lower().endswith(".md"):
            raise ToolFailure("append_note only writes Markdown (.md) notes")
        text = a["text"]
        if "\x00" in text:
            raise ToolFailure("text must not contain NUL characters")
        data = (text if text.endswith("\n") else text + "\n").encode("utf-8")
        if len(data) > MAX_APPEND_BYTES:
            raise ToolFailure(f"text is larger than {MAX_APPEND_BYTES} bytes")
        fd = open_file(self.policy, parts, write=True)
        try:
            if os.fstat(fd).st_size + len(data) > self.policy.max_file_bytes:
                raise ToolFailure(f"the note would exceed {self.policy.max_file_bytes} bytes")
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view):]
        finally:
            os.close(fd)
        return f"appended {len(data)} bytes to {'/'.join(parts)}"


# ------------------------------------------------------------------ stdio loop
def serve(server: NotesServer, stdin=None, stdout=None) -> None:
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    while True:
        line = stdin.readline(MAX_LINE + 1)
        if not line:
            return                                                     # stdin closed: the client is done
        if len(line) > MAX_LINE and not line.endswith("\n"):
            while True:                                                # drop the rest of the oversized message
                rest = stdin.readline(MAX_LINE)
                if not rest or rest.endswith("\n"):
                    break
            reply = server._dump(server._error(None, E_REQUEST, "message too large"))
        else:
            if not line.strip():
                continue
            reply = server.handle_line(line)
        if reply is not None:
            stdout.write(reply + "\n")
            stdout.flush()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="miniagent-notes-server")
    ap.add_argument("--root", required=True, help="notes directory (the only place the server can read or write)")
    ap.add_argument("--allow-write", action="store_true", help="enable the append_note tool (off by default)")
    ap.add_argument("--allow-tools", help="comma-separated whitelist of tool names; others behave as if they did not exist")
    args = ap.parse_args(argv)
    allow = set(args.allow_tools.split(",")) if args.allow_tools else None
    try:
        server = NotesServer(args.root, allow_write=args.allow_write, allow_tools=allow)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")      # the wire format is UTF-8, whatever the locale says
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"notes server on {server.policy.root}; tools: {', '.join(server.enabled)}", file=sys.stderr)
    serve(server, sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
