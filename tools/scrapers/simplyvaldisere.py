#!/usr/bin/env python3
"""Simply Val d'Isère (simplyvaldisere.com, agent for many operators) -> JSON lines (SCHEMA columns + images).

    python3 tools/scrapers/simplyvaldisere.py la-daille-le-cret
    python3 tools/scrapers/simplyvaldisere.py fornet            (aliases: daille, fornet, centre, legettaz, joseray, all)
    python3 tools/scrapers/simplyvaldisere.py all --list-codes  (operator codes found in rate-table titles)
    options: --limit N  --dry-run (sitemap only, no page requests)  --min-sleeps N

Steps: 1) /sitemap.xml -> every /accom/<area>/<slug> page (areas: resort-centre, legettaz, la-daille-le-cret,
le-fornet-laisinant, joseray-chatelard); 2) one static page per unit: h1 name, "Sleeps up to N", holiday type
(board), facilities/catering text, pricing guide, and the rate table(s) "<CODE> 2026-27 <name>" with rows
date from / date to / nights / price / availability -> 20 Mar (21 Mar if Sunday changeover) week price +
availability, season range, changeover day. <CODE> names the operator (OPERATORS); unknown codes are kept in notes.
Weeks missing from a table are usually booked/withdrawn -> available_20_27_mar = unknown (noted).
"""
import datetime as dt, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch, text, oneline, words, num, CURRENCY, row, emit, log, base_args, setup, hot_tub_from_text, Blocked, STATS

BASE = "https://www.simplyvaldisere.com"
AREAS = {"la-daille-le-cret": "La Daille", "le-fornet-laisinant": "Le Fornet", "resort-centre": "Val d'Isère",
         "legettaz": "Val d'Isère", "joseray-chatelard": "Val d'Isère"}
ALIAS = {"daille": "la-daille-le-cret", "la-daille": "la-daille-le-cret", "cret": "la-daille-le-cret",
         "fornet": "le-fornet-laisinant", "le-fornet": "le-fornet-laisinant", "laisinant": "le-fornet-laisinant",
         "centre": "resort-centre", "center": "resort-centre", "val-d-isere": "resort-centre",
         "joseray": "joseray-chatelard", "chatelard": "joseray-chatelard", "la-legettaz": "legettaz"}
# rate-table title code -> operator. Confirmed by collectors (rows/notes) or by the operator list in the site footer.
OPERATORS = {"YSE": "YSE", "BMST": "Build My Ski Trip", "HIP": "Hip Hideouts", "LE SKI": "Le Ski",
             "CIM": "Cimalpes", "SF": "Ski France", "VIP": "VIP SKI", "SW": "Skiworld", "ING": "Inghams",
             "CON": "Consensio", "BRAMBLE": "Bramble Ski", "PURPLE": "Purple Ski"}
# Seen 2026-10-06 but not mapped (no operator of that name in the site's operator list): COV, VAG, VLO, CT, CT/MC, OOAK.
# Some tables have no code at all ("Chalet Black Pearl 2026-27", "Mont Izia 2026-27").


def table_code(title):
    """'YSE 2026-27 Chalet X' -> 'YSE'; 'SW Chalet Casa Rivas 2026-27' -> 'SW'; 'Mont Izia 2026-27' -> ''."""
    pre = (re.match(r"(.+?)\s+20\d\d[-/]\d\d\b", title) or [None, ""])[1].strip()
    for k in sorted(OPERATORS, key=len, reverse=True):
        if re.match(re.escape(k) + r"\b", pre, re.I):
            return pre[:len(k)]
    m = re.match(r"([A-Z]{2,5}(?:/[A-Z]{1,4})?)(?:\s|$)", pre)
    return m.group(1) if m else ""


TARGET = dt.date(2027, 3, 20)
SEASON = (dt.date(2026, 10, 1), dt.date(2027, 6, 1))
MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
WORDNUM = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}


def sitemap(areas):
    st, s, _ = fetch(BASE + "/sitemap.xml")
    out = []
    for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", s):
        m = re.match(r"https?://(?:www\.)?simplyvaldisere\.com/accom/([a-z0-9-]+)/([a-z0-9-]+)/?$", u)
        if m and (not areas or m.group(1) in areas) and u not in out:
            out.append(u)
    return out


def sec(s, cls):
    m = re.search(r'<section class="%s">(.*?)</section>' % cls, s, re.S)
    return text(m.group(1)) if m else ""


def div(s, cls):
    m = re.search(r'<div class="%s">(.*?)</div>' % cls, s, re.S)
    return oneline(m.group(1)) if m else ""


def tables(s):
    """-> [dict(title, code, rows=[dict(start, end, nights, price, cur, avail)])]"""
    out = []
    for blk in s.split('<div class="bf-priceavail">')[1:]:
        title = oneline((re.search(r'<span class="bf-title">(.*?)</span>', blk, re.S) or [None, ""])[1])
        code = table_code(title)
        rows = []
        for tr in re.findall(r'<tr class="bf-datarow([^"]*)"[^>]*>(.*?)</tr>', blk.split("</table>", 1)[0], re.S):
            cls, body = tr
            dates = re.findall(r'<span class="day">(\d+)\w*</span>\s*<span class="month">(\w+)</span>\s*<span class="year">(\d{4})</span>', body)
            try:
                st, en = [dt.date(int(y), MONTHS[m[:3]], int(d)) for d, m, y in dates[:2]]
            except (ValueError, KeyError):
                continue
            pc = oneline((re.search(r'class="bf-pricecol">(.*?)</td>', body, re.S) or [None, ""])[1])
            av = oneline((re.search(r'class="bf-availcol">(.*?)</td>', body, re.S) or [None, ""])[1])
            nights = num(oneline((re.search(r'class="bf-nightscol">(.*?)</td>', body, re.S) or [None, ""])[1]))
            sym = re.search(r"[£€]|CHF", pc)
            rows.append(dict(start=st, end=en, nights=nights or (en - st).days, price=num(pc), ptxt=pc,
                             cur=CURRENCY.get(sym.group(0)) if sym else "", avail=av, cls=cls.strip()))
        out.append(dict(title=title, code=code, rows=rows))
    return out


def avail_of(r):
    a = (r["avail"] + " " + r["cls"]).lower()
    if re.search(r"sold|booked|unavail|full|closed", a):
        return "no"
    if re.search(r"avail", a):
        return "yes"
    return "unknown"


def board_of(what, name, catering):
    w = what.lower()
    if "club med" in w or "all inclusive" in w:
        return "catered"
    if "bed & breakfast" in w or "bed and breakfast" in w:
        return "breakfast-only"
    if "flexi" in w:
        return "catered-or-self"
    if "part catered" in w:
        return "half-board"
    if "catered chalet" in w:
        return "chalet-hotel" if re.search(r"\bhotel\b", name, re.I) else "catered"
    if "self catered" in w:
        if re.search(r"self[- ]catered or (?:fully )?catered|catered or self", catering, re.I):
            return "catered-or-self"
        return "self-catered"
    if w.strip() == "hotel":
        return "half-board" if re.search(r"half[- ]board|demi", catering, re.I) else ""
    return ""


def bedrooms_of(body, layout):
    m = re.search(r"\b(\d{1,2}|" + "|".join(WORDNUM) + r")[ -](?:double |twin |en[- ]suite |good sized |)bedrooms?\b", body, re.I)
    if m:
        v = m.group(1).lower()
        return (int(v) if v.isdigit() else WORDNUM[v]), ""
    rooms = re.findall(r"(?im)^\s*(?:master (?:suite|bedroom)|room \d+|bedroom \d+)\b", layout)
    if len(rooms) >= 2:
        return len(rooms), "bedrooms counted from room list"
    return "", ""


def page(url, area):
    st, s, _ = fetch(url)
    if st != 200 or "<h1>" not in s:
        return None
    s = re.sub(r"(?s)<script.*?</script>", " ", s)
    notes = []
    h1 = oneline((re.search(r"<h1>(.*?)</h1>", s, re.S) or [None, ""])[1])
    what, cap, where = div(s, "accom-what"), div(s, "accom-capacity"), div(s, "accom-where")
    intro, descr, loc, layout, custom = (sec(s, c) for c in ("accom-intro", "accom-description", "accom-location",
                                                              "accom-layout", "accom-custom"))
    body = " ".join([intro, descr, layout, custom])
    allt = " ".join([intro, descr, loc, layout, custom])
    cat_m = re.search(r"\bCatering\b(.*?)(?:Pricing Guide|$)", custom, re.S)
    catering = oneline(cat_m.group(1)) if cat_m else ""
    guide = oneline((re.search(r"Pricing Guide(.*?)(?:Please contact us|Enquire Now|$)", custom, re.S) or [None, ""])[1])
    # name: "Chalet Davos (8 + 2)" -> "Chalet Davos"; keep text after the capacity parenthesis ("... (8+4) Catered")
    m = re.match(r"(.*?)\s*\((\d+)\s*(?:\+\s*(\d+)|-\s*(\d+))?\)\s*(.*)$", h1)
    name = (m.group(1) + (" " + m.group(5) if m and m.group(5) else "")).strip() if m else h1
    smin = ""
    if m and (m.group(3) or m.group(4)):
        smin = int(m.group(2))
    smax = num((re.search(r"Sleeps up to (\d+)", cap) or [None, ""])[1])
    if not smax and m:
        smax = int(m.group(2)) + int(m.group(3) or 0) if m.group(3) else int(m.group(4) or m.group(2))
    if smin and smax and smin >= smax:
        smin = ""
    board = board_of(what, h1, catering + " " + body)
    if what:
        notes.append(f"Simply VDI holiday type: {what}")
    if re.search(r"a la carte|à la carte", catering + " " + guide, re.I) and board == "self-catered":
        notes.append("a-la-carte catering available at extra cost")
    # property type
    if re.search(r"\bhotel\b", h1, re.I) or what.lower() in ("hotel", "all inclusive (club med)"):
        ptype = "chalet-hotel" if board == "chalet-hotel" else "hotel"
    elif re.search(r"\bchalet\b|\bferme\b|\bmaison\b|\bvilla\b", h1, re.I):
        ptype = "chalet"
    elif re.search(r"apartment|penthouse|studio|residence|duplex|appartement", h1 + " " + intro[:200], re.I) or "self catered" in what.lower():
        ptype = "apartment"
    else:
        ptype = "chalet" if "chalet" in what.lower() else ""
    whole = ptype == "chalet"
    beds, bnote = bedrooms_of(body, layout)
    if bnote:
        notes.append(bnote)
    ht = hot_tub_from_text(allt, False, whole)
    if not ht:
        ht = "none" if allt else "unknown"
    elif ptype in ("hotel", "chalet-hotel") and ht == "yes-type-unknown" and not re.search(r"private|in (?:the|your) room", allt, re.I):
        ht = "shared"  # hotel spa
    sauna = "yes" if re.search(r"sauna", allt, re.I) else ("no" if allt else "unknown")
    other = [f for f in ["steam room", "hammam", "swimming pool", "indoor pool", "open fire", "log fire", "wood burn", "fireplace",
                         "boot warmer", "games room", "cinema", "gym", "pool table", "table tennis"] if f in allt.lower()]
    # village: area -> village; the La Daille & Le Crêt area is mostly Le Crêt/Cacholet (= Val d'Isère)
    village = AREAS.get(area, "Val d'Isère")
    if area == "la-daille-le-cret" and re.search(r"Le Cr[eê]t|Cacholet", allt) and not re.search(r"La Daille", allt):
        village = "Val d'Isère"; notes.append("Le Crêt/Cacholet (Val d'Isère), not La Daille")
    elif area == "le-fornet-laisinant" and re.search(r"Laisinant", allt) and not re.search(r"Fornet", allt):
        village = "Val d'Isère"; notes.append("Laisinant (between Le Fornet and Val d'Isère)")
    notes.append(f"Simply VDI area: {where or area}")
    # rate tables
    tabs = [t for t in tables(s) if t["rows"]]
    season_tabs = [t for t in tabs if any(SEASON[0] <= r["start"] < SEASON[1] for r in t["rows"])] or tabs
    codes = []
    for t in season_tabs:
        if t["code"] and t["code"] not in codes:
            codes.append(t["code"])
    operator = ""
    for c in codes:
        op = OPERATORS.get(c.upper()) or OPERATORS.get(c.upper().replace(" ", ""))
        if op:
            operator = op
            break
    if codes:
        notes.append("Simply VDI rate-table code " + "/".join(f'"{c}"' for c in codes)
                     + ("" if operator else " (operator code not mapped)"))
    price20, av, lo, hi, cur, changeover = "", "unknown", "", "", "", ""
    if season_tabs:
        t = season_tabs[0]
        rows = [r for r in t["rows"] if SEASON[0] <= r["start"] < SEASON[1] and r["price"]]
        days = {r["start"].weekday() for r in rows if r["nights"] == 7}
        changeover = {5: "Saturday", 6: "Sunday"}.get(next(iter(days)), "") if len(days) == 1 else ("flexible" if days else "")
        cur = next((r["cur"] for r in rows if r["cur"]), "")
        vals = [r["price"] for r in rows if r["cur"] == cur and r["nights"] == 7]
        if vals:
            lo, hi = min(vals), max(vals)
        start = TARGET + dt.timedelta(1) if changeover == "Sunday" else TARGET
        hit = [r for r in t["rows"] if r["start"] == start] or \
              [r for r in t["rows"] if r["start"] <= start < r["end"] and r["nights"] >= 7]
        if hit:
            r = hit[0]
            av = avail_of(r)
            if r["start"] == start and r["nights"] == 7 and r["price"]:
                price20 = r["price"]
            notes.append(f"20 Mar row: {r['start']:%d %b}-{r['end']:%d %b} {r['ptxt']} {r['avail']}")
        else:
            notes.append(f"{start:%d %b} week not in rate table (weeks missing from the table are often booked)")
        if len(season_tabs) > 1:
            notes.append("other rate tables: " + "; ".join(x["title"] for x in season_tabs[1:]))
    gm = re.search(r"([£€])\s*([\d,]+)(?:pp)?\s*(?:-|to|–)\s*[£€]?\s*([\d,]+)", guide)
    if not lo and gm:
        lo, hi, cur = num(gm.group(2)), num(gm.group(3)), CURRENCY[gm.group(1)]
        notes.append("range from pricing guide")
    if not changeover:
        cm = re.search(r"(Saturday|Sunday)\s*(?:-|to|–)\s*(Saturday|Sunday)", guide + " " + catering)
        changeover = cm.group(1) if cm and cm.group(1) == cm.group(2) else ""
    basis = "per-person" if re.search(r"\bpp\b|per person|per adult", guide, re.I) else ("whole-chalet" if (lo or price20) else "")
    if guide:
        notes.append("pricing guide: " + words(guide, 30))
    if re.search(r"flights?", guide, re.I):
        notes.append("guide prices may include flights/transfers")
    if not tabs:
        notes.append("no availability table; pass2: exact-week price")
    ptype_price = "exact-week" if price20 else ("season-range" if lo != "" and lo != hi else ("season-from" if lo else "quote-needed"))
    imgs = []
    for f in re.findall(r'(?:src|href)="/uploads/(?:original|small|thumb)/([^"]+)"', s):
        u = f"{BASE}/uploads/original/{f}"
        if u not in imgs and not re.search(r"floor|plan|logo|\.png$", f, re.I):
            imgs.append(u)
    return row(chalet_name=name, operator=operator, village=village, ski_area="Espace Killy", country="France",
               sleeps_min=smin, sleeps_max=smax or "", bedrooms=beds, property_type=ptype, board=board,
               catering_detail=words(catering, 30) if board not in ("self-catered", "") else ("self-catered" if board == "self-catered" else ""),
               hot_tub=ht, sauna=sauna, other_facilities=", ".join(other), changeover_day=changeover,
               price_week_20_27_mar_2027=price20, price_basis=basis if (price20 or lo) else "",
               price_currency=cur if (price20 or lo) else "", price_type=ptype_price,
               price_range_low=lo, price_range_high=hi, available_20_27_mar=av,
               description=words(intro or descr, 40), url=url, listed_on="Simply Val d'Isère",
               notes="; ".join(notes), images=imgs[:10], _source="simplyvaldisere",
               _source_id=url.rstrip("/").rsplit("/", 1)[1], _codes=codes)


def main():
    p = base_args(__doc__.split("\n")[0])
    p.add_argument("area", nargs="?", default="", help="area slug or alias; 'all' = every area")
    p.add_argument("--min-sleeps", type=int, default=0)
    p.add_argument("--list-codes", action="store_true", help="only print rate-table codes and their unit counts")
    a = p.parse_args()
    setup(a)
    if not a.area:
        print("areas:", ", ".join(AREAS), "| aliases:", ", ".join(ALIAS))
        return
    areas = []
    for x in a.area.lower().split(","):
        x = ALIAS.get(x.strip(), x.strip())
        if x == "all":
            areas = []
            break
        if x not in AREAS:
            sys.exit(f"unknown area {x!r}; areas: {', '.join(AREAS)}")
        areas.append(x)
    try:
        urls = sitemap(areas)
    except Blocked as e:
        log(f"simplyvaldisere: BLOCKED {e}"); return
    log(f"simplyvaldisere: {len(urls)} pages (areas={','.join(areas) or 'all'})")
    n, codes = 0, {}
    for u in urls:
        if a.limit and n >= a.limit:
            break
        area = u.split("/accom/")[1].split("/")[0]
        if a.dry_run:
            emit(row(chalet_name=u.rstrip("/").rsplit("/", 1)[1].replace("-", " ").title(), village=AREAS.get(area, ""),
                     url=u, listed_on="Simply Val d'Isère", _source="simplyvaldisere", notes="dry-run: sitemap only"))
            n += 1
            continue
        try:
            r = page(u, area)
        except Blocked as e:
            log(f"simplyvaldisere: BLOCKED {e} - stopping"); break
        if not r:
            continue
        for c in r["_codes"]:
            codes[c] = codes.get(c, 0) + 1
        if a.min_sleeps and r["sleeps_max"] and int(r["sleeps_max"]) < a.min_sleeps:
            continue
        if not a.list_codes:
            emit(r)
        n += 1
    if a.list_codes:
        for c, k in sorted(codes.items(), key=lambda x: -x[1]):
            print(f"{c}\t{k}\t{OPERATORS.get(c.upper(), '?')}")
    log(f"simplyvaldisere: done, {n} rows, {STATS['requests']} requests; codes: {codes}")


if __name__ == "__main__":
    main()
