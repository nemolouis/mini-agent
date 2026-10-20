class FakeClock:
    def __init__(self, t=0.0):
        self.t = t

    def now(self):
        return self.t

    def set(self, t):
        self.t = t
