from rows import parse_line
from table import load


def test_plain():
    assert parse_line("a, b ,c") == ["a", "b", "c"]


def test_quoted_comma():
    assert parse_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_escaped_quote():
    assert parse_line('"say ""hi""",x') == ['say "hi"', "x"]


def test_empty_fields():
    assert parse_line("a,,c") == ["a", "", "c"]


def test_load_with_types():
    text = 'name,age\n"Doe, Jane",31\nBob,40\n'
    assert load(text, {"age": int}) == [
        {"name": "Doe, Jane", "age": 31},
        {"name": "Bob", "age": 40},
    ]
