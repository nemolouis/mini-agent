import random
import pytest
from version import Version
from ranges import satisfies

V = Version.parse
CHAIN = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
         "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]


def test_precedence_chain():
    vs = [V(s) for s in CHAIN]
    for a, b in zip(vs, vs[1:]):
        assert a < b and not (b < a) and a != b


def test_sorting():
    vs = [V(s) for s in CHAIN]
    shuffled = vs[:]
    random.Random(1).shuffle(shuffled)
    assert sorted(shuffled) == vs


def test_build_ignored():
    a, b = V("1.0.0+a"), V("1.0.0+b.2")
    assert a == b and hash(a) == hash(b) and not a < b and not b < a
    assert len({a, b}) == 1


def test_build_ignored_with_prerelease():
    assert V("1.0.0-rc.1+x") == V("1.0.0-rc.1+y")


@pytest.mark.parametrize("s", ["01.0.0", "1.02.0", "1.0.00", "1.0.0-01", "1.0.0-a..b", "1.0.0-", "1.0.0-a.01"])
def test_invalid_versions(s):
    with pytest.raises(ValueError):
        V(s)


def test_alnum_identifier_with_leading_zero_ok():
    assert V("1.0.0-0a").pre == ("0a",)
    assert V("1.0.0-0").pre == ("0",)


def test_numeric_lower_than_alnum():
    assert V("1.0.0-1") < V("1.0.0-a")
    assert V("1.0.0-alpha.1") < V("1.0.0-alpha.a")


def test_caret_zero_major():
    assert satisfies(V("0.2.9"), "^0.2.3")
    assert not satisfies(V("0.3.0"), "^0.2.3")
    assert not satisfies(V("0.2.2"), "^0.2.3")
    assert not satisfies(V("1.0.0"), "^0.2.3")


def test_caret_zero_zero():
    assert satisfies(V("0.0.3"), "^0.0.3")
    assert not satisfies(V("0.0.4"), "^0.0.3")


def test_prerelease_never_satisfies():
    assert not satisfies(V("1.5.0-rc.1"), "^1.2.3")
    assert not satisfies(V("1.2.4-alpha"), "~1.2.3")


def test_build_metadata_in_range():
    assert satisfies(V("1.4.0+exp.sha"), "^1.2.3")
