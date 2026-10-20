from difflib_lite import diff


def rebuild(ops):
    return [x for o, x in ops if o in "=-"], [x for o, x in ops if o in "=+"]


def test_identical():
    assert diff(list("abc"), list("abc")) == [("=", "a"), ("=", "b"), ("=", "c")]


def test_insert_and_delete():
    ops = diff(list("abc"), list("abxc"))
    assert rebuild(ops) == (list("abc"), list("abxc"))


def test_empty():
    assert diff([], []) == []
    assert diff([], [1]) == [("+", 1)]
