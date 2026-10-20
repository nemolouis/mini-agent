import pytest
from units import ConversionError, convert


def test_simple():
    assert convert(2, "km", "m") == pytest.approx(2000)


def test_speed():
    assert convert(36, "km/h", "m/s") == pytest.approx(10)


def test_mismatch():
    with pytest.raises(ConversionError):
        convert(1, "m", "s")
