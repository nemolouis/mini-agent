class TransferError(Exception):
    pass


class UnknownAccount(TransferError):
    pass


class InsufficientFunds(TransferError):
    pass


class IdempotencyConflict(TransferError):
    pass
