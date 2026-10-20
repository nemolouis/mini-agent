class Cache:
    def __init__(self):
        self._d = {}

    def get(self, key, loader):
        if key not in self._d:
            self._d[key] = loader(key)
        return self._d[key]

    def invalidate(self, key=None):
        if key is None:
            self._d.clear()
        else:
            self._d.pop(key, None)
