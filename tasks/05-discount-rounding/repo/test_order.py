from order import total

def test_no_discount():
    assert total([1000, 250]) == 1250

def test_round_half_up():
    assert total([105], 50) == 53   # 52.5 -> 53

def test_discount():
    assert total([999], 10) == 899  # 899.1 -> 899
