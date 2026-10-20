class History:
    """Undo/redo stacks of opaque snapshots."""

    def __init__(self):
        self._undo = []
        self._redo = []

    def push(self, snapshot):
        self._undo.append(snapshot)

    def undo(self, current):
        if not self._undo:
            return None
        self._redo.append(current)
        return self._undo.pop()

    def redo(self, current):
        if not self._redo:
            return None
        self._undo.append(current)
        return self._redo.pop()
