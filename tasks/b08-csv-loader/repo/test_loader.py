import pytest
from pipeline import load


def write(tmp_path, text, mode="w"):
    p = tmp_path / "d.csv"
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text)
    return str(p)


def test_basic(tmp_path):
    p = write(tmp_path, "Name,Age\nann,31\nbob,40\n")
    assert load(p, {"age": "int"}) == [{"name": "ann", "age": 31}, {"name": "bob", "age": 40}]


def test_whitespace_in_cells_and_headers(tmp_path):
    p = write(tmp_path, " Name , Age \n ann , 31 \n")
    assert load(p) == [{"name": "ann", "age": "31"}]


def test_blank_lines_skipped(tmp_path):
    p = write(tmp_path, "a,b\n\n1,2\n\n")
    assert load(p) == [{"a": "1", "b": "2"}]
