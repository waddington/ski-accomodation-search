#!/usr/bin/env python3
"""Compare scraper JSON lines against rows already collected (chalets_all.csv + chalets/raw/*.csv).

    python3 tools/scrapers/allchalets.py les-menuires > /tmp/x.jsonl
    python3 tools/scrapers/validate.py /tmp/x.jsonl [--village "Les Menuires"] [--source-url allchalets.com] [-v]

Matches by url (then by normalised name + village). Prints: scraped / matched / new / known-but-not-scraped
(for --source-url host), and per-field agreement over matched rows where both sides are non-blank.
"""
import csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, slug
from match import Known, nurl as _nurl

FIELDS = ["sleeps_max", "bedrooms", "board", "hot_tub", "has_hot_tub", "sauna", "has_sauna", "changeover_day",
          "price_week_20_27_mar_2027", "price_currency", "price_range_low", "price_range_high", "available_20_27_mar"]


PRICE_FIELDS = {"changeover_day", "price_week_20_27_mar_2027", "price_currency", "price_range_low", "price_range_high", "available_20_27_mar"}


def nurl(u):
    return _nurl(u)  # match.nurl keeps listing-id query params (Orchestra ?s_pid=N)


def known_rows():
    """chalet_id -> merged row (first non-blank wins), like find_chalet.py."""
    rows = {}
    files = [ROOT / "chalets/chalets_all.csv"] + sorted((ROOT / "chalets/raw").glob("*.csv"))
    for p in files:
        if p.name.endswith(("HEADER.csv", ".issues.csv", ".sites.csv", ".changes.csv", ".newsites.csv")):
            continue
        try:
            for r in csv.DictReader(p.open(newline="")):
                cid = r.get("chalet_id")
                if not cid:
                    continue
                m = rows.setdefault(cid, {})
                for k, v in r.items():
                    if k and v and not m.get(k):
                        m[k] = v
                    elif k == "url" and v and v not in m.get("_urls", ""):
                        pass
                m.setdefault("_urls", set()).add(nurl(r.get("url")))
        except Exception:
            pass
    return rows


def index(rows):
    by_url, by_name = {}, {}
    for cid, r in rows.items():
        for u in r.get("_urls", ()):
            if u:
                by_url.setdefault(u, cid)
        by_name.setdefault((slug(r.get("chalet_name")), slug(r.get("village"))), cid)
    return by_url, by_name


def norm(f, v):
    v = (v or "").strip() if isinstance(v, str) else ("" if v is None else str(v))
    if f.startswith("price") and f != "price_currency" and v:
        try:
            return str(round(float(v)))
        except ValueError:
            return v
    if f in ("sleeps_max", "bedrooms") and v:
        try:
            return str(int(float(v)))
        except ValueError:
            return v
    return v.lower()


def has_ht(v):
    v = (v or "").lower()
    if not v or v == "unknown":
        return ""
    return "no" if v == "none" else "yes"


def main():
    a = sys.argv[1:]
    verbose = "-v" in a
    village = a[a.index("--village") + 1] if "--village" in a else None
    host = a[a.index("--source-url") + 1] if "--source-url" in a else None
    scraped = [json.loads(l) for l in open(a[0]) if l.strip().startswith("{")]
    K = Known()
    rows = K.rows
    matched, new, amb = [], [], 0
    for s in scraped:
        cid, how, cands = K.match(s)
        amb += how == "ambiguous"
        (matched if cid else new).append((cid, s))
    print(f"scraped {len(scraped)} | matched existing {len(matched)} | new {len(new)} (ambiguous name matches {amb})")
    if host:
        got = {nurl(s.get("url")) for s in scraped}
        missing = [(cid, r) for cid, r in rows.items()
                   if any(host in u for u in r.get("_urls", ()))
                   and (not village or slug(village) in slug(r.get("village")))
                   and not (r["_urls"] & got)]
        print(f"known rows with {host} url{' in ' + village if village else ''} not in scrape: {len(missing)}")
        for cid, r in missing:
            print(f"   MISSING {cid} {sorted(r['_urls'])[:1]}")
    agree = {f: [0, 0] for f in FIELDS}
    diffs = []
    for cid, s in matched:
        k = rows[cid]
        host = lambda u: re.sub(r"^https://([^/]+).*", r"\1", nurl(u))
        same_src = bool(k.get("url")) and host(k.get("url")) == host(s.get("url"))
        for f in FIELDS:
            if f in PRICE_FIELDS and not same_src:
                continue  # prices/availability only comparable against rows from the same source
            if f == "has_sauna":
                a1, b1 = ("yes" if s.get("sauna") == "yes" else "not-yes"), ("yes" if k.get("sauna") == "yes" else "not-yes")
                if not k.get("sauna") or not s.get("sauna"):
                    continue
            elif f == "has_hot_tub":
                a1, b1 = has_ht(s.get("hot_tub")), has_ht(k.get("hot_tub"))
            if f not in ("has_sauna", "has_hot_tub"):
                a1, b1 = norm(f, s.get(f)), norm(f, k.get(f))
            if f == "available_20_27_mar" and "unknown" in (a1, b1):
                continue
            if f == "hot_tub" and "unknown" in (a1, b1):
                continue
            if a1 == "" or b1 == "":
                continue
            agree[f][1] += 1
            if a1 == b1:
                agree[f][0] += 1
            else:
                diffs.append(f"{cid}: {f} scraped={a1!r} known={b1!r}")
    print("field | agree/compared | %")
    for f, (ok, n) in agree.items():
        print(f"{f} | {ok}/{n} | {round(100 * ok / n) if n else '-'}")
    if verbose:
        print("\n".join(diffs))
        for _, s in new:
            print(f"   NEW {s.get('chalet_name')} | {s.get('village')} | {s.get('url')}")


if __name__ == "__main__":
    main()
