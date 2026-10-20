from datetime import datetime
import pytest
from cron import next_after


def test_every_minute():
    assert next_after("* * * * *", datetime(2024, 1, 1, 0, 0)) == datetime(2024, 1, 1, 0, 1)


def test_strictly_after():
    assert next_after("30 12 * * *", datetime(2024, 1, 1, 12, 30)) == datetime(2024, 1, 2, 12, 30)


def test_step():
    assert next_after("*/15 * * * *", datetime(2024, 1, 1, 10, 16)) == datetime(2024, 1, 1, 10, 30)


def test_bad_field_count():
    with pytest.raises(ValueError):
        next_after("* * * *", datetime(2024, 1, 1))
