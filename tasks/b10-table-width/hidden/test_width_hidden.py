import pytest
from render import pad, render_table
from width import char_width, display_width, truncate


def test_char_widths():
    assert char_width("a") == 1
    assert char_width("名") == 2
    assert char_width("Ａ") == 2          # fullwidth Latin
    assert char_width("ｱ") == 1           # halfwidth katakana
    assert char_width("\u0301") == 0      # combining acute
    assert char_width("\u200d") == 0      # zero width joiner


def test_display_width():
    assert display_width("名前") == 4
    assert display_width("abc") == 3
    assert display_width("e\u0301") == 1  # e + combining acute
    assert display_width("Zürich") == 6
    assert display_width("") == 0


def test_ansi_is_zero_width():
    assert display_width("\x1b[31mred\x1b[0m") == 3
    assert display_width("\x1b[1;32m名\x1b[0m") == 2


def test_pad_uses_display_width():
    assert pad("名前", 6) == "名前  "
    assert pad("名前", 6, "right") == "  名前"
    assert pad("ab", 5, "center") == " ab  "
    assert pad("\x1b[31mab\x1b[0m", 4) == "\x1b[31mab\x1b[0m  "
    assert pad("toolong", 3) == "toolong"


def test_truncate_wide():
    assert truncate("名前名前", 8) == "名前名前"
    assert truncate("名前名前", 6) == "名前…"        # 4 + 1 = 5 <= 6, next wide char would make 7
    assert truncate("名前名前", 5) == "名前…"
    assert truncate("名前名前", 4) == "名…"
    assert display_width(truncate("名前名前", 4)) <= 4


def test_truncate_ascii_and_edge():
    assert truncate("abcdef", 4) == "abc…"
    assert truncate("abc", 3) == "abc"
    assert truncate("abcdef", 1) == "…"
    with pytest.raises(ValueError):
        truncate("abcdef", 0)


def test_truncate_custom_ellipsis():
    assert truncate("abcdefgh", 6, "...") == "abc..."


def test_cjk_table_alignment():
    out = render_table(["name", "qty"], [["名前", 3], ["apple", 12]])
    assert out == "\n".join([
        "+-------+-----+",
        "| name  | qty |",
        "+-------+-----+",
        "| 名前  | 3   |",
        "| apple | 12  |",
        "+-------+-----+",
    ])


def test_combining_and_ansi_in_table():
    out = render_table(["w"], [["e\u0301"], ["\x1b[31mab\x1b[0m"], ["abc"]])
    lines = out.splitlines()
    assert lines[3] == "| e\u0301   |"
    assert lines[4] == "| \x1b[31mab\x1b[0m  |"
    assert lines[5] == "| abc |"


def test_max_col_width_with_cjk_and_center():
    out = render_table(["h"], [["名前名前名前"], ["x"]], align=["center"], max_col_width=6)
    assert out.splitlines()[3] == "| 名前… |"
    assert out.splitlines()[4] == "|   x   |"
