# Transfer specification

All amounts are integer cents.

`transfer(bank, src, dst, amount, idem_key=None)` moves `amount` from account `src` to
account `dst` and returns a `Receipt`.

- `amount` must be a positive `int`, otherwise `ValueError`. `src == dst` is a `ValueError`.
- A fee is charged to the **sender on top of** the amount: fee = 1% of `amount`, rounded
  half up to a whole cent, with a minimum of 1 cent. (150 -> 2, 149 -> 1, 49 -> 1.)
- The sender pays `amount + fee`; the receiver gets `amount`; the fee is added to `bank.fees`.
- Unknown `src` or `dst` raises `UnknownAccount`. Insufficient funds (balance < amount + fee)
  raises `InsufficientFunds`. A failed transfer changes **nothing**: no balance, no fee total,
  no ledger entry.
- A successful transfer appends exactly one entry to `bank.ledger` and the receipt's
  `transfer_id` is `T<n>` where n is the new ledger length.
- Idempotency: if `idem_key` was used by an earlier **successful** transfer with the same
  `(src, dst, amount)`, return the original receipt and change nothing. The same key with
  different parameters raises `IdempotencyConflict`. A key is only remembered after success,
  so retrying after a failure with the same key is allowed.
