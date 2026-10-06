#!/usr/bin/env python3
"""Merge every collector CSV into one chalet list, add derived flags, filter, and pivot.

    python3 chalets/build_chalets.py

Reads   raw/*.csv              (one file per collector; HEADER.csv is skipped)
Writes  chalets_all.csv        every chalet, de-duplicated, with derived columns
        chalets_filtered.csv   chalets passing RULES (edit them below)
        chalets_removed.csv    chalets dropped, with the rule that dropped them
        by_resort.csv          one row per village: counts + chalet names
        by_site.csv            one row per (site, chalet): which site lists what
        access_issues.csv      everything collectors got stuck on (from raw/*.issues.csv)
        site_yield.csv         per collector and site: listings found, how many were new (raw/*.sites.csv)

Corrections: corrections.csv (chalet_id,field,value,note) sets a field after merging —
use it to remove or fix a value a collector got wrong (merging can only fill gaps).

Manual overrides: a `status` of keep/drop in overrides.csv (chalet_id,status,note)
forces a chalet in or out regardless of the rules.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw"
OVERRIDES = HERE / "overrides.csv"

GROUP_MIN, GROUP_MAX = 8, 10
BUDGET_PP_GBP = 750  # accommodation + catering only (user, 2026-10-06)
# Package prices include travel: subtract an assumed allowance before comparing with the budget.
FLIGHTS_TRANSFERS_ALLOWANCE_GBP = 250  # return flight + resort transfer, per person (assumption)
TRANSFERS_ONLY_ALLOWANCE_GBP = 40      # resort transfer only, per person (assumption)
# Rough conversion for comparing prices; refresh before booking.
TO_GBP = {"GBP": 1.0, "EUR": 0.86, "CHF": 0.93}


# --- derived columns ---------------------------------------------------------

def num(v):
    m = re.search(r"\d[\d,]*\.?\d*", v or "")
    return float(m.group().replace(",", "")) if m else None


def yn(b):
    return "" if b is None else ("yes" if b else "no")


def price_pp_gbp(row):
    """Per-person price in GBP for this group: exact week if known, else the top of the
    published 2026/27 range (late March is usually not the cheapest week)."""
    price = num(row["price_week_20_27_mar_2027"]) or num(row["price_range_high"]) or num(row["price_range_low"])
    rate = TO_GBP.get(row["price_currency"].strip().upper())
    if price is None or rate is None:
        return None
    if re.search(r"per (?:person )?(?:per )?night|/night|par nuit", (row["price_includes"] + " " + row["notes"]).lower()) \
            and not row["price_week_20_27_mar_2027"].strip():
        price *= 7  # nightly rate -> week
    if row["price_basis"].strip() == "whole-chalet":
        sleeps = num(row["sleeps_max"])
        if not sleeps:
            return None
        price /= min(max(sleeps, GROUP_MIN), GROUP_MAX)
    return round(price * rate)


def infer_type(row):
    """property_type if the collector gave one, else inferred from name/board."""
    pt = row.get("property_type", "").strip().lower()
    if pt:
        return pt
    name, board = row["chalet_name"].lower(), row["board"].strip().lower()
    if board == "chalet-hotel" or "chalet hotel" in name or "chalet-hotel" in name:
        return "chalet-hotel"
    if re.search(r"\bhotel\b|\bhôtel\b|albergo|pension|gasthof|sporthotel|garni", name):
        return "hotel"
    if re.search(r"\bapartment|\bappartement|\bapt\b|\bstudio\b|residence|résidence|penthouse|\bflat\b|duplex", name):
        return "apartment"
    if " + " in name or "combined" in row.get("notes", "").lower()[:80]:
        return "combined-booking" if row.get("combines") else "chalet"
    return "chalet"


def travel_included(text, word):
    """Is `word` (flight/transfer) included in a price_includes text? Reads negations in context:
    'Without Flights', 'no flights/transfers', 'excludes … transfers', 'transfers … extra', 'at supplement'."""
    for clause in text.lower().split(";"):
        if word not in clause:
            continue
        items = clause.split(",")
        for i, item in enumerate(items):
            if word not in item:
                continue
            if re.search(r"without|not incl|\bno\b|supplement", item):
                return False
            if re.search(r"exclud", ",".join(items[:i + 1])):
                return False
            if re.search(r"\bextra\b|not included", clause[clause.index(word):]):
                return False
            return True
    return False


def derive(row):
    hot_tub = row["hot_tub"].strip().lower()
    sleeps_max = num(row["sleeps_max"])
    sleeps_min = num(row["sleeps_min"]) or sleeps_max
    pp = price_pp_gbp(row)
    row["has_hot_tub"] = yn(None if hot_tub in ("", "unknown") else hot_tub != "none")
    row["has_private_hot_tub"] = yn(None if hot_tub in ("", "unknown", "yes-type-unknown") else hot_tub.startswith("private"))
    row["has_sauna"] = yn(None if row["sauna"] in ("", "unknown") else row["sauna"] == "yes")
    row["is_catered"] = yn(None if not row["board"] else row["board"] in ("catered", "half-board", "catered-or-self", "chalet-hotel"))
    row["type"] = infer_type(row)
    if row["type"] in ("hotel", "chalet-hotel"):
        # Hotels/chalet hotels are booked by the room: total capacity only needs to fit the group.
        # ...unless it only takes groups bigger than ours (e.g. a group house with a 40-person minimum).
        row["sleeps_8_to_10"] = yn(None if sleeps_max is None else
                                   sleeps_max >= GROUP_MIN and (num(row["sleeps_min"]) or 0) <= GROUP_MAX)
    else:
        row["sleeps_8_to_10"] = yn(None if sleeps_max is None else sleeps_max >= GROUP_MIN and sleeps_min <= GROUP_MAX)
    row["has_exact_week_price"] = yn(bool(row["price_week_20_27_mar_2027"].strip()))
    row["price_pp_gbp_est"] = "" if pp is None else str(pp)
    inc = row["price_includes"]
    travel = (FLIGHTS_TRANSFERS_ALLOWANCE_GBP if travel_included(inc, "flight")
              else TRANSFERS_ONLY_ALLOWANCE_GBP if travel_included(inc, "transfer")
              else 0)
    accom = None if pp is None else max(pp - travel, 0)
    row["price_pp_gbp_accom_est"] = "" if accom is None else str(accom)
    row["under_budget"] = yn(None if accom is None else accom <= BUDGET_PP_GBP)
    row["missing_fields"] = missing_fields(row)
    return row


# Key fields reported in missing_fields when blank/unknown.
KEY_FIELDS = ["sleeps_max", "bedrooms", "board", "hot_tub", "price_week_20_27_mar_2027",
              "price_range_low", "price_currency", "available_20_27_mar", "url", "image_count"]


def missing_fields(row):
    gaps = [k for k in KEY_FIELDS if row.get(k, "").strip() in ("", "unknown", "0")]
    return "; ".join(gaps)


DERIVED = ["type", "missing_fields", "has_hot_tub", "has_private_hot_tub", "has_sauna", "is_catered", "sleeps_8_to_10",
           "has_exact_week_price", "price_pp_gbp_est", "price_pp_gbp_accom_est", "under_budget"]


# --- rules (return a reason to drop, or None) --------------------------------
# "unknown" passes every rule: we only drop on evidence.

def drop_no_hot_tub(row):
    if row["has_hot_tub"] == "no":
        return "no hot tub"


def drop_not_catered(row):
    if row["is_catered"] == "no":
        return "not catered"


def drop_wrong_size(row):
    if row["sleeps_8_to_10"] == "no":
        span = "-".join(v for v in (row["sleeps_min"], row["sleeps_max"]) if v)
        return f"sleeps {span}, not {GROUP_MIN}-{GROUP_MAX}"


def drop_over_budget(row):
    if row["under_budget"] == "no":
        return f"~£{row['price_pp_gbp_accom_est']}pp (accommodation) over £{BUDGET_PP_GBP}"


def drop_unavailable(row):
    if row["available_20_27_mar"] == "no":
        return "not available 20-27 Mar"


# drop_no_hot_tub is off: hot tub became a nice-to-have on 2026-10-05 (still shown in has_hot_tub).
RULES = [drop_unavailable, drop_not_catered, drop_wrong_size, drop_over_budget]


# -----------------------------------------------------------------------------

def merge(rows):
    """One row per chalet_id: first non-blank (and not 'unknown') value wins; listed_on/found_via
    are unioned. Callers pass enrichment rows first so their findings override collector gaps."""
    out = {}
    for r in rows:
        r = {k: (v or "") for k, v in r.items() if k is not None}
        cur = out.get(r["chalet_id"])
        if cur is None:
            out[r["chalet_id"]] = dict(r)
            continue
        for k, v in r.items():
            if k in ("listed_on", "found_via"):
                parts = {p.strip() for p in (cur[k] + ";" + v).split(";") if p.strip()}
                cur[k] = "; ".join(sorted(parts))
            elif cur.get(k, "") in ("", "unknown") and v not in ("", "unknown"):
                cur[k] = v
    return list(out.values())


def write(path, rows, fields):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    fields = next(csv.reader((RAW / "HEADER.csv").open()))
    raw = []
    # enrich-*.csv first: its values win over the original collector's.
    for p in sorted(RAW.glob("*.csv"), key=lambda p: (not p.name.startswith("enrich"), p.name)):
        if p.name.endswith(("HEADER.csv", ".issues.csv", ".sites.csv", ".changes.csv", ".newsites.csv")):
            continue
        raw += [r for r in csv.DictReader(p.open(newline="")) if r.get("chalet_id")]
    merged = merge(raw)
    corr = HERE / "corrections.csv"
    if corr.exists():
        by_id = {r["chalet_id"]: r for r in merged}
        for c in csv.DictReader(corr.open(newline="")):
            if c["chalet_id"] in by_id:
                by_id[c["chalet_id"]][c["field"]] = c["value"]
    chalets = [derive({**{f: "" for f in fields}, **r}) for r in merged]
    chalets.sort(key=lambda r: (r["country"], r["ski_area"], r["village"], r["chalet_name"]))

    overrides = {}
    if OVERRIDES.exists():
        overrides = {r["chalet_id"]: r["status"].strip().lower() for r in csv.DictReader(OVERRIDES.open())}

    kept, removed = [], []
    for r in chalets:
        o = overrides.get(r["chalet_id"])
        reason = "manual: drop" if o == "drop" else None if o == "keep" else "; ".join(
            x for rule in RULES if (x := rule(r)))
        r["removed_by"] = reason or ""
        (removed if reason else kept).append(r)

    all_fields = fields + DERIVED
    write(HERE / "chalets_all.csv", chalets, all_fields + ["removed_by"])
    write(HERE / "chalets_filtered.csv", kept, all_fields)
    write(HERE / "chalets_removed.csv", removed, all_fields + ["removed_by"])

    by_village = defaultdict(list)
    for r in chalets:
        by_village[(r["country"], r["ski_area"], r["village"])].append(r)
    kept_ids = {r["chalet_id"] for r in kept}
    with (HERE / "by_resort.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["country", "ski_area", "village", "chalets", "passing_filters", "with_hot_tub",
                    "catered", "sleeps_8_to_10", "passing_chalet_names"])
        for (c, a, v), rs in sorted(by_village.items()):
            w.writerow([c, a, v, len(rs), sum(r["chalet_id"] in kept_ids for r in rs),
                        sum(r["has_hot_tub"] == "yes" for r in rs), sum(r["is_catered"] == "yes" for r in rs),
                        sum(r["sleeps_8_to_10"] == "yes" for r in rs),
                        "; ".join(r["chalet_name"] for r in rs if r["chalet_id"] in kept_ids)])

    with (HERE / "by_site.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["site", "chalet_id", "chalet_name", "operator", "village", "passes_filters", "url"])
        for r in chalets:
            for site in sorted({s.strip() for s in r["listed_on"].split(";") if s.strip()} or {r["operator"]}):
                w.writerow([site, r["chalet_id"], r["chalet_name"], r["operator"], r["village"],
                            yn(r["chalet_id"] in kept_ids), r["url"]])

    issues = []
    for p in sorted(RAW.glob("*.issues.csv")):
        issues += list(csv.DictReader(p.open(newline="")))
    issue_fields = next(csv.reader((RAW / "ISSUES_HEADER.csv").open()))
    write(HERE / "access_issues.csv", issues, issue_fields)

    yields = []
    for p in sorted(RAW.glob("*.sites.csv")):
        yields += list(csv.DictReader(p.open(newline="")))
    if yields:
        write(HERE / "site_yield.csv", yields, list(yields[0].keys()))

    print(f"{len(issues)} access issues logged; "
          f"{sum(bool(r['missing_fields']) for r in chalets)} chalets have missing key fields")
    print(f"{len(raw)} raw rows -> {len(chalets)} chalets; {len(kept)} pass filters, {len(removed)} removed")
    from collections import Counter
    for reason, n in Counter(re.sub(r"[~£\d.-]+", "#", x) for r in removed
                             for x in r["removed_by"].split("; ")).most_common():
        print(f"  {n:3}  {reason}")


if __name__ == "__main__":
    main()
