#!/usr/bin/env python3
"""Extract tables from a PDF into CSV files (sample script for agent-skills-lint)."""

import argparse
import csv
import os


def parse_pages(spec):
    pages = []
    for part in spec.split(","):
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="1")
    ap.add_argument("--out", default="tables")
    args = ap.parse_args()

    import pdfplumber  # imported late so --help works without it

    os.makedirs(args.out, exist_ok=True)
    with pdfplumber.open(args.pdf) as pdf:
        for number in parse_pages(args.pages):
            page = pdf.pages[number - 1]
            for i, table in enumerate(page.extract_tables(), 1):
                path = os.path.join(args.out, "page%d_table%d.csv" % (number, i))
                with open(path, "w", newline="") as fh:
                    csv.writer(fh).writerows(table)
                print(path)


if __name__ == "__main__":
    main()
