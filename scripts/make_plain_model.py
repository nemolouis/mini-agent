"""Model directory for the plain-text tool-call format: symlinks to a model's files plus prompts/chat_template_plain.jinja.

The server reads chat_template.jinja from the model directory, so a separate directory is the unambiguous way to make it render
conversations the way sft_mlx.py --chat-template did during training.

  python scripts/make_plain_model.py models/qwen2.5-coder-1.5b-instruct-4bit   # -> models/qwen2.5-coder-1.5b-instruct-4bit-plain
"""
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1]).resolve()
dst = src.with_name(src.name + "-plain")
dst.mkdir(exist_ok=True)
for f in src.iterdir():
    if f.name != "chat_template.jinja" and not (dst / f.name).exists():
        (dst / f.name).symlink_to(f)
shutil.copyfile(Path(__file__).resolve().parent.parent / "prompts" / "chat_template_plain.jinja", dst / "chat_template.jinja")
print(dst)
