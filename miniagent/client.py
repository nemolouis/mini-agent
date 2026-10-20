"""Minimal chat-completions client for OpenAI-compatible endpoints (DeepSeek by
default; GLM/Zhipu and others via base_url). Standard library only; the agent loop
depends solely on `ChatClient.chat()` and the `ModelResponse` it returns.

Configuration, in order of precedence:
  api key:  api_key argument > $LLM_API_KEY > $DEEPSEEK_API_KEY
  base url: base_url argument > $LLM_BASE_URL > $DEEPSEEK_BASE_URL > DeepSeek's endpoint
  extra_body: provider-specific request fields merged into every request body
              (e.g. {"thinking": {"type": "disabled"}} for GLM)."""
from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

DEFAULT_BASE_URL = "https://api.deepseek.com"
_RETRY_STATUS = {429, 500, 502, 503, 504}


class APIError(Exception):
    pass


class QuotaExhausted(APIError):
    """A 429 whose suggested retry delay is far too long to wait (daily free-tier quota)."""

    def __init__(self, message: str, retry_after_s: float):
        super().__init__(message)
        self.retry_after_s = retry_after_s


_RETRY_IN = re.compile(r"retry in\s+(?:(\d+)h)?\s*(?:(\d+)m)?\s*([\d.]+)s", re.I)
QUOTA_WAIT_LIMIT_S = 600.0  # a server-suggested wait longer than this is treated as quota exhaustion


def suggested_delay(body: str) -> float | None:
    """Seconds the server asks us to wait ('Please retry in 14h4m26.1s' / 'retryDelay: 50s')."""
    m = _RETRY_IN.search(body)
    if m:
        return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3))
    m = re.search(r'"retryDelay"\s*:\s*"([\d.]+)s"', body)
    return float(m.group(1)) if m else None


def extract_text_tool_calls(text: str, tool_names: set[str]) -> tuple[str, list["ToolCall"]]:
    """Tool calls written as plain JSON objects in the reply text -> (text without them, calls).

    For a model that cannot emit its chat template's tool-call markers. The case that motivated it: in Qwen2.5-Coder-1.5B the
    embeddings of <tool_call> / </tool_call> are untrained placeholders, practically equal to that of token 124, and the output
    layer is tied to the embeddings, so a fine-tuned model that has learned the whole format still emits token 124 (decoded as
    U+FFFD) where the markers belong, and the server never sees a tool call. Only objects {"name": <an offered tool>,
    "arguments": {...}} count; stray U+FFFD characters and marker strings are dropped from the remaining text."""
    dec, calls, out, i = json.JSONDecoder(), [], [], 0
    while i < len(text):
        if text[i] == "{":
            try:
                obj, end = dec.raw_decode(text, i)
            except ValueError:
                obj, end = None, i
            if isinstance(obj, dict) and obj.get("name") in tool_names and isinstance(obj.get("arguments", {}), (dict, str)):
                args = obj.get("arguments", {})
                calls.append(ToolCall(f"call_{len(calls)}", obj["name"], args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)))
                i = end
                continue
        out.append(text[i])
        i += 1
    cleaned = "".join(out).replace("\ufffd", "").replace("<tool_call>", "").replace("</tool_call>", "")
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip() if calls else text, calls


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON string exactly as emitted by the model
    # provider-specific fields attached to the call (e.g. Gemini's extra_content.google.thought_signature);
    # kept verbatim and echoed back when the assistant message is replayed in the history
    extra: dict = field(default_factory=dict)


@dataclass
class ModelResponse:
    text: str
    tool_calls: list[ToolCall]
    finish_reason: str  # stop | tool_calls | length | ...
    usage: dict  # input_tokens, output_tokens, cache_hit_tokens
    model: str = ""  # model name the server reports having used (may differ from the alias requested)
    reasoning: str = ""  # visible thinking text when the provider returns it (never sent back in the history)


class ChatClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 timeout: float = 120, retries: int = 6, extra_body: dict | None = None,
                 tool_result_json: bool = False, api_style: str = "openai", text_tool_calls: bool = False):
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL")
                         or os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        # DEEPSEEK_API_KEY is only a fallback for DeepSeek's own endpoint: falling back to it for an
        # arbitrary base_url (a relay, another vendor) would hand that third party the DeepSeek key.
        key = api_key or os.environ.get("LLM_API_KEY")
        if not key and "deepseek" in self.base_url:
            key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise APIError(f"no API key for {self.base_url}: set LLM_API_KEY (or pass api_key / api_key_env)")
        self.api_key = key
        self.timeout = timeout
        self.retries = retries
        self.extra_body = dict(extra_body or {})
        # Gemini's native functionResponse must be a JSON *object*. Some OpenAI-compatible relays pass the
        # tool message content through unchanged, so a plain-text result is rejected with HTTP 400.
        self.tool_result_json = tool_result_json
        # "openai": POST {base}/chat/completions.  "gemini": the native generateContent protocol,
        # for relays that translate (and break) OpenAI-format tool calls: they forward native calls untouched.
        if api_style not in ("openai", "gemini"):
            raise APIError(f"unknown api_style {api_style!r}")
        self.api_style = api_style
        # read tool calls written as plain JSON in the reply text when the server returns none (see extract_text_tool_calls)
        self.text_tool_calls = text_tool_calls
        if api_style == "gemini" and "/v1" not in urllib.parse.urlparse(self.base_url).path:
            self.base_url += "/v1beta"

    def chat(self, *, model: str, messages: list[dict], system: str | None = None,
             tools: list[dict] | None = None, max_tokens: int = 4096,
             temperature: float | None = None) -> ModelResponse:
        impl = self._chat_gemini if self.api_style == "gemini" else self._chat_openai
        return impl(model=model, messages=messages, system=system, tools=tools,
                    max_tokens=max_tokens, temperature=temperature)

    # ------------------------------------------------------------------ Gemini native
    @staticmethod
    def _gemini_schema(schema):
        """Gemini accepts an OpenAPI subset: drop keys it rejects, recurse into the rest."""
        if isinstance(schema, dict):
            return {k: ChatClient._gemini_schema(v) for k, v in schema.items()
                    if k not in ("additionalProperties", "$schema", "default", "title")}
        if isinstance(schema, list):
            return [ChatClient._gemini_schema(v) for v in schema]
        return schema

    @staticmethod
    def _to_gemini_contents(messages: list[dict]) -> list[dict]:
        names, contents, pending = {}, [], []

        def flush():
            if pending:                 # all results of one model turn go into a single user content
                contents.append({"role": "user", "parts": list(pending)})
                pending.clear()

        for m in messages:
            role = m["role"]
            if role == "tool":
                content = m.get("content")
                try:
                    obj = json.loads(content)
                    resp = obj if isinstance(obj, dict) else {"output": content}
                except (TypeError, ValueError):
                    resp = {"output": content}
                pending.append({"functionResponse": {
                    "name": m.get("name") or names.get(m.get("tool_call_id"), "tool"), "response": resp}})
                continue
            flush()
            if role == "user":
                contents.append({"role": "user", "parts": [{"text": m["content"]}]})
            elif role == "assistant":
                parts = [{"text": m["content"]}] if m.get("content") else []
                for c in m.get("tool_calls") or []:
                    fn = c["function"]
                    names[c["id"]] = fn["name"]
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except ValueError:
                        args = {}
                    part = {"functionCall": {"name": fn["name"], "args": args if isinstance(args, dict) else {}}}
                    sig = c.get("thought_signature") or \
                        ((c.get("extra_content") or {}).get("google") or {}).get("thought_signature")
                    if sig:
                        part["thoughtSignature"] = sig
                    parts.append(part)
                contents.append({"role": "model", "parts": parts or [{"text": ""}]})
        flush()
        return contents

    def _chat_gemini(self, *, model, messages, system, tools, max_tokens, temperature) -> ModelResponse:
        body: dict = {"contents": self._to_gemini_contents(messages),
                      "generationConfig": {"maxOutputTokens": max_tokens}}
        if temperature is not None:
            body["generationConfig"]["temperature"] = temperature
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            body["tools"] = [{"functionDeclarations": [
                {"name": t["function"]["name"], "description": t["function"].get("description", ""),
                 "parameters": self._gemini_schema(t["function"].get("parameters") or {"type": "object", "properties": {}})}
                for t in tools]}]
        _deep_update(body, self.extra_body)
        data = self._post(f"/models/{model}:generateContent", body)

        cands = data.get("candidates") or []
        if not cands:
            reason = (data.get("promptFeedback") or {}).get("blockReason") or "no_candidates"
            return ModelResponse("", [], reason.lower(), self._gemini_usage(data), model=data.get("modelVersion") or "")
        parts = (cands[0].get("content") or {}).get("parts") or []
        text = "".join(p["text"] for p in parts if isinstance(p.get("text"), str) and not p.get("thought"))
        reasoning = "".join(p["text"] for p in parts if isinstance(p.get("text"), str) and p.get("thought"))
        calls = []
        for p in parts:
            fc = p.get("functionCall")
            if fc:
                extra = {"thought_signature": p["thoughtSignature"]} if p.get("thoughtSignature") else {}
                calls.append(ToolCall(fc.get("id") or f"call_{len(calls)}", fc["name"],
                                      json.dumps(fc.get("args") or {}, ensure_ascii=False), extra))
        reason = (cands[0].get("finishReason") or "STOP").upper()
        finish = "tool_calls" if calls else {"STOP": "stop", "MAX_TOKENS": "length"}.get(reason, reason.lower())
        return ModelResponse(text, calls, finish, self._gemini_usage(data), model=data.get("modelVersion") or "",
                             reasoning=reasoning)

    @staticmethod
    def _gemini_usage(data: dict) -> dict:
        u = data.get("usageMetadata") or {}
        thoughts = u.get("thoughtsTokenCount", 0) or 0
        return {
            "input_tokens": u.get("promptTokenCount", 0) or 0,          # includes cached tokens
            "output_tokens": (u.get("candidatesTokenCount", 0) or 0) + thoughts,   # thinking is billed as output
            "cache_hit_tokens": u.get("cachedContentTokenCount", 0) or 0,
            "reasoning_tokens": thoughts,
            "reasoning_chars": 0,
        }

    # ------------------------------------------------------------------ OpenAI-style
    def _chat_openai(self, *, model: str, messages: list[dict], system: str | None = None,
                     tools: list[dict] | None = None, max_tokens: int = 4096,
                     temperature: float | None = None) -> ModelResponse:
        body: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": ([{"role": "system", "content": system}] if system else []) + self._prepare(messages),
        }
        if tools:
            body["tools"] = tools
        if temperature is not None:
            body["temperature"] = temperature
        body.update(self.extra_body)
        data = self._post("/chat/completions", body)
        try:
            choice = data["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError, TypeError):
            raise APIError(f"unexpected response: {str(data)[:300]}")
        calls = [ToolCall(c.get("id") or f"call_{i}", c["function"]["name"], c["function"].get("arguments") or "{}",
                          {k: v for k, v in c.items() if k not in ("id", "type", "function", "index")})
                 for i, c in enumerate(msg.get("tool_calls") or [])]
        text = msg.get("content") or ""
        finish = choice.get("finish_reason") or "stop"
        if self.text_tool_calls and not calls and tools:
            text, calls = extract_text_tool_calls(text, {t["function"]["name"] for t in tools})
            if calls and finish == "stop":
                finish = "tool_calls"
        u = data.get("usage") or {}
        usage = {
            "input_tokens": u.get("prompt_tokens", 0) or 0,  # includes cached prefix tokens
            "output_tokens": u.get("completion_tokens", 0) or 0,
            # DeepSeek reports prompt_cache_hit_tokens; OpenAI-style APIs (GLM) report
            # prompt_tokens_details.cached_tokens
            "cache_hit_tokens": (u.get("prompt_cache_hit_tokens")
                                 or (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0),
            # visibility into hidden thinking: both are 0 when the provider does not report them
            "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0,
            "reasoning_chars": len(msg.get("reasoning_content") or ""),
        }
        return ModelResponse(text, calls, finish, usage,
                             model=data.get("model") or "", reasoning=msg.get("reasoning_content") or "")

    def _prepare(self, messages: list[dict]) -> list[dict]:
        """Provider quirks applied only on the wire; the agent's own history is left untouched."""
        if not self.tool_result_json:
            return messages
        names = {}
        for m in messages:
            for c in m.get("tool_calls") or []:
                names[c["id"]] = c["function"]["name"]
        out = []
        for m in messages:
            if m.get("role") != "tool":
                out.append(m)
                continue
            content = m.get("content")
            try:
                is_obj = isinstance(json.loads(content), dict)
            except (TypeError, ValueError):
                is_obj = False
            new = {**m, "content": content if is_obj else json.dumps({"output": content}, ensure_ascii=False)}
            if m.get("tool_call_id") in names:
                new["name"] = names[m["tool_call_id"]]
            out.append(new)
        return out

    @staticmethod
    def _delay(attempt: int, status: int | None, retry_after: str | None) -> float:
        """Backoff before a retry: honour Retry-After; rate limiting (429) waits longer
        because free tiers stay overloaded for tens of seconds; capped at 60 s plus jitter."""
        if retry_after and retry_after.strip().isdigit():
            return min(float(retry_after), 120.0)
        base = 5.0 if status == 429 else 1.0
        return min(base * 2 ** attempt, 60.0) + random.random()

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + path, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json",
                     **({"x-goog-api-key": self.api_key} if self.api_style == "gemini"
                        else {"Authorization": f"Bearer {self.api_key}"})},
        )
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                full = e.read().decode("utf-8", "replace")
                detail = full[:500]
                wait = suggested_delay(full) if e.code == 429 else None
                if wait is not None and wait > QUOTA_WAIT_LIMIT_S:
                    raise QuotaExhausted(f"HTTP 429 quota exhausted, server says retry in {wait / 3600:.1f} h: {detail}", wait)
                if e.code in _RETRY_STATUS and attempt < self.retries:
                    if wait is not None:       # a short, explicit server hint beats our own backoff
                        time.sleep(min(wait + 1.0, 120.0))
                    else:
                        time.sleep(self._delay(attempt, e.code, e.headers.get("Retry-After")))
                    continue
                raise APIError(f"HTTP {e.code}: {detail}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < self.retries:
                    time.sleep(self._delay(attempt, None, None))
                    continue
                raise APIError(f"network error: {e}")
        raise APIError("unreachable")


def _deep_update(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v
    return dst
