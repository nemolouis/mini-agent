"""The agent loop, written directly against the chat-completions tool-calling protocol."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Callable

from .client import ModelResponse
from .sandbox import SandboxError
from .tools import Tool, ToolError, Workspace, build_tools
from .trajectory import Trajectory

SYSTEM_PROMPT = """You are a coding agent working inside a git-style repository. \
Your job is to fix the bug or complete the task the user describes.

Work method: explore first (grep, read_file), form a hypothesis, make the smallest \
edit that fixes the root cause, then run the project's tests with bash to verify. \
Do not edit tests to make them pass. Paths are relative to the workspace root, and bash already runs there: do not cd elsewhere. \
When you are done, reply with a short summary of what you changed and the test result, \
and make no further tool calls."""

SUMMARY_PROMPT = """Below is the transcript of an agent working on a coding task. Write a \
dense progress summary the agent can continue from: files inspected and what was learned, \
edits made (file + what changed), commands run and their outcomes, current hypothesis, \
and what remains. Do not invent anything."""


@dataclass
class RunResult:
    status: str  # done | max_steps | length | error
    steps: int
    final_text: str
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


@dataclass
class Agent:
    client: object  # miniagent.client.ChatClient or anything with a compatible .chat()
    model: str
    workspace: Workspace
    confirm: Callable[[str, dict], bool] = lambda name, args: True
    trajectory: Trajectory = field(default_factory=lambda: Trajectory(None))
    max_steps: int = 30
    max_tokens: int = 4096
    context_limit: int = 100_000  # compact when input tokens exceed 70% of this
    keep_recent: int = 8  # messages kept verbatim during compaction
    # If a compaction cannot bring the next request below the 70% threshold (the prompt, the tool definitions and the
    # verbatim recent messages are already too big), compacting again at once cannot help. The loop then waits until the
    # input has grown by this fraction of its post-compaction size (1.0 = it may double). When the last compaction did
    # get below the threshold nothing changes: the trigger stays at 70% of context_limit.
    compact_regrowth: float = 1.0
    system: str = SYSTEM_PROMPT
    temperature: float | None = None  # None -> API default; evals should set it
    disabled_tools: tuple[str, ...] = ()
    meta: dict = field(default_factory=dict)  # task_id, config name, ... -> run_start
    extra_tools: dict = field(default_factory=dict)  # e.g. MCP tools: name -> Tool (see miniagent.mcp.client)
    log_reasoning: bool = False  # also write the model's visible thinking into model_call events (large; for SFT data)

    def __post_init__(self):
        self.tools: dict[str, Tool] = {
            n: t for n, t in {**build_tools(self.workspace), **self.extra_tools}.items() if n not in self.disabled_tools
        }

    # ------------------------------------------------------------ main loop
    def run(self, task: str) -> RunResult:
        messages: list[dict] = [{"role": "user", "content": task}]
        self.trajectory.log(
            "run_start", task=task, model=self.model, meta=self.meta,
            config={"max_steps": self.max_steps, "context_limit": self.context_limit,
                    "keep_recent": self.keep_recent, "compact_regrowth": self.compact_regrowth, "max_tokens": self.max_tokens,
                    "temperature": self.temperature, "tools": sorted(self.tools),
                    "system_sha1": hashlib.sha1(self.system.encode()).hexdigest()[:12]},
            # full text, so the exact model input can be rebuilt later (SFT export) without guessing from a hash
            system=self.system, tool_specs=[t.spec() for t in self.tools.values()])
        in_tok = out_tok = 0
        last_input = 0
        floor: int | None = None        # input tokens measured on the first request after the latest compaction
        awaiting_floor = False
        final_text = ""
        status = "max_steps"
        step = 0
        try:
            for step in range(1, self.max_steps + 1):
                if last_input > self._compact_trigger(floor):
                    messages = self._compact(messages, trigger_tokens=last_input)
                    awaiting_floor = True
                    last_input = 0

                t0 = time.time()
                resp: ModelResponse = self.client.chat(
                    model=self.model, max_tokens=self.max_tokens, system=self.system,
                    tools=[t.spec() for t in self.tools.values()], messages=messages,
                    temperature=self.temperature,
                )
                calls = [_parse_call(c) for c in resp.tool_calls]
                last_input = resp.usage["input_tokens"]
                if awaiting_floor:
                    floor, awaiting_floor = last_input, False
                    if floor >= self.context_limit * 0.7:
                        self.trajectory.log("compaction_floor", step=step, input_tokens=floor,
                                            threshold=int(self.context_limit * 0.7), next_trigger=int(self._compact_trigger(floor)),
                                            note="compaction could not get below the threshold; next one waits for regrowth")
                in_tok += last_input
                out_tok += resp.usage["output_tokens"]
                self.trajectory.log(
                    "model_call", step=step, latency_s=round(time.time() - t0, 3),
                    finish_reason=resp.finish_reason, text=resp.text, response_model=resp.model,
                    # `extra` = provider fields echoed back in the history (Gemini thought signatures); kept so that a
                    # replay rebuilds a history of the same size, which the compaction decisions depend on
                    tool_calls=[{"id": c["id"], "name": c["name"], "input": c["input"], **({"extra": r.extra} if r.extra else {})}
                                for c, r in zip(calls, resp.tool_calls)],
                    usage=resp.usage,
                    **({"reasoning": resp.reasoning} if self.log_reasoning and resp.reasoning else {}),
                )
                messages.append(_assistant_message(resp))
                final_text = resp.text

                if resp.tool_calls:
                    messages.extend(self._run_tool(step, c) for c in calls)
                    continue
                status = "done" if resp.finish_reason == "stop" else resp.finish_reason
                break
        except Exception as e:  # API failure etc.; keep the trajectory consistent
            self.trajectory.log("run_end", status="error", steps=step, error=repr(e),
                                input_tokens=in_tok, output_tokens=out_tok, final_text=final_text)
            return RunResult("error", step, final_text, in_tok, out_tok, repr(e))

        self.trajectory.log("run_end", status=status, steps=step, input_tokens=in_tok,
                            output_tokens=out_tok, final_text=final_text)
        return RunResult(status, step, final_text, in_tok, out_tok)

    # ---------------------------------------------------------------- tools
    def _run_tool(self, step: int, call: dict) -> dict:
        name, args = call["name"], call["input"]
        t0 = time.time()
        approved, is_error = True, False
        tool = self.tools.get(name)
        if tool is None:
            out, is_error = f"unknown tool: {name}", True
        elif call.get("parse_error"):
            out, is_error = f"error: arguments are not valid JSON ({call['parse_error']})", True
        else:
            if tool.needs_confirm and not self.confirm(name, args):
                approved, is_error, out = False, True, "user denied this action; try a different approach or explain why it is needed"
            else:
                try:
                    out = tool.func(args)
                except ToolError as e:
                    out, is_error = f"error: {e}", True
                except SandboxError:
                    raise          # infrastructure fault: ends the run as an error, is not shown to the model as a tool result
                except (KeyError, TypeError, ValueError) as e:
                    out, is_error = f"error: bad arguments ({e!r})", True
                except Exception as e:  # tool bug must not kill the run
                    out, is_error = f"error: {type(e).__name__}: {e}", True
        self.trajectory.log("tool_result", step=step, tool_call_id=call["id"], name=name, input=args,
                            output=out, is_error=is_error, approved=approved,
                            duration_s=round(time.time() - t0, 3))
        return {"role": "tool", "tool_call_id": call["id"], "content": out}

    # ----------------------------------------------------------- compaction
    def _compact_trigger(self, floor: int | None) -> float:
        """Input-token count above which the history is compacted."""
        base = self.context_limit * 0.7
        if floor is None or floor < base:        # no compaction yet, or the last one worked: original behaviour
            return base
        return floor * (1 + self.compact_regrowth)

    def _compact(self, messages: list[dict], trigger_tokens: int | None = None) -> list[dict]:
        before = _estimate_tokens(messages)
        # Stage 1: elide old tool outputs (cheap, lossless for the structure).
        cutoff = max(len(messages) - self.keep_recent, 1)
        out = [m for m in messages]
        for i in range(1, cutoff):
            m = out[i]
            if m["role"] == "tool" and len(m["content"]) > 200:
                out[i] = {**m, "content": f"[elided {len(m['content'])} chars]"}
        after = _estimate_tokens(out)
        self.trajectory.log("compaction", kind="elide", est_tokens_before=before, est_tokens_after=after,
                            trigger_input_tokens=trigger_tokens)
        if after <= self.context_limit * 0.5:
            return out

        # Stage 2: summarise the middle. Tail must start at an assistant message so
        # tool_calls/tool-result pairs stay intact and roles keep alternating.
        i = max(len(out) - self.keep_recent, 1)
        while i < len(out) and out[i]["role"] != "assistant":
            i += 1
        if i >= len(out) or i <= 1:
            return out
        transcript = _render(messages[1:i])  # un-elided: elision must not starve the summary
        resp = self.client.chat(
            model=self.model, max_tokens=1500, temperature=self.temperature,
            messages=[{"role": "user", "content": f"{SUMMARY_PROMPT}\n\n<task>\n{out[0]['content']}\n</task>\n\n<transcript>\n{transcript}\n</transcript>"}],
        )
        summary = resp.text
        if not summary.strip():
            # An empty summary (e.g. a thinking model used the whole token budget) would silently delete the middle of the
            # history. Keep it, only the elision of old tool outputs stands, and say so in the trajectory.
            self.trajectory.log("compaction", kind="summary_failed", est_tokens_before=after, est_tokens_after=after,
                                trigger_input_tokens=trigger_tokens, finish_reason=resp.finish_reason)
            return out
        head = {"role": "user", "content": f"{out[0]['content']}\n\n[Progress so far, summarised from earlier steps]\n{summary}"}
        new = [head] + out[i:]
        self.trajectory.log("compaction", kind="summary", est_tokens_before=after,
                            est_tokens_after=_estimate_tokens(new), summary=summary, trigger_input_tokens=trigger_tokens)
        return new


# ------------------------------------------------------------------ helpers
def _parse_call(c) -> dict:
    try:
        args = json.loads(c.arguments or "{}")
        if not isinstance(args, dict):
            raise ValueError("expected a JSON object")
        return {"id": c.id, "name": c.name, "input": args}
    except ValueError as e:
        return {"id": c.id, "name": c.name, "input": {"_raw_arguments": c.arguments}, "parse_error": str(e)}


def _assistant_message(resp: ModelResponse) -> dict:
    msg: dict = {"role": "assistant", "content": resp.text or None}
    if resp.tool_calls:
        msg["tool_calls"] = [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}, **c.extra}
            for c in resp.tool_calls]
    return msg


def _estimate_tokens(messages: list[dict]) -> int:
    return len(json.dumps(messages, ensure_ascii=False)) // 3


def _render(messages: list[dict]) -> str:
    parts = []
    for m in messages:
        if m["role"] == "tool":
            parts.append(f"[result] {str(m['content'])[:500]}")
            continue
        if m.get("content"):
            parts.append(f"[{m['role']}] {m['content']}")
        for c in m.get("tool_calls") or []:
            f = c["function"]
            parts.append(f"[call {f['name']}] {f['arguments'][:500]}")
    return "\n".join(parts)
