class EventBus:
    def __init__(self):
        self._handlers = {}

    def subscribe(self, topic, fn):
        self._handlers.setdefault(topic, []).append(fn)

        def unsubscribe():
            try:
                self._handlers[topic].remove(fn)
            except (KeyError, ValueError):
                pass

        return unsubscribe

    def publish(self, topic, payload=None):
        errors = []
        for fn in list(self._handlers.get(topic, [])):
            try:
                fn(payload)
            except Exception as e:
                errors.append(e)
        return errors
