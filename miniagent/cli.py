import argparse
import sys
import time
from contextlib import nullcontext
from pathlib import Path

import json

from .agent import Agent
from .mcp.client import mcp_session
from .client import APIError, ChatClient
from .tools import Workspace
from .trajectory import Trajectory

DEFAULT_MODEL = "deepseek-chat"


def _make_confirm(auto: bool):
    approve_all = auto

    def confirm(name: str, args: dict) -> bool:
        nonlocal approve_all
        if approve_all:
            return True
        shown = args.get("command") or args.get("path") or ""
        ans = input(f"\n[confirm] {name}: {shown}\n  allow? [y]es / [n]o / [a]ll: ").strip().lower()
        if ans == "a":
            approve_all = True
        return ans in ("y", "a")

    return confirm


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="miniagent")
    ap.add_argument("task", help="what the agent should do")
    ap.add_argument("-w", "--workspace", default=".", help="repo root the agent may touch")
    ap.add_argument("-m", "--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-steps", type=int, default=30)
    ap.add_argument("-y", "--yes", action="store_true", help="auto-approve write/edit/bash (deny-list still applies)")
    ap.add_argument("--context-limit", type=int, default=100_000,
                    help="compact history when input tokens exceed 70%% of this; set low (e.g. 3000) to exercise compaction")
    ap.add_argument("--keep-recent", type=int, default=8, help="messages kept verbatim when compacting")
    ap.add_argument("--compact-regrowth", type=float, default=1.0,
                    help="after a compaction that cannot get under the threshold, wait for this much input growth before the next one (0 = every step)")
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--mcp-config", help="JSON file with a list of MCP servers: [{name, command, allow, trusted?}]")
    ap.add_argument("--disable-tools", default="", help="comma-separated built-in tools to hide, e.g. bash,grep,read_file")
    ap.add_argument("--sandbox", action="store_true", help="run bash in a Docker container (no network, read-only root, only the workspace mounted)")
    ap.add_argument("--runs-dir", default="runs")
    args = ap.parse_args(argv)

    try:
        client = ChatClient()
    except APIError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    run_dir = Path(args.runs_dir) / time.strftime("%Y%m%d-%H%M%S")
    servers = json.loads(Path(args.mcp_config).read_text()) if args.mcp_config else []
    from .sandbox import Sandbox, SandboxError, available
    if args.sandbox and not available():
        print("error: the sandbox image is missing or Docker is not running (build it with: miniagent-eval sandbox-build)", file=sys.stderr)
        return 2
    with mcp_session(servers) as mcp_tools, (Sandbox(args.workspace) if args.sandbox else nullcontext()) as sb:
        agent = Agent(
            client=client, model=args.model, workspace=Workspace(args.workspace, sandbox=sb),
            confirm=_make_confirm(args.yes), trajectory=Trajectory(run_dir), max_steps=args.max_steps,
            context_limit=args.context_limit, keep_recent=args.keep_recent, compact_regrowth=args.compact_regrowth,
            temperature=args.temperature, extra_tools=mcp_tools,
            disabled_tools=tuple(t for t in args.disable_tools.split(",") if t),
        )
        res = agent.run(args.task)
    print(f"\n=== {res.status} | {res.steps} steps | {res.input_tokens} in / {res.output_tokens} out tokens ===")
    print(res.final_text)
    print(f"trajectory: {run_dir / 'trajectory.jsonl'}")
    return 0 if res.status == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
