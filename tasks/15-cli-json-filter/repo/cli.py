import argparse
import csv
import sys

from report import summarize, format_text


def main(argv=None, out=None):
    out = out or sys.stdout
    p = argparse.ArgumentParser()
    p.add_argument("csv_path")
    args = p.parse_args(argv)
    with open(args.csv_path, newline="") as f:
        rows = [{"name": r["name"], "amount": float(r["amount"])} for r in csv.DictReader(f)]
    print(format_text(summarize(rows)), file=out)
    return 0
