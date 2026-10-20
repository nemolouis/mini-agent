from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._d = OrderedDict()

    def get(self, key, default=None):
        return self._d.get(key, default)

    def put(self, key, value):
        self._d[key] = value
        if len(self._d) > self.capacity + 1:
            self._d.popitem(last=False)

    def __len__(self):
        return len(self._d)
