_DB = {}

def seed(data):
    _DB.clear()
    _DB.update(data)

def read(sku):
    return _DB.get(sku, 0)

def write(sku, qty):
    _DB[sku] = qty
