from merge import merge3


def test_identical():
    assert merge3(["a"], ["a"], ["a"]) == (["a"], 0)


def test_only_ours_changed():
    assert merge3(["a", "b"], ["a", "B"], ["a", "b"]) == (["a", "B"], 0)


def test_only_theirs_changed():
    assert merge3(["a", "b"], ["a", "b"], ["A", "b"]) == (["A", "b"], 0)
