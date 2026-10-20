class Cart:
    def __init__(self, items=[]):
        self.items = items

    def add(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)
