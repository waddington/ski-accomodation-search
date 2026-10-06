#!/usr/bin/env python3
"""Append one chalet row to a collector CSV, checked against chalets/raw/HEADER.csv.

    python3 tools/append_row.py <collector.csv> '<json object>'

Creates the CSV with the header if missing. Unknown keys are rejected; missing keys are blank.
For an issues/sites log, pass --header=chalets/raw/ISSUES_HEADER.csv (or any header file).
"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("--header=")]
hdr_arg = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--header=")), None)
header_file = Path(hdr_arg) if hdr_arg else ROOT / "chalets/raw/HEADER.csv"
if not header_file.is_absolute():
    header_file = ROOT / header_file
if len(args) != 2:
    sys.exit(__doc__)
out = Path(args[0])
if not out.is_absolute():
    out = ROOT / out
row = json.loads(args[1])
fields = next(csv.reader(header_file.open()))
bad = set(row) - set(fields)
if bad:
    sys.exit(f"unknown columns: {sorted(bad)}\nallowed: {fields}")
new = not out.exists() or out.stat().st_size == 0
with out.open("a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    if new:
        w.writeheader()
    w.writerow({k: ("" if v is None else str(v)) for k, v in row.items()})
print(f"appended {row.get('chalet_id') or row.get('site') or ''} -> {out}")
