#!/usr/bin/env python3
"""Diagnose how an OpenAI-compatible relay handles Gemini 3 tool calls and thought signatures.

Usage:  RELAY_BASE_URL=https://host/v1 RELAY_API_KEY=... python3 scripts/probe_relay.py [model]

It makes a handful of tiny requests (about 5, each a few hundred tokens), prints the *structure* of
the assistant message the relay returns (long strings truncated, the key is never printed), and then
tries several ways of replaying the tool call so we know which one the relay accepts.
"""
import copy
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("RELAY_BASE_URL", "").rstrip("/")
KEY = os.environ.get("RELAY_API_KEY", "")
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.1-flash-lite"
if not BASE or not KEY:
    sys.exit("set RELAY_BASE_URL and RELAY_API_KEY")

TOOLS = [{"type": "function", "function": {
    "name": "bash", "description": "Run a shell command.",
    "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}}]


def post(body):
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:600]
    except Exception as e:
        return 0, repr(e)


def shape(x, depth=0):
    """Same JSON with long strings abbreviated, so signatures are visible but not huge."""
    if isinstance(x, dict):
        return {k: shape(v, depth + 1) for k, v in x.items()}
    if isinstance(x, list):
        return [shape(v, depth + 1) for v in x]
    if isinstance(x, str) and len(x) > 60:
        return x[:40] + f"...<{len(x)} chars>"
    return x


def find_signature_paths(x, path=""):
    hits = []
    if isinstance(x, dict):
        for k, v in x.items():
            p = f"{path}.{k}" if path else k
            if "signature" in k.lower() or "thought" in k.lower() or k in ("extra_content", "provider_specific_fields"):
                hits.append(p)
            hits += find_signature_paths(v, p)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            hits += find_signature_paths(v, f"{path}[{i}]")
    elif isinstance(x, str) and ("thought" in x.lower() and "__" in x):
        hits.append(f"{path} (value contains '__thought__'-style marker)")
    return hits


user = {"role": "user", "content": "Use the bash tool to run `ls`. Call the tool now."}
print(f"model={MODEL} base={BASE}\n")
status, data = post({"model": MODEL, "messages": [user], "tools": TOOLS, "max_tokens": 2048})
print("1) first request:", status)
if status != 200:
    sys.exit(f"   failed: {data}")
msg = data["choices"][0]["message"]
print("   assistant message structure:")
print(json.dumps(shape(msg), indent=2, ensure_ascii=False))
print("   fields that look like signatures:", find_signature_paths(data) or "NONE FOUND")
if not msg.get("tool_calls"):
    sys.exit("   the model did not call the tool; rerun")

tool_msg = {"role": "tool", "tool_call_id": msg["tool_calls"][0].get("id") or "call_0", "name": "bash",
            "content": json.dumps({"output": "exit code: 0\nfoo.py"})}


def attempt(label, assistant):
    s, d = post({"model": MODEL, "messages": [user, assistant, tool_msg], "tools": TOOLS, "max_tokens": 2048})
    ok = s == 200
    print(f"   {label:55s} -> {'OK' if ok else 'FAIL ' + str(s)}")
    if not ok:
        print("      ", str(d)[:300].replace("\n", " "))
    return ok


print("\n2) replay strategies (assistant message as sent back in the second turn):")
orig = {"role": "assistant", "content": msg.get("content"), "tool_calls": msg["tool_calls"]}
for k in msg:                       # keep any message-level extras exactly as received
    if k not in ("role", "content", "tool_calls", "refusal", "annotations", "audio"):
        orig[k] = msg[k]
results = {}
results["as_received"] = attempt("A. exactly as received", copy.deepcopy(orig))

b = copy.deepcopy(orig)
for tc in b["tool_calls"]:
    tc.setdefault("extra_content", {}).setdefault("google", {})["thought_signature"] = "skip_thought_signature_validator"
results["dummy_extra_content"] = attempt("B. dummy signature in extra_content.google", b)

c = copy.deepcopy(orig)
for tc in c["tool_calls"]:
    tc["thought_signature"] = "skip_thought_signature_validator"
results["dummy_toplevel"] = attempt("C. dummy signature as tool_call.thought_signature", c)

d = copy.deepcopy(orig)
for tc in d["tool_calls"]:
    tc["provider_specific_fields"] = {"thought_signature": "skip_thought_signature_validator"}
results["dummy_provider_fields"] = attempt("D. dummy signature in provider_specific_fields", d)

print("\nSummary:", {k: ("OK" if v else "fail") for k, v in results.items()})
