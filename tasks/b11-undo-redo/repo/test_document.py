import pytest
from document import Document


def test_insert_delete_undo_redo():
    d = Document("hello")
    d.insert(5, " world")
    d.delete(0, 1)
    assert d.text == "ello world"
    assert d.undo() and d.text == "hello world"
    assert d.undo() and d.text == "hello"
    assert not d.undo()
    assert d.redo() and d.text == "hello world"
    assert d.redo() and d.text == "ello world"
    assert not d.redo()


def test_transaction_is_one_step():
    d = Document("")
    with d.transaction():
        d.insert(0, "a")
        d.insert(1, "b")
        d.insert(2, "c")
    assert d.text == "abc"
    assert d.undo() and d.text == ""
    assert not d.undo()


def test_bounds():
    d = Document("abc")
    with pytest.raises(IndexError):
        d.insert(4, "x")
    with pytest.raises(IndexError):
        d.delete(2, 5)
