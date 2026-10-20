import pytest
from pipeline import load


def write(tmp_path, data):
    p = tmp_path / "d.csv"
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return str(p)


def test_bom(tmp_path):
    p = write(tmp_path, b"\xef\xbb\xbfName,Age\nann,31\n")
    assert load(p) == [{"name": "ann", "age": "31"}]


def test_crlf(tmp_path):
    p = write(tmp_path, "a,b\r\n1,2\r\n3,4\r\n")
    assert load(p) == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]


def test_quoted_commas_quotes_and_newlines(tmp_path):
    p = write(tmp_path, 'name,note\n"Doe, Jane","said ""hi""\nthen left"\nbob,plain\n')
    assert load(p) == [{"name": "Doe, Jane", "note": 'said "hi"\nthen left'}, {"name": "bob", "note": "plain"}]


def test_header_normalization(tmp_path):
    p = write(tmp_path, " Unit   Price ,QTY,,\n1,2,3,4\n")
    assert load(p) == [{"unit_price": "1", "qty": "2", "column_3": "3", "column_4": "4"}]


def test_duplicate_headers(tmp_path):
    p = write(tmp_path, "id,Name,name,NAME\n1,a,b,c\n")
    assert load(p) == [{"id": "1", "name": "a", "name_2": "b", "name_3": "c"}]


def test_types_and_empty_cells(tmp_path):
    p = write(tmp_path, "n,x,ok,s\n3,1.5,Yes,\n,,,z\n7,2,0,hi\n")
    schema = {"n": "int", "x": "float", "ok": "bool"}
    assert load(p, schema) == [
        {"n": 3, "x": 1.5, "ok": True, "s": ""},
        {"n": None, "x": None, "ok": None, "s": "z"},
        {"n": 7, "x": 2.0, "ok": False, "s": "hi"},
    ]


def test_bool_values(tmp_path):
    p = write(tmp_path, "b\ntrue\nNO\ny\nN\n1\n0\n")
    assert [r["b"] for r in load(p, {"b": "bool"})] == [True, False, True, False, True, False]


def test_bad_bool_and_int(tmp_path):
    with pytest.raises(ValueError):
        load(write(tmp_path, "b\nmaybe\n"), {"b": "bool"})
    with pytest.raises(ValueError):
        load(write(tmp_path, "n\nabc\n"), {"n": "int"})


def test_short_and_long_rows(tmp_path):
    p = write(tmp_path, "a,b,c\n1,2\n")
    assert load(p) == [{"a": "1", "b": "2", "c": None}]
    with pytest.raises(ValueError):
        load(write(tmp_path, "a,b\n1,2,3\n"))


def test_unicode(tmp_path):
    p = write(tmp_path, "名前,city\n太郎,Zürich\n")
    assert load(p) == [{"名前": "太郎", "city": "Zürich"}]


def test_empty_file(tmp_path):
    assert load(write(tmp_path, "")) == []
    assert load(write(tmp_path, "a,b\n")) == []


def test_quoted_cell_whitespace_stripped(tmp_path):
    p = write(tmp_path, 'a\n"  x  "\n')
    assert load(p) == [{"a": "x"}]
