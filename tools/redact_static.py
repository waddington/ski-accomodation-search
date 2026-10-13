#!/usr/bin/env python3
"""Redact personal details from EVERY field of EVERY CSV in a static_site build (post-processing step)."""
import csv, re, sys
from pathlib import Path
SITE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "docs"
NAME = r"[A-Z][\w'’-]+(?:\s(?:&|and)\s[A-Z][\w'’-]+)?(?:\s[A-Z][\w'’-]+)?"
RULES = [
    (re.compile(r"\b((?:enquiry |advertiser |owner )?contact(?: name)?:?\s*)" + NAME), r"\1[name removed]"),
    (re.compile(r"\b(Martin Bright|Scott Allen|Toorna Salmon|Toorna)\b"), "[name removed]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[email removed]"),
    (re.compile(r"(?<!\d)(?:\+|00)\d[\d\s().-]{7,}\d"), "[phone removed]"),
    (re.compile(r"(api[-_ ]?key[:=\s]+)[0-9A-Fa-f]{16,}", re.I), r"\1[removed]"),
]
total = 0
for f in SITE.rglob("*.csv"):
    rows = list(csv.reader(f.open(newline="")))
    n = 0
    for r in rows[1:]:
        for i, v in enumerate(r):
            new = v
            for rx, rep in RULES:
                new = rx.sub(rep, new)
            if new != v:
                r[i] = new; n += 1
    if n:
        csv.writer(f.open("w", newline="")).writerows(rows)
        print(f"{f.relative_to(SITE)}: {n} fields redacted")
    total += n
print("total", total)
