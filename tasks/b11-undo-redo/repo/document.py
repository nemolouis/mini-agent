from contextlib import contextmanager

from history import History
from marks import shift_for_delete, shift_for_insert


class Document:
    """A text buffer with named position marks and undo/redo.

    - insert(pos, s) / delete(pos, n) edit the text (IndexError if out of range).
      Marks are kept in sync: see marks.py.
    - set_mark(name, pos) sets a mark (IndexError if pos is outside 0..len(text)).
    - Every edit, including set_mark, is one undoable step; undo() restores text AND marks.
    - undo()/redo() return True if something was undone/redone, else False.
    - Performing a new edit after undo discards the redo history.
    - transaction() is a context manager grouping all edits inside it into ONE undo step.
      Transactions may be nested (they merge into the outermost one). A transaction in
      which nothing was edited adds no undo step. If an exception escapes the outermost
      transaction, the document is rolled back to its state before the transaction, no
      undo step is added, and the exception propagates.
    """

    def __init__(self, text=""):
        self.text = text
        self.marks = {}
        self._history = History()
        self._tx_depth = 0
        self._tx_start = None
        self._tx_dirty = False

    def _state(self):
        return {"text": self.text, "marks": self.marks}

    def _restore(self, state):
        self.text = state["text"]
        self.marks = state["marks"]

    def _record(self):
        self._history.push(self._state())

    def insert(self, pos, s):
        if not 0 <= pos <= len(self.text):
            raise IndexError(pos)
        self._record()
        self.text = self.text[:pos] + s + self.text[pos:]
        self.marks = shift_for_insert(self.marks, pos, len(s))

    def delete(self, pos, n):
        if n < 0 or not 0 <= pos <= len(self.text) - n:
            raise IndexError(pos)
        self._record()
        self.text = self.text[:pos] + self.text[pos + n:]
        self.marks = shift_for_delete(self.marks, pos, n)

    def set_mark(self, name, pos):
        if not 0 <= pos <= len(self.text):
            raise IndexError(pos)
        self._record()
        self.marks[name] = pos

    def undo(self):
        state = self._history.undo(self._state())
        if state is None:
            return False
        self._restore(state)
        return True

    def redo(self):
        state = self._history.redo(self._state())
        if state is None:
            return False
        self._restore(state)
        return True

    @contextmanager
    def transaction(self):
        yield self
