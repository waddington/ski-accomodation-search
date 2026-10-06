#!/usr/bin/env python3
"""MSEM tourist-office booking widget (services.msem.tech, ESF platform) -> JSON lines (SCHEMA columns + images).

    python3 tools/scrapers/msem.py stgervais                 (Saint-Gervais tourist office, resort 569)
    python3 tools/scrapers/msem.py stgervais --adults 8 --min-sleeps 8
    python3 tools/scrapers/msem.py --resort-id N --channel OT-N --page-url https://<office>/<booking page>/ --village X
    options: --limit N  --dry-run (lodging list + offers only, no detail calls)  --no-detail  --sites

API (JSON, no auth; the widget's own calls):
  GET  /api/lodging/resort/<id>/<channel>                    every lodging (name, slug, kind, maxCapacity, sectors...)
  POST /api/lodging/resort/<id>/offers {channel, adults, start, end, prod:true}  -> {lodging id: {price}} = bookable
       20-27 Mar 2027 for N adults (price excl. tourist tax); lodgings missing are booked, closed or offline-only
  POST /api/lodging/accomodation/<slug> {resort, language, facet, channel}  -> capacity/bedrooms/bathrooms, options,
       description, billingName (agency = operator), sectors
Public page of a lodging: <page-url>?slug=<slug> (the widget's prefixUrl redirect). No season price range (only the
dated offer). Other tourist offices run the same widget (find resort id/channel in the page's MseM.lodging options).
"""
import html, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch, text, words, row, emit, log, base_args, setup, hot_tub_from_text, Blocked, STATS

API = "https://services.msem.tech/api/lodging"
SITES = {
    "stgervais": dict(resort=569, channel="OT-569", page="https://www.saintgervais.com/reserver-mon-sejour/hebergement/",
                      site="Saint-Gervais tourist office booking (MSEM widget)", village="St-Gervais-les-Bains", ski_area="Évasion Mont-Blanc",
                      country="France",
                      # sector name / description words -> resorts_raw.csv village
                      villages=[(r"Bettex", "St-Gervais Le Bettex"), (r"Nicolas|V[ée]roce", "St-Nicolas-de-Véroce"),
                                (r"Fayet|Saint[- ]Gervais|St[- ]Gervais", "St-Gervais-les-Bains")]),
}
START, END = "2027-03-20", "2027-03-27"
JSON_H = {"Content-Type": "application/json", "Accept": "application/json"}


def post(url, body):
    st, s, _ = fetch(url, data=json.dumps(body), headers=JSON_H, method="POST")
    return json.loads(s) if s else {}


def ptype_of(kind, mk):
    kind, mk = (kind or "").upper(), (mk or "").upper()
    if kind == "HOTEL":
        return "hotel"
    if kind == "CHAMBRE_HOTE":
        return "room"
    if mk == "CHALET":
        return "chalet"
    return "apartment"


def main():
    p = base_args(__doc__.split("\n")[0])
    p.add_argument("site", nargs="?", default="")
    p.add_argument("--resort-id", type=int, default=0)
    p.add_argument("--channel", default="")
    p.add_argument("--page-url", default="")
    p.add_argument("--village", default="", help="default village (custom resort)")
    p.add_argument("--adults", type=int, default=2)
    p.add_argument("--min-sleeps", type=int, default=0)
    p.add_argument("--no-detail", action="store_true")
    p.add_argument("--sites", action="store_true")
    a = p.parse_args()
    setup(a)
    if a.sites or not (a.site or a.resort_id):
        for k, v in SITES.items():
            print(k, v["resort"], v["channel"], v["page"])
        return
    if a.site:
        cfg = dict(SITES[a.site])
    else:
        cfg = dict(resort=a.resort_id, channel=a.channel or f"OT-{a.resort_id}", page=a.page_url, villages=[],
                   site=f"MSEM resort {a.resort_id}", village=a.village, ski_area="", country="France")
    if a.village:
        cfg["village"] = a.village
    rid, ch = cfg["resort"], cfg["channel"]
    try:
        st, s, _ = fetch(f"{API}/resort/{rid}/{ch}", headers={"Accept": "application/json"})
        data = json.loads(s)
        offers = post(f"{API}/resort/{rid}/offers", {"channel": ch, "adults": a.adults, "start": START, "end": END, "prod": True})
    except Blocked as e:
        log(f"msem: BLOCKED {e}"); return
    lodgings = data.get("accomodations", [])
    sectors = {x["id"]: x["name"] for x in data.get("sectors", [])}
    log(f"msem/{a.site or rid}: {len(lodgings)} lodgings, {len(offers)} bookable 20-27 Mar for {a.adults} adults")
    n = 0
    for L in lodgings:
        if a.limit and n >= a.limit:
            break
        acc = L.get("accommodation") or {}
        cap = L.get("maxCapacity")
        if a.min_sleeps and cap and cap < a.min_sleeps:
            continue
        d = {}
        if not (a.dry_run or a.no_detail):
            try:
                d = post(f"{API}/accomodation/{L['slug']}", {"resort": rid, "language": "fr", "facet": 0, "channel": ch})
            except Blocked as e:
                log(f"msem: BLOCKED {e}"); break
            except Exception as e:  # one broken lodging must not stop the run
                log(f"msem: detail failed for {L['slug']}: {e}")
        c = d.get("capacity") or {}
        cap = c.get("maxCapacity") or cap
        desc = text(html.unescape((d.get("descriptions") or {}).get("long") or (L.get("descriptions") or {}).get("long") or ""))
        opts = [o.get("label", "") for o in d.get("options", [])] if d else []
        notes = [f"MSEM lodging id {L['id']} ({L['slug']})"]
        ptype = ptype_of(L.get("kind") or acc.get("kind"), L.get("meubleKind") or acc.get("meuble_kind"))
        if (L.get("meubleKind") or "").upper() == "APT-IN-CHALET":
            notes.append("apartment in a chalet")
        board = "self-catered" if ptype in ("chalet", "apartment") else ("breakfast-only" if ptype == "room" else "")
        if L.get("isAllInclusive"):  # "tout compris" = services included (seen on self-catered chalets), not catering
            notes.append("flagged all-inclusive (services included)")
        nm = L.get("name") or ""
        if ptype == "apartment" and re.match(r"(?:le |la )?chalet\b", nm, re.I) and not re.search(r"appart|apt\b|studio|duplex", nm, re.I):
            ptype, board = "chalet", "self-catered"
            notes.append(f"type {L.get('meubleKind') or 'unset'} on MSEM; named a chalet")
        if ptype == "hotel":
            notes.append("hotel: board not stated by the API")
        # village: lodging sectors, then description head ("SAINT GERVAIS LES BAINS - Le Bettex")
        sec_names = [sectors.get(x, "") for x in L.get("sectors", [])] + [x.get("name", "") for x in d.get("sectors", []) if isinstance(x, dict)]
        village, vspec = "", False
        for rx, v in cfg.get("villages", []):
            if any(re.search(rx, x) for x in sec_names) or re.search(rx, desc[:120]):
                village, vspec = v, v != cfg["village"]
                break
        village = village or cfg["village"]
        if sec_names:
            notes.append("sector: " + "/".join(x for x in sec_names if x))
        opt_txt = " ".join(opts)
        listed = bool(re.search(r"jacuzzi|spa privatif|bain nordique|hot tub", opt_txt, re.I))
        ht = hot_tub_from_text(desc + " " + opt_txt, listed, ptype == "chalet")
        if ht and ptype in ("hotel", "apartment") and ht.startswith(("yes", "private")) and \
                not re.search(r"priv[ée]|private|privatif", desc, re.I) and re.search(r"r[ée]sidence|h[ôo]tel", desc + " " + L.get("name", ""), re.I):
            ht = "shared"
        ht = ht or ("none" if d else "unknown")
        sauna = "yes" if re.search(r"sauna", desc + " " + opt_txt, re.I) else ("no" if d else "unknown")
        other = [f for f, rx in [("steam room", r"hammam|steam"), ("swimming pool", r"\bpiscine\b|swimming pool"),
                                 ("spa", r"espace spa|spa\b"), ("fireplace", r"chemin[ée]e|po[êe]le|fireplace")]
                 if re.search(rx, opt_txt + " " + desc, re.I)]
        if re.search(r"piscine (?:municipale|publique)|centre aquatique", desc, re.I) and "swimming pool" in other:
            notes.append("pool may be public")
        off = offers.get(str(L["id"])) or offers.get(L["id"])
        if off and off.get("price"):
            price, av = off["price"], "yes"
            price = int(price) if float(price) == int(price) else price
            notes.append(f"offers API 20-27 Mar 2027 for {a.adults} adults: EUR {off['price']} (excl. tourist tax)"
                         + (f", public price {off['publicPrice']}" if off.get("publicPrice") else ""))
        else:
            price, av = "", "unknown"
            notes.append(f"not in 20-27 Mar offers for {a.adults} adults (booked, closed or offline-only)")
        # private owners' billing names are people: never copied; agencies (PROFESSIONAL) are the operator
        if L.get("owner") in ("INDIVIDUAL", "PRIVATE"):
            operator = "Private owner"
        else:
            operator = d.get("billingName") or ""
            if operator:
                notes.append(f"billing/agency: {operator}")
        if L.get("arkianeConfigName"):
            notes.append(f"agency system: {L['arkianeConfigName']}")
        loc = L.get("location") or {}
        if loc.get("address1"):
            notes.append(f"address {loc.get('address1')} {loc.get('cp', '')} {loc.get('city', '')}".strip())
        imgs = [x.get("src") for x in (d.get("images") or L.get("images") or []) if isinstance(x, dict) and x.get("src")]
        imgs = [re.sub(r"-medium\.(jpe?g|png)$", r"-huge.\1", u) for u in imgs]
        page = cfg["page"]
        emit(row(chalet_name=html.unescape(L.get("name") or d.get("title") or ""), operator=operator, village=village,
                 ski_area=cfg["ski_area"], country=cfg["country"], sleeps_max=cap or "",
                 bedrooms=c.get("nbBedrooms") or "", bathrooms=c.get("nbBathrooms") or "", property_type=ptype, board=board,
                 catering_detail="self-catered" if board == "self-catered" else "", hot_tub=ht, sauna=sauna,
                 other_facilities=", ".join(other), changeover_day="",
                 price_week_20_27_mar_2027=price, price_basis="whole-chalet" if price and ptype != "room" else "",
                 price_currency="EUR" if price else "", price_type="exact-week" if price else "quote-needed",
                 price_includes="accommodation only (tourist tax extra)" if price else "",
                 available_20_27_mar=av, description=words(desc, 40),
                 url=f"{page}?slug={L['slug']}" if page else f"{API}/accomodation/{L['slug']}",
                 listed_on=cfg["site"], notes="; ".join(notes), images=imgs[:10],
                 _source=f"msem-{a.site or rid}", _source_id=L["id"], _village_specific=vspec))
        n += 1
    log(f"msem/{a.site or rid}: done, {n} rows, {STATS['requests']} requests")


if __name__ == "__main__":
    main()
