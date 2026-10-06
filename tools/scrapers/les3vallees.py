#!/usr/bin/env python3
"""Les 3 Vallées Réservation (reservation.les3vallees.com, Orchestra platform) -> JSON lines (SCHEMA + images).

    python3 tools/scrapers/les3vallees.py les_menuires --min-pax 8
    python3 tools/scrapers/les3vallees.py Val_Thorens --type chalet
    python3 tools/scrapers/les3vallees.py --site combloux [--capacity-scan]   (reservation.combloux.com, no station)
    stations: Courchevel, LA_TANIA, meribel, Brides-les-Bains, Saint-Martin-de-Bell, les_menuires, Val_Thorens, Orelle
    options: --limit N  --dry-run (SERP only, no product pages)  --min-pax N (server filter s_c.PAX=N)
             --type chalet|apartment|all  --adults N (dated search, default = min-pax or 2)  --no-detail
             --village SUBSTR (keep units whose subtitle/'Village:' contains SUBSTR, e.g. Reberty, Bruy)

Steps: undated SERP /en/serp?s_c.ACCOMMODATION=..&s_c.Station=..(&s_c.PAX=N)&page=N (20/page, static)
= every unit with a "from" price; dated SERP (&s_dpda=2027-03-20&s_minMan=7&adultsNumber=N) = units bookable
for the 20-27 Mar week with the stay price; product page (static) = capacity, village, reference, characteristics,
description. Agencies are not named (the property reference prefix and image host hint at the agency).
"""
import html, json, math, re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch, oneline, words, num, row, emit, log, base_args, setup, hot_tub_from_text, Blocked, STATS

BASE = "https://reservation.les3vallees.com"
TYPES = {"all": "apartment,chalet", "chalet": "chalet", "apartment": "apartment"}
# Other Orchestra tourist-office sites. Combloux: SERP at /serp (no /en, no Station), lang param, product pages
# /product?s_pid=N; result pages SHUFFLE between requests -> every page is fetched and passes repeat until all
# 'total' units are seen (passes); product pages have no capacity -> --capacity-scan (PAX filter passes).
SITES = {
    "les3vallees": dict(base=BASE, serp="/en/serp", extra=[], types=TYPES, ski_area="Les 3 Vallées",
                        listed_on="Les 3 Vallées Réservation", source="les3vallees", passes=1),
    "combloux": dict(base="https://reservation.combloux.com", serp="/serp", extra=[("lang", "en_US")],
                     types={"all": "apartment,chalet,appartement_chalet,chalet_mitoyen", "chalet": "chalet,chalet_mitoyen",
                            "apartment": "apartment,appartement_chalet"}, type_param=True,
                     village="Combloux", ski_area="Évasion Mont-Blanc",
                     listed_on="Combloux Réservation (official, Orchestra)", source="orchestra-combloux", passes=6,
                     sorts=["base_price", "base_price_desc", "c.LIFTS_CBX"]),
}
CFG = SITES["les3vallees"]
VILLAGE = {"les_menuires": "Les Menuires", "Val_Thorens": "Val Thorens", "meribel": "Méribel", "Courchevel": "Courchevel",
           "LA_TANIA": "La Tania", "Saint-Martin-de-Bell": "St-Martin-de-Belleville", "Brides-les-Bains": "Brides-les-Bains",
           "Orelle": "Orelle"}


def serp(params, limit=0):
    """All units of a SERP. Fetches every page 1..ceil(total/20); with CFG passes > 1 repeats the whole run until
    'total' distinct units are seen (pages shuffle between requests on some sites)."""
    out, total = {}, 0
    for npass in range(CFG.get("passes", 1)):
        page, before = 1, len(out)
        while True:
            srt = CFG.get("sorts")
            got, total, arts = serp_page(params + ([("s_st", srt[npass % len(srt)])] if srt else []), page, out)
            if not arts or len(out) >= total or (limit and len(out) >= limit) or page > 80:
                break
            if CFG.get("passes", 1) == 1 and not got:
                break
            if page >= math.ceil(total / 20):
                break
            page += 1
        if len(out) >= total or (limit and len(out) >= limit):
            break
        if npass and len(out) == before:  # stable: 'total' counts offers, a product can appear twice
            log(f"orchestra: stable at {len(out)} distinct units (site total {total} counts duplicate offers)")
            break
        log(f"orchestra: pass {npass + 1}: {len(out)}/{total} units (+{len(out) - before}); pages may shuffle, re-querying")
    return list(out.values()), total


def serp_page(params, page, out):
    p = CFG["extra"] + params + ([("page", page)] if page > 1 else [])
    st, s, _ = fetch(CFG["base"] + CFG["serp"] + "?" + urllib.parse.urlencode(p, safe=",/"))
    total = int((re.search(r'nb_result">(\d+)', s) or [0, 0])[1])
    arts = re.findall(r"<article(.*?)</article>", s, re.S)
    new = 0
    for a in arts:
        m = re.search(r"data-product='(\{.*?\})'", a, re.S)
        try:
            prod = json.loads(m.group(1).replace("\n", "")) if m else {}
        except ValueError:
            prod = {}
        pid = prod.get("id") or (re.search(r"/product-(\d+)", a) or [None, ""])[1]
        if not pid or pid in out:
            continue
        price = re.search(r'<span class="price">([\d,. ]+)<', a)
        imgs = []
        for u in re.findall(r'data-src="https://ip1\.orchestra-platform\.com/[^/]+/(https?://[^"]+)"', a):
            if u not in imgs:
                imgs.append(u)
        out[pid] = dict(pid=pid, title=html.unescape(prod.get("title") or "") or oneline((re.search(r'result-rich-title">(.*?)</h3>', a, re.S) or [0, ""])[1]),
                        acc=prod.get("accommodation", ""), loc=html.unescape(prod.get("stationLocation", "")),
                        url=CFG["base"] + html.unescape(prod.get("url") or ""), desc=oneline((re.search(r'result-rich-description">(.*?)</div>', a, re.S) or [0, ""])[1]),
                        price=num(price.group(1)) if price else None, imgs=imgs or ([prod["img"]] if prod.get("img") else []))
        new += 1
    return new, total, arts


def product(url):
    st, s, _ = fetch(url)
    if st != 200:
        return {}
    i = s.find("<h1")
    t = oneline(s[i:] if i > 0 else s)
    g = lambda rx: (re.search(rx, t) or [None, ""])[1]
    desc = (g(r"Description\s+(?:Your accommodation\s+)?(.*?)\s+Characteristic\b") or g(r"Description\s+(.*?)\s+Information\b")
            or g(r"Description\s+(?:Included / Not Included\s+Description\s+)?(.*?)\s+(?:Included / Not Included|Book from|Select & book)\b"))
    chars = g(r"Characteristic\s+(.*?)\s+Information\b")
    return dict(text=t, desc=desc, chars=chars, cap=num(g(r"Capacity:\s*(\d+)")), resort=g(r"Resort:\s*(.+?)\s+-\s+Village:"),
                village=g(r"Village:\s*(.+?)\s+-\s+Property reference"), ref=g(r"Property reference:\s*(\S+)"),
                typ=g(r"Type of rental:\s*(\w+)"), district=g(r"District\s+(.+?)\s+Book\b"),
                coords=g(r"Coordinates\s+([\d.]+,\s*[\d.]+)"))


def main():
    p = base_args(__doc__.split("\n")[0])
    p.add_argument("station", nargs="?", default="")
    p.add_argument("--site", default="les3vallees", choices=list(SITES), help="Orchestra site (default les3vallees)")
    p.add_argument("--capacity-scan", action="store_true",
                   help="capacity from the PAX filter (max N for which a unit is listed; extra SERP passes) - for sites whose product pages lack it")
    p.add_argument("--min-pax", type=int, default=0)
    p.add_argument("--adults", type=int, default=0)
    p.add_argument("--type", default="all", choices=list(TYPES))
    p.add_argument("--no-detail", action="store_true")
    p.add_argument("--village", default="")
    a = p.parse_args()
    setup(a)
    global CFG
    CFG = SITES[a.site]
    if a.site == "les3vallees" and not a.station:
        p.error("station required for les3vallees")
    types = CFG["types"]
    base = [("s_c.ACCOMMODATION", types[a.type])] + ([("type", types[a.type])] if CFG.get("type_param") else []) \
        + ([("s_c.Station", a.station)] if a.station else [])
    if a.min_pax:
        base.append(("s_c.PAX", a.min_pax))
    adults = a.adults or a.min_pax or 2
    try:
        units, total = serp(base, a.limit if not a.village else 0)
        log(f"les3vallees: {a.station} {a.type} pax>={a.min_pax or 'any'}: {len(units)}/{total} units (undated)")
        dated, dtotal = serp(base + [("s_dpda", "2027-03-20"), ("s_minMan", 7), ("adultsNumber", adults), ("childrenNumber", 0)])
        log(f"les3vallees: {len(dated)}/{dtotal} bookable 20-27 Mar for {adults} adults")
    except Blocked as e:
        log(f"les3vallees: BLOCKED {e}"); return
    dmap = {d["pid"]: d for d in dated}
    capmap = {}
    if a.capacity_scan and not a.dry_run:
        try:
            for pax in range(max(2, a.min_pax), 31):
                got, tot = serp([x for x in base if x[0] != "s_c.PAX"] + [("s_c.PAX", pax)])
                for x in got:
                    capmap[x["pid"]] = pax
                log(f"orchestra: capacity scan PAX={pax}: {len(got)}/{tot}")
                if not tot:
                    break
        except Blocked as e:
            log(f"orchestra: BLOCKED during capacity scan {e}")
    known = {u["pid"] for u in units}
    units += [d for d in dated if d["pid"] not in known]
    n = 0
    for u in units:
        if a.limit and n >= a.limit:
            break
        if a.village and a.village.lower() not in u["loc"].lower() and not a.no_detail and a.dry_run:
            continue
        d = {}
        if not (a.dry_run or a.no_detail):
            try:
                d = product(u["url"])
            except Blocked as e:
                log(f"les3vallees: BLOCKED {e}"); break
        if a.village and a.village.lower() not in (u["loc"] + " " + d.get("village", "") + " " + d.get("district", "")).lower():
            continue
        notes = []
        dd = dmap.get(u["pid"])
        if dd and dd.get("price"):
            price, av = dd["price"], "yes"
            notes.append(f"20-27 Mar bookable on {CFG['listed_on'].split(' (')[0]} for {adults} adults: EUR {dd['price']}")
        else:
            price, av = "", "no"
            notes.append(f"not in 20-27 Mar dated search ({adults} adults)")
        if u.get("price"):
            notes.append(f"undated 'from' price EUR {u['price']} / stay")
        acc = (d.get("typ") or u["acc"]).lower()
        ptype = "apartment" if re.search(r"apart|appart|studio", acc) else ("chalet" if "chalet" in acc else "apartment")
        full = d.get("text", "") or u["desc"]
        jtxt = " ".join(re.findall(r"[^.]{0,120}(?:jac+u+z+i|hot tub|spa bath|whirlpool|nordic bath|bain nordique)[^.]{0,120}", full, re.I))
        ht = hot_tub_from_text(jtxt, False, ptype == "chalet") if jtxt else ("none" if d else "unknown")
        if jtxt:
            notes.append("spa text: " + words(jtxt, 25))
        sauna = "yes" if re.search(r"sauna", full, re.I) else "unknown"
        if re.search(r"(swimming pool|indoor pool|piscine)", full, re.I):
            notes.append("pool mentioned")
        capt = re.search(r"(\d+)\s*(?:persons?|pers\b|people|personnes)|\b\d+/(\d+)\s*p\b|\b(\d+)\s*p\b", u["title"], re.I)
        cap = d.get("cap") or (num(next(g for g in capt.groups() if g)) if capt else None)
        if u["pid"] in capmap:
            if not cap or capmap[u["pid"]] > cap:
                cap = capmap[u["pid"]]
            notes.append(f"capacity {capmap[u['pid']]} from the site's guest filter (listed for PAX={capmap[u['pid']]}, not {capmap[u['pid']] + 1})")
        rooms = re.search(r"(\d+)\s*rooms", u["title"])
        if rooms:
            notes.append(f"{rooms.group(1)} rooms (French 'pièces', not bedrooms)")
        beds = len(set(re.findall(r"Bedroom\s*(\d+)", full))) or ""
        loc = u["loc"]
        if d.get("village"):
            notes.append(f"village: {d['village'].title()}" + (f", district {d['district']}" if d.get("district") else ""))
        if d.get("ref"):
            notes.append(f"ref {d['ref']}")
        if d.get("coords"):
            notes.append(f"GPS {d['coords']}")
        village = CFG.get("village") or VILLAGE.get(a.station, a.station)
        if re.search(r"reberty", loc + d.get("district", ""), re.I) and village == "Les Menuires":
            village = "Les Menuires: Reberty 2000"
        elif re.search(r"bruy", loc + d.get("district", ""), re.I) and village == "Les Menuires":
            village = "Les Menuires: Les Bruyères"
        elif re.search(r"Saint-Martin|St Martin", d.get("resort", ""), re.I):
            village = "St-Martin-de-Belleville"
        emit(row(chalet_name=u["title"], operator="", village=village, ski_area=CFG["ski_area"], country="France",
                 sleeps_max=cap or "", bedrooms=beds, property_type=ptype, board="self-catered", catering_detail="self-catered",
                 hot_tub=ht, sauna=sauna, other_facilities=", ".join(x for x in ["fireplace" if re.search(r"fireplace|chimney", full, re.I) else ""] if x),
                 changeover_day="Saturday" if av == "yes" else "", price_week_20_27_mar_2027=price,
                 price_basis="whole-chalet" if price else "", price_currency="EUR" if price else "",
                 price_type="exact-week" if price else "quote-needed", available_20_27_mar=av,
                 description=words(d.get("desc") or u["desc"], 40), url=u["url"], listed_on=CFG["listed_on"],
                 notes="; ".join(notes), images=u["imgs"][:10], _source=CFG["source"], _source_id=u["pid"], _subtitle=loc))
        n += 1
    log(f"les3vallees: done, {n} rows, {STATS['requests']} requests")


if __name__ == "__main__":
    main()
