"""mlx_lm.server with a memory ceiling of its own (run with .venv-mlx/bin/python; arguments are mlx_lm.server's).

mlx's default memory limit is 1.5 x the GPU's recommended working set. On this Mac that let a training run allocate until the
driver failed (kernel panic, 2026-10-20), so the server gets an explicit, smaller limit: MLX_MEMORY_LIMIT_GB (default 4).

An adapter trained with sft_mlx.py --chat-template must be served with the same template: if its adapter_config.json names one,
the model directory's chat_template.jinja has to be that file (see scripts/make_plain_model.py), or the server refuses to start."""
import json
import os
import sys
from pathlib import Path


def check_template(argv: list[str]) -> None:
    arg = lambda name: argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None
    model, adapter = arg("--model"), arg("--adapter-path")
    cfg = Path(adapter) / "adapter_config.json" if adapter else None
    wanted = json.loads(cfg.read_text()).get("chat_template") if cfg and cfg.is_file() else None
    if wanted:
        have = Path(model) / "chat_template.jinja" if model else None
        if not (have and have.is_file() and have.read_text(encoding="utf-8") == Path(wanted).read_text(encoding="utf-8")):
            sys.exit(f"{adapter} was trained with chat template {wanted}, but {model}/chat_template.jinja is not that file "
                     f"(python scripts/make_plain_model.py <model dir>, then --model <model dir>-plain)")
    elif adapter and model and (Path(model) / "chat_template.jinja").is_file() and "plain" in Path(model).name:
        sys.exit(f"{model} has the plain-text template, but {adapter} was trained with the model's own template")


if __name__ == "__main__":
    import mlx.core as mx

    check_template(sys.argv)
    mx.set_memory_limit(int(float(os.environ.get("MLX_MEMORY_LIMIT_GB", "4")) * 2**30))
    mx.set_cache_limit(2**30)

    from mlx_lm.server import main

    main()
