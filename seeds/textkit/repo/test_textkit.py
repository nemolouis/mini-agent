import pytest

from textkit import (camel_to_snake, count_words, from_roman, is_palindrome, slugify, snake_to_camel, title_case,
                     to_roman, truncate, wrap)


def test_slugify_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_collapses_and_trims():
    assert slugify("  --Many   spaces & symbols--  ") == "many-spaces-symbols"


def test_slugify_keeps_digits():
    assert slugify("Python 3.12 released") == "python-3-12-released"


def test_truncate_short_text_unchanged():
    assert truncate("hello", 5) == "hello"


def test_truncate_adds_suffix():
    assert truncate("hello world", 8) == "hello..."


def test_truncate_exact_limit_of_result():
    assert len(truncate("abcdefghijklmnop", 10)) == 10


def test_truncate_tiny_limit():
    assert truncate("abcdef", 2) == ".."


def test_truncate_custom_suffix():
    assert truncate("abcdefghij", 6, suffix="~") == "abcde~"


def test_wrap_basic():
    assert wrap("the quick brown fox jumps", 10) == ["the quick", "brown fox", "jumps"]


def test_wrap_exact_fit():
    assert wrap("abc def", 7) == ["abc def"]


def test_wrap_long_word_alone():
    assert wrap("a extraordinarily b", 5) == ["a", "extraordinarily", "b"]


def test_wrap_empty():
    assert wrap("", 10) == []


def test_camel_to_snake():
    assert camel_to_snake("camelCaseName") == "camel_case_name"
    assert camel_to_snake("HTTPServer") == "http_server"
    assert camel_to_snake("already_snake") == "already_snake"


def test_snake_to_camel():
    assert snake_to_camel("snake_case_name") == "snakeCaseName"
    assert snake_to_camel("single") == "single"
    assert snake_to_camel("double__underscore") == "doubleUnderscore"


def test_title_case_small_words():
    assert title_case("the lord of the rings") == "The Lord of the Rings"


def test_title_case_last_word_capitalised():
    assert title_case("what is this for") == "What Is This For"


def test_title_case_normalises_rest():
    assert title_case("hELLO wORLD") == "Hello World"


def test_palindrome_true():
    assert is_palindrome("A man, a plan, a canal: Panama")
    assert is_palindrome("")


def test_palindrome_false():
    assert not is_palindrome("hello")


@pytest.mark.parametrize("n,s", [(1, "I"), (4, "IV"), (9, "IX"), (14, "XIV"), (40, "XL"), (90, "XC"),
                                 (400, "CD"), (1994, "MCMXCIV"), (3999, "MMMCMXCIX")])
def test_roman_round_trip(n, s):
    assert to_roman(n) == s
    assert from_roman(s) == n


def test_roman_bounds():
    with pytest.raises(ValueError):
        to_roman(0)
    with pytest.raises(ValueError):
        to_roman(4000)


def test_from_roman_rejects_non_canonical():
    for bad in ("IIII", "VX", "IC", "", "ABC"):
        with pytest.raises(ValueError):
            from_roman(bad)


def test_count_words():
    assert count_words("It's the end. The END, it's!") == {"it's": 2, "the": 2, "end": 2}
