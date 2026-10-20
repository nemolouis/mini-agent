"""LoRA fine-tuning of a chat model on agent trajectories with MLX (Apple silicon). Run with .venv-mlx/bin/python.

Why this is not just `mlx_lm.lora`: that tool computes the loss on everything after one prompt offset, which for a
multi-turn trajectory means the model is also trained to predict the tool outputs (file contents, test output) that its own
tool calls will receive. Here the loss covers only the tokens of the assistant turns (tool calls, text and the closing
<|im_end|>); system, user and tool messages are context only.

usage:
  .venv-mlx/bin/python scripts/sft_mlx.py check  --model models/<m> --data data/x.jsonl          # tokenise, count, verify masks
  .venv-mlx/bin/python scripts/sft_mlx.py train  --model models/<m> --data data/x.jsonl --out adapters/<name> [options]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))        # miniagent is standard library only: importable from .venv-mlx
from miniagent.trainguard import TrainingDiverged, make_guard  # noqa: E402


def load_rows(path: str, limit: int | None = None) -> list[dict]:
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    return rows[:limit] if limit else rows


def to_template_messages(messages: list[dict]) -> list[dict]:
    """Chat templates want tool-call arguments as an object, the OpenAI shape has them as a JSON string."""
    out = []
    for m in messages:
        m = {k: v for k, v in m.items() if k != "reasoning_content"}
        if m.get("tool_calls"):
            m["tool_calls"] = [{**c, "function": {**c["function"], "arguments": json.loads(c["function"]["arguments"])}}
                               for c in m["tool_calls"]]
        out.append(m)
    return out


def encode(row: dict, tokenizer) -> tuple[list[int], list[int]]:
    """(token ids of the whole conversation, 0/1 mask: 1 on the tokens of assistant turns)."""
    ids = tokenizer.apply_chat_template(to_template_messages(row["messages"]), tools=row.get("tools"), tokenize=True,
                                        return_dict=False)
    start = tokenizer.convert_tokens_to_ids("<|im_start|>")
    end = tokenizer.convert_tokens_to_ids("<|im_end|>")
    asst = tokenizer.encode("assistant\n", add_special_tokens=False)
    mask = [0] * len(ids)
    i = 0
    while i < len(ids):
        if ids[i] == start and ids[i + 1:i + 1 + len(asst)] == asst:
            j = i + 1 + len(asst)                               # first token of the turn's content
            while j < len(ids) and ids[j] != end:
                j += 1
            for k in range(i + 1 + len(asst), min(j + 1, len(ids))):          # content and the closing <|im_end|>
                mask[k] = 1
            i = j
        i += 1
    return ids, mask


def build(rows, tokenizer, max_len: int | None):
    data, dropped, lens = [], 0, []
    for r in rows:
        ids, mask = encode(r, tokenizer)
        lens.append(len(ids))
        if (max_len and len(ids) > max_len) or sum(mask) > MAX_LOSS_TOKENS:
            dropped += 1
            continue
        data.append((ids, mask))
    return data, dropped, lens


def cmd_check(a):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)
    rows = load_rows(a.data, a.limit)
    data, dropped, lens = build(rows, tok, None)
    lens_np = np.array(lens)
    print(f"{len(rows)} examples | tokens: total {lens_np.sum():,}  median {int(np.median(lens_np))}  p90 {int(np.percentile(lens_np, 90))}  max {lens_np.max()}")
    for L in (4096, 6144, 8192, 12288, 16384):
        print(f"  <= {L:5}: {int((lens_np <= L).sum()):4} examples ({100 * (lens_np <= L).mean():.0f}%), {int(lens_np[lens_np <= L].sum()):,} tokens")
    trained = sum(sum(m) for _, m in data)
    print(f"tokens with loss (assistant turns): {trained:,} = {100 * trained / lens_np.sum():.1f}% of all tokens")
    # show one example with the masked part marked
    ids, mask = data[0]
    text = ""
    for k, (t, m) in enumerate(zip(ids, mask)):
        piece = tok.decode([t])
        text += (f"[[{piece}" if m and (k == 0 or not mask[k - 1]) else piece) + ("]]" if m and (k + 1 == len(mask) or not mask[k + 1]) else "")
    print("--- first example, masked spans in [[ ]] (truncated) ---")
    print(text[-1800:])
    # every assistant message of every example must be fully covered, nothing else
    bad = 0
    for r, (ids, mask) in zip(rows, data):
        n_asst = sum(1 for m in r["messages"] if m["role"] == "assistant")
        starts = sum(1 for k in range(len(mask)) if mask[k] and (k == 0 or not mask[k - 1]))
        bad += starts != n_asst
    print(f"examples whose number of masked spans differs from the number of assistant messages: {bad}")


def cmd_selftest(a):
    """masked_loss must equal full_loss on real data."""
    import mlx.core as mx
    from mlx_lm.utils import load
    model, tok = load(a.model)
    rows = load_rows(a.data, 12)
    data, _, _ = build(rows, tok, 8192)
    for ids, m in data[:5]:
        t, mm = mx.array([ids]), mx.array([m])
        l1, n1 = full_loss(model, t, mm)
        l2, n2 = masked_loss(model, *make_batch([(ids, m)], 99999))
        mx.eval(l1, l2)
        print(f"len {len(ids):5}  loss tokens {int(n1.item()):4}/{int(n2.item()):4}  full {l1.item():.5f}  gathered {l2.item():.5f}  diff {abs(l1.item() - l2.item()):.2e}")


def cmd_gradcheck(a):
    """The chunked, checkpointed loss must give the same GRADIENTS for the LoRA weights as the plain full-logits loss."""
    import mlx.core as mx
    import mlx.nn as nn
    from mlx.utils import tree_flatten
    from mlx_lm.tuner.utils import linear_to_lora_layers
    from mlx_lm.utils import load
    limit_memory(mx, 8.0, 1.0)
    model, tok = load(a.model)
    data, _, _ = build(load_rows(a.data, 40), tok, 3300)
    ids, m = sorted(data, key=lambda x: len(x[0]))[0]
    model.freeze()
    linear_to_lora_layers(model, 16, {"rank": 8, "scale": 20.0, "dropout": 0.0})
    for _, mod in model.named_modules():                                    # lora_b starts at zero: give it values so both factors get gradients
        if hasattr(mod, "lora_b"):
            mod.lora_b = mx.random.normal(mod.lora_b.shape).astype(mod.lora_b.dtype) * 0.01
    fit_loss_budget([(ids, m)])
    t, mm = mx.array([ids]), mx.array([m])
    (l1, _), g1 = nn.value_and_grad(model, full_loss)(model, t, mm)
    mx.eval(l1, g1)
    (l2, _), g2 = nn.value_and_grad(model, masked_loss)(model, *make_batch([(ids, m)], 99999))
    mx.eval(l2, g2)
    f1, f2 = dict(tree_flatten(g1)), dict(tree_flatten(g2))
    dot = sum((f1[k].astype(mx.float32) * f2[k].astype(mx.float32)).sum().item() for k in f1)
    n1 = sum((f1[k].astype(mx.float32) ** 2).sum().item() for k in f1) ** 0.5
    n2 = sum((f2[k].astype(mx.float32) ** 2).sum().item() for k in f1) ** 0.5
    cos = dot / (n1 * n2)
    # bf16 gradients differ tensor by tensor by summation order (an un-chunked gather is no closer to the plain loss: cosine 0.977
    # against 0.996 for the chunked one), so the criterion is global: direction and size of the whole gradient.
    print(f"length {len(ids)}, loss {l1.item():.5f} vs {l2.item():.5f}; {len(f1)} gradient tensors; cosine {cos:.4f}; norms {n1:.3f} vs {n2:.3f}")
    assert abs(l1.item() - l2.item()) < 1e-4 and cos > 0.99 and abs(n2 / n1 - 1) < 0.03, "gradients differ"
    print("gradcheck passed")


def iterate_batches_factory(seed):
    rng = random.Random(seed)

    def iterate(dataset, batch_size, max_seq_length, loop=False, seed=None, comm_group=None):
        order = sorted(range(len(dataset)), key=lambda i: len(dataset[i][0]))          # similar lengths together: less padding
        batches = [order[i:i + batch_size] for i in range(0, len(order) - batch_size + 1, batch_size)]
        while True:
            rng.shuffle(batches)
            for b in batches:
                yield make_batch([dataset[j] for j in b], max_seq_length)
            if not loop:
                break
    return iterate


BUCKET = 1024                 # sequence lengths are padded up to a multiple of this
MAX_LOSS_TOKENS = 2048        # fixed number of positions per sequence at which logits are computed (see masked_loss)


def full_loss(model, tokens, mask):
    """Reference implementation: logits at every position (needs a lot of memory for long sequences)."""
    import mlx.core as mx
    import mlx.nn as nn
    logits = model(tokens[:, :-1])
    m = mask[:, 1:].astype(mx.float32)
    ce = nn.losses.cross_entropy(logits.astype(mx.float32), tokens[:, 1:]) * m
    return ce.sum() / mx.maximum(m.sum(), 1), m.sum()


def make_batch(items, max_len):
    """items: [(ids, mask)]. -> (tokens (B,L), order (B,K), weights (B,K)): `order` lists, per sequence, the positions whose
    next token carries loss (padded with 0 and weight 0), computed here on the CPU because a compiled step cannot do the
    data-dependent selection itself (mx.argsort inside the compiled gradient step fails with 'key not found')."""
    import mlx.core as mx
    L = min(max(len(x[0]) for x in items), max_len)
    L = min(-(-L // BUCKET) * BUCKET, -(-max_len // BUCKET) * BUCKET)       # a few fixed shapes: MLX recompiles for every new one
    tokens = np.zeros((len(items), L), np.int32)
    order = np.zeros((len(items), MAX_LOSS_TOKENS), np.int32)
    weights = np.zeros((len(items), MAX_LOSS_TOKENS), np.float32)
    for r, (ids, m) in enumerate(items):
        n = min(len(ids), L)
        tokens[r, :n] = ids[:n]
        pos = np.nonzero(np.array(m[1:n], dtype=bool))[0]              # t such that tokens[t + 1] has loss
        pos = pos[:MAX_LOSS_TOKENS]
        order[r, :len(pos)] = pos
        weights[r, :len(pos)] = 1.0
    return mx.array(tokens), mx.array(order), mx.array(weights)


LOSS_CHUNK = 128            # loss positions whose logits exist at the same time (the rest are recomputed in the backward pass)


def masked_loss(model, tokens, order, weights):
    """Same value as full_loss, but the output projection (151,936 words) is applied only at the loss positions, a chunk at a
    time, and each chunk is recomputed in the backward pass instead of stored (mx.checkpoint): the logits, their fp32 copy and
    their gradient (several GB for a thousand positions) are never alive together."""
    import mlx.core as mx
    import mlx.nn as nn
    h = model.model(tokens[:, :-1])                                           # (B, T, D), final norm included
    hk = mx.take_along_axis(h, order[:, :, None], axis=1)                     # (B, K, D)
    tk = mx.take_along_axis(tokens[:, 1:], order, axis=1)
    head = model.model.embed_tokens.as_linear if model.args.tie_word_embeddings else model.lm_head

    def chunk_loss(tc, wc):
        def f(hc):                                       # only the hidden states are differentiated: targets and weights are closed over
            ce = nn.losses.cross_entropy(head(hc).astype(mx.float32), tc)
            return mx.where(wc > 0, ce, 0.0).sum()
        return mx.checkpoint(f)

    total = 0.0
    for i in range(0, hk.shape[1], LOSS_CHUNK):
        sl = slice(i, i + LOSS_CHUNK)
        total = total + chunk_loss(tk[:, sl], weights[:, sl])(hk[:, sl])
    # Two separate counts on purpose: dividing by weights.sum() and returning the same sum makes MLX 0.32's compiled
    # gradient step fail with "unordered_map::at: key not found" (bisected).
    n = (weights > 0).sum()
    return total / mx.maximum(n, 1), weights.sum()


def clipped_adamw(lr_schedule, max_norm: float, bias_correction: bool = True):
    """AdamW whose gradients are first scaled down to a global norm of at most `max_norm`.

    bias_correction=True on purpose: MLX's default is False, and then the update is lr * m / (sqrt(v) + eps) with m and v still
    warming up, i.e. 3.2x the nominal step at update 1, 6.5x at update 10, 6.3x at update 20, 4.5x at update 50 and 3.2x at update
    100 for a consistent gradient. Both runs that diverged (lr 1e-4 at update 10, lr 5e-5 at update 19) did so inside this window."""
    import mlx.optimizers as optim

    if max_norm <= 0:
        return optim.AdamW(learning_rate=lr_schedule, weight_decay=0.0, bias_correction=bias_correction)

    class ClippedAdamW(optim.AdamW):
        def apply_gradients(self, gradients, parameters):
            gradients, _ = optim.clip_grad_norm(gradients, max_norm)
            return super().apply_gradients(gradients, parameters)

    return ClippedAdamW(learning_rate=lr_schedule, weight_decay=0.0, bias_correction=bias_correction)


def lr_schedule(peak: float, updates: int, warmup: int):
    import mlx.optimizers as optim
    warmup = min(warmup, max(updates - 1, 1))
    return optim.join_schedules([optim.linear_schedule(peak * 0.1, peak, warmup),
                                 optim.cosine_decay(peak, max(1, updates - warmup))], [warmup])


def limit_memory(mx, limit_gb: float, cache_gb: float):
    """MLX's default memory limit is 1.5 x the GPU's recommended working set (about 17.7 GB on this 16 GB Mac), i.e. it will
    happily allocate until the driver refuses. A lower limit makes MLX release cached buffers first and raise an exception
    in its own process instead. The kernel panic of 2026-10-20 (IOGPU 'prepare count underflow') followed Metal out-of-memory
    errors of exactly this kind."""
    mx.set_memory_limit(int(limit_gb * 2**30))
    mx.set_cache_limit(int(cache_gb * 2**30))


def fit_loss_budget(data):
    """The fixed number of loss positions per sequence is the largest count in the data, rounded up to 128."""
    global MAX_LOSS_TOKENS
    MAX_LOSS_TOKENS = max(128, -(-max(sum(m) for _, m in data) // 128) * 128)
    return MAX_LOSS_TOKENS


def cmd_train(a):
    import mlx.core as mx
    import mlx.optimizers as optim
    from mlx.utils import tree_flatten
    from mlx_lm.tuner.trainer import TrainingArgs, TrainingCallback, train
    from mlx_lm.tuner.utils import linear_to_lora_layers, print_trainable_parameters
    from mlx_lm.utils import load, save_config

    limit_memory(mx, a.memory_limit_gb, a.cache_limit_gb)
    model, tok = load(a.model)
    rows = load_rows(a.data, a.limit)
    random.Random(a.seed).shuffle(rows)
    n_val = max(2, int(len(rows) * a.val_frac))
    val_rows, train_rows = rows[:n_val], rows[n_val:]
    train_data, dropped_t, _ = build(train_rows, tok, a.max_len)
    val_data, dropped_v, _ = build(val_rows, tok, a.max_len)
    print(f"train {len(train_data)} (dropped {dropped_t} longer than {a.max_len}) | val {len(val_data)} (dropped {dropped_v})")
    print(f"loss positions per sequence: {fit_loss_budget(train_data + val_data)}; memory limit {a.memory_limit_gb} GB, cache limit {a.cache_limit_gb} GB")
    steps_per_epoch = len(train_data) // a.batch_size
    iters = int(a.iters or round(steps_per_epoch * a.epochs))
    print(f"batch {a.batch_size} x accumulation {a.accum}: {steps_per_epoch} steps per epoch, training {iters} steps")

    model.freeze()
    lora = {"rank": a.rank, "scale": a.scale, "dropout": 0.0}
    linear_to_lora_layers(model, a.lora_layers, lora)
    print_trainable_parameters(model)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    save_config({"model": str(a.model), "fine_tune_type": "lora", "num_layers": a.lora_layers, "lora_parameters": lora,
                 "max_seq_length": a.max_len, "data": a.data, "seed": a.seed}, out / "adapter_config.json")

    args = TrainingArgs(batch_size=a.batch_size, iters=iters, val_batches=min(a.val_batches, max(1, len(val_data) // a.batch_size)),
                        steps_per_report=a.report_every, steps_per_eval=a.eval_every, steps_per_save=a.save_every,
                        max_seq_length=a.max_len, adapter_file=str(out / "adapters.safetensors"),
                        grad_checkpoint=True, grad_accumulation_steps=a.accum,
                        clear_cache_threshold=int(a.clear_cache_gb * 2**30))
    updates = max(1, iters // a.accum)
    opt = clipped_adamw(lr_schedule(a.lr, updates, a.warmup), a.clip, bool(a.bias_correction))
    print(f"Adam bias correction: {'on' if a.bias_correction else 'OFF (MLX default)'}")
    print(f"{updates} optimizer updates, peak lr {a.lr}, warmup {a.warmup}, gradient clip {a.clip}, "
          f"stops if validation loss > {a.guard_val}x the untrained model's or training loss > {a.guard_train}")
    guard_train, guard_val = make_guard(a.guard_val, a.guard_train)

    class Log(TrainingCallback):
        def on_train_loss_report(self, info):
            print("train", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in info.items()}, flush=True)
            guard_train(info)

        def on_val_loss_report(self, info):
            print("val  ", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in info.items()}, flush=True)
            guard_val(info)

    t0 = time.time()
    try:
        train(model, opt, train_data, val_data, args, loss=masked_loss,
              iterate_batches=iterate_batches_factory(a.seed), training_callback=Log())
    except TrainingDiverged as e:
        (out / "DIVERGED.txt").write_text(f"{e}\nCheckpoints in this directory are from a diverging run: do not use them.\n")
        print(f"STOPPED: {e}", file=sys.stderr)
        sys.exit(3)
    mx.save_safetensors(str(out / "adapters.safetensors"), dict(tree_flatten(model.trainable_parameters())))
    print(f"done in {(time.time() - t0) / 60:.1f} min; adapter saved to {out}")
    print(f"peak memory {mx.get_peak_memory() / 2**30:.1f} GB")


def cmd_memtest(a):
    """Peak memory and time of ONE optimizer step at increasing sequence lengths, with the real loss, LoRA, gradient
    checkpointing and optimizer. Stops at the first length whose peak exceeds --stop-gb. Run before any long training."""
    from functools import partial
    import mlx.core as mx
    import mlx.nn as nn
    from mlx_lm.tuner.trainer import grad_checkpoint
    from mlx_lm.tuner.utils import linear_to_lora_layers
    from mlx_lm.utils import load
    limit_memory(mx, a.memory_limit_gb, a.cache_limit_gb)
    model, tok = load(a.model)
    data, _, _ = build(load_rows(a.data), tok, a.max_len)
    print(f"{len(data)} examples <= {a.max_len} tokens; loss positions per sequence {fit_loss_budget(data)}")
    model.freeze()
    linear_to_lora_layers(model, a.lora_layers, {"rank": a.rank, "scale": a.scale, "dropout": 0.0})
    grad_checkpoint(model.layers[0])
    opt = clipped_adamw(lr_schedule(a.lr, 100, 10), a.clip, bool(a.bias_correction))
    vg = nn.value_and_grad(model, masked_loss)
    state = [model.state, opt.state, mx.random.state]

    @partial(mx.compile, inputs=state, outputs=state)
    def step(batch):
        (l, n), g = vg(model, *batch)
        opt.update(model, g)
        return l, n

    model.train()
    print(f"clip {a.clip}, rank {a.rank}; model + lora in memory: {mx.get_active_memory() / 2**30:.2f} GB; stop above {a.stop_gb} GB")
    for bucket in range(BUCKET, a.max_len + 1, BUCKET):
        pool = [x for x in data if bucket - BUCKET < len(x[0]) <= bucket]
        if not pool:
            continue
        pool.sort(key=lambda x: -len(x[0]))
        for rep in range(2):                                              # the second pass is the steady state, without compilation
            mx.reset_peak_memory()
            t0 = time.time()
            l, n = step(make_batch([pool[0]], a.max_len))
            mx.eval(l, n, state)
            peak = mx.get_peak_memory() / 2**30
            print(f"len {len(pool[0][0]):5} (bucket {bucket}) pass {rep + 1}: peak {peak:.2f} GB  {time.time() - t0:5.1f}s  loss {l.item():.3f}  active {mx.get_active_memory() / 2**30:.2f} GB", flush=True)
        if peak > a.stop_gb:
            print(f"STOP: peak {peak:.2f} GB is above {a.stop_gb} GB; do not train with this length/configuration")
            sys.exit(4)
    print("memtest passed")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "train", "selftest", "memtest", "gradcheck"):
        p = sub.add_parser(name)
        p.add_argument("--model", required=True)
        p.add_argument("--data", required=True)
        p.add_argument("--limit", type=int)
    mt = sub._name_parser_map["memtest"]
    mt.add_argument("--max-len", type=int, default=4096)
    mt.add_argument("--clip", type=float, default=1.0)
    mt.add_argument("--bias-correction", type=int, default=1)
    mt.add_argument("--rank", type=int, default=16)
    mt.add_argument("--lora-layers", type=int, default=16, help="LoRA on the last N layers; layer 0 has gradients of 1e15 (see docs)")
    mt.add_argument("--scale", type=float, default=20.0)
    mt.add_argument("--lr", type=float, default=2e-5)
    mt.add_argument("--memory-limit-gb", type=float, default=8.0)
    mt.add_argument("--cache-limit-gb", type=float, default=1.0)
    mt.add_argument("--stop-gb", type=float, default=6.5, help="the peak that counts as too close to the limit")
    t = sub._name_parser_map["train"]
    t.add_argument("--out", required=True)
    t.add_argument("--max-len", type=int, default=8192, help="examples longer than this are dropped, not truncated")
    t.add_argument("--batch-size", type=int, default=1)
    t.add_argument("--accum", type=int, default=8, help="gradient accumulation steps")
    t.add_argument("--epochs", type=float, default=2)
    t.add_argument("--iters", type=int, default=0, help="overrides --epochs")
    t.add_argument("--lr", type=float, default=2e-5, help="peak learning rate (mlx_lm.lora defaults to 1e-5; 1e-4 diverged here)")
    t.add_argument("--bias-correction", type=int, default=1, help="Adam bias correction (1/0). MLX defaults to off, which inflates the first ~100 steps 3-6x")
    t.add_argument("--warmup", type=int, default=10, help="optimizer updates of linear warm-up from 10%% of the peak")
    t.add_argument("--clip", type=float, default=1.0, help="global gradient-norm clip (0 = off)")
    t.add_argument("--memory-limit-gb", type=float, default=7.0, help="MLX raises an exception beyond this instead of letting the driver run out (see limit_memory)")
    t.add_argument("--cache-limit-gb", type=float, default=1.0)
    t.add_argument("--clear-cache-gb", type=float, default=1.0, help="free MLX's allocator cache between steps when it exceeds this (0 = never); on a 16 GB Mac the peak sits close to the GPU limit")
    t.add_argument("--guard-val", type=float, default=1.3, help="stop if validation loss exceeds this x the untrained model's")
    t.add_argument("--guard-train", type=float, default=3.0, help="stop if the reported training loss exceeds this")
    t.add_argument("--rank", type=int, default=16)
    t.add_argument("--lora-layers", type=int, default=16, help="LoRA on the last N layers. All 28 diverged: layer 0 has LoRA gradients around 1e15 (all other layers about 1)")
    t.add_argument("--scale", type=float, default=20.0)
    t.add_argument("--val-frac", type=float, default=0.06)
    t.add_argument("--val-batches", type=int, default=10)
    t.add_argument("--report-every", type=int, default=5)
    t.add_argument("--eval-every", type=int, default=50)
    t.add_argument("--save-every", type=int, default=50)
    t.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    {"check": cmd_check, "train": cmd_train, "selftest": cmd_selftest, "memtest": cmd_memtest, "gradcheck": cmd_gradcheck}[a.cmd](a)


if __name__ == "__main__":
    main()
