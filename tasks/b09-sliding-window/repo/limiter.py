class SlidingWindowLimiter:
    """Allow at most `limit` events per `window` seconds for each key.

    An event made at time t counts toward the limit for requests at times in
    (t, t + window): an event exactly `window` seconds old no longer counts.

    allow(key)       -> True and records the event if fewer than `limit` events are in the
                        window, otherwise False (denied calls are not recorded).
    retry_after(key) -> 0.0 if a call would be allowed now, otherwise the number of seconds
                        until the oldest counted event leaves the window.
    pending(key)     -> number of events currently counted for key. The limiter must not
                        keep more than `limit` timestamps per key, nor timestamps of
                        events that have left the window.
    reset(key)       -> forget all events of key.

    It must stay fast with hundreds of thousands of calls.
    """

    def __init__(self, limit, window, clock):
        self.limit = limit
        self.window = window
        self.clock = clock
        self._events = {}

    def allow(self, key):
        now = self.clock.now()
        events = self._events.setdefault(key, [])
        recent = [t for t in events if t > now - self.window]
        if len(recent) > self.limit:
            return False
        events.append(now)
        return True

    def retry_after(self, key):
        return self.window

    def pending(self, key):
        return len(self._events.get(key, []))

    def reset(self, key):
        self._events.pop(key, None)
