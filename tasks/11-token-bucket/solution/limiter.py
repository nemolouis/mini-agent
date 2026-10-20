class TokenBucket:
    """Allows up to `capacity` burst, refilling `rate` tokens per second."""

    def __init__(self, capacity, rate, clock):
        self.capacity = capacity
        self.rate = rate
        self.clock = clock
        self.tokens = capacity
        self.last = clock.now()

    def allow(self, cost=1):
        now = self.clock.now()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
