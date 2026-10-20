def is_leap(year):
    """Gregorian leap year rule."""
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def days_in_month(year, month):
    days = [31, 29 if is_leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return days[month - 1]
