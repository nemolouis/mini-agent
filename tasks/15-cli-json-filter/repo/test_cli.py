import io
import json
from cli import main


def run(tmp_path, *flags):
    p = tmp_path / "d.csv"
    p.write_text("name,amount\na,10\nb,20\nc,60\n")
    buf = io.StringIO()
    assert main([str(p), *flags], out=buf) == 0
    return buf.getvalue().strip()


def test_text_unchanged(tmp_path):
    assert run(tmp_path) == "count=3 total=90.0 average=30.00"


def test_json(tmp_path):
    assert json.loads(run(tmp_path, "--json")) == {"count": 3, "total": 90.0, "average": 30.0}


def test_min_amount(tmp_path):
    assert run(tmp_path, "--min-amount", "20") == "count=2 total=80.0 average=40.00"


def test_json_and_filter_rounding(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("name,amount\na,1\nb,1\nc,2\n")
    buf = io.StringIO()
    main([str(p), "--json"], out=buf)
    assert json.loads(buf.getvalue())["average"] == 1.33
