from dataclasses import dataclass

from errors import IdempotencyConflict, InsufficientFunds, UnknownAccount


@dataclass(frozen=True)
class Receipt:
    transfer_id: str
    src: str
    dst: str
    amount: int
    fee: int


def transfer(bank, src, dst, amount, idem_key=None):
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError("amount must be a positive integer number of cents")
    if src == dst:
        raise ValueError("src and dst must differ")
    params = (src, dst, amount)
    if idem_key is not None and idem_key in bank.receipts:
        prev_params, receipt = bank.receipts[idem_key]
        if prev_params != params:
            raise IdempotencyConflict(idem_key)
        return receipt
    if src not in bank.accounts:
        raise UnknownAccount(src)
    if dst not in bank.accounts:
        raise UnknownAccount(dst)
    fee = max(1, (amount + 50) // 100)
    total = amount + fee
    s, d = bank.accounts[src], bank.accounts[dst]
    if s.balance < total:
        raise InsufficientFunds(src)
    s.balance -= total
    d.balance += amount
    bank.fees += fee
    receipt = Receipt(f"T{len(bank.ledger) + 1}", src, dst, amount, fee)
    bank.ledger.append(receipt)
    if idem_key is not None:
        bank.receipts[idem_key] = (params, receipt)
    return receipt
