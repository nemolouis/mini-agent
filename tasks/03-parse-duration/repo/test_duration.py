import pytest
from duration import parse_duration

def test_single():
    assert parse_duration("45s") == 45

def test_combined():
    assert parse_duration("1h30m") == 5400

def test_all_units():
    assert parse_duration("1h1m1s") == 3661

def test_invalid():
    with pytest.raises(ValueError):
        parse_duration("abc")
