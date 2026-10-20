from datetime import date
from calendar_utils import days_in_month, is_leap
from recur import monthly
from schedule import adjust_to_business_day, business_schedule


def test_century_rules():
    assert not is_leap(1900) and not is_leap(2100) and is_leap(2000) and is_leap(2024)
    assert days_in_month(1900, 2) == 28 and days_in_month(2000, 2) == 29


def test_non_leap_century_in_schedule():
    assert monthly(date(1900, 1, 31), 2)[1] == date(1900, 2, 28)
    assert monthly(date(2100, 1, 31), 2)[1] == date(2100, 2, 28)
    assert monthly(date(2000, 1, 31), 2)[1] == date(2000, 2, 29)


def test_zero_and_negative_count():
    assert monthly(date(2023, 1, 1), 0) == []
    assert monthly(date(2023, 1, 1), -3) == []


def test_year_rollover_every_five():
    assert monthly(date(2023, 11, 30), 3, 5) == [date(2023, 11, 30), date(2024, 4, 30), date(2024, 9, 30)]


def test_no_drift_over_a_year():
    got = monthly(date(2023, 1, 31), 13)
    assert got[2] == date(2023, 3, 31) and got[4] == date(2023, 5, 31) and got[12] == date(2024, 1, 31)


def test_business_schedule_does_not_cross_month():
    assert business_schedule(date(2023, 4, 30), 2) == [date(2023, 4, 28), date(2023, 5, 30)]


def test_sunday_to_friday_and_weekdays_unchanged():
    assert adjust_to_business_day(date(2023, 7, 2)) == date(2023, 6, 30)
    assert adjust_to_business_day(date(2023, 7, 3)) == date(2023, 7, 3)
