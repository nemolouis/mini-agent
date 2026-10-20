from cart import Cart

def test_add():
    c = Cart()
    c.add("a")
    assert c.count() == 1

def test_independent_carts():
    a, b = Cart(), Cart()
    a.add("x")
    assert b.count() == 0

def test_initial_items_not_aliased():
    src = ["p"]
    c = Cart(src)
    c.add("q")
    assert src == ["p"]
