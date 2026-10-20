import pytest
from api import list_users

USERS = list(range(25))


def test_first_page():
    r = list_users(USERS, 1, 10)
    assert r["items"] == list(range(10))
    assert r["total_pages"] == 3
    assert r["has_next"] is True


def test_middle_page():
    r = list_users(USERS, 2, 10)
    assert r["items"] == list(range(10, 20))
    assert r["has_next"] is True


def test_last_partial_page():
    r = list_users(USERS, 3, 10)
    assert r["items"] == [20, 21, 22, 23, 24]
    assert r["has_next"] is False


def test_exact_multiple():
    r = list_users(list(range(20)), 2, 10)
    assert r["total_pages"] == 2
    assert r["has_next"] is False


def test_empty():
    r = list_users([], 1, 10)
    assert r == {"items": [], "page": 1, "total_pages": 0, "has_next": False}


def test_bad_page():
    with pytest.raises(ValueError):
        list_users(USERS, 0, 10)
