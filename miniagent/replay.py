"""Record and replay model responses, so loop/harness changes can be checked without calling a model.

Two clients, both with the same `.chat()` signature as `ChatClient`:

* `CassetteClient`: a response cache keyed by a hash of the whole request. Modes: "record" (always call the real
  client and store the answer), "auto" (use a stored answer, else call and store), "replay" (stored answers only; a
  request that was never recorded raises `ReplayMiss` instead of quietly reaching the network). The key covers
  model, system, tools, messages, max_tokens, temperature and a caller-supplied `fingerprint` (use the config hash:
  provider-side options such as extra_body are not visible here). Because the key includes the full message list, a
  hit needs byte-identical history, so tool outputs must be reproducible (timings in pytest output, temp paths in
  `ls -la` and similar will miss). It is a cache for reruns of the same setup, not a way to replay a past run.

* `TrajectoryReplayClient`: feeds the model answers stored in an old `trajectory.jsonl` back to the loop in the order
  they were given, ignoring the request. Tools run for real in a fresh copy of the task, so what it checks is the
  loop itself: given the same model answers, does the current code take the same steps, compact at the same points
  and end the same way?
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict
from pathlib import Path

from .client import ModelResponse, ToolCall

_ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0, "cache_hit_tokens": 0}


class ReplayMiss(Exception):
    """A request has no recorded answer (or the recorded trajectory ran out / went out of step)."""


def request_key(*, model: str, messages: list, system: str | None = None, tools: list | None = None,
                max_tokens: int = 4096, temperature: float | None = None, fingerprint: str = "") -> str:
    blob = json.dumps({"model": model, "system": system, "tools": tools, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature, "fingerprint": fingerprint},
                      sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def response_to_dict(r: ModelResponse) -> dict:
    return asdict(r)


def response_from_dict(d: dict) -> ModelResponse:
    return ModelResponse(
        text=d.get("text", ""),
        tool_calls=[ToolCall(c["id"], c["name"], c["arguments"], dict(c.get("extra") or {})) for c in d.get("tool_calls", [])],
        finish_reason=d.get("finish_reason", "stop"), usage=dict(d.get("usage") or _ZERO_USAGE),
        model=d.get("model", ""), reasoning=d.get("reasoning", ""))


class CassetteClient:
    MODES = ("auto", "record", "replay")

    def __init__(self, path: str | Path, inner=None, mode: str = "auto", fingerprint: str = ""):
        if mode not in self.MODES:
            raise ValueError(f"unknown cassette mode {mode!r}")
        if mode != "replay" and inner is None:
            raise ValueError(f"mode {mode!r} needs a real client to call")
        self.path, self.inner, self.mode, self.fingerprint = Path(path), inner, mode, fingerprint
        self.hits = self.misses = 0
        self._lock = threading.Lock()
        self._store: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._store[rec["key"]] = rec["response"]          # a later entry replaces an earlier one

    def chat(self, *, model: str, messages: list, system: str | None = None, tools: list | None = None,
             max_tokens: int = 4096, temperature: float | None = None) -> ModelResponse:
        key = request_key(model=model, messages=messages, system=system, tools=tools, max_tokens=max_tokens,
                          temperature=temperature, fingerprint=self.fingerprint)
        if self.mode != "record":
            with self._lock:
                stored = self._store.get(key)
                if stored is not None:
                    self.hits += 1
                    return response_from_dict(stored)       # a fresh object: the loop may not alter the store
        if self.mode == "replay":
            with self._lock:
                self.misses += 1
            raise ReplayMiss(f"no recorded response for this request (key {key}, {len(messages)} messages, model {model})")
        resp = self.inner.chat(model=model, messages=messages, system=system, tools=tools,
                               max_tokens=max_tokens, temperature=temperature)
        with self._lock:
            self.misses += 1
            self._store[key] = response_to_dict(resp)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "model": model, "n_messages": len(messages),
                                    "response": self._store[key]}, ensure_ascii=False) + "\n")
        return resp


class TrajectoryReplayClient:
    """Plays the answers recorded in a trajectory back in order. `kind` tells a main step from a compaction summary."""

    def __init__(self, events: list[dict]):
        self.queue: list[tuple[str, ModelResponse]] = []
        for e in events:
            if e["event"] == "model_call":
                calls = []
                for c in e["tool_calls"]:
                    inp = c["input"]
                    # a call whose arguments were not valid JSON was logged as {"_raw_arguments": <the raw string>}
                    args = inp["_raw_arguments"] if set(inp) == {"_raw_arguments"} else json.dumps(inp, ensure_ascii=False)
                    calls.append(ToolCall(c["id"], c["name"], args, dict(c.get("extra") or {})))
                self.queue.append(("main", ModelResponse(e["text"], calls, e["finish_reason"], dict(e["usage"]),
                                                         e.get("response_model", ""), e.get("reasoning", ""))))
            elif e["event"] == "compaction" and e["kind"] in ("summary", "summary_failed"):
                self.queue.append(("summary", ModelResponse(e.get("summary", ""), [], e.get("finish_reason", "stop"),
                                                            dict(_ZERO_USAGE))))
        self.served = 0

    @classmethod
    def from_file(cls, path: str | Path) -> "TrajectoryReplayClient":
        return cls([json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()])

    @property
    def remaining(self) -> int:
        return len(self.queue)

    def chat(self, *, model: str, messages: list, system: str | None = None, tools: list | None = None,
             max_tokens: int = 4096, temperature: float | None = None) -> ModelResponse:
        if not self.queue:
            raise ReplayMiss(f"the recorded trajectory has no more answers (served {self.served})")
        kind = "summary" if system is None else "main"      # the loop sends no system prompt with a summary request
        if self.queue[0][0] != kind:
            raise ReplayMiss(f"out of step: the loop made a {kind} request, the recording has a {self.queue[0][0]} answer next "
                             f"(served {self.served})")
        self.served += 1
        return self.queue.pop(0)[1]
