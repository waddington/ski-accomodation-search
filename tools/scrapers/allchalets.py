#!/usr/bin/env python3
"""allChalets.com -> JSON lines (chalets/SCHEMA.md columns + images) for one location.

    python3 tools/scrapers/allchalets.py les-menuires            # location slug
    python3 tools/scrapers/allchalets.py "Tignes Les Brévières"   # village name (slugified)
    python3 tools/scrapers/allchalets.py https://www.allchalets.com/search/location:les-coches
    options: --limit N  --dry-run (search pages only)  --contact (+1 request/listing: advertiser name)
             --no-cal (skip availability calendar)  --include-residences  --ids 62092,6771

Per listing: 1 detail page (static) + 1 calendar request (Dec 2026-Apr 2027, rails UJS JS) [+1 enquiry
page with --contact]. 2 s between requests. Search: /search/location:<slug>/page:N (20 per page, static).
"""
import html, re, sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (fetch, text, oneline, slug, words, num, CURRENCY, row, emit, log, base_args, setup,
                    hot_tub_from_text, Blocked, STATS)

BASE = "https://www.allchalets.com"
TARGET = dt.date(2027, 3, 20)
SEASON = (dt.date(2026, 10, 1), dt.date(2027, 6, 1))
SKIP_IMG = re.compile(r"floor ?plan|plan_|logo|map", re.I)


def search(loc, limit=0):
    if loc.startswith("http"):
        url = loc.split("?")[0].rstrip("/")
        url = re.sub(r"/page:\d+$", "", url)
        if "/search/" not in url:  # location page like /les-menuires
            url = BASE + "/search/location:" + url.rsplit("/", 1)[1]
    else:
        url = BASE + "/search/location:" + slug(loc)
    out, page = {}, 1
    total = None
    while True:
        st, s, _ = fetch(url + (f"/page:{page}" if page > 1 else ""))
        if st == 404 or not s:
            log(f"allchalets: no such location {url}")
            break
        if total is None:
            m = re.search(r"Has returned (\d+) holiday rentals", s)
            total = int(m.group(1)) if m else 0
            log(f"allchalets: {url} -> {total} listings")
        new = 0
        for blk in s.split('class="property-snippet')[1:]:
            m = re.search(r'href="(/holiday-rentals/(\d+)-([a-z]+)-in-([a-z0-9-]+?)-([a-z-]+?))"', blk)
            if not m or m.group(2) in out:
                continue
            title = re.search(r'<h3 class="panel-title">\s*<a[^>]*>(.*?)</a>', blk, re.S)
            hl = oneline(re.search(r'property-highlights">(.*?)</div>', blk, re.S).group(1)) if 'property-highlights' in blk else ""
            crumbs = re.findall(r'<a href="/[^"]*">([^<]+)</a>', blk.split('location-breadcrumbs', 1)[1][:600]) if 'location-breadcrumbs' in blk else []
            imgs = re.findall(r'(?:src|data-lazy)="(/system/property_images/[^"?]+)', blk)
            out[m.group(2)] = dict(id=m.group(2), path=m.group(1), ptype=m.group(3), headline=oneline(title.group(1)) if title else "",
                                   highlights=hl, crumbs=crumbs, images=[BASE + i.replace("/preview/", "/medium/") for i in imgs])
            new += 1
        if limit and len(out) >= limit:
            break
        if f'/page:{page + 1}"' not in s or new == 0:
            break
        page += 1
    return list(out.values())


def parse_rates(s):
    """Rows of the 'Prices' table -> list of dict(start, end, checkin, catering, pricing, weekly, night, wkend, cur, desc)."""
    body = s.split('data-properties-rates-table-target="ratesTable"', 1)
    if len(body) < 2:
        return []
    body = body[1].split("</tbody>", 1)[0]
    rates, cur = [], {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        if "rateDescriptionCell" in tr:
            if rates:
                rates[-1]["desc"] = oneline(tr)
            continue
        tds = re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S)
        cells = {}
        dates = [oneline(v) for a, v in tds if "allow-wrap" in a]
        if len(dates) == 2:
            cur["start"], cur["end"] = dates
        for a, v in tds:
            t = oneline(v)
            if "checkInCell" in a: cur["checkin"] = t
            elif "minimumStayCell" in a: cur["minstay"] = t
            elif "cateringCell" in a: cells["catering"] = t
            elif "pricingCell" in a: cells["pricing"] = t
            elif "weekdayRate" in a: cells["night"] = t
            elif "weekendRate" in a: cells["wkend"] = t
            elif 'class="text-right"' in a: cells["weekly"] = t
        try:
            st = dt.datetime.strptime(cur.get("start", ""), "%d %b %Y").date()
            en = dt.datetime.strptime(cur.get("end", ""), "%d %b %Y").date()
        except ValueError:
            continue
        r = dict(start=st, end=en, checkin=cur.get("checkin", ""), minstay=cur.get("minstay", ""), desc="", **cells)
        sym = re.search(r"[£€]|CHF", r.get("weekly", "") + r.get("night", "") + r.get("wkend", ""))
        r["cur"] = CURRENCY.get(sym.group(0)) if sym else ""
        rates.append(r)
    return rates


def calendar(path):
    """{date: classes} for Dec 2026-Apr 2027, plus {date: tooltip} for check-in days."""
    st, js, _ = fetch(f"{BASE}/calendar/{path.rsplit('/', 1)[1]}?from=2026-12-01&months=5",
                      headers={"X-Requested-With": "XMLHttpRequest", "Accept": "text/javascript, application/javascript"})
    js = js.replace('\\"', '"').replace("\\/", "/")
    days, tips = {}, {}
    for m in re.finditer(r'class="current [a-z]+">([A-Z][a-z]{2} \d{4})</th>(.*?)</table>', js, re.S):
        base = dt.datetime.strptime("1 " + m.group(1), "%d %b %Y").date()
        for cls, attrs, d in re.findall(r'<td class="day ([^"]*)"([^>]*)>\s*(?:<div>)?(\d+)', m.group(2)):
            if "otherMonth" in cls:
                continue
            day = base.replace(day=int(d))
            days[day] = cls
            t = re.search(r'title="([^"]*)"', attrs)
            if t:
                tips[day] = oneline(t.group(1).replace("&lt;", "<").replace("&gt;", ">"))
    return days, tips


def week_available(days, start):
    wk = [start + dt.timedelta(i) for i in range(7)]
    if any(d not in days for d in wk):
        return ""
    if not any("booked" in c for c in days.values()):
        return "unmaintained"
    c0 = days[wk[0]]
    if "booked" in c0 and "changeover-booked-available" not in c0:
        return "no"
    if any("booked" in days[d] for d in wk[1:]):
        return "no"
    return "yes"


def board_of(s):
    s = (s or "").lower()
    cat, self_ = "catered" in s.replace("self catered", "").replace("self-catered", ""), "self" in s
    hb = "half board" in s or "half-board" in s
    if cat and self_: return "catered-or-self"
    if cat: return "catered"
    if hb: return "half-board"
    if self_: return "self-catered"
    if "b&b" in s or "bed and breakfast" in s or "breakfast" in s: return "breakfast-only"
    return ""


# allChalets files everything under the resort; listings whose headline names a satellite village get that village
# (resorts/resorts_raw.csv spelling). Keyed by slug(resort crumb).
SUBVILLAGES = {
    "val-d-isere": [(r"La Daille", "La Daille"), (r"(?:Le )?Fornet", "Le Fornet")],
    "alpe-d-huez": [(r"Vaujany", "Vaujany"), (r"\bOz(?:-en-Oisans| en Oisans| 3300)?\b", "Oz-en-Oisans"),
                    (r"Auris", "Auris-en-Oisans"), (r"Villard[- ]Reculas", "Villard-Reculas"),
                    (r"Huez (?:village|1500)|village of Huez|Huez-en-Oisans", "Huez (village)")],
    "st-gervais": [(r"Bettex|Communailles", "St-Gervais Le Bettex"), (r"Nicolas|V[ée]roce", "St-Nicolas-de-Véroce")],
}
# resort crumb -> resorts_raw.csv village when no satellite is named
CRUMB_VILLAGE = {"st-gervais": "St-Gervais-les-Bains", "val-d-isere": "Val d'Isère", "alpe-d-huez": "Alpe d'Huez"}


def unescape_row(r):
    """HTML-unescape every text field (village crumbs came through as Val d&#39;Isere)."""
    for k, v in r.items():
        if isinstance(v, str) and "&" in v:
            r[k] = html.unescape(v)
    return r


def sub_village(village, h1, loc=""):
    """Satellite village named in the headline or in the listing's own location text
    ('Location Details: Located in ..., Closest ski lift: ...'), never from the search slug."""
    for rx, name in SUBVILLAGES.get(slug(village), []):
        if re.search(rx, h1 or "") or re.search(rx, loc or ""):
            return name
    return ""


def header(J, pid):
    """'<Type> <id> Catered, Self catering, Sleeps 4[-6], 2 bedrooms, 1 bathroom Prices:/Facilities:' ->
    (board words, sleeps, sleeps2, bedrooms, bathrooms). Parsed from the segment after the listing id only (an
    unanchored regex used to pick up 'Catered ...' menu text -> catered-or-self) and every part is optional
    (studios have no bedrooms)."""
    m = re.search(r"\b(?:Chalet|Apartment|Studio|Residence|Hotel|Villa|Farmhouse|Cottage|House|Room|Penthouse|Duplex)\s+"
                  + re.escape(pid) + r"\s+(.{0,200}?)\s*(?:Prices:|Facilities:|Suitable for:|Location type:|Quick Links|$)", J)
    seg = m.group(1) if m else ""
    if not seg:  # fallback: old pattern, but board words only right before "Sleeps"
        m = re.search(r"((?:Catered|Self catered|Self catering|Half board|B&B|Bed and breakfast)(?:,\s*(?:Catered|Self catering|Self catered|Half board|B&B))*,)?\s*Sleeps\s*\d+[^:]{0,60}", J)
        seg = m.group(0) if m else ""
    sl = re.search(r"Sleeps\s*(\d+)(?:\s*-\s*(\d+))?", seg)
    pre = seg[:sl.start()] if sl else ""
    g = lambda rx: (re.search(rx, seg) or [None, ""])[1] or ""
    return (pre.strip(" ,"), sl.group(1) if sl else "", (sl.group(2) or "") if sl else "",
            g(r"(\d+)\s*bedrooms?"), g(r"(\d+)\s*bathrooms?"))


def desc_capacity(desc):
    """Largest 'sleeps N' / 'N people|persons|guests|adults' stated in the description (None if none)."""
    caps = [int(x) for x in re.findall(r"\bsleeps\s+(\d{1,2})\b|\b(\d{1,2})\s+(?:people|persons|guests|adults)\b", desc, re.I)
            for x in x if x and 1 < int(x) < 60]
    return max(caps) if caps else None


def name_from(desc, headline, ptype, pid):
    for src in (desc[:250], headline):
        m = re.search(r"\b((?:Chalet|Apartment|Appartement|Appartment|Residence|Résidence|Ferme|Maison|Villa)\s+(?:(?:de|des|du|la|le|les|d'|l')\s*)?[A-Z][\w'’-]+(?:\s+(?:&|and)\s+[A-Z][\w'’-]+|\s+[A-Z][\w'’-]+){0,2})", src)
        if m and not re.search(r"\b(Is|In|The|With|Has|Of|For|Apartment|Apartments|Chalet|Chalets|Residence|Holiday|Holidays|Ski|Located|Situated|Details|Description|Information|Info|Features|Overview|Sleeps|Rental|Rentals|For)\b", m.group(1).split(None, 1)[1] if " " in m.group(1) else "x"):
            return m.group(1).strip(), True
    return f"{ptype.capitalize()} {pid}", False


def detail(it, want_cal=True, want_contact=False):
    url = BASE + it["path"]
    st, s, _ = fetch(url)
    if st == 404:
        return None
    notes = []
    head = s.split('id="description"', 1)[0]
    crumbs = re.findall(r'<a href="/([a-z0-9-]+)">([^<]+)</a>', s.split('class="breadcrumbs"', 1)[1][:800]) if 'class="breadcrumbs"' in s else []
    crumbs = [c for c in crumbs if c[0] not in ("",)]
    country = crumbs[0][1] if crumbs else ""
    village = crumbs[-1][1] if len(crumbs) > 1 else ""
    h1 = oneline((re.search(r'<h1 id="top">(.*?)</h1>', s, re.S) or [None, ""])[1])
    J = oneline(head)
    board_h, sleeps, sleeps2, beds, baths = header(J, it["id"])
    fac = (re.search(r"Facilities:\s*(.*?)\s*(?:Suitable for|Location type|Quick Links|$)", J) or [None, ""])[1]
    m = re.search(r"Prices:\s*From\s*([£€]|CHF)\s*([\d,.]+)\s*(?:\(([^)]*)\))?\s*per (week|night|person)", J)
    from_price = (CURRENCY[m.group(1)], num(m.group(2)), m.group(3) or "", m.group(4)) if m else None
    desc_html = (re.search(r'id="description-full">(.*?)</div>', s, re.S) or [None, ""])[1]
    desc = oneline(desc_html)
    # long facilities section
    fsec = s.split('id="facilities"', 1)[1] if 'id="facilities"' in s else s.split("<h2>Facilities</h2>", 1)[-1]
    fsec = oneline(fsec.split("Quick Links", 1)[0])[:3000]
    allfac = fac + " " + fsec
    lift = re.search(r"Nearest ski lift\s*(.*?)\s*at\s*([\d.]+)\s*km", oneline(s))
    rates = parse_rates(s)
    images = []
    for p in re.findall(r'(/system/property_images/data/[\d/]+/medium/[^"?]+)', s.split('id="gallery"', 1)[-1]):
        u = BASE + p
        if u not in images and not SKIP_IMG.search(p):
            images.append(u)
    name, named = name_from(desc, h1, it["ptype"], it["id"])
    ptype = {"chalet": "chalet", "apartment": "apartment", "residence": "apartment", "hotel": "hotel",
             "villa": "chalet", "farmhouse": "chalet", "cottage": "chalet"}.get(it["ptype"], it["ptype"])
    if re.search(r"chalet[- ]hotel", h1 + " " + desc[:300], re.I):
        ptype = "chalet-hotel"
    whole = ptype == "chalet"
    listed_ht = bool(re.search(r"Jacuzzi|Hot Tub", allfac, re.I))
    ht = hot_tub_from_text(desc, listed_ht, whole)
    if not ht:
        ht = "none"
        notes.append("hot tub not in facility list/description")
    elif listed_ht:
        notes.append("hot tub in facility list")
    sauna = "yes" if re.search(r"sauna", allfac + " " + desc, re.I) else "no"
    # facilities: drop distance/public-amenity lines ("outdoor/public swimming pool 2 km") before matching
    ftxt = re.sub(r"(?i)[^.;:\n]{0,40}\b(?:public|municipal|outdoor/public|nearby|nearest)\b[^.;\n]{0,60}|"
                  r"[^.;:,\n]{0,40}\bpool\b[^.;,\n]{0,15}?\d+(?:[.,]\d+)?\s*(?:km|m)\b", " ", allfac + " " + desc).lower()
    other = [f for f in ["steam room", "swimming pool", "indoor pool", "log fire", "open fire", "wood burner", "fireplace",
                         "boot warmer", "boot dryer", "games room", "cinema", "gym", "pool table", "table tennis"]
             if f in ftxt]
    # board
    cat_cells = " / ".join(sorted({r.get("catering", "") for r in rates if r.get("catering")}))
    board = board_of(board_h or "") or board_of(cat_cells)
    if board_of(board_h or "") and cat_cells and board_of(cat_cells) not in ("", board_of(board_h)):
        board = "catered-or-self" if {"catered", "self-catered"} <= {board_of(board_h), board_of(cat_cells)} else board
    if ptype == "chalet-hotel" and board in ("catered", ""):
        board = "chalet-hotel"
    if not board and from_price and from_price[2]:
        board = board_of(from_price[2])
    if not board:
        board = board_of(re.sub(r"(?i)catered ski|ski chalet", "", h1))
        if board:
            notes.append("board from listing headline")
    catering_detail = ""
    m = re.search(r"((?:fully )?catered (?:service )?includes?:?.{0,400})", desc, re.I)
    if m:
        catering_detail = words(m.group(1), 45)
    elif board == "self-catered":
        catering_detail = "self-catered"
    # changeover
    cis = {r["checkin"] for r in rates if r.get("checkin") and SEASON[0] <= r["start"] < SEASON[1]} or \
        {r["checkin"] for r in rates if r.get("checkin")}
    changeover = ""
    cis = {c.strip() for c in cis if c.strip()}
    if cis == {"Saturday"}: changeover = "Saturday"
    elif cis == {"Sunday"}: changeover = "Sunday"
    elif cis:  # several check-in days (or Any) -> flexible; schema allows only Saturday/Sunday/flexible/unknown
        changeover = "flexible"
        notes.append("check-in days: " + "/".join(sorted(cis)))
    # season rates
    def weekly_of(r):
        w = num(r.get("weekly", ""))
        if w is None and num(r.get("night", "")) is not None:
            n, e = num(r.get("night", "")), num(r.get("wkend", "")) or num(r.get("night", ""))
            w = round(n * 5 + e * 2)
        return w
    season = [r for r in rates if SEASON[0] <= r["start"] < SEASON[1] and weekly_of(r)]
    basis_set = {r.get("pricing", "") for r in season}
    basis = "per-person" if any("person" in b.lower() for b in basis_set) else ("whole-chalet" if season else "")
    cur = next((r["cur"] for r in season if r["cur"]), "") or (from_price[0] if from_price else "")
    vals = [weekly_of(r) for r in season if r["cur"] == cur and (("person" in r.get("pricing", "").lower()) == (basis == "per-person"))]
    if len(vals) >= 3:
        med = sorted(vals)[len(vals) // 2]
        odd = [v for v in vals if v > 4 * med or v < med / 4]
        if odd:
            notes.append(f"ignored outlier rate(s) {odd} in range")
            vals = [v for v in vals if v not in odd]
    lo, hi = (min(vals), max(vals)) if vals else ("", "")
    # target week
    start = TARGET + dt.timedelta(1) if changeover == "Sunday" else TARGET
    tw = [r for r in rates if r["start"] <= start < r["end"] and (r["end"] - r["start"]).days >= 7 or r["start"] == start]
    price20 = ""
    if tw:
        # prefer catered row if multiple
        tw.sort(key=lambda r: (0 if "catered" in r.get("catering", "").lower() and "self" not in r.get("catering", "").lower() else 1))
        r = tw[0]
        if r["start"] == start or (r["end"] - r["start"]).days > 7:
            price20 = weekly_of(r) if (r["end"] - r["start"]).days >= 7 else ""
            if price20 and (r["end"] - r["start"]).days > 7 and not num(r.get("weekly", "")):
                notes.append("20 Mar price computed from nightly rates")
            if len(tw) > 1:
                notes.append("20 Mar rates: " + "; ".join(f"{x.get('catering','')} {x.get('pricing','')} {x.get('weekly') or x.get('night')}" for x in tw))
    avail = ""
    if want_cal:
        try:
            days, tips = calendar(it["path"])
            a = week_available(days, start)
            if a == "unmaintained":
                avail = "unknown"
                notes.append("calendar shows no bookings all season (probably unmaintained)")
            else:
                avail = a or "unknown"
            tip = tips.get(start)
            if tip:
                notes.append(f"calendar {start:%d %b}: {tip}")
                if not price20:
                    m = re.search(r"([£€]|CHF)\s*([\d,.]+)\s*([a-z -]*?)\s*per week", tip)
                    if m and CURRENCY[m.group(1)] == (cur or CURRENCY[m.group(1)]):
                        price20 = num(m.group(2)); cur = cur or CURRENCY[m.group(1)]
                        notes.append("20 Mar price from calendar tooltip")
                        if not basis:
                            basis = "per-person" if "person" in tip.lower() else "whole-chalet"
        except Blocked:
            raise
        except Exception as e:  # calendar is best effort
            notes.append(f"calendar fetch failed: {e}")
    if not avail:
        avail = "unknown"
    if price20 and avail == "no":
        notes.append("rate listed for 20 Mar week but calendar shows booked")
    ptype_price = "exact-week" if price20 else ("season-range" if lo != "" and lo != hi else ("season-from" if lo != "" or from_price else "quote-needed"))
    if not lo and from_price and from_price[3] == "week":
        lo = from_price[1]; cur = cur or from_price[0]
        notes.append(f"'From' price only ({from_price[2] or 'basis not stated'})")
    if not rates:
        notes.append("no rate table on allChalets")
    contact = ""
    if want_contact:
        try:
            _, e, _ = fetch(url + "/enquiry")
            m = re.search(r"Name:\s*([^|<\n]+?)\s*(?:Spoken languages|$|\n|<)", text(e))
            contact = m.group(1).strip() if m else ""
            if contact:
                notes.append(f"advertiser contact: {contact}")
        except Blocked:
            raise
        except Exception:
            pass
    if not named:
        notes.append(f"unnamed listing; headline: {h1}")
    if it["ptype"] == "residence":
        notes.append("residence parent listing (units listed separately)")
    village = html.unescape(village); country = html.unescape(country); h1 = html.unescape(h1)
    locm = re.search(r"Location Details:(.{0,400}?)(?:Included in our service|Optional Services|Read More|$)", desc)
    sv = sub_village(village, h1, locm.group(1) if locm else "")
    crumb = village
    if sv:
        notes.append(f"allChalets files it under {village}; headline names {sv}")
        village = sv
    elif CRUMB_VILLAGE.get(slug(village)):
        village = CRUMB_VILLAGE[slug(village)]
    sl_max = sleeps2 or sleeps
    # garbled headers, e.g. 'Sleeps 7, 7 bedrooms, 14 bathrooms' for a 14-guest/7-bedroom chalet
    dc = desc_capacity(desc)
    bad = sl_max and ((beds and int(sl_max) < int(beds)) or (baths and int(baths) > int(sl_max)))
    if bad and dc and dc > int(sl_max):
        notes.append(f"header says sleeps {sl_max}, {beds or '?'} bedrooms, {baths or '?'} bathrooms (inconsistent); sleeps from description ({dc})")
        if baths and int(baths) == dc:
            baths = ""
        sl_max, sleeps = str(dc), ""
    elif bad:
        notes.append(f"header inconsistent: sleeps {sl_max}, {beds or '?'} bedrooms, {baths or '?'} bathrooms")
    elif not sl_max and dc:
        sl_max = str(dc); notes.append("sleeps from description")
    elif dc and dc > int(sl_max):
        notes.append(f"description mentions up to {dc} people")
    return unescape_row(row(
        chalet_name=name, operator="", village=village, country=country,
        sleeps_min=sleeps if sleeps2 else "", sleeps_max=sl_max, bedrooms=beds, bathrooms=baths or "",
        property_type=ptype, board=board, catering_detail=catering_detail, hot_tub=ht, sauna=sauna,
        other_facilities=", ".join(other), distance_to_lift_m=round(float(lift.group(2)) * 1000) if lift else "",
        ski_in_out="yes" if re.search(r"Ski-in / Ski-out", allfac) else "unknown", changeover_day=changeover,
        price_week_20_27_mar_2027=price20, price_basis=basis if (price20 or lo != "") else "",
        price_currency=cur if (price20 or lo != "") else "", price_type=ptype_price,
        price_range_low=lo, price_range_high=hi, available_20_27_mar=avail,
        description=words(desc, 40), url=url, listed_on="allChalets",
        notes="; ".join(notes), images=images[:10], _source="allchalets", _source_id=it["id"],
        _headline=h1, _named=named, _village_specific=bool(sv), _village_crumb=crumb))


def main():
    p = base_args(__doc__.split("\n")[0])
    p.add_argument("location")
    p.add_argument("--contact", action="store_true")
    p.add_argument("--no-cal", action="store_true")
    p.add_argument("--include-residences", action="store_true")
    p.add_argument("--ids", default="", help="comma-separated listing ids to keep")
    a = p.parse_args()
    setup(a)
    items = search(a.location, 0 if a.ids else a.limit)
    if not a.include_residences:
        items = [i for i in items if i["ptype"] != "residence"]
    if a.ids:
        keep = set(a.ids.split(","))
        items = [i for i in items if i["id"] in keep]
    if a.limit:
        items = items[: a.limit]
    log(f"allchalets: {len(items)} listings to process")
    n = 0
    for it in items:
        if a.dry_run:
            m = re.search(r"Sleeps\s*(\d+),\s*(\d+)\s*bedrooms?,\s*(\d+)\s*bathrooms?", it["highlights"])
            emit(unescape_row(row(chalet_name=it["headline"], village=it["crumbs"][-1] if it["crumbs"] else "",
                     sleeps_max=m.group(1) if m else "", bedrooms=m.group(2) if m else "", bathrooms=m.group(3) if m else "",
                     url=BASE + it["path"], listed_on="allChalets", images=it["images"][:5], _source="allchalets",
                     _source_id=it["id"], notes="dry-run: listing card only")))
            continue
        try:
            r = detail(it, not a.no_cal, a.contact)
        except Blocked as e:
            log(f"allchalets: BLOCKED {e} - stopping")
            break
        if r:
            emit(r); n += 1
    log(f"allchalets: done, {n} rows, {STATS['requests']} requests")


if __name__ == "__main__":
    main()
