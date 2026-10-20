from words import top_words

def test_most_frequent_first():
    assert top_words("a b b c c c", 2) == ["c", "b"]

def test_ties_alphabetical():
    assert top_words("b a c", 3) == ["a", "b", "c"]

def test_case_insensitive():
    assert top_words("Go go GO stop", 1) == ["go"]
