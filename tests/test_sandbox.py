"""Sandbox tests. The first group needs no Docker; the escape tests are skipped when Docker or the image is missing
(build the image with: miniagent-eval sandbox-build)."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from miniagent.agent import Agent
from miniagent.client import ModelResponse, ToolCall
from miniagent.eval.grade import run_tests
from miniagent.sandbox import (OUTPUT_CAP, Sandbox, SandboxConfig, SandboxError, available, cleanup_orphans,
                               docker_run_args)
from miniagent.tools import ToolError, Workspace

needs_docker = pytest.mark.skipif(not available(), reason="Docker or the miniagent-sandbox image is not available")


# ------------------------------------------------------------------ the command line (no Docker needed)
def args(**kw):
    return docker_run_args("n", Path("/tmp/ws"), SandboxConfig(**kw), 501, 20)


def pair(a, flag, value):
    return any(a[i] == flag and a[i + 1] == value for i in range(len(a) - 1))


def test_every_security_option_is_on_the_command_line():
    a = args()
    assert pair(a, "--network", "none")
    assert "--read-only" in a
    assert pair(a, "--cap-drop", "ALL") and pair(a, "--security-opt", "no-new-privileges")
    assert pair(a, "--user", "501:20")
    assert pair(a, "--pids-limit", "256") and pair(a, "--memory", "1g") and pair(a, "--memory-swap", "1g")
    assert pair(a, "--cpus", "1.0")
    assert any(x.startswith("--tmpfs=/tmp:") and "size=256m" in x for x in a)
    assert "--init" in a and pair(a, "--label", "miniagent-sandbox=1")


def test_nothing_else_of_the_host_is_handed_to_the_container():
    a = args()
    mounts = [a[i + 1] for i in range(len(a) - 1) if a[i] == "-v"]
    assert mounts == ["/tmp/ws:/work:rw"]
    envs = [a[i + 1] for i in range(len(a) - 1) if a[i] == "-e"]
    assert envs == ["HOME=/tmp"]
    for bad in ("--privileged", "--pid", "--ipc", "--device", "--env-file", "--volumes-from"):
        assert not any(x == bad or x.startswith(bad + "=") for x in a), bad
    assert not pair(a, "--network", "host")
    assert not any("docker.sock" in x for x in a)


def test_network_is_off_unless_explicitly_enabled():
    assert pair(args(), "--network", "none")
    assert "--network" not in args(network=True)


# ------------------------------------------------------------------ against a real container
@pytest.fixture(scope="module")
def box(tmp_path_factory):
    d = tmp_path_factory.mktemp("ws")
    with Sandbox(d) as sb:
        sb.dir = d
        yield sb


@needs_docker
def test_the_workspace_is_shared_and_files_belong_to_the_host_user(box):
    (box.dir / "in.txt").write_text("from host")
    r = box.exec("cat in.txt && echo from-container > out.txt && pwd")
    assert r.returncode == 0 and "from host" in r.stdout and r.stdout.strip().endswith("/work")
    assert (box.dir / "out.txt").read_text().strip() == "from-container"
    assert (box.dir / "out.txt").stat().st_uid == os.getuid()


@needs_docker
def test_no_network(box):
    r = box.exec("python -c \"import socket; socket.create_connection(('1.1.1.1', 53), 3)\"")
    assert r.returncode != 0 and "unreachable" in r.stderr.lower() or "error" in r.stderr.lower()
    assert box.exec("python -c \"import socket; socket.gethostbyname('example.com')\"").returncode != 0


@needs_docker
def test_host_files_are_invisible(box, tmp_path):
    secret = tmp_path / "outside.txt"
    secret.write_text("TOP SECRET")
    for cmd in (f"cat {secret}", f"ls {tmp_path}", "ls /Users", "cat ../outside.txt"):
        r = box.exec(cmd)
        assert r.returncode != 0 and "TOP SECRET" not in r.stdout, cmd
    assert "nemo" not in box.exec("cat /etc/passwd").stdout


@needs_docker
def test_host_environment_variables_do_not_reach_the_container(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-very-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "gm-very-secret")
    with Sandbox(tmp_path) as sb:
        r = sb.exec("env; cat /proc/self/environ | tr '\\0' '\\n'")
    assert "very-secret" not in r.stdout and "API_KEY" not in r.stdout


@needs_docker
def test_root_filesystem_is_read_only_but_tmp_and_work_are_writable(box):
    assert box.exec("touch /usr/x").returncode != 0
    assert box.exec("echo x > /etc/hosts").returncode != 0
    assert box.exec("echo x > /tmp/ok && cat /tmp/ok").returncode == 0
    assert box.exec("echo x > ok.txt").returncode == 0


@needs_docker
def test_the_daemon_applied_every_option(box):
    cfg = json.loads(subprocess.run(["docker", "inspect", box.name, "--format", "{{json .HostConfig}}"],
                                    capture_output=True, text=True, check=True).stdout)
    assert cfg["ReadonlyRootfs"] is True and cfg["Init"] is True and cfg["NetworkMode"] == "none"
    assert cfg["CapDrop"] == ["ALL"] and "no-new-privileges" in cfg["SecurityOpt"][0]
    assert cfg["PidsLimit"] == 256 and cfg["Memory"] == 1024 ** 3 and cfg["MemorySwap"] == cfg["Memory"]
    assert cfg["Privileged"] is False and [b.split(":")[1] for b in cfg["Binds"]] == ["/work"]


@needs_docker
def test_not_root_and_no_capabilities(box):
    assert box.exec("id -u").stdout.strip() == str(os.getuid()) != "0"
    assert box.exec("mount -t tmpfs none /tmp").returncode != 0
    caps = box.exec("grep CapEff /proc/self/status").stdout.split()[-1]
    assert int(caps, 16) == 0
    assert int(box.exec("grep CapBnd /proc/self/status").stdout.split()[-1], 16) == 0        # and none can be regained
    assert "NoNewPrivs:\t1" in box.exec("grep NoNewPrivs /proc/self/status").stdout


@needs_docker
def test_a_fork_bomb_is_contained_and_the_command_returns_on_time(tmp_path):
    with Sandbox(tmp_path, SandboxConfig(pids=64)) as sb:
        t0 = time.time()
        r = sb.exec(":(){ :|:& };:; sleep 30", timeout=4)
        assert time.time() - t0 < 15 and r.timed_out
        assert sb.exec("echo still-alive", timeout=20).stdout.strip() == "still-alive"        # the container survived


def box_ok(sb):
    return sb.exec("python -c 'print(1+1)'").stdout.strip() == "2"


@needs_docker
def test_process_limit_stops_forking(tmp_path):
    with Sandbox(tmp_path, SandboxConfig(pids=32)) as sb:
        r = sb.exec("python -c \"import os, time\nn = 0\nfor _ in range(200):\n    try:\n        if os.fork() == 0:\n            time.sleep(5); os._exit(0)\n        n += 1\n    except OSError:\n        break\nprint(n)\"", timeout=20)
        assert 0 < int(r.stdout.strip().splitlines()[-1]) < 40


@needs_docker
def test_memory_limit_kills_the_runaway_not_the_host(tmp_path):
    with Sandbox(tmp_path, SandboxConfig(memory="128m")) as sb:
        r = sb.exec("python -c \"x = bytearray(400 * 1024 * 1024); x[::4096] = b'1' * len(x[::4096])\"", timeout=30)
        assert r.returncode not in (0, None) and not r.timed_out          # killed by the kernel (137), not allowed to finish
        assert sb.exec("echo ok").stdout.strip() == "ok"
        assert box_ok(sb)


@needs_docker
def test_timeout_kills_the_whole_process_group(box):
    t0 = time.time()
    r = box.exec("sleep 300 & sleep 301", timeout=2)
    assert r.timed_out and time.time() - t0 < 10
    left = box.exec("for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline; echo; done | grep -c 'sleep 30[01]'").stdout.strip()
    assert left == "0"
    assert not box.exec("sleep 5", timeout=1).returncode == 0


@needs_docker
def test_output_floods_are_capped(box):
    t0 = time.time()
    r = box.exec("yes", timeout=3)
    assert r.timed_out and len(r.stdout) < OUTPUT_CAP + 200 and "bytes dropped" in r.stdout
    assert time.time() - t0 < 15


@needs_docker
def test_a_symlink_made_in_the_container_cannot_be_followed_by_the_file_tools(tmp_path):
    with Sandbox(tmp_path) as sb:
        assert sb.exec("ln -s /etc/passwd link && ln -s ../../.. up").returncode == 0
        ws = Workspace(tmp_path, sandbox=sb)
        with pytest.raises(ToolError, match="escapes"):
            ws.read_file({"path": "link"})
        with pytest.raises(ToolError, match="escapes"):
            ws.write_file({"path": "up/x.txt", "content": "pwn"})


@needs_docker
def test_workspace_bash_goes_through_the_sandbox(box):
    out = Workspace(box.dir, sandbox=box).bash({"command": "pwd; id -u"})
    assert out.startswith("exit code: 0") and "/work" in out


@needs_docker
def test_close_removes_the_container_and_later_use_fails_loudly(tmp_path):
    sb = Sandbox(tmp_path).start()
    name = sb.name
    sb.close()
    left = subprocess.run(["docker", "ps", "-aq", "--filter", f"name={name}"], capture_output=True, text=True).stdout
    assert left.strip() == ""
    with pytest.raises(SandboxError):
        sb.exec("true")


@needs_docker
def test_orphans_can_be_cleaned_up_and_a_removed_container_is_replaced_on_next_use(tmp_path):
    sb = Sandbox(tmp_path).start()
    old = sb.name
    assert cleanup_orphans() >= 1
    gone = subprocess.run(["docker", "ps", "-aq", "--filter", f"name={old}"], capture_output=True, text=True).stdout
    assert gone.strip() == ""
    assert sb.exec("echo back").stdout.strip() == "back" and sb.name != old        # recovered by itself, once
    sb.close()


@needs_docker
def test_grading_in_a_sandbox(tmp_path):
    (tmp_path / "m.py").write_text("def f():\n    return 2\n")
    (tmp_path / "test_m.py").write_text("from m import f\n\ndef test_f():\n    assert f() == 2\n")
    ok, out = run_tests(tmp_path, "pytest -q", sandbox=True)
    assert ok, out
    (tmp_path / "m.py").write_text("def f():\n    return 1\n")
    assert not run_tests(tmp_path, "pytest -q", sandbox=True)[0]
    (tmp_path / "test_m.py").write_text("import time\n\ndef test_hang():\n    time.sleep(60)\n")
    ok, out = run_tests(tmp_path, "pytest -q", timeout=3, sandbox=True)
    assert not ok and "timed out" in out


@needs_docker
def test_a_dead_sandbox_ends_the_run_as_an_error_not_as_a_tool_result(tmp_path):
    class One:
        def chat(self, **kw):
            return ModelResponse("", [ToolCall("1", "bash", json.dumps({"command": "echo hi"}))], "tool_calls",
                                 {"input_tokens": 1, "output_tokens": 1, "cache_hit_tokens": 0})

    sb = Sandbox(tmp_path).start()
    ws = Workspace(tmp_path, sandbox=sb)
    sb.close()
    res = Agent(One(), "m", ws).run("t")
    assert res.status == "error" and "SandboxError" in res.error


# ------------------------------------------------------------------ host/VM file-sharing lag (measured on OrbStack)
from miniagent.sandbox import workspace_manifest  # noqa: E402


@needs_docker
def test_the_host_manifest_is_what_the_container_computes(tmp_path):
    (tmp_path / "a b.txt").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "é.py").write_text("yy")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "z.pyc").write_text("z")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "v").write_text("v")
    (tmp_path / "link").symlink_to("a b.txt")
    with Sandbox(tmp_path) as sb:
        theirs = sb.exec("find . -type f -not -path '*/__pycache__/*' -not -path './.pytest_cache/*' -printf '%P\\t%s\\t%Ts\\n' | LC_ALL=C sort").stdout
    assert workspace_manifest(tmp_path).decode() == theirs
    assert "z.pyc" not in theirs and "link" not in theirs and ".pytest_cache" not in theirs


@needs_docker
def test_a_command_is_not_run_on_a_view_that_differs_from_the_host(tmp_path, monkeypatch):
    import miniagent.sandbox as sbmod
    (tmp_path / "f.txt").write_text("one")
    with Sandbox(tmp_path) as sb:
        monkeypatch.setattr(sbmod, "SYNC_SECONDS", 0.3)
        monkeypatch.setattr(sbmod, "workspace_manifest", lambda root: b"f.txt\t999\t1\n")      # a host state the container will never see
        with pytest.raises(SandboxError, match="does not see the current files"):
            sb.exec("echo should-not-run > ran.txt")
    assert not (tmp_path / "ran.txt").exists()


@needs_docker
def test_edits_by_the_host_are_seen_by_the_next_command_in_the_same_container(tmp_path):
    f = tmp_path / "m.py"
    with Sandbox(tmp_path) as sb:
        for i in range(25):
            f.write_text(f"VALUE = {i}\n" + "# padding\n" * (i % 7))
            assert sb.exec("python -c 'import m; print(m.VALUE)'").stdout.strip() == str(i)


@needs_docker
def test_grading_a_replaced_file_never_sees_the_old_version(tmp_path):
    """Regression for the failure seen when verifying generated tasks: with the grading container mounted on the directory an
    earlier container had read, about 8 of 100 gradings saw a file as it was before the host replaced it (a bigger file
    replacing a smaller one). Grading in a fresh copy fixed that (0 of 300). Same flow as there: copy a task repo, run its
    tests, put the reference file in place, run again."""
    import threading
    from miniagent.taskgen.mutate import apply, candidates
    seed = Path("seeds/inflection/repo")
    if not seed.exists():
        pytest.skip("seed not available")
    rel = "inflection/__init__.py"
    original = (seed / rel).read_text()
    broken = []
    for m in [c for c in candidates(original) if c.family == "delete"][:6]:
        d = tmp_path / f"task{len(broken)}"
        shutil.copytree(seed, d, ignore=shutil.ignore_patterns("__pycache__"))
        (d / rel).write_text(apply(original, m))
        old = time.time() - 1800                                       # generated tasks were written half an hour before they run
        os.utime(d / rel, (old, old))
        broken.append(d)
    assert len(broken) == 6
    failures = []

    def work(k):
        for i in range(15):
            src = broken[(k + i) % 6]
            w = tmp_path / f"w{k}_{i}"
            shutil.copytree(src, w)                                   # keeps mtimes, like copy_repo does
            run_tests(w, "python -m pytest -q", sandbox=True)         # container 1 reads the broken file
            shutil.copy(seed / rel, w / rel)
            ok, out = run_tests(w, "python -m pytest -q", sandbox=True)
            if not ok:
                failures.append((k, i, out[-200:]))

    ts = [threading.Thread(target=work, args=(k,)) for k in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert not failures, failures[:2]
