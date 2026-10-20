from dataclasses import dataclass

from errors import InsufficientFunds, UnknownAccount


@dataclass(frozen=True)
class Receipt:
    transfer_id: str
    src: str
    dst: str
    amount: int
    fee: int


def transfer(bank, src, dst, amount, idem_key=None):
    if not isinstance(amount, int) or amount <= 0:
        raise ValueError("amount must be a positive integer number of cents")
    fee = int(amount * 0.01)
    s = bank.accounts[src]
    s.balance -= amount + fee
    if s.balance < 0:
        s.balance += amount + fee
        raise InsufficientFunds(src)
    d = bank.accounts[dst]
    d.balance += amount
    bank.fees += fee
    receipt = Receipt(f"T{len(bank.ledger) + 1}", src, dst, amount, fee)
    bank.ledger.append(receipt)
    return receipt
