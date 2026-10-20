"""mlx_lm.server with a memory ceiling of its own (run with .venv-mlx/bin/python; arguments are mlx_lm.server's).

mlx's default memory limit is 1.5 x the GPU's recommended working set. On this Mac that let a training run allocate until the
driver failed (kernel panic, 2026-10-20), so the server gets an explicit, smaller limit: MLX_MEMORY_LIMIT_GB (default 4)."""
import os

import mlx.core as mx

mx.set_memory_limit(int(float(os.environ.get("MLX_MEMORY_LIMIT_GB", "4")) * 2**30))
mx.set_cache_limit(2**30)

from mlx_lm.server import main  # noqa: E402

main()
