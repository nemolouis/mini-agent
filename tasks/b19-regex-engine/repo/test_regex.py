from regex import fullmatch, search


def test_literals_and_dot():
    assert fullmatch("a.c", "abc") and not fullmatch("a.c", "ac")


def test_star_plus_question():
    assert fullmatch("ab*", "abbb") and fullmatch("ab+", "ab") and not fullmatch("ab+", "a")
    assert fullmatch("colou?r", "color") and fullmatch("colou?r", "colour")


def test_search_leftmost():
    assert search("b+", "aabbbcb") == (2, 5)
    assert search("x", "abc") is None
