"""Shrink the old_string of every edit_file call in an SFT file to the shortest line-aligned snippet that is still unique.

The teacher often quotes many unchanged lines around the one it changes. A 1.5B student has to copy old_string
character by character from the file it read, and every extra line is another chance to mis-copy it. Here each edit is
re-derived from the task's starting files: strip the lines shared by old_string and new_string at both ends, then add
context lines (alternating before / after, never beyond what the teacher quoted) only until the snippet is unique.

Every rewritten edit is checked offline: applying it to the file gives exactly the same text as the teacher's edit.
An edit that cannot be reproduced from the starting files (the file was changed earlier by bash, say) is left as it was.

  python scripts/shrink_edits.py data/sft_train_v2.jsonl data/sft_train_v3.jsonl [--tasks-root gen_tasks]
"""
import argparse
import json
import statistics
from collections import Counter
from pathlib import Path


def shrink(text: str, old: str, new: str) -> tuple[str, str]:
    o, n = old.split("\n"), new.split("\n")
    a = 0
    while a < min(len(o), len(n)) - 1 and o[a] == n[a]:
        a += 1
    b = 0
    while b < min(len(o), len(n)) - 1 - a and o[len(o) - 1 - b] == n[len(n) - 1 - b]:
        b += 1
    lo, hi, nlo, nhi = a, len(o) - b, a, len(n) - b          # o[lo:hi] and n[nlo:nhi] are the changed core
    if lo == hi and nlo == nhi:                              # identical, cannot happen for a valid edit
        return old, new
    take_before = True
    while True:
        cand_o, cand_n = "\n".join(o[lo:hi]), "\n".join(n[nlo:nhi])
        if cand_o and text.count(cand_o) == 1:
            return cand_o, cand_n
        can_b, can_a = lo > 0, hi < len(o)
        if not (can_b or can_a):
            return old, new
        if (take_before and can_b) or not can_a:
            lo, nlo = lo - 1, nlo - 1
        else:
            hi, nhi = hi + 1, nhi + 1
        take_before = not take_before


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--tasks-root", default="gen_tasks")
    args = ap.parse_args()
    root = Path(args.tasks_root)
    st, before, after = Counter(), [], []
    out = []
    for line in open(args.src, encoding="utf-8"):
        ex = json.loads(line)
        repo = root / ex["task_id"] / "repo"
        files: dict[str, str] = {}
        for m in ex["messages"]:
            for c in m.get("tool_calls") or []:
                fn = c["function"]
                if fn["name"] != "edit_file":
                    continue
                raw = fn["arguments"]
                a = json.loads(raw) if isinstance(raw, str) else raw
                p = a["path"]
                if p not in files:
                    files[p] = (repo / p).read_text(encoding="utf-8") if (repo / p).is_file() else None
                text = files[p]
                if text is None or text.count(a["old_string"]) != 1:
                    st["unverifiable"] += 1
                    continue
                expect = text.replace(a["old_string"], a["new_string"], 1)
                o2, n2 = shrink(text, a["old_string"], a["new_string"])
                got = text.replace(o2, n2, 1) if text.count(o2) == 1 else None
                files[p] = expect                           # later edits see the teacher's result either way
                if got != expect:
                    st["rewrite_rejected"] += 1             # the check failed: keep the teacher's edit
                    continue
                before.append(len(a["old_string"]))
                after.append(len(o2))
                if o2 == a["old_string"]:
                    st["unchanged"] += 1
                    continue
                st["shrunk"] += 1
                a = {**a, "old_string": o2, "new_string": n2}
                fn["arguments"] = json.dumps(a, ensure_ascii=False) if isinstance(raw, str) else a
        out.append(ex)
    with open(args.dst, "w", encoding="utf-8") as f:
        for ex in out:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"examples {len(out)}  edit calls {sum(st.values())}: {dict(st)}")
    if before:
        q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
        for name, xs in (("old_string chars before", before), ("after", after)):
            print(f"  {name}: mean {statistics.mean(xs):.0f}  median {q(xs, .5)}  p90 {q(xs, .9)}  max {max(xs)}")
        print(f"  total old_string chars {sum(before)} -> {sum(after)} ({sum(after) / sum(before):.0%})")


if __name__ == "__main__":
    main()
