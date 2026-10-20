import pytest
from accounts import Bank
from errors import InsufficientFunds
from transfer import transfer


def bank():
    b = Bank()
    b.open("a", 100_000)
    b.open("b", 0)
    return b


def test_basic_transfer_and_fee():
    b = bank()
    r = transfer(b, "a", "b", 10_000)
    assert r.fee == 100 and r.transfer_id == "T1"
    assert b.balance("a") == 100_000 - 10_100 and b.balance("b") == 10_000 and b.fees == 100


def test_insufficient_funds():
    b = bank()
    with pytest.raises(InsufficientFunds):
        transfer(b, "a", "b", 200_000)
    assert b.balance("a") == 100_000 and b.balance("b") == 0


def test_bad_amount():
    with pytest.raises(ValueError):
        transfer(bank(), "a", "b", 0)
