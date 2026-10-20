#!/usr/bin/env bash
# Run miniagent on one task from tasks/ in a throwaway copy, then grade it
# with the task's own test command.
#   scripts/run_task.sh 03            # prefix match, asks before each write/bash
#   scripts/run_task.sh 03 -y         # auto-approve (deny-list still applies)
#   scripts/run_task.sh all -y        # every task in tasks/
# Extra args after the task are passed to miniagent (e.g. -m deepseek-reasoner).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL="${MINIAGENT_MODEL:-deepseek-chat}"

[ $# -ge 1 ] || { sed -n '2,8p' "$0"; exit 2; }
sel="$1"; shift
[ -x "$ROOT/.venv/bin/miniagent" ] || { echo "missing .venv; run: python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"; exit 2; }
[ -n "${LLM_API_KEY:-${DEEPSEEK_API_KEY:-}}" ] || { echo "set LLM_API_KEY (or DEEPSEEK_API_KEY) in this shell"; exit 2; }
export PATH="$ROOT/.venv/bin:$PATH"   # so the agent's bash finds pytest

run_one() {
  local dir="$1" name; shift; name="$(basename "$dir")"
  local prompt test_cmd work
  prompt="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["prompt"])' "$dir/task.json")"
  test_cmd="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["test_cmd"])' "$dir/task.json")"
  work="$(mktemp -d)/repo"
  cp -R "$dir/repo" "$work"
  echo "=============== $name ==============="
  echo "workspace: $work"
  miniagent "$prompt" -w "$work" -m "$MODEL" --runs-dir "$ROOT/runs" "$@"
  echo "--- grading: $test_cmd"
  if (cd "$work" && bash -c "$test_cmd"); then echo "RESULT $name: PASS"; return 0
  else echo "RESULT $name: FAIL"; return 1; fi
}

shopt -s nullglob
if [ "$sel" = all ]; then dirs=("$ROOT"/tasks/*/); else dirs=("$ROOT"/tasks/"$sel"*/); fi
[ ${#dirs[@]} -gt 0 ] || { echo "no task matches '$sel'"; exit 2; }

fail=0
for d in "${dirs[@]}"; do run_one "${d%/}" "$@" || fail=$((fail+1)); done
[ ${#dirs[@]} -gt 1 ] && echo "=== ${#dirs[@]} tasks, $fail failed ==="
exit $((fail>0))
