from datetime import date
from recur import monthly
from schedule import adjust_to_business_day


def test_month_end_chain():
    assert monthly(date(2023, 1, 31), 3) == [date(2023, 1, 31), date(2023, 2, 28), date(2023, 3, 31)]


def test_leap_2024():
    assert monthly(date(2024, 1, 31), 2)[1] == date(2024, 2, 29)


def test_every_two_months():
    assert monthly(date(2023, 1, 15), 3, 2) == [date(2023, 1, 15), date(2023, 3, 15), date(2023, 5, 15)]


def test_weekend_moves_back():
    assert adjust_to_business_day(date(2023, 7, 1)) == date(2023, 6, 30)
