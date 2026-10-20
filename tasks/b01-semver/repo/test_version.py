import pytest
from version import Version
from ranges import satisfies


def V(s):
    return Version.parse(s)


def test_parse_roundtrip():
    assert str(V("1.2.3-rc.1+build.5")) == "1.2.3-rc.1+build.5"


def test_invalid():
    with pytest.raises(ValueError):
        V("1.2")


def test_numeric_ordering():
    assert V("1.2.3") < V("1.10.0") < V("2.0.0")


def test_release_beats_prerelease():
    assert V("1.0.0-rc.1") < V("1.0.0")


def test_caret_and_tilde():
    assert satisfies(V("1.9.0"), "^1.2.3")
    assert not satisfies(V("2.0.0"), "^1.2.3")
    assert satisfies(V("1.2.9"), "~1.2.3")
    assert not satisfies(V("1.3.0"), "~1.2.3")
