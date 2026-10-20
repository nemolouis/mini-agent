class EventBus:
    def __init__(self):
        self._handlers = {}

    def subscribe(self, topic, fn):
        self._handlers.setdefault(topic, []).append(fn)
        return lambda: self._handlers[topic].remove(fn)

    def publish(self, topic, payload=None):
        for fn in self._handlers.get(topic, []):
            fn(payload)
