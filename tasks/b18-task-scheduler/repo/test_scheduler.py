from scheduler import schedule


def test_chain():
    s = schedule([{"name": "a", "duration": 2}, {"name": "b", "duration": 3, "deps": ["a"]}], 1)
    assert s.start == {"a": 0, "b": 2} and s.makespan == 5


def test_parallel():
    s = schedule([{"name": "a", "duration": 2}, {"name": "b", "duration": 3}], 2)
    assert s.start == {"a": 0, "b": 0} and s.makespan == 3


def test_empty():
    assert schedule([], 4).makespan == 0
