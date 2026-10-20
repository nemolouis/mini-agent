def moving_average(xs, k):
    """Return the average of each window of k consecutive items."""
    out = []
    for i in range(len(xs) - k + 1):
        out.append(sum(xs[i:i + k]) / k)
    return out
