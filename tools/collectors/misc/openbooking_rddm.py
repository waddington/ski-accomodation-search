#!/usr/bin/env python3
"""Région Dents du Midi (openbooking.ch whitelabel) -> chalet rows appended to a task CSV.

usage: openbooking_rddm.py <task_id> <place_code> <village> [--dry-run]
place codes: rddm-1873-1 Val-d'Illiez, rddm-1873-2 Les Crosets, rddm-1873-3 Champoussin,
             rddm-1874-1 Champéry, rddm-1875-1 Morgins
"""
import html, json, re, subprocess, sys, time, urllib.request

ROOT = "/home/kai/Documents/Misc/ski-chalet-finder"
KEY = "4BA615F77D1B41C7A5E2CFAEFC7D77C1"
API = "https://api.openbooking.ch"
PAGE = "https://www.regiondentsdumidi.ch/en/booking/accommodations/chalets-apartments-26263/#detail/"
HDR = {"api-key": KEY, "Referer": "https://www.regiondentsdumidi.ch/", "Content-Type": "application/json",
       "User-Agent": "Mozilla/5.0"}


def req(url, body=None):
    time.sleep(2)
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=HDR)
    return json.load(urllib.request.urlopen(r, timeout=40))


def slug(s):
    s = html.unescape(s).lower()
    for a, b in (("éèêë", "e"), ("àâä", "a"), ("ôö", "o"), ("ûüù", "u"), ("îï", "i"), ("ç", "c")):
        for ch in a:
            s = s.replace(ch, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def text(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


def main():
    task, place, village = sys.argv[1:4]
    dry = "--dry-run" in sys.argv
    d = req(API + "/whitelabel/list?limit=200&skip=0", {"lang": "en", "sort": "stars", "places": [place]})
    accs = d["accommodations"]
    print(f"{len(accs)} units (found {d['found']})", file=sys.stderr)
    out = []
    for a in accs:
        aid = a["id"]
        det = req(f"{API}/accommodations/{aid}?lang=en")
        try:
            av = req(f"{API}/availabilities/{aid}")[0]
        except Exception:
            av = {}
        facts = det.get("facts") or {}
        f = facts.get("apartment") or next(iter(facts.values()), {}) if facts else {}
        desc_en = text((det.get("description") or {}).get("en")) or text((det.get("description") or {}).get("fr"))
        cond = text((det.get("description_conditions") or {}).get("en"))
        feats = [x if isinstance(x, str) else x.get("name", "") for x in det.get("features") or []]
        alltxt = (desc_en + " " + cond + " " + text((det.get("description") or {}).get("fr"))).lower()
        if re.search(r"hot ?tub|jacuzzi|whirlpool|spa bath|bain nordique|nordic bath|jacuzzi", alltxt):
            hot = "yes-type-unknown"
            if re.search(r"(private|own) (outdoor )?(hot ?tub|jacuzzi)|outdoor (hot ?tub|jacuzzi)|jacuzzi ext", alltxt):
                hot = "private-outdoor" if "outdoor" in alltxt or "ext" in alltxt else "private (location not stated)"
        else:
            hot = "none" if a["type"] != "bnb" else "unknown"
        sauna = "yes" if ("sauna-dampfbad" in feats or "sauna" in alltxt) else "unknown"
        name = html.unescape(a["name"])
        add = html.unescape(a.get("name_add") or "")
        full = name if (not add or add == name) else f"{name} - {add}"
        is_chalet = (f.get("type") == "chalet") or "chalet" in add.lower()
        ptype = "room" if a["type"] == "bnb" else ("chalet" if is_chalet else "apartment")
        board = "breakfast-only" if a["type"] == "bnb" else "self-catered"
        m = re.search(r"for (\d+) (?:persons|people|guests)", desc_en)
        sleeps = f.get("maxAdults") or (m and m.group(1)) or ""
        free = set(av.get("free") or [])
        arr = set(av.get("arrival") or [])
        week = [270320 + i for i in range(7)]
        if av:
            avail = "yes" if (270320 in arr and all(x in free for x in week)) else "no"
        else:
            avail = "unknown"
        mp = a.get("minprice") or {}
        pw = (a.get("price") or {}).get("value") or ""
        other = [x for x in feats if x in ("kamin", "schwimmbad", "spa", "sauna-dampfbad", "gym")]
        omap = {"kamin": "fireplace", "schwimmbad": "pool", "spa": "spa", "sauna-dampfbad": "sauna/steam", "gym": "gym"}
        cid = "regiondentsdumidi-" + slug(full)
        imgs = [i["url"] for i in (det.get("images") or []) if i.get("season") != "summer"][:5] or \
               [i["url"] for i in (det.get("images") or [])][:5]
        notes = [f"openbooking id {aid}; booked via TOMAS {((det.get('bookingUrl') or {}).get('en') or '')}"]
        if pw and a["type"] != "bnb":
            notes.append(f"from CHF {pw}/week (site min price; not 20 Mar specific)")
        if a["type"] == "bnb" and pw:
            notes.append(f"from CHF {pw} per double room/night")
        notes.append("availability from openbooking availabilities endpoint (free nights 20-26 Mar + arrival 20 Mar)")
        notes.append("hot tub: none = not in description or feature list"); notes.append("pass2: exact-week price")
        if f.get("maxChildren"):
            notes.append(f"maxAdults {f.get('maxAdults')}, maxChildren {f.get('maxChildren')}")
        row = dict(chalet_id=cid, chalet_name=full, operator="", village=village, ski_area="Portes du Soleil",
                   country="Switzerland", sleeps_max=sleeps, bedrooms=f.get("bedrooms") or "",
                   property_type=ptype, board=board, hot_tub=hot, sauna=sauna,
                   other_facilities=", ".join(omap[x] for x in other),
                   changeover_day="flexible" if len([x for x in arr if 270301 <= x <= 270331]) > 6 else "unknown",
                   price_basis="whole-chalet" if a["type"] != "bnb" else "",
                   price_currency="CHF" if pw else "", price_type="season-from" if pw else "quote-needed",
                   price_range_low=pw if a["type"] != "bnb" else "", available_20_27_mar=avail,
                   description=desc_en[:230], url=PAGE + aid, listed_on="Région Dents du Midi (openbooking)",
                   found_via=task, image_dir=f"chalets/images/{cid}/", date_checked="2026-10-06",
                   notes="; ".join(notes))
        out.append((row, imgs))
        print(json.dumps({k: row[k] for k in ("chalet_id", "sleeps_max", "bedrooms", "property_type", "hot_tub",
                                              "sauna", "price_range_low", "available_20_27_mar")}), file=sys.stderr)
    if dry:
        return
    for row, imgs in out:
        if imgs:
            r = subprocess.run(["python3", "tools/save_images.py", row["chalet_id"], *imgs], cwd=ROOT,
                               capture_output=True, text=True)
            m = re.findall(r"\d+", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
            row["image_count"] = m[-1] if m else ""
        subprocess.run(["python3", "tools/append_row.py", f"chalets/raw/{task}.csv", json.dumps(row)], cwd=ROOT)


main()
