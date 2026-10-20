from money import apply_percent

def total(prices_cents, discount_percent=0):
    return apply_percent(sum(prices_cents), discount_percent)
