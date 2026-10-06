#!/usr/bin/env python3
"""Ingenie-platform official resort booking sites -> JSON lines (SCHEMA columns + images).

Same vendor (Ingenie "genius" engine) behind several tourist-office booking sites; one scraper, per-site config.

    python3 tools/scrapers/ingenie.py tignes --quarter IBREVIERES,IVILLARET      (comma = several quarters)
    python3 tools/scrapers/ingenie.py lesmenuires --quarter IBRUYERES --min-sleeps 8
    python3 tools/scrapers/ingenie.py lesmenuires --list-quarters
    python3 tools/scrapers/ingenie.py valdisere --quarter FRRASAVADAILL     (Val d'Isère: ZONEGEO areas, Le Fornet = FRRASAVAFORNE)
    options: --limit N  --dry-run (list + dated search only, no detail pages)  --adults N (dated search, default 2)
             --min-sleeps N (skip units whose capacity is known and < N; capacity from card/name/detail)
             --type chalet|apartment|all (filter on detail 'type of accommodation' / name; default all)
             --no-detail  --sites (print configured sites)

Steps: 1) undated list /search?mid=..&sans_dates=1&criteres[]=IQUART[<code>[<T> (20/page, static) = every unit;
2) dated list /booking?cid=..&datedeb=20/03/2027&datefin=27/03/2027&adultes=N (+criteres) = units bookable that
week with the week price ("from"/"à partir de"); 3) detail page per unit (static): capacity, bedrooms, bathrooms,
description, jacuzzi/sauna text. Season price range is NOT fetched (weekly planning is a JS widget).
"""
import re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch, text, oneline, words, num, row, emit, log, base_args, setup, hot_tub_from_text, Blocked, STATS

SITES = {
    "lesmenuires": dict(host="https://fr.locationlesmenuires.com", mid=3, cid=3, tp="I", village="Les Menuires",
                        ski_area="Les 3 Vallées", country="France", site="Les Menuires Réservation (locationlesmenuires.com)",
                        quarters={"IBRUYERES": "Les Menuires: Les Bruyères", "IBALCBRU": "Les Menuires: Les Bruyères",
                                  "IREB2000": "Les Menuires: Reberty 2000", "IREBERTY": "Les Menuires: Reberty 2000",
                                  "ICROISETTE": "Les Menuires", "IPREYERAND": "Les Menuires", "IFONTANETTES": "Les Menuires",
                                  "IAIRELLES": "Les Menuires"}),
    "tignes": dict(host="https://booking.tignes.net", mid=1, cid=1, tp="G", village="Tignes", ski_area="Espace Killy",
                   country="France", site="Tignes Réservation (booking.tignes.net)",
                   quarters={"IBREVIERES": "Tignes Les Brévières", "IVILLARET": "Tignes Les Brévières", "IBOISSES": "Tignes Les Boisses", "I1800": "Tignes 1800",
                             "ILAVACHET": "Tignes Le Lavachet", "IALMES": "Tignes Le Lac", "IROSSET": "Tignes Le Lac",
                             "IBECROUGE": "Tignes Le Lac", "ICHARTREUX": "Tignes Val Claret", "IVALCLARET": "Tignes Val Claret",
                             "IVCCENTRE": "Tignes Val Claret"}),
    "serrechevalier": dict(host="https://booking.serre-chevalier.com", mid=4, cid=4, tp="I", qcrit="SECTEUR", client_filter=True,
                           village="Serre Chevalier", ski_area="Serre Chevalier", country="France",
                           site="Serre Chevalier Réservation (booking.serre-chevalier.com)",
                           quarters={"CHAN": "Serre Chevalier: Chantemerle (1350)", "CHANAUTRE": "Serre Chevalier: Chantemerle (1350)",
                                     "VILL": "Serre Chevalier: Villeneuve (1400)", "VILLAUTRE": "Serre Chevalier: Villeneuve (1400)",
                                     "VILLARDLATE": "Serre Chevalier: Villeneuve (1400)", "MON": "Serre Chevalier: Le Monêtier (1500)",
                                     "BRICENTRE": "Serre Chevalier: Briançon (1200)", "BRIPERIPHERIE": "Serre Chevalier: Briançon (1200)",
                                     "BRIPROREL": "Serre Chevalier: Briançon (1200)"}),
    # Val d'Isère: areas are ZONEGEO tags (not IQUART); a card has several (place + distance/"West"/"Ski in")
    "valdisere": dict(host="https://booking.valdisere.com", mid=3, cid=3, tp="G", qcrit="ZONEGEO",
                      village="Val d'Isère", ski_area="Espace Killy", country="France",
                      site="Val d'Isère Réservation (booking.valdisere.com)",
                      # other place zones (village = Val d'Isère): FRRASAVACENTR Center, FRRASAVALEGET Legettaz,
                      # FRRASAVARONDP Rond Point des Pistes, FRRASAVACE500, ESTCENTRE, OUESTCENTRE, SKIAUXPIEDS ...
                      quarters={"FRRASAVADAILL": "La Daille", "FRRASAVAFORNE": "Le Fornet"}),
}
DATEDEB, DATEFIN = "20/03/2027", "27/03/2027"


def crit(cfg, quarter):
    if not quarter or cfg.get("client_filter"):  # no server-side area criterion: filter cards by class instead
        return []
    return [("criteres[]", f"{cfg.get('qcrit', 'IQUART')}[{quarter}[{cfg['tp']}")]


def cards(s, cfg):
    out = []
    for b in re.split(r'<div[^>]*id="PRESTATION-', s)[1:]:
        pid = b.split('"', 1)[0]
        b = re.sub(r"(?s)<script.*?</script>", "", b.split('class="pied_page')[0][:40000])
        m = re.search(r'href="([^"?#]+\.html)', b)
        if not m:
            continue
        url = urllib.parse.urljoin(cfg["host"] + "/", m.group(1))
        nm = re.search(r'<div class="nom">(.*?)</a>', re.sub(r"(?s)<!--.*?-->", "", b), re.S)
        name = oneline(re.sub(r'<span class="code_prest">.*?</span>\s*</span>', "", nm.group(1), flags=re.S)) if nm else ""
        name = name.replace("-->", "").strip()
        zones = re.findall(r'class="(?:IQUART|SECTEUR|ZONEGEO)-([A-Z0-9_]+)-\w">([^<]+)', b)
        # Val d'Isère cards carry several ZONEGEO tags (place + "500 m from centre"/"West"/"Ski in"): prefer a mapped one
        q = next((z for z in zones if z[0] in cfg.get("quarters", {})), zones[0] if zones else None)
        cap = (re.search(r'(?:ICAPAC|CAPACITEMAX)[^"]*"><span class="quantite">(\d+)', b)
               or re.search(r'class="NBMAXI-(\d+)PERS', b))
        beds = re.search(r'INBCHAMBRE-(\d+)CH', b)
        surf = re.search(r'ISUPER[^"]*"><span class="quantite">(\d+)', b) or re.search(r"Surface\s*:\s*(\d+)", oneline(b))
        price = re.search(r'class="prix_en_cours">([^<]+)<', b)
        normal = re.search(r'class="prix_barre">([^<]+)<', b)
        imgs = []
        for u in re.findall(r'(?:src|data-src)="(https?://[^"]+/medias/images/prestations/[^"]+)"', b):
            u = re.sub(r"/multitailles/\d+x\d+_", "/multitailles/1200x900_", u)
            if u not in imgs:
                imgs.append(u)
        classes = set(re.findall(r'<li class="([A-Z][^"]+)"', b))
        out.append(dict(pid=pid, url=url, name=name, qcode=q[0] if q else "", qname=oneline(q[1]) if q else "",
                        zones=[(z[0], oneline(z[1])) for z in zones],
                        cap=int(cap.group(1)) if cap else None, beds=int(beds.group(1)) if beds else None,
                        surf=surf.group(1) if surf else "", price=num(price.group(1)) if price else None,
                        normal=num(normal.group(1)) if normal else None, imgs=imgs, classes=classes,
                        agency=pid.split("-")[1] if pid.count("-") >= 2 else "",
                        bookable=bool(re.search(r"Réserver|Book|Disponibilit|Availability", oneline(b)))))
    return out


def pages(first_url, cfg, limit=0, max_pages=120):
    """Explicit &page=N with ordre_type=alphabetique (the default order is random per request)."""
    allc, seen = [], set()
    for page in range(1, max_pages + 1):
        st, s, _ = fetch(first_url + f"&ordre_type=alphabetique&page={page}")
        new = [c for c in cards(s, cfg) if c["pid"] not in seen]
        for c in new:
            seen.add(c["pid"])
        allc += new
        if not new or (limit and len(allc) >= limit):
            break
    return allc


def undated(cfg, quarter, limit=0):
    p = [("mid", cfg["mid"]), ("action", "result"), ("sans_dates", 1), ("type_prestataire", cfg["tp"]), ("affiner", 1)] + crit(cfg, quarter)
    return pages(cfg["host"] + "/search?" + urllib.parse.urlencode(p), cfg, limit)


def dated(cfg, quarter, adults):
    p = [("cid", cfg["cid"]), ("MOTEUR_TYPES_PRESTATAIRE", "MOTEUR_HEBERGEMENT"), ("action", "result"),
         ("type_prestataire", cfg["tp"]), ("datedeb", DATEDEB), ("datefin", DATEFIN), ("duree", 7),
         ("adultes", adults), ("enfants", 0)] + ([("affiner", 1)] + crit(cfg, quarter) if quarter else [])
    return {c["pid"]: c for c in pages(cfg["host"] + "/booking?" + urllib.parse.urlencode(p), cfg)}


def detail(url):
    st, s, _ = fetch(url)
    if st != 200:
        return {}
    s = re.sub(r"(?s)<script.*?</script>", "", s)
    i = s.find("<h1")
    t = oneline(s[i:] if i > 0 else s)
    # Val d'Isère boilerplate: "Tips Benefits : ... 20% discount at the Aquasportif Center (Wellness ...) ... Summary"
    # and the site footer would otherwise count as spa / wellness text
    t = re.sub(r"Tips Benefits\s*:.*?(?=Summary\b)", " ", t)
    t = re.split(r"\bContact us Our opening hours\b", t)[0]
    g = lambda rx: (re.search(rx, t, re.I) or [None, ""])[1]
    desc = g(r"(?:Presentation|Présentation)\s+(.*?)\s+(?:Location Information|Informations? de localisation|Localisation|In Short|En bref|En Résumé|Réservez|Situation|Equipment & services|Équipements & services|To note|Availability Location)")
    cap = num(g(r"(?:Capacity maximum|Capacité maximum|Capacité|Number of people \(max\)|Nombre de personnes \(max\))\s*:\s*(\d+)"))
    capd = num(g(r"(?:jusqu'à|for up to|sleeps|up to|confort pour|accueillir)\s+(\d+)\s+(?:personnes|people|persons|guests)"))
    nb = re.findall(r"\b(\d+)\s+(?:chambres|bedrooms)\b", desc, re.I)
    return dict(text=t, desc=desc,
                cap=cap, capd=capd,
                beds=num(g(r"(?:Number of bedrooms|Nombre de chambres)\s*:\s*(\d+)")) or num(g(r"^[^:]{0,120}?\((\d+) (?:bedrooms?|chambres?)\)"))
                     or (int(nb[0]) if len(nb) == 1 else None),
                baths=num(g(r"(?:Number of bathrooms|Nombre de salles? de bains?)\s*:\s*(\d+)")),
                typ=g(r"(?:Type of accommodation|Type d'hébergement|Type de logement)\s*:\s*(.+?)\s+(?:Surface|Capacity|Capacité|Number|Nombre)"),
                chalet=g(r"In Short\s+Chalet\s*:\s*(.+?)\s+Type of"),
                lat=g(r"Latitude\s*:\s*([\d.]+)"), lon=g(r"Longitude\s*:\s*([\d.]+)"))


# Equipment labels that name several facilities at once; they say nothing about a hot tub on their own.
# "Sauna/Jacuzzi/Steam room" = picto IEQUIP-ISPAS (Tignes), also printed in the detail-page equipment list.
SPA_LABELS = (r"Sauna/Jacuzzi/(?:Steam room|Hammam)|Sauna/Jacuzzi/Hammam|Piscine, Sauna, Hammam\s*:|"
              r"Pool, Steam room, Sauna\s*:|Espace bien [êe]tre/piscine")
HOT_TUB_WORDS = (r"jac+u+z+is?|hot[ -]?tubs?|spa bath|bains? nordiques?|nordic bath|bains? (?:à|a) remous|"
                 r"whirlpool|baignoire balnéo|outdoor spa")
PRIVATE_WORDS = r"private|privatif|privée?|in the apartment|dans l'appartement|own (?:hot tub|jacuzzi)"


def spa_fields(full, desc, classes, is_chalet, typ_name, have_detail):
    """-> (hot_tub, sauna, notes). The combined picto/label 'Sauna/Jacuzzi/Steam room' (ISPAS) means sauna=yes but
    NOT a hot tub: hot tub only when the text itself says jacuzzi/hot tub/spa bath/bains à remous/whirlpool.
    Apartments / residence units: a jacuzzi is the residence's (shared) unless the text says private."""
    notes = []
    ispas = "ISPAS" in " ".join(classes)
    nolab = re.sub(SPA_LABELS, " ", full)
    jtxt = " ".join(re.findall(r"[^.]{0,120}(?:" + HOT_TUB_WORDS + r")[^.]{0,120}", nolab, re.I))
    residence = (not is_chalet) or bool(re.search(r"r[ée]sidence", typ_name, re.I))
    ht = ""
    if jtxt:
        ht = hot_tub_from_text(jtxt, False, is_chalet)
        if residence and ht != "shared":
            ht = "yes-type-unknown" if re.search(PRIVATE_WORDS, jtxt, re.I) else "shared"
        notes.append("spa text: " + words(jtxt, 25))
    if not ht:
        ht = "none" if have_detail else "unknown"
        if ispas:
            notes.append("picto 'Sauna/Jacuzzi/Steam room' but no jacuzzi/hot tub in text")
    # detail equipment line "Pool, Steam room, Sauna : Steam room Included Services ..." lists what is really there
    eq = re.search(r"(?:Pool, Steam room, Sauna|Piscine, Sauna, Hammam)\s*:\s*(.{0,160}?)(?=\s+(?:Included|Inclus|Services|Destination|"
                   r"Ski locker|Casier|Fireplace|Chemin|Kitchen|Cuisine|Living room|Séjour|Parking|Car park|Bathroom|Salle)\b|$)", full)
    eq_items = eq.group(1) if eq else ""
    if eq_items:
        notes.append("wellness equipment: " + words(eq_items, 15))
    rest = re.sub(r"(?:Pool, Steam room, Sauna|Piscine, Sauna, Hammam)\s*:\s*" + re.escape(eq_items), " ", nolab) if eq_items else nolab
    if re.search(r"sauna", desc + " " + rest + " " + eq_items, re.I) or (ispas and not eq_items):
        sauna = "yes"
    elif not have_detail or re.search(r"\bspa\b|wellness|bien[- ][êe]tre", nolab, re.I):
        sauna = "unknown"
    else:
        sauna = "no"
    if ispas and residence:
        notes.append("sauna/spa probably residence facility (shared)")
    return ht, sauna, notes


def main():
    p = base_args(__doc__.split("\n")[0])
    p.add_argument("site", nargs="?")
    p.add_argument("--quarter", default="")
    p.add_argument("--adults", type=int, default=2)
    p.add_argument("--min-sleeps", type=int, default=0)
    p.add_argument("--type", default="all", choices=["all", "chalet", "apartment"])
    p.add_argument("--no-detail", action="store_true")
    p.add_argument("--list-quarters", action="store_true")
    p.add_argument("--sites", action="store_true")
    a = p.parse_args()
    setup(a)
    if a.sites or not a.site:
        for k, v in SITES.items():
            print(k, v["host"], "quarters:", " ".join(v["quarters"]))
        return
    cfg = SITES[a.site]
    q = a.quarter.upper()
    if a.list_quarters:
        found = {}
        for c in undated(cfg, "", limit=400):
            for code, name in c["zones"] or [("", "")]:
                found.setdefault(code, [name, 0])[1] += 1
        for k, (n, cnt) in sorted(found.items()):
            print(f"{k}\t{n}\t{cnt} (in first ~400 units)")
        return
    qs = [x for x in q.split(",") if x] or [""]
    units, avail = [], {}
    try:
        if cfg.get("client_filter"):
            units = [u for u in undated(cfg, "", 0) if not q or {z[0] for z in u["zones"]} & set(qs)]
            avail = {k: v for k, v in dated(cfg, "", a.adults).items() if not q or {z[0] for z in v["zones"]} & set(qs)}
        else:
            for qq in qs:
                got = {u["pid"] for u in units}
                units += [u for u in undated(cfg, qq, a.limit * 3 if a.limit and a.min_sleeps else a.limit) if u["pid"] not in got]
                avail.update(dated(cfg, qq, a.adults))
        log(f"ingenie/{a.site}: {len(units)} units (undated, quarter={q or 'all'})")
        log(f"ingenie/{a.site}: {len(avail)} bookable 20-27 Mar for {a.adults} adults")
    except Blocked as e:
        log(f"ingenie: BLOCKED {e}"); return
    # units only in dated results (shouldn't happen, but keep them)
    known = {u["pid"] for u in units}
    units += [c for pid, c in avail.items() if pid not in known]
    n = 0
    for u in units:
        if a.limit and n >= a.limit:
            break
        capn = num((re.search(r"(\d+)\s*(?:people|personnes|pers\b|persons)", u["name"], re.I) or [None, ""])[1])
        cap = u["cap"] or capn
        if a.min_sleeps and cap and max(cap, capn or 0) < a.min_sleeps:
            continue
        d = {}
        if not (a.dry_run or a.no_detail):
            try:
                d = detail(u["url"])
            except Blocked as e:
                log(f"ingenie: BLOCKED {e}"); break
        cap = d.get("cap") or cap or d.get("capd")
        if a.min_sleeps and cap and max(cap, capn or 0, d.get("capd") or 0) < a.min_sleeps:
            continue
        typ = (d.get("typ") or "").lower()
        nm = u["name"]
        is_chalet = "chalet" in typ or (not typ and re.search(r"\bchalet\b", nm, re.I)
                                         and not re.search(r"chalets\b|r[ée]sidence|dame blanche", nm, re.I))
        if a.type == "chalet" and not is_chalet or a.type == "apartment" and is_chalet:
            continue
        notes = []
        dd = avail.get(u["pid"])
        if dd and dd["price"]:
            price, av = dd["price"], "yes"
            notes.append(f"20-27 Mar bookable on {cfg['site'].split(' (')[0]} for {a.adults} adults: EUR {dd['price']}"
                         + (f" (normal {dd['normal']})" if dd.get("normal") else ""))
        else:
            # validation: some units absent from the dated search were free in their weekly planning -> unknown, not no
            price, av = "", "unknown"
            notes.append(f"not in 20-27 Mar dated search ({a.adults} adults)" + ("" if u["bookable"] else "; unit not bookable online")
                         + "; pass2: weekly planning")
        desc = d.get("desc", "")
        full = d.get("text", "")
        board, catd = "self-catered", "self-catered"
        mcat = re.search(r"[^.]{0,80}(service traiteur|catered|chef |pension complète|full board|demi-pension|half[- ]board)[^.]{0,160}", desc, re.I)
        if mcat and re.search(r"on request|extra (?:cost|charge)|en option|sur demande|optional|supplément|payant", mcat.group(0), re.I):
            notes.append("optional catering at extra cost: " + words(mcat.group(0).strip(), 25))
        elif mcat:
            board = "half-board" if re.search(r"demi-pension|half[- ]board", mcat.group(0), re.I) else "catered"
            catd = words(mcat.group(0).strip(), 30)
            notes.append("catering mentioned in description")
        ht, sauna, spa_notes = spa_fields(full, desc, u["classes"], bool(is_chalet), typ + " " + nm, bool(d))
        notes += spa_notes
        if re.search(r"(collective|collectif|commun|shared)[^.]{0,60}(sauna|jacuzzi|spa|pool|piscine)", full, re.I):
            notes.append("residence has shared wellness area")
        ptype = "chalet" if is_chalet else "apartment"
        village = cfg["quarters"].get(u["qcode"], cfg["village"])
        if u["qname"]:
            notes.append(f"quarter: {u['qname']}")
        if u["agency"]:
            notes.append(f"agency code: {u['agency']}")
        if d.get("lat"):
            notes.append(f"GPS {d['lat']},{d['lon']}")
        name = nm if not d.get("chalet") or d["chalet"].lower() in nm.lower() else f"{nm} ({d['chalet'].title()})"
        emit(row(chalet_name=name, operator="", village=village, ski_area=cfg["ski_area"], country=cfg["country"],
                 sleeps_max=cap or "", bedrooms=d.get("beds") or u["beds"] or "", bathrooms=d.get("baths") or "",
                 property_type=ptype, board=board, catering_detail=catd, hot_tub=ht, sauna=sauna,
                 changeover_day="Saturday" if av == "yes" else "",
                 price_week_20_27_mar_2027=price, price_basis="whole-chalet" if price else "",
                 price_currency="EUR" if price else "", price_type="exact-week" if price else "quote-needed",
                 available_20_27_mar=av, description=words(desc, 40), url=u["url"],
                 listed_on=cfg["site"].split(" (")[0], notes="; ".join(notes), images=u["imgs"][:10],
                 _source="ingenie-" + a.site, _source_id=u["pid"], _surface_m2=u["surf"],
                 _village_specific=u["qcode"] in cfg["quarters"]))
        n += 1
    log(f"ingenie/{a.site}: done, {n} rows, {STATS['requests']} requests")


if __name__ == "__main__":
    main()
