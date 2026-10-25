"""The plain-text tool-call format (prompts/chat_template_plain.jinja): nothing the model has to generate is an untrained special token."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from miniagent.client import extract_text_tool_calls

ROOT = Path(__file__).parent.parent
PLAIN = ROOT / "prompts" / "chat_template_plain.jinja"
MODEL = ROOT / "models" / "qwen2.5-coder-1.5b-instruct-4bit"
NAMES = {"bash", "edit_file"}


def test_client_drops_the_wrapper_lines():
    text = 'Looking.\n[TOOL_CALL]\n{"name": "bash", "arguments": {"command": "ls"}}\n[/TOOL_CALL]'
    cleaned, calls = extract_text_tool_calls(text, NAMES)
    assert cleaned == "Looking." and [(c.name, json.loads(c.arguments)) for c in calls] == [("bash", {"command": "ls"})]


def test_client_leaves_text_without_calls_alone():
    text = "Done. See [TOOL_CALL] in the docs."
    assert extract_text_tool_calls(text, NAMES) == (text, [])


def test_template_differs_from_qwens_only_in_the_call_wrapper():
    t = PLAIN.read_text(encoding="utf-8")
    assert "<tool_call>" not in t and "</tool_call>" not in t and "[TOOL_CALL]" in t and "[/TOOL_CALL]" in t
    assert "<tool_response>" in t                                  # tool results are input only, left as Qwen has them


def load_sft():
    spec = importlib.util.spec_from_file_location("sft_mlx", ROOT / "scripts" / "sft_mlx.py")
    sys.path.insert(0, str(ROOT))
    spec.loader.exec_module(m := importlib.util.module_from_spec(spec))
    return m


@pytest.mark.skipif(not (MODEL / "tokenizer.json").is_file(), reason="model files not downloaded")
def test_assistant_tokens_have_no_untrained_markers_and_parse_back():
    pytest.importorskip("transformers")
    pytest.importorskip("numpy")
    from transformers import AutoTokenizer
    try:
        sft = load_sft()
    except ImportError:
        pytest.skip("sft_mlx imports need the MLX environment")
    tok = AutoTokenizer.from_pretrained(MODEL)
    tools = [{"type": "function", "function": {"name": n, "description": n, "parameters": {"type": "object", "properties": {}}}} for n in NAMES]
    args = '{"path": "a.py", "old_string": "x = 1\\n", "new_string": "x = 2\\n"}'
    row = {"tools": tools, "messages": [
        {"role": "system", "content": "sys"}, {"role": "user", "content": "fix it"},
        {"role": "assistant", "content": "Reading first.", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command": "cat a.py"}'}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "x = 1"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c2", "type": "function", "function": {"name": "edit_file", "arguments": args}}]},
        {"role": "tool", "tool_call_id": "c2", "content": "edited a.py"},
        {"role": "assistant", "content": "Fixed."}]}

    def assistant_tokens(template):
        sft.use_template(tok, template)
        ids, mask = sft.encode(row, tok)
        return ids, mask

    ids, mask = assistant_tokens(None)
    assert {151657, 151658} <= {t for t, m in zip(ids, mask) if m}      # Qwen's own format asks the model to generate them

    ids, mask = assistant_tokens(str(PLAIN))
    gen = [t for t, m in zip(ids, mask) if m]
    assert not any(151643 <= t != 151645 for t in gen)                  # only <|im_end|> is special
    turns, cur = [], []
    for t in gen:
        if t == 151645:
            turns.append(tok.decode(cur))
            cur = []
        else:
            cur.append(t)
    got = [(c.name, json.loads(c.arguments)) for tx in turns for c in extract_text_tool_calls(tx, NAMES)[1]]
    assert got == [("bash", {"command": "cat a.py"}), ("edit_file", json.loads(args))]


def serve_module():
    spec = importlib.util.spec_from_file_location("serve_mlx", ROOT / "scripts" / "serve_mlx.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_server_refuses_a_template_mismatch(tmp_path):
    serve = serve_module()
    model, adapter = tmp_path / "m", tmp_path / "a"
    model.mkdir(), adapter.mkdir()
    (model / "chat_template.jinja").write_text("qwen's own")
    (adapter / "adapter_config.json").write_text(json.dumps({"chat_template": str(PLAIN)}))
    argv = ["--model", str(model), "--adapter-path", str(adapter)]
    with pytest.raises(SystemExit):
        serve.check_template(argv)
    (model / "chat_template.jinja").write_text(PLAIN.read_text(encoding="utf-8"))
    serve.check_template(argv)                                          # same template: accepted
    (adapter / "adapter_config.json").write_text(json.dumps({"chat_template": None}))
    plain_model = tmp_path / "m-plain"
    plain_model.mkdir()
    (plain_model / "chat_template.jinja").write_text("x")
    with pytest.raises(SystemExit):                                     # plain model dir with an adapter trained on Qwen's format
        serve.check_template(["--model", str(plain_model), "--adapter-path", str(adapter)])
