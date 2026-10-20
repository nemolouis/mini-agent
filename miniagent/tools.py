"""Tool implementations: read_file, write_file, edit_file, bash, grep.

Every tool takes a plain dict (the model's parsed arguments) and returns a string.
Failures raise ToolError; the agent loop turns those into is_error results so
the model can recover instead of the run crashing.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .proc import run_shell
from .safety import check_command

MAX_OUTPUT_CHARS = 20_000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


class ToolError(Exception):
    pass


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n...[truncated {len(text) - limit} chars]...\n{text[-half:]}"


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    func: Callable[[dict], str]
    needs_confirm: bool = False

    def spec(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.input_schema}}


class Workspace:
    def __init__(self, root: str | Path, sandbox=None):
        """`sandbox`: a miniagent.sandbox.Sandbox over `root`. With it, `bash` runs in the container instead of the host."""
        self.root = Path(root).resolve()
        self.sandbox = sandbox
        if not self.root.is_dir():
            raise ValueError(f"workspace is not a directory: {self.root}")

    def resolve(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if p != self.root and self.root not in p.parents:
            raise ToolError(f"path escapes workspace: {path}")
        return p

    # ---- tools ----
    def read_file(self, args: dict) -> str:
        p = self.resolve(args["path"])
        if not p.is_file():
            raise ToolError(f"not a file: {args['path']}")
        offset = max(int(args.get("offset", 1)), 1)
        limit = int(args.get("limit", 2000))
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            raise ToolError("file is not valid UTF-8 text")
        chunk = lines[offset - 1 : offset - 1 + limit]
        out = "\n".join(f"{i:>6}\t{l}" for i, l in enumerate(chunk, start=offset))
        if offset - 1 + limit < len(lines):
            out += f"\n... ({len(lines) - (offset - 1 + limit)} more lines, use offset)"
        return truncate(out) or "(empty file)"

    def write_file(self, args: dict) -> str:
        p = self.resolve(args["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"], encoding="utf-8")
        return f"wrote {len(args['content'])} chars to {args['path']}"

    def edit_file(self, args: dict) -> str:
        p = self.resolve(args["path"])
        if not p.is_file():
            raise ToolError(f"not a file: {args['path']}")
        old, new = args["old_string"], args["new_string"]
        if old == new:
            raise ToolError("old_string and new_string are identical")
        text = p.read_text(encoding="utf-8")
        n = text.count(old)
        if n == 0:
            raise ToolError("old_string not found (must match exactly, including whitespace)")
        if n > 1:
            raise ToolError(f"old_string matches {n} places; include more context to make it unique")
        p.write_text(text.replace(old, new, 1), encoding="utf-8")
        return f"edited {args['path']}"

    def bash(self, args: dict) -> str:
        cmd = args["command"]
        reason = check_command(cmd)
        if reason:
            raise ToolError(f"command blocked by safety policy: {reason}")
        timeout = min(int(args.get("timeout", 60)), 300)
        if self.sandbox is not None:
            r = self.sandbox.exec(cmd, timeout=timeout)
        else:
            r = run_shell(cmd, shell=True, cwd=self.root, timeout=timeout,
                          env={**os.environ, "GIT_PAGER": "cat", "PAGER": "cat"})
        if r.timed_out:
            raise ToolError(f"command timed out after {timeout}s")
        return truncate(f"exit code: {r.returncode}\n{r.stdout}{r.stderr}".rstrip())

    def grep(self, args: dict) -> str:
        try:
            rx = re.compile(args["pattern"])
        except re.error as e:
            raise ToolError(f"invalid regex: {e}")
        base = self.resolve(args.get("path", "."))
        glob = args.get("glob")
        files = [base] if base.is_file() else (
            f for f in sorted(base.rglob(glob or "*"))
            if f.is_file() and not (SKIP_DIRS & set(f.relative_to(self.root).parts))
        )
        hits: list[str] = []
        for f in files:
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{f.relative_to(self.root)}:{i}:{line[:300]}")
                        if len(hits) >= 200:
                            return "\n".join(hits) + "\n... (stopped at 200 matches)"
            except (UnicodeDecodeError, OSError):
                continue
        return "\n".join(hits) or "no matches"


def build_tools(ws: Workspace) -> dict[str, Tool]:
    S = lambda **props: {"type": "object", "properties": props, "required": [k for k, v in props.items() if not v.pop("optional", False)]}
    tools = [
        Tool("read_file", "Read a text file with line numbers. Paths are relative to the workspace root.",
             S(path={"type": "string"}, offset={"type": "integer", "description": "1-based start line", "optional": True},
               limit={"type": "integer", "description": "max lines (default 2000)", "optional": True}),
             ws.read_file),
        Tool("write_file", "Create or overwrite a file with the given content.",
             S(path={"type": "string"}, content={"type": "string"}), ws.write_file, needs_confirm=True),
        Tool("edit_file", "Replace one exact occurrence of old_string with new_string. Fails if old_string is missing or not unique.",
             S(path={"type": "string"}, old_string={"type": "string"}, new_string={"type": "string"}),
             ws.edit_file, needs_confirm=True),
        Tool("bash", "Run a shell command in the workspace root. Use for running tests, git, etc.",
             S(command={"type": "string"}, timeout={"type": "integer", "description": "seconds, default 60, max 300", "optional": True}),
             ws.bash, needs_confirm=True),
        Tool("grep", "Regex search over files (skips .git, node_modules, venvs). Returns path:line:text.",
             S(pattern={"type": "string"}, path={"type": "string", "description": "file or dir, default '.'", "optional": True},
               glob={"type": "string", "description": "e.g. '*.py'", "optional": True}),
             ws.grep),
    ]
    return {t.name: t for t in tools}
