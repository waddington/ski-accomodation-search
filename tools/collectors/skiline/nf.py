#!/usr/bin/env python3
"""nf.py <run-slug> : for catered/chalet rows with private hot tub, fetch page and flag shared-residence hot tubs + 'Bedrooms: N'."""
import sys, json, re, time, subprocess, html, csv
CSV='/home/kai/Documents/Misc/ski-chalet-finder/chalets/raw/site-ski-line.csv'
IDS={}
for x in csv.DictReader(open(CSV)):
    for u in [x['url']] + re.findall(r'https://www.skiline\S+', x['notes']):
        IDS.setdefault(u.rstrip(';,'), (x['chalet_id'], x['bedrooms']))
rows = [json.loads(l) for l in open(f"tools/collectors/skiline/runs/{sys.argv[1]}.jsonl")]
for r in rows:
    if not r["hot_tub"].startswith("private") or r["property_type"] not in ("chalet", "chalet-hotel", ""):
        continue
    t = subprocess.run(["curl", "-s", "-A", "Mozilla/5.0 (X11; Linux x86_64) Chrome/120", "-e", "https://www.skiline.co.uk/", r["url"]], capture_output=True, text=True).stdout
    t = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S)))
    t = re.sub(r"\s+", " ", t)
    i = t.find("Sleeps"); t = t[max(0, i - 200):] if i > 0 else t
    t = t[:t.find("Similar")] if "Similar" in t else t
    sh = [m.group(0) for m in re.finditer(r"[^.]{0,120}(hot ?tub|jacuzzi|whirlpool|spa)[^.]{0,120}", t, re.I)
          if re.search(r"residen|shared(?! balcony| with access)|communal(?! facilities| areas)|complex|whirlpool bath|hotel|wellness|extra charge|on site|apartment block", m.group(0), re.I)]
    b = re.search(r"Bedrooms\s*:?\s*(\d+)\b", t)
    flag = "SHARED?" if sh else "ok"
    cid, wb = IDS.get(r["url"], ("", ""))
    if b and cid and str(wb) != b.group(1):
        with open("/home/kai/Documents/Misc/ski-chalet-finder/chalets/corrections.csv", "a", newline="") as f:
            csv.writer(f).writerow([cid, "bedrooms", b.group(1), f"site-ski-line 2026-10-06: Ski Line page 'Bedrooms {b.group(1)}' (scraper gave '{wb}')"])
        print(f"   corrected bedrooms {cid}: {wb} -> {b.group(1)}")
    if not sh and not b: time.sleep(2); continue
    print(f"{flag} | {r['chalet_name']} | {r['board']} | {r['hot_tub']} | bedrooms {r['bedrooms']} page {b.group(1) if b else '-'} | {r['url']}")
    for s in sh[:2]:
        print("     ", s.strip()[:220])
    time.sleep(2)
