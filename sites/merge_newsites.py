#!/usr/bin/env python3
"""Add sites that agents discovered (chalets/raw/*.newsites.csv) to sites/sites.csv, skipping known names/URLs.

    python3 sites/merge_newsites.py && python3 sites/build_sites_md.py
"""
import csv
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites/sites.csv"
rows = list(csv.DictReader(SITES.open(newline="")))
fields = list(rows[0].keys())
host = lambda u: urlparse(u).netloc.removeprefix("www.").removeprefix("fr.").removeprefix("en.")
names, hosts = {r["name"].lower() for r in rows}, {host(r["url"]) for r in rows if r["url"]}
added = 0
for p in sorted((ROOT / "chalets/raw").glob("*.newsites.csv")):
    for n in csv.DictReader(p.open(newline="")):
        if n["name"].lower() in names or (n["url"] and host(n["url"]) in hosts):
            continue
        cat = {"official": "fallback"}.get(n["category"], n["category"] or "company")
        rows.append({**{f: "" for f in fields}, "name": n["name"], "url": n["url"], "category": cat,
                     "area": n["area"], "notes": n["notes"], "added": f"agent: {p.name.split('.')[0]}"})
        names.add(n["name"].lower()); hosts.add(host(n["url"])); added += 1
with SITES.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
print(f"{added} new sites added; {len(rows)} total")
