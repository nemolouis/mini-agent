"""Progress of a running sft_mlx.py training, read from its log (standard library only).
usage: python scripts/train_status.py adapters/qwen15-v1.log"""
import ast
import os
import re
import subprocess
import sys
import time

path = sys.argv[1] if len(sys.argv) > 1 else "adapters/qwen15-v1.log"
text = re.sub(r"\x1b\[[0-9;]*m", "", open(path, errors="replace").read())
alive = subprocess.run(["pgrep", "-f", "sft_mlx.py train"], capture_output=True, text=True).stdout.split()
total = re.search(r"training (\d+) steps", text)
total = int(total.group(1)) if total else None
rows = [ast.literal_eval(m) for m in re.findall(r"^train (\{.*\})$", text, re.M)]
vals = [ast.literal_eval(m) for m in re.findall(r"^val\s+(\{.*\})$", text, re.M)]
age = time.time() - os.path.getmtime(path)
print(f"process: {'RUNNING (pid ' + alive[0] + ')' if alive else 'NOT running'}   log last written {age / 60:.1f} min ago")
if rows:
    last = rows[-1]
    ips = sum(r["iterations_per_second"] for r in rows) / len(rows)
    it = last["iteration"]
    line = f"step {it}" + (f" / {total} ({100 * it / total:.0f}%)" if total else "")
    if total and ips:
        line += f"   about {(total - it) / ips / 3600:.1f} h left at {1 / ips:.0f} s/step"
    print(line)
    print("train loss (every report):", " ".join(f"{r['train_loss']:.2f}" for r in rows[-12:]))
    print(f"peak memory {last['peak_memory']:.1f} GB")
for v in vals:
    print(f"validation at step {v['iteration']}: loss {v['val_loss']:.3f}")
if not rows:
    print("no training report yet (the first one comes after about 5 minutes)")
