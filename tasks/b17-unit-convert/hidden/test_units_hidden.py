import pytest
from units import ConversionError, convert

A = pytest.approx


def test_left_to_right_operators():
    assert convert(5, "m/s*s", "m") == A(5)
    assert convert(1, "kg/m*m", "kg") == A(1)
    assert convert(1, "m/s/s", "m/s^2") == A(1)
    assert convert(1, "km/h*h", "m") == A(1000)


def test_parentheses_and_powers():
    assert convert(1, "kg*(m/s)^2", "J") == A(1)
    assert convert(1, "(km)^2", "m^2") == A(1e6)
    assert convert(1, "m/(s*s)", "m/s^2") == A(1)
    assert convert(2, "(m*kg)/(s^2)", "N") == A(2)


def test_negative_exponents_and_one():
    assert convert(1, "s^-1", "1/s") == A(1)
    assert convert(1, "1/s", "1/min") == A(60)
    assert convert(1, "m*s^-2", "m/s^2") == A(1)
    assert convert(5, "m/m", "1") == A(5)
    assert convert(3, "1", "m/m") == A(3)


def test_derived_units():
    assert convert(1, "N*m", "J") == A(1)
    assert convert(1, "kg*m^2/s^2", "J") == A(1)
    assert convert(1, "kg*m/s^2", "N") == A(1)
    assert convert(1, "J/s", "W") == A(1)
    assert convert(1, "N/m^2", "Pa") == A(1)
    assert convert(1, "kW*h", "kJ") == A(3600)


def test_values():
    assert convert(1, "km/h", "m/s") == A(1000 / 3600)
    assert convert(60, "mi/h", "km/h") == A(96.56064)
    assert convert(1, "L", "m^3") == A(0.001)
    assert convert(1, "ft", "in") == A(12)
    assert convert(1, "lb", "g") == A(453.59237)
    assert convert(10, "m/s^2", "km/h/s") == A(36)


def test_whitespace_ignored():
    assert convert(1, " km / h ", "m / s") == A(1000 / 3600)
    assert convert(1, "kg * m ^ 2 / s ^ 2", "J") == A(1)


@pytest.mark.parametrize("src,dst", [("m", "s"), ("N", "J"), ("kg", "g/s"), ("m/s", "m*s"), ("1", "m")])
def test_dimension_mismatch(src, dst):
    with pytest.raises(ConversionError):
        convert(1, src, dst)


@pytest.mark.parametrize("bad", ["furlong", "Km", "n", "", "   ", "m//s", "m/", "/s", "(m", "m)", "m^", "m^x",
                                 "m s", "m*", "*m", "m^2^3", "(m", "()", "m^1.5", "m**s"])
def test_errors(bad):
    with pytest.raises(ConversionError):
        convert(1, bad, "m")
    with pytest.raises(ConversionError):
        convert(1, "m", bad)
