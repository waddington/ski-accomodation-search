#!/usr/bin/env python3
"""Look up known chalets without reading the whole of chalets_all.csv.

    python3 tools/find_chalet.py --village "Les Menuires"        # all known chalets in a village (substring)
    python3 tools/find_chalet.py "vithos"                        # name / id / operator substring
    python3 tools/find_chalet.py "chamois" --village coches      # both

Prints one compact line per match: chalet_id | name | operator | village | sleeps | board | listed_on.
Includes rows collectors wrote in the last minute (reads chalets/raw/*.csv too).
"""
import csv, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
norm = lambda s: unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
args = [a for a in sys.argv[1:] if not a.startswith("--village")]
village = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--village=")), None)
if "--village" in sys.argv:
    i = sys.argv.index("--village"); village = sys.argv[i + 1]; args = [a for a in args if a != village]
q = norm(" ".join(args))
seen = {}
files = [ROOT / "chalets/chalets_all.csv"] + sorted((ROOT / "chalets/raw").glob("*.csv"))
for p in files:
    if p.name.endswith(("HEADER.csv", ".issues.csv", ".sites.csv", ".changes.csv", ".newsites.csv")):
        continue
    try:
        for r in csv.DictReader(p.open(newline="")):
            cid = r.get("chalet_id")
            if not cid or cid in seen:
                if cid in seen:
                    for k in ("listed_on",):
                        if r.get(k) and r[k] not in seen[cid].get(k, ""):
                            seen[cid][k] = (seen[cid].get(k, "") + "; " + r[k]).strip("; ")
                continue
            seen[cid] = r
    except Exception:
        pass
hits = [r for r in seen.values()
        if (not village or norm(village) in norm(r.get("village")))
        and (not q or q in norm(" ".join([r.get("chalet_id", ""), r.get("chalet_name", ""), r.get("operator", "")])))]
for r in sorted(hits, key=lambda r: (r.get("village", ""), r.get("chalet_name", ""))):
    print(" | ".join([r["chalet_id"], r.get("chalet_name", ""), r.get("operator", ""), r.get("village", ""),
                      r.get("sleeps_max", ""), r.get("board", ""), r.get("listed_on", "")]))
print(f"-- {len(hits)} match(es)", file=sys.stderr)
