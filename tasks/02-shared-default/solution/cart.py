class Cart:
    def __init__(self, items=None):
        self.items = list(items) if items is not None else []

    def add(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)
