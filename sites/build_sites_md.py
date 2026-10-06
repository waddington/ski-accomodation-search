#!/usr/bin/env python3
"""Rebuild the site markdown lists from sites.csv.

    python3 build_sites_md.py

sites.csv is the source of truth: add or edit rows there, then re-run this.
Writes broad-search-sites.md, chalet-companies.md and fallback-accommodation.md.
"""
import csv
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "sites.csv"

# Price levels sorted last (over the £750pp budget).
PRICEY = {"luxury", "high"}

INTROS = {
    "broad": (
        "Broad search / aggregator sites",
        "Sites that list chalets from many operators or owners. Useful for every tier.\n\n"
        "Best starting points: **Sno** (hot tub, budget and group-size filters), "
        "**allChalets** (catered and jacuzzi filters), **Ski Line**, **Iglu Ski**, "
        "**ChaletFinder**, **Heidi**, **Erna Low**. Discovery sites at the bottom are "
        "directories for finding more small operators, not booking engines.",
    ),
    "company": (
        "Specialist chalet companies",
        "Operators that run their own catered chalets (tiers 1–2).\n\n"
        "Best fits for £750pp + catered + hot tub in a linked area: **White Horizon**, "
        "**Chalet Chardons**, **Tignes.co.uk** (Tignes); **Icebreaker**, **Alpine365**, "
        "**Ice and Fire** (Les Coches/Montchavin); **Treeline**, **Riders Refuge** (Morzine); "
        "**Ski Blanc**, **The Chalet Company** (Méribel); **Skialot** (Châtel); "
        "**Wens Chalets** (Austria); **Ski Beat**, **Alpine Elements**, **Club Alpine**, "
        "**Mountain Heaven**.\n\n"
        "Outside France there are few budget catered operators: mainly Inghams, Crystal, "
        "Skiworld, Snowscape and Wens Chalets.",
    ),
    "fallback": (
        "Fallback accommodation sites",
        "Self-catered chalets, residences, club hotels and hotels (tiers 2–4 in the "
        "[search plan](../search-plan.md)). Used only if no catered chalet fits. "
        "General platforms (Booking.com, Airbnb, Vrbo, Holidu, Interhome) are in "
        "[broad-search-sites.md](broad-search-sites.md).",
    ),
}
FILES = {
    "broad": "broad-search-sites.md",
    "company": "chalet-companies.md",
    "fallback": "fallback-accommodation.md",
}


def cell(text):
    return (text or "").replace("|", "/").replace("\n", " ")


def sort_key(row):
    return (
        row["tiers"] == "discovery",
        row["price_level"] in PRICEY,
        row["added"] != "pass 1",
    )


def table(rows):
    lines = [
        "| # | Site | Tiers | Area | Catered | Hot tubs | Price | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        name = f"[{cell(r['name'])}]({r['url']})" if r["url"] else cell(r["name"])
        notes = cell(r["notes"])
        if r["access_notes"]:
            notes += f" _Access: {cell(r['access_notes'])}_"
        lines.append(
            f"| {i} | {name} | {cell(r['tiers'])} | {cell(r['area'])} | {cell(r['catered'])} "
            f"| {cell(r['hot_tubs'])} | {cell(r['price_level'])} | {notes} |"
        )
    return "\n".join(lines)


def main():
    rows = list(csv.DictReader(CSV.open(newline="")))
    closed = [r for r in rows if r["category"] == "closed"]

    for cat, filename in FILES.items():
        title, intro = INTROS[cat]
        these = sorted((r for r in rows if r["category"] == cat), key=sort_key)
        parts = [
            f"# {title}",
            f"_Generated from [sites.csv](sites.csv) by build_sites_md.py · {len(these)} sites_",
            intro,
            "Tiers: 1 catered chalet · 2 chalet hotel/club · 3 self-catered chalet · "
            "4 apartment/hotel · discovery = directory. Sorted: in-budget first, "
            "luxury/high next, directories last.",
            table(these),
        ]
        if cat == "company":
            parts.append("## Closed, merged or untraceable — don't rely on these")
            parts.append("\n".join(f"- **{r['name']}** — {cell(r['notes'])}" for r in closed))
        (HERE / filename).write_text("\n\n".join(parts) + "\n")
        print(f"{filename}: {len(these)} rows")
    print(f"closed: {len(closed)}")


if __name__ == "__main__":
    main()
