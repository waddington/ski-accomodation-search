#!/usr/bin/env python3
"""Filter the raw resort list into a working shortlist.

    python3 filter_resorts.py

Reads   resorts_raw.csv      (source data, never edited by this script)
Writes  resorts_filtered.csv (villages that pass every rule)
        resorts_removed.csv  (villages dropped, with the rule that dropped them)

To add a filtering round, write a rule function below and add it to RULES.
A rule takes a row and returns a reason string to drop it, or None to keep it.

Manual overrides: put "keep" or "drop" in the `status` column of
resorts_raw.csv to force a village in or out regardless of the rules.
"""
import csv
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "resorts_raw.csv"
OUT = HERE / "resorts_filtered.csv"
REMOVED = HERE / "resorts_removed.csv"

MIN_VILLAGE_ALT_M = 950
MIN_VERTICAL_DROP_M = 1000

# price_level values to drop. Add "mid-premium" to be stricter
# (that would also drop Val Thorens, Val d'Isère, Tignes Le Lac, Alpe d'Huez).
PRICE_LEVELS_TO_DROP = {"premium"}

# Low villages kept anyway because they are major towns, worth staying in
# despite the altitude (lifts from town, restaurants, apres, transport).
MAJOR_TOWNS = {
    "Kitzbühel",
    "Mayrhofen",
    "Bourg-St-Maurice",
    "St-Gervais-les-Bains",
}

# Low villages kept anyway because they sit in a known snow pocket.
SNOW_POCKETS = {
    "Samoëns",             # Grand Massif: first big area hit by Atlantic storms
    "Morillon (village)",  # Grand Massif
    "Sixt-Fer-à-Cheval",   # Grand Massif (note: lifts close ~7 March)
    "Fieberbrunn",         # the Tyrol "Schneeloch" (snow hole)
}


def first_int(value):
    m = re.match(r"\d+", value.replace(",", ""))
    return int(m.group()) if m else None


def altitude(row):
    return first_int(row["village_alt_m"])


def vertical_drop(row):
    """Ski area's lift-served vertical; falls back to top minus bottom altitude."""
    drop = first_int(row["vertical_drop_m"])
    if drop is None:
        top, bottom = first_int(row["top_alt_m"]), first_int(row["bottom_alt_m"])
        if top and bottom:
            drop = top - bottom
    return drop


def has_satellite_value(row):
    return row["satellite_value"].strip().lower().startswith(("yes", "partial"))


# --- rules -------------------------------------------------------------------

def drop_c_grade_without_satellite_value(row):
    if row["calibre"] == "C" and not has_satellite_value(row):
        return "C grade with no satellite value"


def drop_low_villages(row):
    alt = altitude(row)
    if alt is None or alt >= MIN_VILLAGE_ALT_M:
        return None
    if row["village"] in MAJOR_TOWNS or row["village"] in SNOW_POCKETS:
        return None
    return f"village below {MIN_VILLAGE_ALT_M} m ({alt} m), not a major town or snow pocket"


def drop_small_vertical(row):
    drop = vertical_drop(row)
    if drop is None:
        return None  # unknown: keep rather than guess
    if drop < MIN_VERTICAL_DROP_M:
        return f"vertical drop below {MIN_VERTICAL_DROP_M} m ({drop} m)"


def drop_premium(row):
    level = row["price_level"].strip().lower()
    if level in PRICE_LEVELS_TO_DROP:
        return f"price level {level}"


RULES = [
    drop_c_grade_without_satellite_value,
    drop_low_villages,
    drop_small_vertical,
    drop_premium,
]

# -----------------------------------------------------------------------------


def main():
    with RAW.open(newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    for name in MAJOR_TOWNS | SNOW_POCKETS:
        if not any(r["village"] == name for r in rows):
            print(f"warning: exception '{name}' matches no village in {RAW.name}")

    kept, removed = [], []
    for row in rows:
        override = row.get("status", "").strip().lower()
        if override == "keep":
            kept.append(row)
            continue
        if override == "drop":
            removed.append({**row, "removed_by": "manual: status=drop"})
            continue
        reason = next((r for rule in RULES if (r := rule(row))), None)
        if reason:
            removed.append({**row, "removed_by": reason})
        else:
            kept.append(row)

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(kept)
    with REMOVED.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["removed_by"])
        w.writeheader()
        w.writerows(removed)

    print(f"{len(rows)} villages in, {len(kept)} kept, {len(removed)} removed")
    for reason, n in Counter(
        re.sub(r" \(\d+ m\)", "", r["removed_by"]) for r in removed
    ).most_common():
        print(f"  {n:3}  {reason}")
    print("kept by country:", dict(Counter(r["country"] for r in kept)))
    print("kept by calibre:", dict(sorted(Counter(r["calibre"] for r in kept).items())))


if __name__ == "__main__":
    main()
