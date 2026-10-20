import random
import pytest
from scheduler import CycleError, schedule


def T(name, d, deps=(), cpus=1):
    return {"name": name, "duration": d, "deps": list(deps), "cpus": cpus}


def test_diamond_with_critical_path_priority():
    s = schedule([T("A", 3), T("B", 2, ["A"]), T("C", 2, ["A"]), T("D", 1, ["B", "C"])], 2)
    assert s.start == {"A": 0, "B": 3, "C": 3, "D": 5} and s.makespan == 6


def test_non_fitting_task_is_skipped_not_blocking():
    s = schedule([T("X", 2, cpus=3), T("Y", 4), T("Z", 1)], 3)
    assert s.start == {"Y": 0, "Z": 0, "X": 4} and s.makespan == 6


def test_simultaneous_completions_are_processed_together():
    s = schedule([T("A", 2), T("B", 2), T("C", 1, ["A", "B"], cpus=2), T("D", 1)], 2)
    assert s.start == {"A": 0, "B": 0, "C": 2, "D": 3} and s.makespan == 4


def test_priority_is_critical_path_not_duration():
    s = schedule([T("S1", 1), T("T1", 10, ["S1"]), T("S2", 4)], 1)
    assert s.start == {"S1": 0, "T1": 1, "S2": 11} and s.makespan == 15


def test_ties_broken_by_name():
    s = schedule([T("b", 2), T("a", 2), T("c", 2)], 1)
    assert s.start == {"a": 0, "b": 2, "c": 4}


def test_input_order_does_not_matter():
    tasks = [T("A", 3), T("B", 2, ["A"]), T("C", 2, ["A"]), T("D", 1, ["B", "C"]), T("E", 4), T("F", 1, ["E"], cpus=2)]
    base = schedule(tasks, 2)
    rng = random.Random(3)
    for _ in range(10):
        shuffled = tasks[:]
        rng.shuffle(shuffled)
        assert schedule(shuffled, 2) == base


def test_validation():
    with pytest.raises(ValueError):
        schedule([T("a", 1), T("a", 2)], 1)
    with pytest.raises(ValueError):
        schedule([T("a", 1, ["nope"])], 1)
    with pytest.raises(ValueError):
        schedule([T("a", 0)], 1)
    with pytest.raises(ValueError):
        schedule([T("a", 1, cpus=3)], 2)
    with pytest.raises(ValueError):
        schedule([T("a", 1, cpus=0)], 2)


def test_cycles():
    with pytest.raises(CycleError):
        schedule([T("a", 1, ["b"]), T("b", 1, ["a"])], 1)
    with pytest.raises(CycleError):
        schedule([T("a", 1, ["a"])], 1)
    with pytest.raises(CycleError):
        schedule([T("a", 1), T("b", 1, ["c"]), T("c", 1, ["d"]), T("d", 1, ["b"])], 2)


def test_defaults():
    s = schedule([{"name": "a", "duration": 2}, {"name": "b", "duration": 2}], 1)
    assert s.start == {"a": 0, "b": 2}


def test_random_schedules_satisfy_invariants():
    rng = random.Random(11)
    for _ in range(150):
        n = rng.randint(1, 12)
        cap = rng.randint(1, 4)
        tasks = []
        for i in range(n):
            deps = [f"t{j}" for j in range(i) if rng.random() < 0.25]
            tasks.append(T(f"t{i}", rng.randint(1, 5), deps, rng.randint(1, cap)))
        s = schedule(tasks, cap)
        by = {t["name"]: t for t in tasks}
        end = {k: s.start[k] + by[k]["duration"] for k in by}
        assert set(s.start) == set(by)
        assert s.makespan == max(end.values())
        for k, t in by.items():                       # dependencies finished before start
            assert all(end[d] <= s.start[k] for d in t["deps"])

        def used(at):
            return sum(by[k]["cpus"] for k in by if s.start[k] <= at < end[k])

        for at in {0} | set(end.values()):
            assert used(at) <= cap
            # work conserving: a task that was ready at `at` but not started must not have fitted
            for k, t in by.items():
                if s.start[k] > at and all(end[d] <= at for d in t["deps"]):
                    assert cap - used(at) < t["cpus"], (tasks, cap, s, at, k)
