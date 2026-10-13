#!/usr/bin/env python3
"""sl_list.py <API resort name> <sitemap slug> -> lists/<slug>.tsv (url, node, operator, name, board, beds, apiresort)"""
import json, sys, time, subprocess, urllib.parse, os
D = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
resort, slug = sys.argv[1], sys.argv[2]
boards = ["Catered Chalet", "Self Catered Chalet", "Chalet Hotel", "Chalet Club Board"]
seen = {}
for page in range(0, 20):
    q = [("page", page), ("page_size", 100), ("date_min", "2026-11-01T00:00:00.000Z"), ("date_max", "2027-05-31T23:59:59.000Z"),
         ("date_flex", 0), ("minValue", 0), ("maxValue", 99999), ("resorts[]", resort), ("adults", 2), ("children", 0),
         ("selected", ""), ("showAccommodationOnly", 1)] + [("boards[]", b) for b in boards] + [("showAllResorts", "true")]
    url = "https://api.skiline.co.uk/?" + urllib.parse.urlencode(q)
    out = subprocess.run(["curl", "-s", "-A", UA, "-H", "Referer: https://www.skiline.co.uk/", url], capture_output=True, text=True).stdout
    d = json.loads(out)
    r = d.get("filteredResults", [])
    for x in r:
        seen.setdefault(x["ref_url"].rstrip("/"), x)
    time.sleep(2.5)
    if len(r) < 100:
        break
sm = [l.strip().rstrip("/") for l in open(os.path.join(D, "acc_urls.txt")) if f"/{slug}/" in l and "chalet" in l.lower()]
rows = []
for u, x in seen.items():
    rows.append([u, x["ext_node_id"], x["operator_name"], x["property_name"], x["board"], x["beds"], x["resort_name"]])
for u in sm:
    if u not in seen:
        rows.append([u, "", "", "", "", "", "sitemap-only"])
with open(os.path.join(D, "lists", slug + ".tsv"), "w") as f:
    for r in rows:
        f.write("\t".join(str(c) for c in r) + "\n")
print(f"{slug}: api={len(seen)} sitemap={len(sm)} union={len(rows)}")
for r in rows:
    print("\t".join(str(c) for c in r))
