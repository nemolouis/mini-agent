import time
from datetime import datetime
import pytest
import tokens
from timeutil import to_epoch


@pytest.fixture(params=["UTC", "America/New_York", "Asia/Kolkata"])
def tz(request, monkeypatch):
    monkeypatch.setenv("TZ", request.param)
    time.tzset()
    yield request.param
    monkeypatch.undo()
    time.tzset()


def test_known_epochs(tz):
    assert to_epoch(datetime(2024, 1, 1)) == 1704067200
    assert to_epoch(datetime(2024, 7, 1)) == 1719792000


def test_expiry(tz):
    now = datetime(2024, 3, 10, 12, 0, 0)
    exp = tokens.issue(now, 3600)
    assert not tokens.is_expired(exp, datetime(2024, 3, 10, 12, 59, 59))
    assert tokens.is_expired(exp, datetime(2024, 3, 10, 13, 0, 0))
