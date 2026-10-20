import argparse
import csv
import json
import sys

from report import summarize, format_text


def main(argv=None, out=None):
    out = out or sys.stdout
    p = argparse.ArgumentParser()
    p.add_argument("csv_path")
    p.add_argument("--json", action="store_true")
    p.add_argument("--min-amount", type=float, default=None)
    args = p.parse_args(argv)
    with open(args.csv_path, newline="") as f:
        rows = [{"name": r["name"], "amount": float(r["amount"])} for r in csv.DictReader(f)]
    if args.min_amount is not None:
        rows = [r for r in rows if r["amount"] >= args.min_amount]
    s = summarize(rows)
    if args.json:
        s["average"] = round(s["average"], 2)
        print(json.dumps(s), file=out)
    else:
        print(format_text(s), file=out)
    return 0
