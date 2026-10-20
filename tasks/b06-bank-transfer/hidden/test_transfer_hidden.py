import pytest
from accounts import Bank
from errors import IdempotencyConflict, InsufficientFunds, UnknownAccount
from transfer import transfer


def bank(a=100_000):
    b = Bank()
    b.open("a", a)
    b.open("b", 0)
    return b


@pytest.mark.parametrize("amount,fee", [(150, 2), (149, 1), (49, 1), (50, 1), (1, 1), (999, 10), (1_000_000, 10_000), (250, 3)])
def test_fee_rounding(amount, fee):
    b = bank(10_000_000)
    assert transfer(b, "a", "b", amount).fee == fee


def test_unknown_destination_changes_nothing():
    b = bank()
    with pytest.raises(UnknownAccount):
        transfer(b, "a", "ghost", 1_000)
    assert b.balance("a") == 100_000 and b.fees == 0 and b.ledger == []


def test_unknown_source():
    b = bank()
    with pytest.raises(UnknownAccount):
        transfer(b, "ghost", "b", 1_000)
    assert b.balance("b") == 0 and b.ledger == []


def test_exact_funds_ok_and_one_cent_short_fails():
    b = bank(10_100)
    transfer(b, "a", "b", 10_000)
    assert b.balance("a") == 0
    b2 = bank(10_099)
    with pytest.raises(InsufficientFunds):
        transfer(b2, "a", "b", 10_000)
    assert b2.balance("a") == 10_099 and b2.balance("b") == 0 and b2.fees == 0 and b2.ledger == []


def test_idempotent_replay():
    b = bank()
    r1 = transfer(b, "a", "b", 5_000, idem_key="k1")
    r2 = transfer(b, "a", "b", 5_000, idem_key="k1")
    assert r1 == r2
    assert b.balance("b") == 5_000 and b.balance("a") == 100_000 - 5_050 and len(b.ledger) == 1 and b.fees == 50


def test_replay_works_even_if_funds_now_insufficient():
    b = bank(5_050)
    r1 = transfer(b, "a", "b", 5_000, idem_key="k")
    assert transfer(b, "a", "b", 5_000, idem_key="k") == r1


def test_idempotency_conflict():
    b = bank()
    transfer(b, "a", "b", 5_000, idem_key="k")
    with pytest.raises(IdempotencyConflict):
        transfer(b, "a", "b", 6_000, idem_key="k")
    assert len(b.ledger) == 1


def test_key_not_remembered_after_failure():
    b = bank(100)
    with pytest.raises(InsufficientFunds):
        transfer(b, "a", "b", 5_000, idem_key="k")
    b.accounts["a"].balance = 100_000
    r = transfer(b, "a", "b", 5_000, idem_key="k")
    assert r.transfer_id == "T1" and b.balance("b") == 5_000


def test_ledger_ids_sequential():
    b = bank()
    ids = [transfer(b, "a", "b", 1_000).transfer_id for _ in range(3)]
    assert ids == ["T1", "T2", "T3"]


def test_same_account_and_non_int():
    b = bank()
    with pytest.raises(ValueError):
        transfer(b, "a", "a", 100)
    with pytest.raises(ValueError):
        transfer(b, "a", "b", 10.5)
    with pytest.raises(ValueError):
        transfer(b, "a", "b", -5)
    assert b.ledger == []
