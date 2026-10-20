import csv


def parse_line(line):
    return [f.strip() for f in next(csv.reader([line]))]
