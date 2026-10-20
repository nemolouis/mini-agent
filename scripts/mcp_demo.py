#!/usr/bin/env python3
"""A tour of the MCP notes server's boundary. No model and no API key are involved: the script plays both the
client and a model that has been talked into attacking the server by a note.

    python3 scripts/mcp_demo.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from miniagent.mcp.client import McpClient, McpRpcError  # noqa: E402

NOTES = Path(__file__).resolve().parent.parent / "examples" / "notes"


def show(title):
    print(f"\n=== {title}")


def call(c, name, **args):
    try:
        text, is_error = c.call_tool(name, args)
    except McpRpcError as e:
        return f"[protocol error {e.code}] {e.message}"
    first = text.strip().splitlines()[0] if text.strip() else "(empty)"
    return ("[tool error] " if is_error else "") + first[:150]


def server(root, *extra):
    c = McpClient([sys.executable, "-m", "miniagent.mcp.notes_server", "--root", str(root), *extra])
    c.start()
    c.initialize()
    return c


def main():
    work = Path(tempfile.mkdtemp(prefix="mcp-demo-"))
    try:
        root, outside = work / "notes", work / "outside"
        shutil.copytree(NOTES, root)
        outside.mkdir()
        (outside / "secret.md").write_text("TOPSECRET: the launch code is 0000\n")
        os.symlink(outside / "secret.md", root / "shortcut.md")           # a planted symlink to a file outside
        os.symlink(outside, root / "shortcut_dir")
        os.link(outside / "secret.md", root / "hardlink.md")
        os.mkfifo(root / "pipe.md")

        c = server(root)
        show(f"connected ({c.era} protocol, server {c.server_info.get('name')})")
        print("tools:", [t["name"] for t in c.list_tools()])

        show("normal use")
        print("search 'budget'  ->", call(c, "search_notes", query="budget"))
        print("read planning    ->", call(c, "read_note", path="meetings/2026-10-01-planning.md"))

        show("a note carries a prompt injection (delivered as plain data)")
        text, _ = c.call_tool("read_note", {"path": "meetings/2026-10-08-vendor-call.md"})
        print("\n".join(l for l in text.splitlines() if "SYSTEM NOTICE" in l or "read_note tool" in l))

        show("the model obeys the note: every escape is refused")
        for label, path in [("absolute path", "/etc/passwd"), ("parent dirs", "../../secret.md"), ("parent via subdir", "meetings/../../outside/secret.md"),
                            ("home dir", "~/.ssh/id_rsa"), ("hidden file", ".git/config"), ("symlink to file", "shortcut.md"),
                            ("through symlinked dir", "shortcut_dir/secret.md"), ("hard link", "hardlink.md"), ("FIFO (would block)", "pipe.md"),
                            ("url-encoded ..", "%2e%2e/outside/secret.md"), ("NUL byte", "ideas.md\x00.png")]:
            print(f"{label:24s} -> {call(c, 'read_note', path=path)}")
        print(f"{'search for the secret':24s} -> {call(c, 'search_notes', query='launch code')}")
        listing = c.call_tool("list_notes", {})[0]
        print(f"{'listing shows planted':24s} -> {[n for n in ('shortcut', 'hardlink', 'pipe') if n in listing] or 'none of them'}")

        show("authorization: the write tool does not exist unless the server was started with --allow-write")
        print("append_note (read-only server) ->", call(c, "append_note", path="pwned.md", text="x"))
        print("file created?                  ->", (root / "pwned.md").exists())
        c.close()

        w = server(root, "--allow-write")
        print("\n(restarted with --allow-write)")
        print("append in the folder  ->", call(w, "append_note", path="ideas.md", text="- an idea added through MCP"))
        print("append outside        ->", call(w, "append_note", path="../outside/pwn.md", text="x"))
        print("append via symlink    ->", call(w, "append_note", path="shortcut.md", text="x"))
        print("secret file untouched ->", (outside / "secret.md").read_text().strip())
        w.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
