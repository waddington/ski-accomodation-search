#!/usr/bin/env python3
"""sl_one.py <todo.tsv> <lineno 1-based> [--village=X] [--dry]  -> fetch detail + prices, append row, save images."""
import json, sys, re, html, time, subprocess, csv, os, urllib.parse, datetime
D = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/kai/Documents/Misc/ski-chalet-finder"
TASK = "site-ski-line"
OUT = f"{ROOT}/chalets/raw/{TASK}.csv"
ISS = f"{ROOT}/chalets/raw/{TASK}.issues.csv"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
TODAY = "2026-10-06"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1") for a in sys.argv[1:] if a.startswith("--"))
todo, ln = args[0], int(args[1])
line = open(todo).read().splitlines()[ln - 1].split("\t")
url, node, op_api, name_api, board_api, beds_api, apires = (line + [""] * 7)[:7]

def curl(u):
    return subprocess.run(["curl", "-sL", "-A", UA, "-H", "Referer: https://www.skiline.co.uk/", u], capture_output=True, text=True).stdout

T3V = "Les 3 Vallées"; PDS = "Portes du Soleil"
# slug -> (default village, ski_area, country, [(regex, village)])
CFG = json.load(open(os.path.join(D, "cfg.json")))
slug = url.split("/")[5]
cfg = CFG.get(slug)
if not cfg:
    sys.exit(f"no cfg for {slug}")
s = curl(url)
time.sleep(2.5)
if not s or "entry-title" not in s:
    print("FAIL fetch", url); sys.exit(2)
def txt(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    h = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    return html.unescape(h)
title = html.unescape(re.search(r'<h1 class="entry-title">(.*?)</h1>', s, re.S).group(1)).strip()
ov = s[s.find('id="overview"'):]
ov = ov[:ov.find('price-and-favorite')]
boardli = re.findall(r'<ul class="board">(.*?)</ul>', ov, re.S)
blis = [txt(x).strip() for x in re.findall(r"<li>(.*?)</li>", boardli[0], re.S)] if boardli else []
board_pg = next((b for b in blis if b and not b.lower().startswith("sleeps")), "")
sleeps_pg = next((b for b in blis if b.lower().startswith("sleeps")), "")
feats = re.findall(r'title="([^"]+)"><span', ov)
dists = [txt(x).strip() for x in re.findall(r"<li>(.*?)</li>", (re.findall(r'<ul class="distances">(.*?)</ul>', ov, re.S) or [""])[0], re.S)]
nid = (re.search(r'data-nid="(\d+)"', s) or re.search(r'ext_node_id=(\d+)', s))
node = node or (nid.group(1) if nid else "")
full = txt(s)
lines = [l.strip() for l in full.split("\n") if l.strip()]
try:
    i = lines.index("Details")
    j = next(k for k in range(i + 1, len(lines)) if lines[k] in ("Please Note", "Catering", "Ski Rental", "Location", "Facilities"))
    det = lines[i + 1:j]
except Exception:
    det = []
dtext = " ".join(det)
board = board_pg or board_api
BMAP = {"Catered Chalet": ("chalet", "catered"), "Self Catered Chalet": ("chalet", "self-catered"), "Chalet Hotel": ("chalet-hotel", "chalet-hotel"),
        "Chalet Club Board": ("chalet", "catered"), "Self Catered Apartment": ("apartment", "self-catered"), "Catered Apartment": ("apartment", "catered")}
if board not in BMAP or (board == "Self Catered Apartment" and not opts.get("keep")):
    print(f"SKIP board={board!r} {title} {url}"); sys.exit(3)
ptype, bd = BMAP[board]
# prices
prices = []
if node:
    q = urllib.parse.urlencode({"ext_node_id": node, "selected": "", "sort_by": "Date", "date_min": "2026-10-06T00:00:00.000Z", "date_max": "2027-06-01T00:00:00.000Z"})
    try:
        prices = json.loads(curl("https://api.skiline.co.uk/prices?" + q))
        if not isinstance(prices, list): prices = []
    except Exception:
        prices = []
    time.sleep(2.5)
api = prices[0] if prices else {}
op = (api.get("operator_name") or op_api or "").strip()
seven = [p for p in prices if str(p.get("duration")) == "7"]
pos = [float(p["now_price"]) for p in seven if float(p.get("now_price") or 0) > 0]
dep = [p for p in seven if p["departure_date"] in ("2027-03-20", "2027-03-21")]
wd = {datetime.date.fromisoformat(p["departure_date"]).weekday() for p in seven}
chg = "Saturday" if wd == {5} else "Sunday" if wd == {6} else ("flexible" if len(wd) > 1 else "unknown")
p20 = [float(p["now_price"]) for p in dep if float(p.get("now_price") or 0) > 0]
notes = []
inc = set()
for p in seven:
    inc.add("flights" if p.get("out_departure_airport") not in (None, "", "Independent Travel") else "no-flights")
price20 = min(p20) if p20 else ""
avail = "yes" if p20 else "unknown"
if dep and not p20:
    notes.append("Ski Line lists a 20 Mar departure but with price 0 (probably sold/on request)")
if not prices:
    notes.append("no prices on Ski Line API for this property; pass2: exact-week price")
elif not dep:
    notes.append("no 20 Mar 2027 departure in Ski Line price list (not offered/sold?)")
if p20:
    d0 = [p for p in dep if float(p["now_price"]) == price20][0]
    notes.append(f"20 Mar price from Ski Line price API ({d0.get('out_departure_airport')}{', room ' + d0['room_type'] if d0.get('room_type') else ''})")
pinc = ""
if inc == {"flights"}: pinc = "flights, transfers (package via Ski Line) + chalet board"
elif inc == {"no-flights"}: pinc = "accommodation + board, no flights (Ski Line)"
elif inc: pinc = "mixed: some departures include flights"
# features
fl = [f.lower() for f in feats]
apiflag = lambda k: api.get(k)
lowtxt = (dtext + " " + " ".join(lines)).lower()
dlow = dtext.lower()
hot = "unknown"
if "hot tub" in fl or apiflag("hot_tub") == 1 or re.search(r"hot[- ]?tub|jacuzzi|spa bath", dlow):
    if re.search(r"(outdoor|outside|terrace|balcony|garden)[^.]{0,40}(hot[- ]?tub|jacuzzi)|(hot[- ]?tub|jacuzzi)[^.]{0,40}(outdoor|outside|terrace|balcony|garden)", dlow) and ptype == "chalet":
        hot = "private-outdoor"
    elif re.search(r"(indoor)[^.]{0,30}(hot[- ]?tub|jacuzzi)", dlow) and ptype == "chalet":
        hot = "private-indoor"
    else:
        hot = "yes-type-unknown"
elif api:
    hot = "none"
sauna = "yes" if ("sauna" in fl or apiflag("sauna") == 1 or "sauna" in dlow) else ("no" if api else "unknown")
other = []
if "swimming pool" in fl or apiflag("pool") == 1: other.append("pool")
if apiflag("steam_room") == 1 or "steam" in dlow: other.append("steam room")
if apiflag("open_fire") == 1 or re.search(r"fireplace|log fire|open fire|wood.?burn", dlow): other.append("fireplace")
if apiflag("childcare") == 1 or "childcare" in fl: other.append("childcare")
if apiflag("private_chauffeur") == 1: other.append("private chauffeur")
if apiflag("in_resort_driver") == 1 or apiflag("private_bus") == 1: other.append("resort driver/minibus")
dist = ""
dd = api.get("distance_toLift") or api.get("distance_toPiste") or (dists[0] if dists else "")
m = re.search(r"(\d+(?:\.\d+)?)\s*(km|m)\b", dd or "")
if m:
    dist = int(float(m.group(1)) * (1000 if m.group(2) == "km" else 1))
sio = "yes" if (api.get("ski_in_ski_out") == 1 or "ski in/ski out" in fl or "ski in/ ski out" in fl) else ("partial" if api.get("nearly_ski_in_ski_out") == 1 else "unknown")
# sleeps
smin = smax = ""
m = re.search(r"Sleeps\s*(\d+)\s*(?:-|to|–)\s*(\d+)", sleeps_pg)
if m: smin, smax = int(m.group(1)), int(m.group(2))
else:
    m = re.search(r"Sleeps\s*(\d+)", sleeps_pg)
    if m: smax = int(m.group(1))
    elif beds_api or api.get("beds"): smax = int(api.get("beds") or beds_api); notes.append("sleeps from Ski Line 'beds' field")
W = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
bedrooms = ""
m = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)[ -](?:en-?suite |spacious |double |large |comfortable |guest )?bed(?:room|rooms)\b", dlow)
if m: bedrooms = W.get(m.group(1), m.group(1)); bedrooms = int(bedrooms)
baths = ""
# village
vil = opts.get("village")
hay = (title + " " + dtext + " " + url).lower()
if not vil:
    vil = cfg["default"]
    for rx, v in cfg.get("pats", []):
        if re.search(rx, hay):
            vil = v; notes.append(f"village from text match '{rx}'"); break
    else:
        if cfg.get("generic"): notes.append(f"exact village/sector not stated on Ski Line page ({cfg['default']})")
# images
imgs = []
for u in re.findall(r'https://www\.skiline\.co\.uk/wp-content/uploads/[^"\'\s)]+?\.(?:webp|jpe?g|png)', s):
    if re.search(r"-\d+x\d+\.", u) or re.search(r"pack-|buy-1-get|logo|icon|feefo|award|abta|atol", u, re.I): continue
    if u not in imgs: imgs.append(u)
if api.get("imageURL") and api["imageURL"] not in imgs: imgs.insert(0, api["imageURL"])
# name / id
name = re.sub(r"\s*\((family|adults? only)\)\s*$", "", title, flags=re.I) if False else title
def slugify(x):
    x = x.lower()
    for a, b in (("é","e"),("è","e"),("ê","e"),("à","a"),("â","a"),("ô","o"),("ö","o"),("ü","u"),("ï","i"),("î","i"),("ç","c"),("'",""),("’","")):
        x = x.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", x).strip("-")
opslug = slugify(op) if op else "skiline"
cid = f"{opslug}-{slugify(re.sub(r'^chalet\s+', '', name, flags=re.I))}" if not name.lower().startswith("chalet") else f"{opslug}-{slugify(name[7:])}"
cid = opts.get("id", cid)
# dup check
def norm(x):
    x = slugify(x)
    x = re.sub(r"^(chalet|le|la|les)-", "", x); x = re.sub(r"-(family|2|3)$", "", x)
    return x
allrows = list(csv.DictReader(open(f"{ROOT}/chalets/chalets_all.csv")))
mine = list(csv.DictReader(open(OUT))) if os.path.exists(OUT) else []
if any(r["chalet_id"] == cid for r in mine) and not opts.get("force"):
    print(f"ALREADY-WRITTEN {cid}"); sys.exit(4)
cands = [r for r in allrows if norm(r["chalet_name"]) == norm(name) and (r["village"].split(":")[0].split(" ")[0][:5].lower() == vil.split(":")[0].split(" ")[0][:5].lower() or r["ski_area"] == cfg["area"])]
exist = None
for r in cands:
    if r["chalet_id"] == cid or (op and op.lower() in r["operator"].lower()) or "unknown" in r["operator"].lower() or not r["operator"]:
        exist = r; break
desc = " ".join(dtext.split()[:40])
row = dict(chalet_id=cid, chalet_name=name, operator=op or "", village=vil, ski_area=cfg["area"], country=cfg["country"],
           sleeps_min=smin, sleeps_max=smax, bedrooms=bedrooms, bathrooms=baths, property_type=ptype, board=bd,
           hot_tub=hot, sauna=sauna, other_facilities=", ".join(other), distance_to_lift_m=dist, ski_in_out=sio,
           changeover_day=chg if seven else "unknown", price_week_20_27_mar_2027=price20, price_basis="per-person" if prices else "",
           price_currency="GBP" if prices else "", price_type=("exact-week" if p20 else ("season-range" if pos else "")),
           price_range_low=min(pos) if pos else "", price_range_high=max(pos) if pos else "", price_includes=pinc,
           available_20_27_mar=avail, description=desc, url=url, listed_on="Ski Line", found_via=TASK,
           date_checked=TODAY)
if not op: notes.append("operator not named on Ski Line page")
if hot not in ("unknown", "none"): notes.append("hot tub per Ski Line facilities/API flag" + ("" if hot == "yes-type-unknown" else " + description"))
if board == "Chalet Club Board": notes.append("Ski Line board 'Chalet Club Board'")
if pos: notes.append("Ski Line prices pp (based on full occupancy per site note)")
if not bedrooms: notes.append("pass2: bedrooms")
row["notes"] = "; ".join(notes)
same = ""
if exist:
    keep = {"chalet_id", "listed_on", "found_via", "date_checked"}
    out = {k: v for k, v in row.items() if k in keep or (v not in ("", None) and not exist.get(k))}
    out["chalet_id"] = exist["chalet_id"]; cid = exist["chalet_id"]
    out["notes"] = "Ski Line: " + row["notes"] + (f"; Ski Line url {url}" if "url" not in out else "")
    lo = exist.get("listed_on", "")
    out["listed_on"] = "Ski Line"
    out.pop("image_count", None)
    row = out
elif cands:
    row["same_as"] = ";".join(r["chalet_id"] for r in cands)
if not exist and imgs and not opts.get("dry"):
    n = subprocess.run(["python3", f"{ROOT}/tools/save_images.py", cid] + imgs[:12] + [f"--referer={url}"], capture_output=True, text=True).stdout.strip().split("\n")[-1]
    try:
        row["image_count"] = int(n); row["image_dir"] = f"chalets/images/{cid}/"
    except Exception:
        row["notes"] += "; pass2: photos"
if not opts.get("dry"):
    subprocess.run(["python3", f"{ROOT}/tools/append_row.py", OUT, json.dumps(row)], check=True)
tag = "DUP->" + cid if exist else ("NEW" + (" same_as?" + row.get("same_as", "") if cands else ""))
print(f"{tag} | {cid} | {name} | {op} | {vil} | {bd} | sl{smin}-{smax} br{bedrooms} | hot={hot} sauna={sauna} | 20Mar={price20} avail={avail} rng={row.get('price_range_low','')}-{row.get('price_range_high','')} | img={row.get('image_count','')} | {row.get('notes','')[:160]}")
