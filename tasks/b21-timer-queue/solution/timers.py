import heapq
import itertools


class Handle:
    def __init__(self, due):
        self.due = due
        self.cancelled = False
        self.finished = False


class TimerQueue:
    def __init__(self, clock):
        self.clock = clock
        self._heap = []          # (due, seq, handle, fn, args, interval)
        self._seq = itertools.count()
        self.errors = []

    def _push(self, h, fn, args, interval):
        heapq.heappush(self._heap, (h.due, next(self._seq), h, fn, args, interval))

    def call_later(self, delay, fn, *args):
        if delay < 0:
            raise ValueError("delay must be >= 0")
        h = Handle(self.clock.now() + delay)
        self._push(h, fn, args, None)
        return h

    def call_every(self, interval, fn, *args, first_delay=None):
        if interval <= 0:
            raise ValueError("interval must be > 0")
        first = interval if first_delay is None else first_delay
        if first < 0:
            raise ValueError("first_delay must be >= 0")
        h = Handle(self.clock.now() + first)
        self._push(h, fn, args, interval)
        return h

    def cancel(self, handle):
        if handle.cancelled or handle.finished:
            return False
        handle.cancelled = True
        return True

    def pending(self):
        return sum(1 for e in self._heap if not e[2].cancelled)

    def run_until(self, t):
        if t < self.clock.now():
            raise ValueError("cannot run backwards")
        ran = 0
        while self._heap and self._heap[0][0] <= t:
            due, _, h, fn, args, interval = heapq.heappop(self._heap)
            if h.cancelled:
                continue
            if due > self.clock.now():
                self.clock.set(due)
            try:
                fn(*args)
            except Exception as e:
                self.errors.append(e)
            ran += 1
            if interval is None:
                h.finished = True
            elif not h.cancelled:
                h.due = due + interval
                self._push(h, fn, args, interval)
        if t > self.clock.now():
            self.clock.set(t)
        return ran
