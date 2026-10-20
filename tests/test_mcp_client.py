"""The MCP client against a real notes server and against misbehaving fake servers."""
import json
import os
import signal
import sys
import textwrap
import time

import pytest

from miniagent.mcp.client import McpClient, McpError, McpRpcError, McpTimeout, mcp_session

FAKE = textwrap.dedent('''
    import json, os, sys, time
    mode = sys.argv[1]
    logf = sys.argv[2] if len(sys.argv) > 2 else None
    def log(s):
        if logf:
            with open(logf, "a") as f: f.write(s + "\\n")
    def send(o):
        sys.stdout.write(json.dumps(o) + "\\n"); sys.stdout.flush()
    if mode == "stderr-flood":
        sys.stderr.write("x" * (4 * 1024 * 1024)); sys.stderr.flush()
    TOOLS = [{"name": "echo", "description": "echo text", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}]
    INFO = {"name": "fake", "version": "0"}
    def modern_result(r): return {"resultType": "complete", **r}
    for line in sys.stdin:
        m = json.loads(line); method = m.get("method"); rid = m.get("id"); params = m.get("params") or {}
        if rid is None:
            log("notification:" + method + ":" + json.dumps(params)); continue
        if mode == "noise": print("this is not json-rpc"); sys.stdout.flush()
        legacy = mode in ("legacy", "silent-discover")
        if method == "server/discover":
            if mode == "silent-discover": continue
            if mode == "legacy": send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}}); continue
            if mode == "mismatch": send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32022, "message": "Unsupported protocol version", "data": {"supported": ["2025-11-25"], "requested": "2026-07-28"}}}); continue
            send({"jsonrpc": "2.0", "id": rid, "result": modern_result({"supportedVersions": ["2026-07-28"], "capabilities": {"tools": {}}, "_meta": {"io.modelcontextprotocol/serverInfo": INFO}, "instructions": "be nice"})})
            if mode == "crash": os._exit(3)
        elif method == "initialize":
            send({"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}}, "serverInfo": INFO}})
        elif method == "tools/list":
            if mode == "pages":
                r = {"tools": [dict(TOOLS[0], name="a")], "nextCursor": "p2"} if not params.get("cursor") else {"tools": [dict(TOOLS[0], name="b")]}
            else:
                r = {"tools": TOOLS}
            send({"jsonrpc": "2.0", "id": rid, "result": r if legacy else modern_result(r)})
        elif method == "tools/call":
            log("call:" + json.dumps(params.get("arguments")))
            if mode == "hang-call": log("pending-id:" + str(rid)); continue          # slow: never answers, keeps reading
            if mode == "input-required": send({"jsonrpc": "2.0", "id": rid, "result": {"resultType": "input_required", "inputRequests": {}}}); continue
            if mode == "image": send({"jsonrpc": "2.0", "id": rid, "result": modern_result({"content": [{"type": "image", "data": "AA==", "mimeType": "image/png"}, {"type": "text", "text": "caption"}], "isError": False})}); continue
            r = {"content": [{"type": "text", "text": "echo:" + str(params["arguments"].get("text"))}], "isError": params["arguments"].get("text") == "boom"}
            send({"jsonrpc": "2.0", "id": rid, "result": r if legacy else modern_result(r)})
        else:
            send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}})
    if mode == "ignore-stdin-close": time.sleep(600)
''')


@pytest.fixture
def fake(tmp_path):
    script = tmp_path / "fake_server.py"
    script.write_text(FAKE)
    log = tmp_path / "fake.log"
    made = []

    def make(mode, **kw):
        c = McpClient([sys.executable, str(script), mode, str(log)], **kw)
        made.append(c)
        c.start()
        return c

    make.log = log
    yield make
    for c in made:
        c.close()


@pytest.fixture
def notes(tmp_path):
    root = tmp_path / "notes"
    root.mkdir()
    (root / "a.md").write_text("# A\nhello TODO\n")
    return root


def real_server(notes, *extra):
    return McpClient([sys.executable, "-m", "miniagent.mcp.notes_server", "--root", str(notes), *extra])


# ---------------------------------------------------------------- against the real server
def test_end_to_end_modern(notes):
    c = real_server(notes)
    c.start()
    try:
        c.initialize()
        assert c.era == "modern" and c.server_info["name"] == "miniagent-notes" and "notes" in c.instructions
        assert [t["name"] for t in c.list_tools()] == ["list_notes", "read_note", "search_notes"]
        text, is_error = c.call_tool("read_note", {"path": "a.md"})
        assert not is_error and "hello TODO" in text
        text, is_error = c.call_tool("read_note", {"path": "../secret"})
        assert is_error and "not allowed" in text
        with pytest.raises(McpRpcError) as ei:
            c.call_tool("append_note", {"path": "x.md", "text": "y"})            # not enabled: a protocol error
        assert ei.value.code == -32602 and "Unknown tool" in ei.value.message
    finally:
        c.close()
    assert not c.alive and not (notes / "x.md").exists()


def test_close_ends_the_server_process_tree(notes):
    c = real_server(notes)
    c.start()
    c.initialize()
    pid = c.proc.pid
    c.close()
    with pytest.raises(ProcessLookupError):
        os.killpg(pid, 0)                                                         # the whole group is gone


# ---------------------------------------------------------------- handshake variants
def test_legacy_server_is_detected_after_a_modern_error(fake):
    c = fake("legacy")
    c.initialize()
    assert c.era == "legacy"
    assert [t["name"] for t in c.list_tools()] == ["echo"]
    assert c.call_tool("echo", {"text": "hi"}) == ("echo:hi", False)
    assert "notification:notifications/initialized" in fake.log.read_text()


def test_legacy_server_that_never_answers_discover_is_detected_by_timeout(fake):
    c = fake("silent-discover")
    t0 = time.time()
    c.initialize(probe_timeout=0.5)
    assert c.era == "legacy" and time.time() - t0 < 5
    assert c.call_tool("echo", {"text": "x"}) == ("echo:x", False)


def test_modern_server_with_no_common_version_is_an_error_not_a_fallback(fake):
    c = fake("mismatch")
    with pytest.raises(McpError, match="does not support"):
        c.initialize()


# ---------------------------------------------------------------- failure handling
def test_request_timeout_sends_a_cancellation(fake):
    c = fake("hang-call")
    c.initialize()
    with pytest.raises(McpTimeout):
        c.call_tool("echo", {"text": "slow"}, timeout=0.5)
    deadline = time.time() + 5
    while "notifications/cancelled" not in fake.log.read_text() and time.time() < deadline:
        time.sleep(0.05)
    log = fake.log.read_text()
    rid = int(next(l for l in log.splitlines() if l.startswith("pending-id:")).split(":")[1])
    assert f'notification:notifications/cancelled:{{"requestId": {rid}' in log          # the server was told which request to drop
    assert [t["name"] for t in c.list_tools()] == ["echo"]                               # the connection survives a timeout
    c.close()
    assert not c.alive


def test_chatty_stderr_does_not_deadlock_the_protocol(fake):
    c = fake("stderr-flood")
    c.initialize()
    assert c.call_tool("echo", {"text": "alive"}) == ("echo:alive", False)
    assert len(c.stderr_tail) <= 200 and all(len(l) <= 500 for l in c.stderr_tail)


def test_server_crash_is_reported_not_hung(fake):
    c = fake("crash")
    c.initialize()
    time.sleep(0.3)
    with pytest.raises(McpError, match="not running|exited"):
        c.call_tool("echo", {"text": "x"})
    c.close()
    c.close()                                                                       # closing twice is harmless


def test_server_that_ignores_stdin_close_is_terminated(fake):
    c = fake("ignore-stdin-close")
    c.initialize()
    t0 = time.time()
    c.close()
    assert not c.alive and time.time() - t0 < 10


def test_garbage_on_stdout_is_ignored(fake):
    c = fake("noise")
    c.initialize()
    assert c.call_tool("echo", {"text": "ok"}) == ("echo:ok", False)


def test_pagination_and_content_handling(fake):
    c = fake("pages")
    c.initialize()
    assert [t["name"] for t in c.list_tools()] == ["a", "b"]
    img = fake("image")
    img.initialize()
    text, err = img.call_tool("echo", {"text": "x"})
    assert text == "[image content omitted]\ncaption" and not err


def test_unsupported_result_type_is_an_error(fake):
    c = fake("input-required")
    c.initialize()
    with pytest.raises(McpError, match="resultType"):
        c.call_tool("echo", {"text": "x"})


def test_a_dead_command_fails_cleanly(tmp_path):
    c = McpClient([sys.executable, "-c", "import sys; sys.stderr.write('boom on startup'); sys.exit(1)"])
    c.start()
    with pytest.raises(McpError, match="boom on startup|exited|not running"):
        c.initialize()
    c.close()


def test_mcp_session_needs_an_allow_list(notes):
    with pytest.raises(ValueError, match="allow"):
        with mcp_session([{"name": "notes", "command": ["python", "-m", "miniagent.mcp.notes_server", "--root", str(notes)]}]):
            pass
