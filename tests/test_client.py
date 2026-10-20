import json

import pytest

from miniagent.client import APIError, ChatClient


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(APIError):
        ChatClient()


def test_glm_style_usage_and_extra_body(monkeypatch):
    c = ChatClient(api_key="k", base_url="http://x", extra_body={"thinking": {"type": "disabled"}})
    seen = {}

    def fake_post(path, body):
        seen["body"] = body
        return {"choices": [{"finish_reason": "stop", "message": {"content": "ok", "reasoning_content": "abc"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 5,
                          "prompt_tokens_details": {"cached_tokens": 64}}}

    monkeypatch.setattr(c, "_post", fake_post)
    r = c.chat(model="glm-4.7-flash", messages=[{"role": "user", "content": "hi"}], temperature=0.0)
    assert seen["body"]["thinking"] == {"type": "disabled"} and seen["body"]["temperature"] == 0.0
    assert r.usage["cache_hit_tokens"] == 64 and r.usage["reasoning_chars"] == 3


def test_backoff_on_429_then_success(monkeypatch):
    import io
    import urllib.error
    from miniagent import client as mod

    calls, sleeps = {"n": 0}, []

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}'

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise urllib.error.HTTPError("http://x", 429, "busy", {}, io.BytesIO(b'{"error":{"code":"1305"}}'))
        return Resp()

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    r = ChatClient(api_key="k", base_url="http://x").chat(model="m", messages=[{"role": "user", "content": "hi"}])
    assert r.text == "ok" and calls["n"] == 3
    assert sleeps[0] >= 5 and sleeps[1] >= 10 and sleeps[1] > sleeps[0]


def test_tool_call_extra_fields_roundtrip_and_missing_ids(monkeypatch):
    from miniagent.agent import _assistant_message
    c = ChatClient(api_key="k", base_url="http://x")
    sig = {"google": {"thought_signature": "SIG=="}}

    def fake_post(path, body):
        return {"choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [
            {"id": "", "type": "function", "extra_content": sig,
             "function": {"name": "grep", "arguments": "{}"}},
            {"type": "function", "function": {"name": "bash", "arguments": "{}"}}]}}]}

    monkeypatch.setattr(c, "_post", fake_post)
    r = c.chat(model="m", messages=[{"role": "user", "content": "hi"}])
    assert [t.id for t in r.tool_calls] == ["call_0", "call_1"]       # synthesised when absent/empty
    assert r.tool_calls[0].extra == {"extra_content": sig} and r.tool_calls[1].extra == {}
    replay = _assistant_message(r)["tool_calls"]
    assert replay[0]["extra_content"] == sig and replay[0]["id"] == "call_0"


def test_daily_quota_429_raises_without_waiting(monkeypatch):
    import io
    import urllib.error
    from miniagent import client as mod

    body = (b'{"error": {"code": 429, "message": "You exceeded your current quota. '
            b'Quota exceeded for metric: generate_content_free_tier_requests, limit: 500. '
            b'Please retry in 14h4m26.118483392s."}}')
    sleeps = []

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError("http://x", 429, "quota", {}, io.BytesIO(body))

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    with pytest.raises(mod.QuotaExhausted) as ei:
        ChatClient(api_key="k", base_url="http://x").chat(model="m", messages=[{"role": "user", "content": "hi"}])
    assert sleeps == [] and abs(ei.value.retry_after_s - (14 * 3600 + 4 * 60 + 26.118)) < 0.01


def test_short_server_delay_hint_is_used(monkeypatch):
    import io
    import urllib.error
    from miniagent import client as mod

    assert mod.suggested_delay("Please retry in 23.5s.") == 23.5
    assert mod.suggested_delay('x "retryDelay": "41s" y') == 41.0
    assert mod.suggested_delay("nothing here") is None


def test_deepseek_key_not_sent_to_other_hosts(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    assert ChatClient().api_key == "sk-deepseek"                       # default endpoint: fine
    with pytest.raises(APIError):
        ChatClient(base_url="https://some-relay.example/v1")           # other host: no fallback


def test_tool_results_wrapped_as_json_objects_for_gemini_relays(monkeypatch):
    c = ChatClient(api_key="k", base_url="http://x", tool_result_json=True)
    seen = {}
    monkeypatch.setattr(c, "_post", lambda path, body: seen.setdefault("body", body) and {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})
    history = [
        {"role": "user", "content": "go"},
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": "{}"}},
            {"id": "c2", "type": "function", "function": {"name": "grep", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "exit code: 0\nfoo.py"},
        {"role": "tool", "tool_call_id": "c2", "content": '{"already": "object"}'},
    ]
    c.chat(model="m", messages=history)
    t1, t2 = seen["body"]["messages"][-2:]
    assert json.loads(t1["content"]) == {"output": "exit code: 0\nfoo.py"} and t1["name"] == "bash"
    assert t2["content"] == '{"already": "object"}' and t2["name"] == "grep"
    assert history[2]["content"] == "exit code: 0\nfoo.py" and "name" not in history[2]   # input untouched


def test_env_precedence(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "old")
    monkeypatch.setenv("LLM_API_KEY", "new")
    monkeypatch.setenv("LLM_BASE_URL", "http://glm/v4/")
    c = ChatClient()
    assert c.api_key == "new" and c.base_url == "http://glm/v4"


def test_parses_response_and_builds_request(monkeypatch):
    c = ChatClient(api_key="k", base_url="http://x/")
    seen = {}

    def fake_post(path, body):
        seen.update(path=path, body=body)
        return {"choices": [{"finish_reason": "tool_calls", "message": {
                    "content": None,
                    "tool_calls": [{"id": "c1", "type": "function",
                                    "function": {"name": "grep", "arguments": json.dumps({"pattern": "a"})}}]}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3, "prompt_cache_hit_tokens": 8}}

    monkeypatch.setattr(c, "_post", fake_post)
    r = c.chat(model="m", system="sys", messages=[{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
    assert c.base_url == "http://x"
    assert seen["path"] == "/chat/completions"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "sys"}
    assert r.finish_reason == "tool_calls" and r.text == ""
    assert r.tool_calls[0].name == "grep" and json.loads(r.tool_calls[0].arguments) == {"pattern": "a"}
    assert r.usage == {"input_tokens": 12, "output_tokens": 3, "cache_hit_tokens": 8,
                       "reasoning_tokens": 0, "reasoning_chars": 0}


# ---------------------------------------------------------------- Gemini native protocol

def _gemini_client(**kw):
    return ChatClient(api_key="k", base_url="http://relay.example", api_style="gemini", **kw)


def test_gemini_base_url_gets_v1beta_and_header(monkeypatch):
    import io
    from miniagent import client as mod
    assert _gemini_client().base_url == "http://relay.example/v1beta"
    assert ChatClient(api_key="k", base_url="http://r/v1beta", api_style="gemini").base_url == "http://r/v1beta"
    seen = {}

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"candidates": [{"content": {"parts": [{"text": "hi"}]}, "finishReason": "STOP"}]}'

    def fake_urlopen(req, timeout=None):
        seen["url"], seen["headers"] = req.full_url, {k.lower(): v for k, v in req.header_items()}
        return Resp()

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    r = _gemini_client().chat(model="gemini-3.1-flash-lite", messages=[{"role": "user", "content": "x"}])
    assert seen["url"] == "http://relay.example/v1beta/models/gemini-3.1-flash-lite:generateContent"
    assert seen["headers"]["x-goog-api-key"] == "k" and "authorization" not in seen["headers"]
    assert r.text == "hi" and r.finish_reason == "stop"


def test_gemini_request_building_and_signature_replay(monkeypatch):
    c = _gemini_client(extra_body={"generationConfig": {"thinkingConfig": {"thinkingLevel": "low"}}})
    seen = {}

    def fake_post(path, body):
        seen["path"], seen["body"] = path, body
        return {"candidates": [{"content": {"parts": [{"text": "done"}]}, "finishReason": "STOP"}]}

    monkeypatch.setattr(c, "_post", fake_post)
    tools = [{"type": "function", "function": {"name": "bash", "description": "run",
              "parameters": {"type": "object", "additionalProperties": False,
                             "properties": {"command": {"type": "string"}}, "required": ["command"]}}}]
    history = [
        {"role": "user", "content": "go"},
        {"role": "assistant", "content": "thinking out loud", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command": "ls"}'},
             "thought_signature": "SIG1"},
            {"id": "c2", "type": "function", "function": {"name": "grep", "arguments": '{"pattern": "a"}'}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "foo.py"},
        {"role": "tool", "tool_call_id": "c2", "content": '{"matches": 3}'},
    ]
    c.chat(model="m", system="be brief", messages=history, tools=tools, max_tokens=99, temperature=0.0)
    b = seen["body"]
    assert seen["path"] == "/models/m:generateContent"
    assert b["systemInstruction"] == {"parts": [{"text": "be brief"}]}
    assert b["generationConfig"] == {"maxOutputTokens": 99, "temperature": 0.0,
                                     "thinkingConfig": {"thinkingLevel": "low"}}   # extra_body deep-merged
    decl = b["tools"][0]["functionDeclarations"][0]
    assert decl["name"] == "bash" and "additionalProperties" not in decl["parameters"]
    user, model, results = b["contents"]
    assert model["role"] == "model"
    assert model["parts"][0] == {"text": "thinking out loud"}
    assert model["parts"][1] == {"functionCall": {"name": "bash", "args": {"command": "ls"}}, "thoughtSignature": "SIG1"}
    assert "thoughtSignature" not in model["parts"][2]
    assert results["role"] == "user" and len(results["parts"]) == 2          # both results in ONE content
    assert results["parts"][0]["functionResponse"] == {"name": "bash", "response": {"output": "foo.py"}}
    assert results["parts"][1]["functionResponse"] == {"name": "grep", "response": {"matches": 3}}


def test_gemini_response_parsing_signature_usage_and_finish(monkeypatch):
    c = _gemini_client()
    data = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
                {"text": "internal summary", "thought": True},
                {"text": "ok "},
                {"functionCall": {"name": "bash", "args": {"command": "ls"}}, "thoughtSignature": "SIG=="},
                {"functionCall": {"name": "grep", "args": {"pattern": "x"}}}]}}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 10, "thoughtsTokenCount": 40,
                              "cachedContentTokenCount": 64},
            "modelVersion": "gemini-3.1-flash-lite"}
    monkeypatch.setattr(c, "_post", lambda p, b: data)
    r = c.chat(model="m", messages=[{"role": "user", "content": "x"}])
    assert r.text == "ok " and r.finish_reason == "tool_calls" and r.model == "gemini-3.1-flash-lite"
    assert [t.name for t in r.tool_calls] == ["bash", "grep"] and [t.id for t in r.tool_calls] == ["call_0", "call_1"]
    assert r.tool_calls[0].extra == {"thought_signature": "SIG=="} and r.tool_calls[1].extra == {}
    assert json.loads(r.tool_calls[0].arguments) == {"command": "ls"}
    assert r.usage == {"input_tokens": 100, "output_tokens": 50, "cache_hit_tokens": 64,
                       "reasoning_tokens": 40, "reasoning_chars": 0}
    from miniagent.agent import _assistant_message
    assert _assistant_message(r)["tool_calls"][0]["thought_signature"] == "SIG=="      # replayed next turn

    data2 = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]}
    monkeypatch.setattr(c, "_post", lambda p, b: data2)
    assert c.chat(model="m", messages=[{"role": "user", "content": "x"}]).finish_reason == "length"
    data3 = {"promptFeedback": {"blockReason": "SAFETY"}}
    monkeypatch.setattr(c, "_post", lambda p, b: data3)
    assert c.chat(model="m", messages=[{"role": "user", "content": "x"}]).finish_reason == "safety"
