"""Grading and rule-based failure attribution.

Grading never trusts the agent's workspace blindly: test files are restored
from the pristine copy first, and tampering is recorded as a flag.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

from ..proc import run_shell

GRADE_TIMEOUT = 120


def is_test_file(rel: Path) -> bool:
    n = rel.name
    # conftest.py / pytest.ini change how tests run (skips, -k filters, fixtures), so they are treated like tests
    return (n.startswith("test_") or n.endswith("_test.py") or n in ("conftest.py", "pytest.ini")
            or "tests" in rel.parts or "test" in rel.parts)


def _files(root: Path) -> dict[Path, bytes]:
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and not {"__pycache__", ".pytest_cache", ".git"} & set(p.relative_to(root).parts)}


def restore_tests(pristine: Path, work: Path) -> dict:
    """Overwrite test files from `pristine`, delete test files the agent added.
    Returns {"tampered": bool, "changed_files": [non-test files that differ]}."""
    orig, now = _files(pristine), _files(work)
    tampered, changed = False, []
    for rel, data in orig.items():
        if is_test_file(rel):
            if now.get(rel) != data:
                tampered = True
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                (work / rel).write_bytes(data)
        elif now.get(rel) != data:
            changed.append(str(rel))
    for rel in now.keys() - orig.keys():
        if is_test_file(rel):
            tampered = True
            (work / rel).unlink()
        else:
            changed.append(str(rel))
    return {"tampered": tampered, "changed_files": sorted(changed)}


def run_tests(work: Path, test_cmd: str, timeout: int = GRADE_TIMEOUT, sandbox: bool = False) -> tuple[bool, str]:
    """`sandbox`: run the tests in a fresh container (the agent's own container may have left processes behind)."""
    if sandbox:
        import tempfile
        from ..sandbox import Sandbox
        # A fresh copy at a new path: a container started over a directory that an earlier container (the agent's) already
        # read can keep seeing the old version of files the host replaced since, for 10 s and more (see sandbox.py).
        with tempfile.TemporaryDirectory(prefix="mini-grade-") as fresh:
            shutil.copytree(work, Path(fresh) / "w", symlinks=True)
            with Sandbox(Path(fresh) / "w") as sb:
                r = sb.exec(test_cmd, timeout=timeout)
        if r.timed_out:
            return False, f"grading timed out after {timeout}s"
        return r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    env = {**os.environ, "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}",
           "PYTHONDONTWRITEBYTECODE": "1"}
    r = run_shell(["bash", "-c", test_cmd], cwd=work, timeout=timeout, env=env)
    if r.timed_out:
        return False, f"grading timed out after {timeout}s"
    return r.returncode == 0, (r.stdout + r.stderr)[-3000:]


def add_hidden(hidden: Path, work: Path) -> None:
    """Copy grading-only files (hidden tests) into the workspace."""
    if hidden.exists():
        shutil.copytree(hidden, work, dirs_exist_ok=True)


def copy_repo(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))


def classify(events: list[dict], passed: bool, tampered: bool, changed_files: list[str]) -> str:
    """Mutually exclusive primary failure class, fixed priority order."""
    if passed:
        return "pass"
    end = next((e for e in reversed(events) if e["event"] == "run_end"), None)
    status = end["status"] if end else "error"
    if status == "error" or end is None:
        return "api_error"
    if status == "max_steps":
        return "max_steps"
    if status == "length":
        return "max_tokens"
    if status != "done":
        return f"stopped_{status}"      # e.g. content_filter
    # Editing test files is recorded as a flag (tampered_tests) but is not a failure class of its own:
    # the pristine tests are restored before grading, so it cannot change the outcome, and a class
    # would hide the real reason the run failed.
    if not changed_files:
        return "no_edit"
    return "tests_failed_after_edit"


_TEST_CMD = re.compile(r"pytest|unittest|py\.test|\btest\b")
_PASSED = re.compile(r"\b\d+ passed\b")
_RED = re.compile(r"\b\d+ (failed|error)|FAILED|Error|Traceback|no tests ran", re.I)


def last_test_green(events: list[dict]) -> bool | None:
    """Did the agent's own last test run (via bash) come out green? None if it never ran tests.
    Combined with a failed grade this is a *false completion*: it verified, saw green, stopped."""
    last = None
    for e in events:
        if e["event"] == "tool_result" and e["name"] == "bash" and not e["is_error"]:
            if _TEST_CMD.search(str(e["input"].get("command", ""))):
                out = str(e["output"])
                last = bool(_PASSED.search(out)) and not _RED.search(out)
    return last


def trajectory_stats(events: list[dict]) -> dict:
    calls = [e for e in events if e["event"] == "model_call"]
    tools = [e for e in events if e["event"] == "tool_result"]
    u = lambda k: sum(c["usage"].get(k, 0) or 0 for c in calls)
    total_in, cached = u("input_tokens"), u("cache_hit_tokens")  # input_tokens already includes cached
    return {
        "response_models": sorted({c.get("response_model") or "" for c in calls} - {""}),
        "steps": len(calls),
        "uncached_input_tokens": total_in - cached,
        "cache_read_tokens": cached,
        "cache_creation_tokens": 0,
        "output_tokens": u("output_tokens"),
        "reasoning_tokens": u("reasoning_tokens"),
        "truncated_calls": sum(1 for c in calls if c.get("finish_reason") == "length"),
        "model_latency_s": round(sum(c["latency_s"] for c in calls), 2),
        "last_test_green": last_test_green(events),
        "tool_calls": len(tools),
        "tool_errors": sum(1 for t in tools if t["is_error"]),
        "blocked_commands": sum(1 for t in tools if "blocked by safety policy" in str(t["output"])),
        "compactions": sum(1 for e in events if e["event"] == "compaction" and e["kind"] == "summary"),
    }
