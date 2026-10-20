from render import render_table


def test_ascii_table():
    out = render_table(["name", "qty"], [["apple", 12], ["fig", 7]])
    assert out == "\n".join([
        "+-------+-----+",
        "| name  | qty |",
        "+-------+-----+",
        "| apple | 12  |",
        "| fig   | 7   |",
        "+-------+-----+",
    ])


def test_right_align():
    out = render_table(["n"], [[5], [100]], align=["right"])
    assert out.splitlines()[3] == "|   5 |"
