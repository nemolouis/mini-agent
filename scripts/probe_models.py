#!/usr/bin/env python3
"""Probe which models a key can really use for an agent: one tiny tool-calling request each.

    GEMINI_API_KEY=... python3 scripts/probe_models.py [model ...]

For every model prints the HTTP status, whether it answered with a tool call, latency, and
the limit / retry hint if the request was rejected for quota. A rejection with "limit: 0"
means the model is not available on your free project. The daily request limit itself is
only revealed when it is exhausted; AI Studio's rate-limit page lists it up front.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("PROBE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
KEY = os.environ.get("PROBE_API_KEY_ENV", "GEMINI_API_KEY")
DEFAULT = ["gemma-4-31b-it", "gemma-4-26b-a4b-it", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite",
           "gemini-3.6-flash", "gemini-3.8-flash"]


def probe(model, key):
    body = {
        "model": model, "max_tokens": 512,
        "messages": [{"role": "system", "content": "You are a tool-using agent."},
                     {"role": "user", "content": "Use the add tool to compute 2 + 3."}],
        "tools": [{"type": "function", "function": {
            "name": "add", "description": "Add two integers.",
            "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                           "required": ["a", "b"]}}}],
    }
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read())
        msg = data["choices"][0]["message"]
        ok = bool(msg.get("tool_calls"))
        return "OK" if ok else "NO-TOOL-CALL", f"{time.time() - t0:.1f}s", \
            ("tool call returned" if ok else f"text answer: {(msg.get('content') or '')[:80]!r}")
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        lim = re.search(r"limit:\s*(\d+)", text)
        retry = re.search(r"retry in\s*([\dhms.]+)", text, re.I)
        msg = re.sub(r"\s+", " ", text)
        if e.code == 429:
            return "QUOTA", f"{time.time() - t0:.1f}s", f"429 limit={lim.group(1) if lim else '?'} retry_in={retry.group(1) if retry else '?'}"
        return f"HTTP {e.code}", f"{time.time() - t0:.1f}s", msg[:160]
    except Exception as e:  # network etc.
        return "ERROR", f"{time.time() - t0:.1f}s", repr(e)[:120]


def main():
    key = os.environ.get(KEY)
    if not key:
        sys.exit(f"set {KEY} first")
    models = sys.argv[1:] or DEFAULT
    print(f"{'model':28} {'result':14} {'time':7} detail")
    for m in models:
        res, t, detail = probe(m, key)
        print(f"{m:28} {res:14} {t:7} {detail}")
        time.sleep(1)


if __name__ == "__main__":
    main()
