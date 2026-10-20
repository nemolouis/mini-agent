"""Task generator tests: the pure parts need nothing; the end-to-end ones need the Docker sandbox."""
import ast
import json
import random
import shutil
from pathlib import Path

import pytest

from miniagent.client import ModelResponse, ToolCall
from miniagent.eval.grade import is_test_file
from miniagent.eval.runner import run_one
from miniagent.eval.tasks import load_tasks
from miniagent.sandbox import available
from miniagent.taskgen.generate import (GenConfig, Seed, SuiteRun, _check_built, _judge, generate, load_seed, parse_suite,
                                        seed_split)
from miniagent.taskgen.mutate import Mutant, apply, candidates
from miniagent.taskgen.testsplit import close_over_calls, find_tests, keep_only, node_key

needs_docker = pytest.mark.skipif(not available(), reason="Docker or the miniagent-sandbox image is not available")


def mutated(source, family, nth=0):
    cs = [m for m in candidates(source) if m.family == family]
    assert len(cs) > nth, f"no {family} candidate #{nth} in {source!r}"
    return apply(source, cs[nth])


# ------------------------------------------------------------------ operators
def test_compare_flips_only_the_operator():
    src = "def f(a, b):\n    return a  <  b  # keep me\n"
    assert mutated(src, "compare") == "def f(a, b):\n    return a  <=  b  # keep me\n"


@pytest.mark.parametrize("old,new", [("a < b", "a <= b"), ("a <= b", "a < b"), ("a > b", "a >= b"), ("a >= b", "a > b"),
                                     ("a == b", "a != b"), ("a != b", "a == b"), ("a is b", "a is not b"),
                                     ("a is not b", "a is b"), ("a in b", "a not in b"), ("a not in b", "a in b")])
def test_every_comparison_operator_has_a_flip(old, new):
    assert mutated(f"x = {old}\n", "compare") == f"x = {new}\n"


def test_arithmetic():
    assert mutated("x = a + b\n", "arith") == "x = a - b\n"
    assert mutated("x = a - b\n", "arith") == "x = a + b\n"
    assert mutated("x = a * b\n", "arith") == "x = a // b\n"
    assert mutated("x = a / b\n", "arith") == "x = a // b\n"
    assert candidates("x = a ** b\ny += 1\nz = -a\n") == [] or all(m.family != "arith" for m in candidates("x = a ** b\ny += 1\nz = -a\n"))


def test_boolop_chain_changes_every_operator():
    assert mutated("x = a and b and c\n", "boolop") == "x = a or b or c\n"
    assert mutated("x = (a or\n     b)\n", "boolop") == "x = (a and\n     b)\n"


def test_negate_inverts_a_plain_comparison_and_wraps_anything_else():
    assert mutated("if a <= b:\n    pass\n", "negate") == "if a > b:\n    pass\n"
    assert mutated("if a and b:\n    pass\n", "negate") == "if not (a and b):\n    pass\n"
    assert mutated("x = 1 if ok else 2\n", "negate") == "x = 1 if not (ok) else 2\n"
    assert [m for m in candidates("if not a:\n    pass\n") if m.family == "negate"] == []


def test_integer_constants_move_by_one_and_stay_non_negative():
    assert mutated("x = s[3]\n", "const", 0) == "x = s[4]\n"
    assert mutated("x = s[3]\n", "const", 1) == "x = s[2]\n"
    assert [apply("x = 0\n", m) for m in candidates("x = 0\n") if m.family == "const"] == ["x = 1\n"]
    assert [apply("x = -1\n", m) for m in candidates("x = -1\n") if m.family == "const"] == ["x = -2\n"]      # -0 is not offered
    assert [m for m in candidates("x = True\ny = 'a'\nz = 1.5\n") if m.family == "const"] == []


def test_loop_control_and_statement_removal():
    src = "for i in r:\n    if i:\n        break\n    continue\n"
    got = {apply(src, m) for m in candidates(src) if m.family == "loopctl"}
    assert got == {"for i in r:\n    if i:\n        continue\n    continue\n", "for i in r:\n    if i:\n        break\n    break\n"}
    assert mutated("def f():\n    x = 1\n    g(x)\n    return x\n", "delete", 0) == "def f():\n    pass\n    g(x)\n    return x\n"
    docstring = '"""doc"""\n'
    assert candidates(docstring) == []


def test_offsets_are_right_with_non_ascii_text_before_the_operator():
    src = 'name = "é中"; ok = a < b\n'
    assert mutated(src, "compare") == 'name = "é中"; ok = a <= b\n'


def test_a_comment_inside_the_gap_makes_the_candidate_disappear():
    src = "x = (a <  # why\n     b)\n"
    assert [m for m in candidates(src) if m.family == "compare"] == []


def test_apply_rejects_broken_or_unchanged_results():
    assert apply("x = 1\n", Mutant("t", 1, "bad", ((0, 1, b"("),))) is None
    assert apply("x = 1\n", Mutant("t", 1, "same", ((0, 1, b"x"),))) is None


def test_every_candidate_of_a_real_file_compiles_and_differs():
    src = Path("seeds/textkit/repo/textkit.py").read_text()
    cs = candidates(src)
    assert len(cs) > 40 and {m.family for m in cs} >= {"compare", "arith", "negate", "const", "delete"}
    outs = [apply(src, m) for m in cs]
    assert all(o is not None and o != src for o in outs)
    assert all(ast.parse(o) for o in outs)


# ------------------------------------------------------------------ test splitting
SPLIT_SRC = '''import pytest
from m import f

def helper(): return 1

@pytest.mark.parametrize("x", [1, 2])
def test_a(x):
    assert f(x)

def test_b():
    assert f(2) == 2

class TestK:
    """doc"""
    def test_c(self):
        assert 1
    def test_d(self):
        assert 2

class TestOnly:
    def test_e(self):
        assert 3

class TestWithSetup:
    def setup_method(self):
        self.v = 1
    def test_f(self):
        assert self.v
'''


def test_test_functions_and_node_keys():
    assert find_tests(SPLIT_SRC) == [(None, "test_a"), (None, "test_b"), ("TestK", "test_c"), ("TestK", "test_d"),
                                         ("TestOnly", "test_e"), ("TestWithSetup", "test_f")]
    assert node_key("t.py::test_a[1-2]") == ("t.py", None, "test_a")
    assert node_key("t.py::TestK::test_c") == ("t.py", "TestK", "test_c")
    assert node_key("t.py") is None


def test_keep_only_removes_functions_with_their_decorators_and_empty_classes():
    out = keep_only(SPLIT_SRC, {(None, "test_b"), ("TestK", "test_d")})
    compile(out, "x", "exec")
    assert find_tests(out) == [(None, "test_b"), ("TestK", "test_d")]
    assert "parametrize" not in out and "TestOnly" not in out and "def helper" in out
    assert "def test_f" not in out and "setup_method" in out      # a class with other members stays, minus its removed tests
    assert keep_only(SPLIT_SRC, set(find_tests(SPLIT_SRC))) == SPLIT_SRC


def test_a_class_keeps_its_setup_when_a_test_of_it_stays():
    out = keep_only(SPLIT_SRC, {("TestWithSetup", "test_f")})
    assert "setup_method" in out and find_tests(out) == [("TestWithSetup", "test_f")]


# ------------------------------------------------------------------ parsing pytest output
def test_parse_suite():
    out = ("FAILED test_a.py::TestK::test_c - assert 1 == 2\nFAILED test_a.py::test_b[1] - x\n"
           "ERROR test_a.py::test_z - boom\n=== 2 failed, 7 passed, 1 error in 0.12s ===\n")
    r = parse_suite(1, out, False)
    assert r.failed == {"test_a.py::TestK::test_c", "test_a.py::test_b[1]", "test_a.py::test_z"}
    assert r.counts == {"failed": 2, "passed": 7, "error": 1} and r.total == 10
    assert parse_suite(0, "9 passed in 0.01s\n", False).total == 9


def test_seed_split_is_stable_and_overridable():
    a = Seed("alpha", Path("."), [], [])
    assert seed_split(a) == seed_split(Seed("alpha", Path("."), [], [])) in ("train", "dev", "test")
    assert seed_split(Seed("alpha", Path("."), [], [], split="test")) == "test"


def test_conftest_and_pytest_ini_count_as_test_files():
    for name in ("conftest.py", "pytest.ini", "sub/conftest.py", "test_x.py"):
        assert is_test_file(Path(name))
    assert not is_test_file(Path("textkit.py"))


# ------------------------------------------------------------------ end to end (Docker)
@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    if not available():
        pytest.skip("no sandbox")
    root = tmp_path_factory.mktemp("seeds")
    shutil.copytree("seeds/seqtools", root / "seqtools")
    out = tmp_path_factory.mktemp("gen")
    cfg = GenConfig(per_seed=4, workers=2, rng=7, candidate_factor=6)
    rep = generate([root / "seqtools"], out, cfg)
    return root, out, rep, cfg


@needs_docker
def test_generated_tasks_are_complete_and_verifiable(generated):
    root, out, rep, _ = generated
    (s,) = rep["seeds"]
    assert len(s["tasks"]) == 4 and s["split"] in ("train", "dev", "test")
    tasks = load_tasks(out)
    assert len(tasks) == 4
    for t in tasks:
        meta = json.loads((t.dir / "task.json").read_text())
        assert meta["layer"] == "G" and meta["gen"]["failing_total"] >= 1
        assert meta["gen"]["file"] not in meta["prompt"] and str(meta["gen"]["line"]) not in meta["prompt"]      # no hint about where
        gen = meta["gen"]
        orig = (root / "seqtools" / "repo" / gen["file"]).read_text()
        assert (t.solution / gen["file"]).read_text() == orig                        # the solution is the original
        assert (t.repo / gen["file"]).read_text() != orig                            # the repo has the bug
        vis, full = (t.repo / "test_seqtools.py").read_text(), (t.hidden / "test_seqtools.py").read_text()
        hidden_only = {f for _, f in find_tests(full)} - {f for _, f in find_tests(vis)}
        assert hidden_only and not any(f"def {name}(" in vis for name in hidden_only)         # hidden tests are not in the repo
    split = json.loads((out / "SPLIT.json").read_text())["tasks"]
    assert {v["split"] for v in split.values()} == {s["split"]} and set(split) == {t.id for t in tasks}   # split by seed


@needs_docker
def test_the_harness_grades_a_generated_task_in_the_sandbox(generated, tmp_path):
    root, out, _, _ = generated
    t = load_tasks(out)[0]
    gen = json.loads((t.dir / "task.json").read_text())["gen"]
    good = (t.solution / gen["file"]).read_text()

    class Script:
        def __init__(self, steps): self.steps = list(steps)

        def chat(self, **kw):
            text, calls = self.steps.pop(0)
            return ModelResponse(text, calls, "tool_calls" if calls else "stop",
                                 {"input_tokens": 10, "output_tokens": 5, "cache_hit_tokens": 0})

    cfg = {"name": "t", "model": "fake", "temperature": 0.0, "max_steps": 6, "sandbox": True}
    fix = ToolCall("1", "write_file", json.dumps({"path": gen["file"], "content": good}))
    run = ToolCall("2", "bash", json.dumps({"command": "python -m pytest -q 2>&1 | tail -3; pwd"}))
    r = run_one(t, cfg, 0, tmp_path / "ok", Script([("", [fix]), ("", [run]), ("done", [])]))
    assert r["passed"] and r["failure_class"] == "pass"
    tool_out = [json.loads(l) for l in open(r["trajectory"]) if '"tool_result"' in l][-1]["output"]
    assert "/work" in tool_out and "passed" in tool_out                              # the command ran in the container

    r = run_one(t, cfg, 1, tmp_path / "noop", Script([("nothing to do", [])]))
    assert not r["passed"] and r["failure_class"] == "no_edit"

    skip_all = ToolCall("3", "write_file", json.dumps({"path": "conftest.py", "content": "import pytest\n\ndef pytest_collection_modifyitems(items):\n    items.clear()\n"}))
    r = run_one(t, cfg, 2, tmp_path / "cheat", Script([("", [skip_all]), ("done", [])]))
    assert r["tampered_tests"] and not r["passed"]                                   # an empty suite must not count as a pass


@needs_docker
def test_generation_is_deterministic_for_a_given_rng(generated, tmp_path):
    root, out, _, cfg = generated
    out2 = tmp_path / "again"
    generate([root / "seqtools"], out2, cfg)
    names = sorted(p.name for p in out.glob("g-*"))
    assert names == sorted(p.name for p in out2.glob("g-*"))
    for n in names:
        a = (out / n / "repo" / "seqtools.py").read_text()
        assert a == (out2 / n / "repo" / "seqtools.py").read_text()
        assert (out / n / "repo" / "test_seqtools.py").read_text() == (out2 / n / "repo" / "test_seqtools.py").read_text()


@needs_docker
def test_a_seed_whose_own_tests_fail_is_skipped_with_a_reason(tmp_path):
    seed = tmp_path / "s"
    (seed / "repo").mkdir(parents=True)
    (seed / "repo" / "m.py").write_text("def f():\n    return 1\n")
    (seed / "repo" / "test_m.py").write_text("from m import f\n\ndef test_f():\n    assert f() == 2\n")
    (seed / "seed.json").write_text(json.dumps({"mutate": ["m.py"], "tests": ["test_m.py"]}))
    rep = generate([seed], tmp_path / "out", GenConfig(per_seed=2, workers=1))
    assert "do not pass" in rep["seeds"][0]["skipped"] and not list((tmp_path / "out").glob("g-*"))


# ------------------------------------------------------------------ the filters, one verdict each (no Docker)
class FakeRunner:
    def __init__(self, *runs): self.runs = list(runs)

    def run_with(self, rel, text): return self.runs.pop(0)


def suite(rc, failed=(), passed=20, timed_out=False, error=0):
    return SuiteRun(rc, frozenset(failed), {"passed": passed, "failed": len(failed), **({"error": error} if error else {})}, timed_out)


ORIG = "def f(a, b):\n    return a + b\n"
MUT = Mutant("arith", 2, "x", ((26, 27, b"-"),))
KEYS = {("test_m.py", None, "test_a"), ("test_m.py", None, "test_b")}
CFG = GenConfig()


def verdict(*runs, mutant=MUT, original=ORIG):
    return _judge(FakeRunner(*runs), "m.py", original, mutant, CFG, KEYS)


def test_judge_verdicts():
    one = suite(1, ["test_m.py::test_a"])
    assert verdict(one, one)[0] == "ok"
    assert verdict(mutant=Mutant("x", 1, "bad", ((0, 1, b"("),)))[0] == "no_compile"
    assert verdict(suite(None, timed_out=True))[0] == "timeout"
    assert verdict(suite(0))[0] == "undetected_by_tests"
    assert verdict(suite(2))[0] == "broken_collection_or_error"
    assert verdict(suite(1, ["test_m.py::test_a"], error=1))[0] == "broken_collection_or_error"
    many = suite(1, [f"test_m.py::test_a[{i}]" for i in range(9)], passed=60)
    assert verdict(many)[0] == "too_many_failures"                                   # more than max_fail_abs
    assert verdict(suite(1, ["test_m.py::test_a", "test_m.py::test_b"], passed=2))[0] == "too_many_failures"   # more than 40%
    assert verdict(suite(1, ["other.py::test_a"]))[0] == "unmappable_test_id"
    assert verdict(suite(1, ["weird"]))[0] == "unmappable_test_id"
    assert verdict(one, suite(1, ["test_m.py::test_b"]))[0] == "flaky"               # a different set the second time
    assert verdict(one, suite(0))[0] == "flaky"                                      # passes the second time
    ok = verdict(suite(1, ["test_m.py::test_a[1]", "test_m.py::test_a[2]"]), suite(1, ["test_m.py::test_a[1]", "test_m.py::test_a[2]"]))
    assert ok[0] == "ok" and ok[1]["fail_keys"] == {("test_m.py", None, "test_a")}   # parametrised variants collapse to one test


@needs_docker
def test_the_built_task_check_rejects_visible_tests_that_cannot_see_the_bug(generated, tmp_path):
    root, out, _, cfg = generated
    seed = load_seed(root / "seqtools")
    good = next(out.glob("g-seqtools-*"))
    assert _check_built(seed, good, cfg) == (True, "")
    blind = tmp_path / "blind"
    shutil.copytree(good, blind)
    shutil.copy(root / "seqtools" / "repo" / "seqtools.py", blind / "repo" / "seqtools.py")      # no bug in the repo
    ok, why = _check_built(seed, blind, cfg)
    assert not ok and "do not fail" in why
    broken = tmp_path / "broken"
    shutil.copytree(good, broken)
    (broken / "solution" / "seqtools.py").write_text("def mean(xs):\n    return 0\n")          # a "solution" that is not
    ok, why = _check_built(seed, broken, cfg)
    assert not ok and "original code" in why


@needs_docker
def test_tasks_of_one_seed_never_fail_exactly_the_same_tests(generated):
    _, out, _, _ = generated
    sigs = [tuple(json.loads(p.read_text())["gen"]["failing_tests"]) for p in out.glob("g-*/task.json")]
    assert len(sigs) == len(set(sigs)) == 4


@needs_docker
def test_a_seed_with_too_few_tests_is_skipped(tmp_path):
    seed = tmp_path / "s"
    (seed / "repo").mkdir(parents=True)
    (seed / "repo" / "m.py").write_text("def f():\n    return 2\n")
    (seed / "repo" / "test_m.py").write_text("from m import f\n\ndef test_f():\n    assert f() == 2\n")
    (seed / "seed.json").write_text(json.dumps({"mutate": ["m.py"], "tests": ["test_m.py"]}))
    rep = generate([seed], tmp_path / "out", GenConfig(per_seed=2, workers=1))
    assert "only 1 tests" in rep["seeds"][0]["skipped"]


@needs_docker
@pytest.mark.parametrize("per_signature", [1, 2])
def test_at_most_per_signature_tasks_share_a_failure_pattern(tmp_path, per_signature):
    seed = tmp_path / "s"
    (seed / "repo").mkdir(parents=True)
    (seed / "repo" / "m.py").write_text("def f(x):\n    y = x + 1\n    z = y * 2\n    return z - 3\n\n\ndef g(x):\n    return x\n")
    tests = ("from m import f, g\n\n\ndef test_f_a():\n    assert f(1) == 1\n\n\ndef test_f_b():\n    assert f(2) == 3\n\n\n"
             + "".join(f"def test_g_{i}():\n    assert g({i}) == {i}\n\n\n" for i in range(1, 9)))
    (seed / "repo" / "test_m.py").write_text(tests)
    (seed / "seed.json").write_text(json.dumps({"mutate": ["m.py"], "tests": ["test_m.py"]}))
    rep = generate([seed], tmp_path / "out", GenConfig(per_seed=10, workers=2, per_signature=per_signature))
    assert len(rep["seeds"][0]["tasks"]) == per_signature                       # f's mutants all fail {test_f_a, test_f_b}
    assert rep["seeds"][0]["rejected"]["same_failure_as_another_task"] >= 1


def test_tests_that_call_other_tests_keep_them_visible_too():
    src = """
def test_valid(check=None):
    assert True

def test_partial():
    test_valid(check=1)

def test_alone():
    assert True

class TestK:
    def test_base(self):
        assert True

    def test_derived(self):
        self.test_base()

    def test_other(self):
        assert True
"""
    assert close_over_calls(src, {(None, "test_partial")}) == {(None, "test_partial"), (None, "test_valid")}
    assert close_over_calls(src, {("TestK", "test_derived")}) == {("TestK", "test_derived"), ("TestK", "test_base")}
    assert close_over_calls(src, {(None, "test_alone")}) == {(None, "test_alone")}
    out = keep_only(src, close_over_calls(src, {(None, "test_partial")}))
    compile(out, "x", "exec")
    assert find_tests(out) == [(None, "test_valid"), (None, "test_partial")]


@needs_docker
def test_regenerating_a_seed_replaces_its_split_entries(generated, tmp_path):
    root, out, _, cfg = generated
    copy = tmp_path / "gen"
    shutil.copytree(out, copy)
    before = set(json.loads((copy / "SPLIT.json").read_text())["tasks"])
    generate([root / "seqtools"], copy, GenConfig(per_seed=2, workers=2, rng=99, candidate_factor=6), force=True)
    after = json.loads((copy / "SPLIT.json").read_text())["tasks"]
    assert len(after) == 2 and set(after) <= before | {p.name for p in copy.glob("g-*")}
    assert {t.id for t in load_tasks(copy)} == set(after)                              # no stale entries, no missing ones
