class Account:
    def __init__(self, account_id, balance=0):
        self.id = account_id
        self.balance = balance


class Bank:
    def __init__(self):
        self.accounts = {}
        self.fees = 0
        self.ledger = []
        self.receipts = {}   # idem_key -> ((src, dst, amount), Receipt)

    def open(self, account_id, balance=0):
        self.accounts[account_id] = Account(account_id, balance)
        return self.accounts[account_id]

    def balance(self, account_id):
        return self.accounts[account_id].balance
