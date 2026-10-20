"""Turn unpacked sdists (from fetch_seeds.py) into seeds/<name>/{repo,seed.json}, keeping only what runs green in the sandbox.
usage: python scripts/make_seeds.py <workdir>      (reads seeds/SOURCES.json and <workdir>/raw/<name>/, writes seeds/ and seeds/SEEDS_REPORT.json)

For each package: copy the source packages/modules, the tests and the license; run the tests in the sandbox; delete the test
files that fail there (missing optional dependency, platform assumptions...) and run again; keep the seed only if enough
tests remain and the whole run is green and fast. Packages without tests in their sdist are reported and dropped."""
import json
import re
import shutil
import sys
import time
from pathlib import Path

from miniagent.taskgen.generate import GenConfig, Runner, Seed

WORK = Path(sys.argv[1])
SKIP_DIRS = {"docs", "doc", "benchmarks", "benchmark", "examples", "demos", "bin", "scripts", "tools", "requirements"}
# plain `pytest` must find the tests, as the agent will run it: a pytest.ini for the two packages that name them differently
PYTEST_INI = {"decorator": "python_files = test.py", "jsonpointer": "python_files = tests.py"}
LICENSE_RE = re.compile(r"^(licen[sc]e|copying|mit-license|notice)", re.I)
IGNORE = shutil.ignore_patterns("__pycache__", "*.egg-info", ".pytest_cache", "*.pyc")
MIN_TESTS, MAX_SECONDS = 15, 20.0


def is_test_file(p: Path) -> bool:
    n = p.name
    return n in ("test.py", "tests.py") or (n.startswith("test_") or n.endswith("_test.py")) and n != "conftest.py"


def build(name: str, root: Path, dest: Path) -> dict:
    py = [p for p in root.rglob("*.py") if not ({"setup.py", "conftest.py"} & {p.name}) and not (SKIP_DIRS & set(p.relative_to(root).parts[:-1]))]
    tests = [p for p in py if is_test_file(p)]
    if not tests:
        return {"dropped": "the sdist contains no tests"}
    tops = {p.relative_to(root).parts[0] for p in py}
    repo = dest / "repo"
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    for top in sorted(tops):
        src = root / top
        (shutil.copytree(src, repo / top, ignore=IGNORE) if src.is_dir() else shutil.copy(src, repo / top))
    for f in root.iterdir():
        if f.is_file() and LICENSE_RE.match(f.name):
            shutil.copy(f, repo / f.name)
    if name in PYTEST_INI:
        (repo / "pytest.ini").write_text(f"[pytest]\n{PYTEST_INI[name]}\n")
    src_layout = (repo / "src").is_dir()
    cmd = ("PYTHONPATH=src " if src_layout else "") + "python -m pytest -q"
    cfg = GenConfig(timeout=90)
    dropped_files: dict[str, str] = {}
    for _ in range(4):
        tfiles = sorted(str(p.relative_to(repo)) for p in repo.rglob("*.py") if is_test_file(p))
        seed = Seed(name, repo, [], tfiles, cmd)
        r = Runner(seed, cfg)
        try:
            t0 = time.time()
            run = r.run()
            took = time.time() - t0
        finally:
            r.close()
        if run.rc == 0:
            break
        bad = {i.split("::")[0] for i in run.failed}
        bad = {b for b in bad if b in tfiles}
        if not bad or run.rc not in (1, 2):
            return {"dropped": f"suite does not run in the sandbox (rc {run.rc}): {run.tail[-300:]!r}"}
        for b in bad:
            dropped_files[b] = "fails in the sandbox"
            (repo / b).unlink()
    else:
        return {"dropped": "still failing after removing failing test files", "dropped_test_files": dropped_files}
    tfiles = sorted(str(p.relative_to(repo)) for p in repo.rglob("*.py") if is_test_file(p))
    if run.total < MIN_TESTS:
        return {"dropped": f"only {run.total} tests pass", "dropped_test_files": dropped_files}
    if took > MAX_SECONDS:
        return {"dropped": f"the suite takes {took:.0f}s; too slow to run once per mutant", "tests": run.total}
    mutate = []
    for p in sorted(repo.rglob("*.py")):
        rel = p.relative_to(repo)
        if is_test_file(p) or "tests" in rel.parts or "test" in rel.parts or p.name in ("__main__.py", "conftest.py", "setup.py"):
            continue
        if SKIP_DIRS & set(rel.parts[:-1]) or "version" in p.name or "egg-info" in str(rel):
            continue
        if sum(1 for l in p.read_text(errors="replace").splitlines() if l.strip() and not l.strip().startswith("#")) >= 15:
            mutate.append(str(rel))
    return {"tests": run.total, "test_files": tfiles, "mutate": mutate, "test_cmd": cmd, "seconds": round(took, 1),
            "dropped_test_files": dropped_files}


sources = json.loads(Path("seeds/SOURCES.json").read_text())
report = {}
for s in sources:
    name = s["name"].replace("-", "_")
    root = next((WORK / "raw" / s["name"]).iterdir())            # the one top-level directory of the unpacked sdist
    out = build(name, root, Path("seeds") / name)
    if "dropped" in out:
        shutil.rmtree(Path("seeds") / name, ignore_errors=True)
        print(f"{name:18} DROPPED  {out['dropped'][:110]}")
    else:
        (Path("seeds") / name / "seed.json").write_text(json.dumps({
            "name": name, "mutate": out["mutate"], "tests": out["test_files"], "test_cmd": out["test_cmd"],
            "origin": f"pypi:{s['name']}=={s['version']} sha256:{s['sha256']}", "license": s["license"]}, indent=2))
        print(f"{name:18} ok  {out['tests']:5} tests  {out['seconds']:5}s  {len(out['mutate'])} mutable files  dropped test files: {list(out['dropped_test_files'])}")
    report[name] = out
Path("seeds/SEEDS_REPORT.json").write_text(json.dumps(report, indent=2))
