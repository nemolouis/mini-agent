import pytest
from document import Document


def test_marks_shift_on_insert():
    d = Document("hello world")
    d.set_mark("w", 6)
    d.set_mark("start", 0)
    d.insert(0, ">> ")
    assert d.marks == {"w": 9, "start": 3}     # mark at the insertion point moves too
    d.insert(12, "!")                           # after every mark: nothing moves
    assert d.marks == {"w": 9, "start": 3}


def test_marks_shift_on_delete():
    d = Document("0123456789")
    for name, p in [("a", 1), ("b", 4), ("c", 6), ("d", 9)]:
        d.set_mark(name, p)
    d.delete(3, 4)                 # removes [3, 7)
    assert d.text == "012789" and d.marks == {"a": 1, "b": 3, "c": 3, "d": 5}


def test_undo_restores_marks():
    d = Document("abcdef")
    d.set_mark("m", 4)
    d.insert(0, "XX")
    assert d.marks["m"] == 6
    d.undo()
    assert d.marks["m"] == 4
    d.redo()
    assert d.marks["m"] == 6


def test_snapshots_not_aliased():
    d = Document("abc")
    d.set_mark("m", 1)
    d.set_mark("m", 2)
    d.set_mark("n", 3)
    d.undo()
    assert d.marks == {"m": 2}
    d.undo()
    assert d.marks == {"m": 1}
    d.undo()
    assert d.marks == {}


def test_set_mark_is_undoable():
    d = Document("abc")
    d.set_mark("m", 2)
    assert d.undo() and d.marks == {}


def test_new_edit_clears_redo():
    d = Document("a")
    d.insert(1, "b")
    d.undo()
    d.insert(1, "c")
    assert d.text == "ac"
    assert not d.redo()
    assert d.text == "ac"


def test_redo_chain_after_two_undos_then_edit():
    d = Document("")
    d.insert(0, "a"); d.insert(1, "b"); d.insert(2, "c")
    d.undo(); d.undo()
    d.insert(1, "X")
    assert d.text == "aX"
    assert not d.redo()
    assert d.undo() and d.text == "a"


def test_transaction_groups_marks_and_text():
    d = Document("abc")
    with d.transaction():
        d.insert(3, "d")
        d.set_mark("end", 4)
        d.delete(0, 1)
    assert d.text == "bcd" and d.marks == {"end": 3}
    d.undo()
    assert d.text == "abc" and d.marks == {}
    d.redo()
    assert d.text == "bcd" and d.marks == {"end": 3}


def test_nested_transactions_merge():
    d = Document("")
    with d.transaction():
        d.insert(0, "a")
        with d.transaction():
            d.insert(1, "b")
        d.insert(2, "c")
    assert d.text == "abc"
    assert d.undo() and d.text == ""
    assert not d.undo()


def test_empty_transaction_adds_no_step():
    d = Document("x")
    d.insert(1, "y")
    with d.transaction():
        pass
    assert d.undo() and d.text == "x"


def test_rollback_on_exception():
    d = Document("abc")
    d.set_mark("m", 1)
    with pytest.raises(RuntimeError):
        with d.transaction():
            d.insert(0, "ZZ")
            d.set_mark("m", 0)
            raise RuntimeError("boom")
    assert d.text == "abc" and d.marks == {"m": 1}
    assert d.undo() and d.marks == {}           # only the earlier set_mark is on the stack
    assert not d.undo()


def test_rollback_does_not_clear_redo():
    d = Document("a")
    d.insert(1, "b")
    d.undo()
    with pytest.raises(ValueError):
        with d.transaction():
            d.insert(1, "z")
            raise ValueError
    assert d.text == "a"
    assert d.redo() and d.text == "ab"


def test_failed_edit_leaves_no_step():
    d = Document("abc")
    with pytest.raises(IndexError):
        d.insert(10, "x")
    assert not d.undo()


def test_edit_after_transaction_is_separate_step():
    d = Document("")
    with d.transaction():
        d.insert(0, "ab")
    d.insert(2, "c")
    d.undo()
    assert d.text == "ab"
    d.undo()
    assert d.text == ""
