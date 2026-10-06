#!/usr/bin/env python3
"""Iglu Ski (igluski.com) -> JSON lines (SCHEMA columns + images) for one Iglu village slug.

    python3 tools/scrapers/igluski.py les-menuires                 # /ski-holidays/les-menuires-ski-chalets
    python3 tools/scrapers/igluski.py meribel-mottaret --kind apartments
    options: --limit N  --dry-run (listing cards only)  --no-detail (skip property pages: no description/bedrooms/images)
             --adults N (dated search, default 8)  --kind chalets|apartments|hotels

Village slugs: see the resort page /ski-resorts/<country>/<resort> (links /ski-holidays/<village>-ski-chalets).
Steps: undated listing (10/page, &page=N) = every property with sleeps, board, hot tub/sauna icons, operator code;
dated listing (&date=20032027&flex=2&ad=N) = 20/21 Mar departures with package £pp ("based on N sharing");
property page = description, room list (bedrooms), catering, photos. Prices are GBP per person, packages incl.
flights/transfers unless the card says otherwise. Not in the dated list => availability unknown (Iglu only lists
what its feeds return). Operator is a supplier code (ING = Inghams); others are not named on the site.
"""
import re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch, oneline, words, num, row, emit, log, base_args, setup, hot_tub_from_text, Blocked, STATS

BASE = "https://www.igluski.com"
SUPPLIERS = {"ING": "Inghams"}
BOARD = {"catered": "catered", "chalet board": "catered", "self catered": "self-catered", "self-catered": "self-catered",
         "half board": "half-board", "bed & breakfast": "breakfast-only", "bed and breakfast": "breakfast-only",
         "room only": "self-catered", "full board": "half-board", "all inclusive": "half-board"}


def cards(s):
    out = []
    for blk in s.split('data-holidayid="')[1:]:
        g = lambda a: (re.search(a + r'="([^"]*)"', 'data-holidayid="' + blk[:2500]) or [0, ""])[1]
        body = blk[:9000]
        board = oneline((re.search(r'search-result__board">(.*?)</div>', body, re.S) or [0, ""])[1])
        sleeps = (re.search(r'Sleeps</span>\s*<span class="search-result__distance-value">([^<]+)', body) or [0, ""])[1]
        slopes = (re.search(r'Slopes</span>\s*<span class="search-result__distance-value">([^<]+)', body) or [0, ""])[1]
        feats = [oneline(x) for x in re.findall(r'search-result__features-title">(.*?)</span>', body, re.S)]
        based = oneline((re.search(r'search-results__based-on">(.*?)</span>', body, re.S) or [0, ""])[1])
        frm = oneline((re.search(r'search-result__from">(.*?)</span>', body, re.S) or [0, ""])[1])
        out.append(dict(hid=g("data-holidayid"), id=g("data-id"), title=g("data-title"), text=g("data-text"),
                        price=num(g("data-price")), url=BASE + g("data-url").split("?")[0], dep=g("data-departuredate"),
                        supplier=g("data-supplier"), resort=g("data-resort"), photo=g("data-photo").split("?")[0],
                        board=board, sleeps=sleeps.strip(), slopes=slopes.strip(), feats=feats, based=based, frm=frm))
    return out


def listing(path, extra, limit=0):
    out, page = {}, 1
    while True:
        q = f"{BASE}/ski-holidays/{path}?&flex=2&nts=7&ch=0&perpage=10&page={page}&sort=0&state=4{extra}"
        st, s, _ = fetch(q)
        if st == 404:
            log(f"iglu: 404 {q}"); break
        new = 0
        for c in cards(s):
            if c["id"] and c["id"] not in out:
                out[c["id"]] = c; new += 1
        total = int((re.search(r"(\d+)\s*(?:results|properties)", s) or [0, 0])[1])
        if not new or len(out) >= total or (limit and len(out) >= limit) or page > 60:
            break
        page += 1
    return out


def detail(url):
    st, s, _ = fetch(url)
    if st != 200:
        return {}
    i = s.find("<h1")
    t = oneline(re.sub(r"(?s)<script.*?</script>", "", s[i:] if i > 0 else s))
    desc = (re.search(r"Slopes:\s*[^ ]+ ?\w*\s+(.*?)\s+(?:Chalet Highlights|Highlights|Room Options|Chalet Room Options|Chalet Catering)", t) or [0, ""])[1]
    rooms = re.findall(r"\bRoom (\d+):", t)
    cat = (re.search(r"Chalet Catering\s+(.*?)\s+It is essential", t) or [0, ""])[1]
    hl = (re.search(r"Highlights\s+(.*?)\s+(?:Chalet Room Options|Room Options|Chalet Catering)", t) or [0, ""])[1]
    imgs = []
    for u in re.findall(r"https://content\.igluski\.com/images/[^\"'?\s)]+", s):
        if u not in imgs:
            imgs.append(u)
    return dict(desc=desc, rooms=len(set(rooms)), catering=cat, highlights=hl, imgs=imgs, text=t[:6000])


def main():
    p = base_args(__doc__.split("\n")[0])
    p.add_argument("village")
    p.add_argument("--kind", default="chalets", choices=["chalets", "apartments", "hotels"])
    p.add_argument("--adults", type=int, default=8)
    p.add_argument("--no-detail", action="store_true")
    a = p.parse_args()
    setup(a)
    path = f"{a.village.strip('/')}-ski-{a.kind}"
    try:
        und = listing(path, "&ad=2", a.limit)
        log(f"iglu: {path}: {len(und)} properties (undated)")
        dat = listing(path, f"&ad={a.adults}&date=20032027")
        dat = {k: v for k, v in dat.items() if v["dep"] in ("2027-03-20", "2027-03-21")}
        log(f"iglu: {len(dat)} with a 20/21 Mar departure for {a.adults} adults")
    except Blocked as e:
        log(f"iglu: BLOCKED {e}"); return
    items = list(und.values()) + [v for k, v in dat.items() if k not in und]
    if a.limit:
        items = items[: a.limit]
    n = 0
    for c in items:
        d = {}
        if not (a.dry_run or a.no_detail):
            try:
                d = detail(c["url"])
            except Blocked as e:
                log(f"iglu: BLOCKED {e}"); break
        notes = []
        dd = dat.get(c["id"])
        if dd and dd["price"]:
            price, av = dd["price"], "yes"
            notes.append(f"Iglu {dd['dep'][8:]} Mar: £{dd['price']}pp {dd['based'].lower()}; {dd['frm']}")
            chg = "Sunday" if dd["dep"].endswith("21") else "Saturday"
        else:
            price, av, chg = "", "unknown", ""
            notes.append(f"no 20/21 Mar departure in Iglu dated search ({a.adults} adults)")
        if c["price"]:
            notes.append(f"undated card: £{c['price']}pp ({c['dep']}, {c['based'].lower()})")
        board = next((v for k, v in BOARD.items() if k in c["board"].lower()), "")
        feats = " ".join(c["feats"])
        listed_ht = bool(re.search(r"hot tub|jacuzzi", feats, re.I))
        txt = d.get("desc", "") + " " + d.get("highlights", "")
        ht = hot_tub_from_text(txt, listed_ht, a.kind == "chalets") or "none"
        sauna = "yes" if re.search(r"sauna", feats + " " + txt, re.I) else "no"
        sup = SUPPLIERS.get(c["supplier"], "")
        if c["supplier"] and not sup:
            notes.append(f"Iglu supplier code {c['supplier']}")
        m = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", c["sleeps"])
        smin, smax = (m.group(1), m.group(2)) if m else ("", num(c["sleeps"]) or "")
        dist = ""
        if "min" in c["slopes"]:
            notes.append(f"slopes {c['slopes']}")
        imgs = d.get("imgs") or ([c["photo"]] if c["photo"] else [])
        emit(row(chalet_name=c["title"], operator=sup, village=c["resort"], country=c["text"].split(",")[-1].strip(),
                 sleeps_min=smin, sleeps_max=smax, bedrooms=d.get("rooms") or "",
                 property_type={"chalets": "chalet", "apartments": "apartment", "hotels": "hotel"}[a.kind],
                 board=board, catering_detail=words(d.get("catering", ""), 30) if board == "catered" else ("self-catered" if board == "self-catered" else ""),
                 hot_tub=ht, sauna=sauna, distance_to_lift_m=dist,
                 ski_in_out="yes" if re.search(r"ski-in,? ?ski-out|ski in/ski out", txt, re.I) else "unknown",
                 changeover_day=chg, price_week_20_27_mar_2027=price, price_basis="per-person" if price else "",
                 price_currency="GBP" if price else "", price_type="exact-week" if price else ("season-from" if c["price"] else "quote-needed"),
                 price_range_low="", price_includes=("package via Iglu: " + dd["frm"]) if dd and dd.get("frm") else "",
                 available_20_27_mar=av, description=words(d.get("desc", ""), 40), url=c["url"], listed_on="Iglu Ski",
                 notes="; ".join(notes), images=imgs[:10], _source="igluski", _source_id=c["id"]))
        n += 1
    log(f"iglu: done, {n} rows, {STATS['requests']} requests")


if __name__ == "__main__":
    main()
