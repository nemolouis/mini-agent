import pytest
import store, service


@pytest.fixture(autouse=True)
def fresh():
    store.seed({"a": 5})
    service.reset()


def test_stock():
    assert service.stock("a") == 5


def test_sell_updates_stock():
    assert service.stock("a") == 5
    service.sell("a", 2)
    assert service.stock("a") == 3


def test_restock_updates_stock():
    assert service.stock("a") == 5
    service.restock("a", 3)
    assert service.stock("a") == 8


def test_oversell():
    with pytest.raises(ValueError):
        service.sell("a", 9)
    assert service.stock("a") == 5
