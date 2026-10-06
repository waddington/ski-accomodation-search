#!/usr/bin/env python3
"""Sno (sno.co.uk) chalets -> JSON lines (SCHEMA columns + images) for one Sno resort/area slug.

    python3 tools/scrapers/sno.py tignes-chalets
    python3 tools/scrapers/sno.py les-menuires-chalets --limit 5
    options: --limit N  --dry-run (list pages only)  --no-price (skip the 20 Mar POST: 1 request/chalet instead of 3)
             --airport LGW (first departure airport to try)  --village-default "Les Menuires"

Packages the site-sno agent's scripts (tmp/site-sno: snolist.py, snodetail.py, mk.py):
  list   GET /ski-chalets/<slug>/ -> hidden input hdssettings -> GET ?r=..&n=30&pg=N (server-rendered, 30/page)
  detail GET /ski-holidays/<name>_<code>/ (board line, distances, summary, features, meals, rooms, images v0 = full size)
  price  POST /Accom/Search (act=50, duration=7, sharing=min(sleeps,10), airport, departureDate=2027-03-20|21,
         __RequestVerificationToken + cookies) -> 302 to ?holidayid=... page whose calendar is priced for that
         sharing/airport -> 20 Mar price (GBP pp) + season range. Retries another airport / sharing Sno offers.
Area pages (e.g. espace-killy-chalets) do NOT include everything on resort pages: run both and let ingest dedupe.
Operator is not named on Sno (operator blank; notes give image code). /Api/ is robots-disallowed and not used.
"""
import re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch, text, oneline, words, num, row, emit, log, base_args, setup, hot_tub_from_text, Blocked, STATS

BASE = "https://www.sno.co.uk"
VIL = ['Val Claret', 'Le Lac', 'Lavachet', 'Tignes 1800', 'Les Boisses', 'Brévières', 'Brevieres', 'La Daille', 'Le Fornet',
       'Le Laisinant', 'Le Crêt', 'La Legettaz', 'Les Richardes', 'Manchet', 'Le Châtelard', 'La Thovex', 'Solaise',
       'Plagne Centre', 'Plagne Villages', 'Plagne Soleil', 'Aime 2000', 'Plagne Bellecote', 'Belle Plagne', 'Plagne 1800',
       'Plagne Montalbert', 'Montalbert', 'Champagny', 'Les Coches', 'Montchavin', 'Arc 1600', 'Arc 1800', 'Arc 1950',
       'Arc 2000', 'Peisey', 'Vallandry', 'Villaroger', 'Courchevel 1850', 'Courchevel 1650', 'Courchevel 1550', 'Le Praz',
       'Moriond', 'Méribel Village', 'Mottaret', 'La Tania', 'Les Menuires', 'Val Thorens', 'Saint Martin', 'St Martin',
       'Reberty', 'Croisette', 'Vaujany', 'Oz-en-Oisans', 'Auris', 'Villard-Reculas', 'Huez', 'Venosc', 'Morzine', 'Les Gets',
       'Avoriaz', 'Châtel', 'Chatel', 'Montriond', 'Ardent', 'Essert-Romand', 'St Jean d\'Aulps']
AIRPORTS = {'LGW': 'Gatwick', 'LHR': 'Heathrow', 'STN': 'Stansted', 'MAN': 'Manchester', 'BHX': 'Birmingham',
            'FOLK': 'Eurotunnel self-drive', 'LTN': 'Luton', 'BRS': 'Bristol', 'EDI': 'Edinburgh', 'AO': 'no flights'}


def listing(slug, limit=0):
    base = f"{BASE}/ski-chalets/{slug.strip('/')}/"
    st, h, _ = fetch(base)
    m = re.search(r'id="hdssettings" type="hidden" value="([^"]*)"', h)
    if not m:
        log(f"sno: no hdssettings on {base}")
        return []
    n = m.group(1).split("|")
    total = int((re.search(r"There are (\d+) holidays", h) or [0, 0])[1])
    out, pg = {}, 1
    while True:
        q = dict(r=n[10], t=n[11], d=n[12], s=n[0], c=n[1], i=n[2], fl=n[9], g=n[3], f=n[4], p=n[5], b=n[6], rt=n[7],
                 dr=n[8], n=30, pg=pg, o=0)
        st, h2, _ = fetch(base + "?" + urllib.parse.urlencode(q))
        got = 0
        for it in h2.split('<div class="hol-item-wrapper">')[1:]:
            u = re.search(r'href="(/ski-holidays/[^"?]+)', it)
            if not u or u.group(1) in out:
                continue
            nm = re.search(r"<h3><a[^>]*>([^<]+)", it)
            m1 = oneline((re.search(r'class="m1">(.*?)</div>', it, re.S) or [0, ""])[1])
            out[u.group(1)] = dict(path=u.group(1), name=oneline(nm.group(1)) if nm else "", m1=m1,
                                   feats=re.findall(r"</span><span>([^<]+)</span>", it))
            got += 1
        if not got or len(out) >= total or (limit and len(out) >= limit):
            break
        pg += 1
    log(f"sno: {slug}: {len(out)}/{total} listings")
    return list(out.values())


def cal(h):
    rows = {}
    i = max(h.find("AVAILABILITY &amp; PRICE"), h.find("AVAILABILITY & PRICE"))
    for s in h[i:].split('<td class="c0">')[1:]:
        d = re.search(r'hidden-xxs">\w+ (\d\d \w+ \d{4})', s)
        if not d:
            continue
        d = d.group(1)
        c1 = re.search(r'class="c1">(.*?)</td>', s, re.S)
        df, do = re.findall(r'data-df="([A-Z]+)"', s), re.findall(r'data-do="(\d+)"', s)
        if df or do:
            rows[d] = {"avail": "other", "airports": df, "sharing": do}
        elif c1:
            v = oneline(c1.group(1))
            m = re.search(r"£([\d,]+)", v)
            rows[d] = {"price": num(m.group(1))} if m else {"status": v}
    return rows


def post(h, url, code, sharing, airport, date):
    tok = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]*)"', h)
    bb = re.search(r'id="sv-boardbasis" value="([^"]*)"', h)
    pt = re.search(r'id="sv-propertytype" value="([^"]*)"', h)
    if not (tok and bb and pt):
        return None
    data = {"__RequestVerificationToken": tok.group(1), "act": 50, "duration": 7, "sharing": sharing, "airport": airport,
            "boardbasis": bb.group(1), "departureDate": date, "accomcode": code, "propertytype": pt.group(1)}
    st, h2, final = fetch(BASE + "/Accom/Search", data=data, headers={"Referer": url})
    if "holidayid=" not in final:
        return None
    sh = re.search(r'id="sv-sharing" value="([^"]*)"', h2)
    ap = re.search(r'id="sv-airport" value="([^"]*)"', h2)
    t = text(h2)
    inc = (re.search(r"WHAT'S INCLUDED\s*(.{0,400}?)SHOW MORE", t, re.S) or [0, ""])[1]
    return dict(url=final, sharing=sh.group(1) if sh else str(sharing), airport=ap.group(1) if ap else airport,
                cal=cal(h2), included=oneline(inc))


def detail(it, want_price=True, airport0="LGW", village_default=""):
    url = BASE + it["path"]
    code = re.search(r"_(\d+)/?$", it["path"]).group(1)
    st, h, url = fetch(url)
    if st != 200:
        return None
    t = text(h)
    title = (re.search(r"<title>([^<]*)", h) or [0, ""])[1].strip()
    name = title.split(",")[0].strip() or it["name"]
    bl = (re.search(r"\n([^\n]*\(sleeps[^\n]*\))", t) or [0, ""])[1]
    m = re.search(r"sleeps (\d+)(?:-(\d+))?", bl)
    smin, smax = (m.group(1), m.group(2)) if m and m.group(2) else ("", m.group(1) if m else "")
    b = bl.lower()
    board = ("self-catered" if "room only" in b else "catered" if b.startswith("catered") else "chalet-hotel" if "chalet hotel" in b
             else "self-catered" if "self" in b else "half-board" if "half" in b else "breakfast-only" if "b&b" in b or "bed & breakfast" in b else "")
    dists = " ; ".join(re.findall(r"\n((?:Town centre|Ski school|Ski lift|Piste|Bus stop|Lift|Shops)[^\n]*•[^\n]*)", t))
    sec = lambda a, z, n=1500: (lambda i: t[i:(t.find(z, i + len(a)) if t.find(z, i + len(a)) > 0 else i + n)][:n] if i >= 0 else "")(t.find(a))
    summary = re.sub(r"\s+", " ", sec(" Summary\n", "WHY YOU WILL LOVE")).replace("Summary", "", 1).strip()
    feats_s = sec("FEATURES & FACILITIES", "\nImportant Info", 1200)
    fe = []
    for x in [x.strip() for x in feats_s.split("\n")[1:] if x.strip()]:
        if x == "Chalet Service" or x.startswith(("MEALS AT", "BEDROOMS")):
            break
        fe.append(x)
    meals = [x.strip() for x in sec("\nMEALS AT", "\nBEDROOMS", 900).split("\n")[2:] if x.strip() and x.strip() != "Chalet Board"]
    bed = sec("\nBEDROOMS", "AVAILABILITY & PRICE", 4000)
    rooms = re.findall(r"\n([^\n|]{0,60}\(sleeps [\d-]+\))", bed)
    communal = re.sub(r"\s+", " ", sec("Communal Facilities", "zzzz", 1200)) if "Communal Facilities" in bed else ""
    prop = t[:t.find("AVAILABILITY & PRICE")] if "AVAILABILITY & PRICE" in t else t
    imgs = []
    for u in re.findall(r"https://static1\.sno\.co\.uk/images/accom/v\d/[a-z0-9]+/[0-9a-f-]+\.(?:jpg|jpeg|png|webp)", h):
        u = re.sub(r"/v\d/", "/v0/", u)
        if u not in imgs:
            imgs.append(u)
    opcode = sorted(set(re.findall(r"images/accom/v\d/([a-z0-9]+)/", h)))
    notes = []
    dc = cal(h)
    date = "2027-03-21" if ("21 Mar 2027" in dc and "20 Mar 2027" not in dc) else "2027-03-20"
    dkey = "21 Mar 2027" if date.endswith("21") else "20 Mar 2027"
    best, tries = None, []
    if want_price:
        sharing = min(int(smax or 8), 10)
        defap = (re.search(r'id="sv-airport" value="([^"]*)"', h) or [0, airport0])[1]
        r = post(h, url, code, sharing, airport0, date)
        if not r and defap != airport0:
            r = post(h, url, code, sharing, defap, date)
        tries.append(r)
        if r:
            v = r["cal"].get(dkey) or {}
            if v.get("avail") == "other":
                if v["airports"]:
                    tries.append(post(h, url, code, sharing, v["airports"][0], date))
                elif v["sharing"]:
                    tries.append(post(h, url, code, max(int(x) for x in v["sharing"]), r["airport"] or airport0, date))
        tr = [x for x in tries if x]
        best = next((x for x in tr if "price" in (x["cal"].get(dkey) or {})), tr[-1] if tr else None)
    v = (best["cal"].get(dkey) or {}) if best else {}
    price20 = v.get("price", "")
    prices = [x["price"] for x in (best["cal"].values() if best else []) if "price" in x]
    if best:
        apn = AIRPORTS.get(best["airport"], best["airport"])
        if price20:
            notes.append(f"Sno {dkey[:6]}: £{price20}pp with {best['sharing']} sharing from {apn}")
        elif v.get("status"):
            notes.append(f"Sno {dkey[:6]}: {v['status']}")
        elif v:
            notes.append(f"Sno {dkey[:6]}: listed but not priced for {best['sharing']} sharing/{apn} (options: airports {v.get('airports')}, sharing {v.get('sharing')})")
        else:
            notes.append("Sno: no 20/21 Mar 2027 departure listed")
        if prices:
            notes.append(f"range = Sno dates priced for {best['sharing']} sharing from {apn}")
        if best["sharing"] == "2" and int(smax or 0) > 4:
            notes.append("Sno only priced 2 sharing (per-bed style price)")
    elif want_price:
        notes.append("Sno price POST failed; pass2: exact-week price")
    vil = [x for x in VIL if x.lower() in prop.lower()]
    village = village_default
    if vil:
        notes.append("villages mentioned: " + ", ".join(vil[:4]))
    notes.append("operator not named on Sno (image code " + ",".join(opcode) + ")")
    htxt = summary + " " + " ".join(fe) + " " + communal
    ht = hot_tub_from_text(htxt, any(re.search(r"hot tub|jacuzzi", x, re.I) for x in fe), "hotel" not in name.lower())
    sauna = "yes" if re.search(r"sauna", htxt, re.I) else "unknown"
    fj = " | ".join(fe)
    nb, nba = re.search(r"(\d+) Bedrooms", fj), re.search(r"(\d+) Bathrooms", fj)
    dl = re.search(r"Ski lift • ([\d.]+)(k?m)", dists)
    incl = [x.strip() for x in (best or {}).get("included", "").split("  ") if x.strip()]
    status = (v.get("status") or "").lower()
    return row(chalet_name=name, operator="", village=village, country="", sleeps_min=smin, sleeps_max=smax,
               bedrooms=len(rooms) or (int(nb.group(1)) if nb else ""), bathrooms=int(nba.group(1)) if nba else "",
               property_type="chalet-hotel" if "hotel" in name.lower() or board == "chalet-hotel" else "chalet", board=board,
               catering_detail="; ".join(meals)[:300], hot_tub=ht or "none", sauna=sauna, other_facilities=", ".join(fe)[:200],
               distance_to_lift_m=int(float(dl.group(1)) * (1000 if dl.group(2) == "km" else 1)) if dl else "",
               ski_in_out="yes" if ("Piste • Ski In/Out" in dists or "Ski In/Out" in fe) else "unknown",
               changeover_day=("Saturday" if dkey.startswith("20") else "Sunday") if (best or dc) else "",
               price_week_20_27_mar_2027=price20, price_basis="per-person" if (price20 or prices) else "",
               price_currency="GBP" if (price20 or prices) else "",
               price_type="exact-week" if price20 else ("season-range" if prices else "quote-needed"),
               price_range_low=min(prices) if prices else "", price_range_high=max(prices) if prices else "",
               price_includes=("package via Sno: " + (best or {}).get("included", ""))[:200] if (best or {}).get("included") else "",
               available_20_27_mar="yes" if price20 else ("no" if status.startswith("sold") else "unknown"),
               description=words(summary, 40), url=url.split("?")[0], listed_on="Sno", notes="; ".join(notes),
               images=imgs[:10], _source="sno", _source_id=code, _boardline=bl, _sharing=(best or {}).get("sharing", ""))


def main():
    p = base_args(__doc__.split("\n")[0])
    p.add_argument("slug", help="Sno list slug, e.g. tignes-chalets, les-menuires-chalets, espace-killy-chalets")
    p.add_argument("--no-price", action="store_true")
    p.add_argument("--airport", default="LGW")
    p.add_argument("--village-default", default="")
    a = p.parse_args()
    setup(a)
    slug = a.slug if a.slug.endswith("-chalets") else a.slug + "-chalets"
    try:
        items = listing(slug, a.limit)
    except Blocked as e:
        log(f"sno: BLOCKED {e}"); return
    if a.limit:
        items = items[: a.limit]
    n = 0
    for it in items:
        if a.dry_run:
            m = re.search(r"sleeps (\d+)(?:-(\d+))?", it["m1"], re.I)
            emit(row(chalet_name=it["name"], sleeps_max=(m.group(2) or m.group(1)) if m else "", url=BASE + it["path"],
                     listed_on="Sno", notes="dry-run: " + it["m1"], _source="sno")); n += 1
            continue
        try:
            r = detail(it, not a.no_price, a.airport, a.village_default)
        except Blocked as e:
            log(f"sno: BLOCKED {e} - stopping"); break
        if r:
            emit(r); n += 1
    log(f"sno: done, {n} rows, {STATS['requests']} requests")


if __name__ == "__main__":
    main()
