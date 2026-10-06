#!/usr/bin/env python3
"""Ski Line (skiline.co.uk) -> JSON lines (chalets/SCHEMA.md columns + images) for one API resort.

    python3 tools/scrapers/skiline.py "Les Menuires"          # API resort name (see --list-resorts)
    python3 tools/scrapers/skiline.py --list-resorts
    options: --limit N  --dry-run (search API only, no per-property requests)
             --chalets-only (boards Catered/Self Catered Chalet, Chalet Hotel, Chalet Club Board)
             --no-detail (skip the HTML page: no description/bedrooms/images)
             --sitemap <resort-url-slug> (also emit sitemap-only chalet pages for that slug, e.g. les-menuires;
                                          no operator/prices for those)

Source: api.skiline.co.uk JSON search (one result per property: operator, beds, board, facility flags,
distance, pp price), /prices?ext_node_id= (all departures -> season range, changeover, 20 Mar price),
then the server-rendered property page (description, bedrooms, images). Prices are GBP per person,
usually including flights/transfers (see price_includes). 2 s between requests.
"""
import datetime as dt, json, re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch, text, oneline, slug, words, row, emit, log, base_args, setup, hot_tub_from_text, Blocked, STATS

API = "https://api.skiline.co.uk/"
HDR = {"Referer": "https://www.skiline.co.uk/", "Accept": "application/json"}
CHALET_BOARDS = ["Catered Chalet", "Self Catered Chalet", "Chalet Hotel", "Chalet Club Board"]
BMAP = {"Catered Chalet": ("chalet", "catered"), "Self Catered Chalet": ("chalet", "self-catered"),
        "Chalet Hotel": ("chalet-hotel", "chalet-hotel"), "Chalet Club Board": ("chalet", "catered"),
        "Self Catered Apartment": ("apartment", "self-catered"), "Catered Apartment": ("apartment", "catered"),
        "Half Board Hotel": ("hotel", "half-board"), "Hotel B&B": ("hotel", "breakfast-only"),
        "Full Board Hotel": ("hotel", "half-board"), "Room Only Hotel": ("hotel", "self-catered"),
        "Hotel Room Only": ("hotel", "self-catered"), "All Inclusive Hotel": ("hotel", "half-board")}
W = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
     "eleven": 11, "twelve": 12}


def q(resort=None, boards=None, page=0, dmin="2026-11-01", dmax="2027-05-31"):
    p = [("page", page), ("page_size", 100), ("date_min", dmin + "T00:00:00.000Z"), ("date_max", dmax + "T23:59:59.000Z"),
         ("date_flex", 0), ("minValue", 0), ("maxValue", 99999)]
    if resort:
        p.append(("resorts[]", resort))
    p += [("adults", 2), ("children", 0), ("selected", ""), ("showAccommodationOnly", 1)]
    p += [("boards[]", b) for b in (boards or [])]
    p.append(("showAllResorts", "true"))
    return urllib.parse.urlencode(p)


def getjson(url):
    st, s, _ = fetch(url, headers=HDR)
    return json.loads(s) if s.strip() else None


def search(resort, boards, limit=0):
    seen = {}
    for page in range(30):
        d = getjson(API + "?" + q(resort, boards, page)) or {}
        res = d.get("filteredResults", [])
        for x in res:
            seen.setdefault(x["ref_url"].rstrip("/"), x)
        if len(res) < 100 or (limit and len(seen) >= limit):
            break
    return list(seen.values())


def prices(node):
    p = urllib.parse.urlencode({"ext_node_id": node, "selected": "", "sort_by": "Date",
                                "date_min": "2026-10-06T00:00:00.000Z", "date_max": "2027-06-01T00:00:00.000Z"})
    try:
        d = getjson(API + "prices?" + p)
        return d if isinstance(d, list) else []
    except (ValueError, KeyError):
        return []


def page_info(url):
    st, s, _ = fetch(url, headers={"Referer": "https://www.skiline.co.uk/"})
    if st != 200 or "entry-title" not in s:
        return {}
    title = oneline((re.search(r'<h1 class="entry-title">(.*?)</h1>', s, re.S) or [None, ""])[1])
    ov = s[s.find('id="overview"'):]
    ov = ov[:ov.find("price-and-favorite")] if "price-and-favorite" in ov else ov[:20000]
    bl = re.findall(r'<ul class="board">(.*?)</ul>', ov, re.S)
    blis = [oneline(x) for x in re.findall(r"<li>(.*?)</li>", bl[0], re.S)] if bl else []
    board = next((b for b in blis if b and not b.lower().startswith("sleeps")), "")
    sleeps = next((b for b in blis if b.lower().startswith("sleeps")), "")
    feats = [f.lower() for f in re.findall(r'title="([^"]+)"><span', ov)]
    lines = [l.strip() for l in text(s).split("\n") if l.strip()]
    det = []
    if "Details" in lines:
        i = lines.index("Details")
        j = next((k for k in range(i + 1, len(lines)) if lines[k] in ("Please Note", "Catering", "Ski Rental", "Location", "Facilities")), i + 1)
        det = lines[i + 1:j]
    cat = []
    if "Catering" in lines:
        i = lines.index("Catering")
        cat = lines[i + 1:i + 6]
    nid = re.search(r'data-nid="(\d+)"', s) or re.search(r"ext_node_id=(\d+)", s)
    imgs = []
    for u in re.findall(r'https://(?:www|cdn)\.skiline\.co\.uk/wp-content/uploads/[^"\'\s]+?\.(?:webp|jpe?g|png)', s):
        if re.search(r"pack-|buy-1-get|buy-one-get|logo|icon|feefo|award|abta|atol|banner", u, re.I):
            continue
        u = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", u).replace("://www.", "://cdn.")
        if u not in imgs:
            imgs.append(u)
    return dict(title=title, board=board, sleeps=sleeps, feats=feats, details=" ".join(det),
                catering=" ".join(cat), node=nid.group(1) if nid else "", images=imgs)


def build(x, info, pr):
    notes = []
    board_name = (info.get("board") or x.get("board") or "")
    ptype, board = BMAP.get(board_name, ("", ""))
    if not ptype:
        notes.append(f"Ski Line board '{board_name}'")
    name = info.get("title") or x.get("property_name", "")
    op = (x.get("operator_name") or "").strip()
    seven = [p for p in pr if str(p.get("duration")) == "7"]
    pos = [float(p["now_price"]) for p in seven if float(p.get("now_price") or 0) > 0]
    wd = {dt.date.fromisoformat(p["departure_date"][:10]).weekday() for p in seven}
    chg = "Saturday" if wd == {5} else "Sunday" if wd == {6} else ("flexible" if len(wd) > 1 else "")
    start = "2027-03-21" if chg == "Sunday" else "2027-03-20"
    dep = [p for p in seven if p["departure_date"][:10] == start]
    p20 = [float(p["now_price"]) for p in dep if float(p.get("now_price") or 0) > 0]
    price20 = round(min(p20)) if p20 else ""
    avail = "yes" if p20 else "unknown"
    if dep and not p20:
        notes.append(f"Ski Line lists a {start[8:]} Mar departure with price 0 (probably sold/on request)")
    if not pr:
        notes.append("no prices on Ski Line API")
    elif not dep:
        notes.append("no 20/21 Mar 2027 departure in Ski Line price list")
    if p20:
        d0 = next(p for p in dep if float(p["now_price"]) == min(p20))
        notes.append(f"20 Mar price from Ski Line ({d0.get('out_departure_airport', '').strip()}{', ' + d0['room_type'] if d0.get('room_type') else ''})")
    inc = {"no-flights" if (p.get("out_departure_airport") or "").strip() in ("", "Independent Travel") else
           ("rail" if "rail" in (p.get("out_departure_airport") or "").lower() else "flights") for p in seven}
    pinc = {frozenset({"flights"}): "flights, transfers + board (Ski Line package)",
            frozenset({"rail"}): "Eurostar/rail travel + board (Ski Line package)",
            frozenset({"no-flights"}): "accommodation + board, no travel (Ski Line)"}.get(frozenset(inc), "mixed: some departures include travel" if inc else "")
    api = (pr[0] if pr else x)
    d = info.get("details", "")
    dlow = d.lower()
    feats = info.get("feats", [])
    listed_ht = "hot tub" in feats or api.get("hot_tub") == 1
    ht = hot_tub_from_text(d, listed_ht, ptype in ("chalet", ""))
    if not ht:
        ht = "none" if (pr or x) else "unknown"
    sauna = "yes" if ("sauna" in feats or api.get("sauna") == 1 or "sauna" in dlow) else "no"
    other = []
    if "swimming pool" in feats or api.get("pool") == 1: other.append("pool")
    if api.get("steam_room") == 1 or "steam" in dlow: other.append("steam room")
    if api.get("open_fire") == 1 or re.search(r"fireplace|log fire|open fire|wood.?burn", dlow): other.append("fireplace")
    if api.get("childcare") == 1 or api.get("in_house_creche") == 1: other.append("childcare")
    if api.get("in_resort_driver") == 1 or api.get("private_bus") == 1 or api.get("shared_driver") == 1: other.append("resort driver/minibus")
    if api.get("private_chauffeur") == 1: other.append("private chauffeur")
    dist = ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(km|m)\b", api.get("distance_toLift") or api.get("distance_toPiste") or "")
    if m:
        dist = int(float(m.group(1)) * (1000 if m.group(2) == "km" else 1))
    sio = "yes" if api.get("ski_in_ski_out") == 1 else ("partial" if api.get("nearly_ski_in_ski_out") == 1 else "unknown")
    smin = smax = ""
    sl = info.get("sleeps", "")
    m = re.search(r"Sleeps\s*(\d+)\s*(?:-|to|–)\s*(\d+)", sl)
    if m:
        smin, smax = int(m.group(1)), int(m.group(2))
    elif re.search(r"Sleeps\s*(\d+)", sl):
        smax = int(re.search(r"Sleeps\s*(\d+)", sl).group(1))
    elif api.get("beds"):
        smax = int(api["beds"]); notes.append("sleeps from Ski Line 'beds' field")
    bedrooms = ""
    m = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)[ -](?:en-?suite |spacious |double |large |comfortable |guest )?bed(?:room|rooms)\b", dlow)
    if m:
        bedrooms = int(W.get(m.group(1), m.group(1)))
    village = x.get("resort_name", "")
    url = x.get("ref_url", "").rstrip("/")
    if url.endswith("-peisey-nancroix") or "peisey" in dlow[:300]:
        notes.append("Ski Line resort 'Les Arcs' but text/url says Peisey-Nancroix - check village")
    if listed_ht:
        notes.append("hot tub per Ski Line facility flag")
    if board_name == "Chalet Club Board":
        notes.append("Ski Line board 'Chalet Club Board'")
    if pos:
        notes.append("Ski Line prices GBP pp")
    if not op:
        notes.append("operator not named (Ski Line sitemap-only page)")
    imgs = info.get("images", [])
    iu = (x.get("imageURL") or "").replace("://www.", "://cdn.")
    if iu and iu not in imgs:
        imgs = [iu] + imgs
    return row(chalet_name=name, operator=op, village=village, country=x.get("country_name", ""),
               sleeps_min=smin, sleeps_max=smax, bedrooms=bedrooms, property_type=ptype, board=board,
               catering_detail=words(info.get("catering", ""), 30) if board in ("catered", "chalet-hotel") else ("self-catered" if board == "self-catered" else ""),
               hot_tub=ht, sauna=sauna, other_facilities=", ".join(other), distance_to_lift_m=dist, ski_in_out=sio,
               changeover_day=chg, price_week_20_27_mar_2027=price20, price_basis="per-person" if pos else "",
               price_currency="GBP" if pos else "", price_type="exact-week" if p20 else ("season-range" if pos else "quote-needed"),
               price_range_low=round(min(pos)) if pos else "", price_range_high=round(max(pos)) if pos else "",
               price_includes=pinc if pos else "", available_20_27_mar=avail, description=words(d, 40), url=url,
               listed_on="Ski Line", notes="; ".join(notes), images=imgs[:10], _source="skiline",
               _source_id=x.get("ext_node_id", ""), _skiline_grade=x.get("chalet_grade", ""))


def sitemap_urls(rslug):
    urls = []
    st, s, _ = fetch("https://www.skiline.co.uk/sitemap_index.xml")
    for sm in re.findall(r"<loc>([^<]*accommodation-sitemap[^<]*)</loc>", s):
        _, x, _ = fetch(sm)
        urls += [u.rstrip("/") for u in re.findall(r"<loc>([^<]+)</loc>", x) if f"/{rslug}/" in u]
    return urls


def main():
    p = base_args(__doc__.split("\n")[0])
    p.add_argument("resort", nargs="?")
    p.add_argument("--list-resorts", action="store_true")
    p.add_argument("--chalets-only", action="store_true")
    p.add_argument("--no-detail", action="store_true")
    p.add_argument("--sitemap", default="")
    a = p.parse_args()
    setup(a)
    if a.list_resorts:
        d = getjson(API + "options?" + q())
        aggs = (d.get("body") or d).get("aggregations", {})
        for b in (aggs.get("resorts", {}).get("buckets") or []):
            print(f"{b['key']}\t{b['doc_count']}")
        return
    if not a.resort:
        p.error("resort required")
    items = search(a.resort, CHALET_BOARDS if a.chalets_only else None, a.limit)
    log(f"skiline: {a.resort} -> {len(items)} properties")
    if a.limit:
        items = items[: a.limit]
    n = 0
    try:
        for x in items:
            if a.dry_run:
                emit(build(x, {}, [])); n += 1
                continue
            pr = prices(x["ext_node_id"])
            info = {} if a.no_detail else page_info(x["ref_url"])
            emit(build(x, info, pr)); n += 1
        if a.sitemap and not a.dry_run:
            known = {x["ref_url"].rstrip("/") for x in items}
            extra = [u for u in sitemap_urls(a.sitemap) if u not in known and "chalet" in u.lower()]
            log(f"skiline: {len(extra)} sitemap-only chalet pages")
            for u in extra[: (a.limit or len(extra))]:
                info = page_info(u)
                if not info:
                    continue
                pr = prices(info["node"]) if info.get("node") else []
                x = dict(pr[0]) if pr else {"ref_url": u, "property_name": info["title"], "resort_name": ""}
                x["ref_url"] = u
                r = build(x, info, pr)
                r["notes"] = (r["notes"] + "; sitemap-only (not in Ski Line search)").strip("; ")
                emit(r); n += 1
    except Blocked as e:
        log(f"skiline: BLOCKED {e} - stopping")
    log(f"skiline: done, {n} rows, {STATS['requests']} requests")


if __name__ == "__main__":
    main()
