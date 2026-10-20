import time


class RealClock:
    def now(self):
        return time.monotonic()


class FakeClock:
    def __init__(self, t=0.0):
        self.t = t

    def now(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds
