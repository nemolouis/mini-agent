import heapq


class Handle:
    def __init__(self, due):
        self.due = due
        self.cancelled = False


class TimerQueue:
    def __init__(self, clock):
        self.clock = clock
        self._heap = []
        self.errors = []

    def call_later(self, delay, fn, *args):
        h = Handle(self.clock.now() + delay)
        heapq.heappush(self._heap, (h.due, fn, args, None, h))
        return h

    def call_every(self, interval, fn, *args, first_delay=None):
        first = interval if first_delay is None else first_delay
        h = Handle(self.clock.now() + first)
        heapq.heappush(self._heap, (h.due, fn, args, interval, h))
        return h

    def cancel(self, handle):
        if handle.cancelled:
            return False
        handle.cancelled = True
        return True

    def pending(self):
        return len(self._heap)

    def run_until(self, t):
        ran = 0
        due_now = [e for e in sorted(self._heap, key=lambda e: e[0]) if e[0] <= t]
        for entry in due_now:
            self._heap.remove(entry)
            due, fn, args, interval, h = entry
            if h.cancelled:
                continue
            fn(*args)
            ran += 1
            if interval is not None:
                h.due = self.clock.now() + interval
                heapq.heappush(self._heap, (h.due, fn, args, interval, h))
        self.clock.set(t)
        return ran
