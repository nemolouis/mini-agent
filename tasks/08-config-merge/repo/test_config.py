import copy
from config import load
from defaults import DEFAULTS


def test_no_overrides():
    assert load() == DEFAULTS


def test_nested_override_keeps_siblings():
    cfg = load({"server": {"port": 9000}})
    assert cfg["server"]["port"] == 9000
    assert cfg["server"]["host"] == "localhost"
    assert cfg["server"]["tls"] == {"enabled": False, "cert": None}


def test_deep_nested_override():
    cfg = load({"server": {"tls": {"enabled": True}}})
    assert cfg["server"]["tls"] == {"enabled": True, "cert": None}


def test_defaults_not_mutated():
    before = copy.deepcopy(DEFAULTS)
    cfg = load({"server": {"port": 1}})
    cfg["server"]["tls"]["enabled"] = True
    assert DEFAULTS == before
    assert load()["server"]["tls"]["enabled"] is False


def test_new_keys_allowed():
    assert load({"extra": 1})["extra"] == 1
