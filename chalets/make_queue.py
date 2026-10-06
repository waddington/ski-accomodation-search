#!/usr/bin/env python3
"""Build / refresh the search work queue: chalets/search_queue.csv.

    python3 chalets/make_queue.py

Re-runnable: existing tasks keep their status/progress; new tasks are appended.
Tasks run strictly one at a time, in `order`.

Phases
  1 enrich   chalets passing the filters but with unknown key fields
  2 site     chalet companies and package/agent sites (whole site, all villages)
  3 discover directories, to find operators missing from sites.csv
  4 village  every village in resorts_filtered.csv (village-searchable aggregators,
             official resort booking site, resort guide site, local independents)
  5 fallback self-catered / hotel / rental platforms — status 'deferred' until needed
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "chalets/search_queue.csv"
FIELDS = ["order", "task_id", "phase", "type", "target", "url", "detail", "status",
          "started", "finished", "collector_file", "rows_written", "new_chalets", "issues", "notes"]

# Fully covered by the pilot.
PILOT_SITES = {"Icebreaker Chalets", "White Horizon Chalets", "Chalet Chardons", "Alpine365",
               "Ice and Fire", "SkiAffinity", "La Source Ski & Adventure"}
PILOT_VILLAGES = {"Les Coches", "Montchavin", "Tignes Les Brévières", "Tignes Les Boisses"}

# Searched inside every village task rather than as a whole-site task.
VILLAGE_AGGREGATORS = {"allChalets", "ChaletFinder", "Chalets Direct", "See Ski network (seetignes/seemorzine/seeverbier/seealpedhuez)"}

# General rental / residence platforms: only if no catered chalet fits.
FALLBACK_PLATFORMS = {"Booking.com", "Airbnb", "Vrbo", "Holidu", "Interhome", "SnowTrex", "Sunweb",
                      "Travelski", "Ski Planet"}

PRICEY = {"luxury", "high", "mid-luxury"}


DOLOMITI_VILLAGES = {"Arabba", "Corvara", "Colfosco", "Selva / Wolkenstein", "Canazei", "Campitello di Fassa",
                     "Ortisei", "Santa Cristina", "La Villa", "San Cassiano", "Pedraces", "Livinallongo"}


def slug(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-").replace("--", "-")


def main():
    existing = {}
    if QUEUE.exists():
        existing = {r["task_id"]: r for r in csv.DictReader(QUEUE.open())}

    tasks = []

    # 1 enrich — only once every task that found the chalet has finished
    running = {r["task_id"] for r in existing.values() if r["status"] in ("in_progress", "partial")}
    filt = ROOT / "chalets/chalets_filtered.csv"
    if filt.exists():
        # Same priority as the search: France first, Dolomiti Superski last; known-catered before unknowns.
        fits = sorted(csv.DictReader(filt.open()), key=lambda r: (
            "Dolomiti" in r["ski_area"] or r["village"] in DOLOMITI_VILLAGES, r["country"] != "France",
            r["is_catered"] != "yes", r["chalet_name"]))
        for r in fits:
            found_by = {x.strip() for x in r["found_via"].split(";")}
            if r["missing_fields"] and not (found_by & running):
                tasks.append(dict(phase="1", type="enrich", target=r["chalet_name"], url=r["url"],
                                  task_id=f"enrich-{r['chalet_id']}",
                                  detail=f"{r['chalet_id']} | {r['village']} | missing: {r['missing_fields']}"))

        # pass 2: every chalet whose collector deferred slow work ("pass2:" in notes), after the fits
        allc = ROOT / "chalets/chalets_all.csv"
        have = {t["task_id"] for t in tasks}
        for r in csv.DictReader(allc.open()):
            found_by = {x.strip() for x in r["found_via"].split(";")}
            tid = f"enrich-{r['chalet_id']}"
            if "pass2:" in r["notes"] and tid not in have and not (found_by & running):
                tasks.append(dict(phase="1", type="enrich", target=r["chalet_name"], url=r["url"], task_id=tid,
                                  detail=f"{r['chalet_id']} | {r['village']} | pass2 (deferred depth) | missing: {r['missing_fields']}"))

    sites = [r for r in csv.DictReader((ROOT / "sites/sites.csv").open()) if r["category"] != "closed"]

    # 2 site: companies + package/agent sites, in-budget first
    site_tasks = []
    for r in sites:
        n = r["name"]
        if n in PILOT_SITES or n in VILLAGE_AGGREGATORS or n in FALLBACK_PLATFORMS:
            continue
        if r["tiers"] == "discovery" or r["category"] == "fallback":
            continue
        if r["category"] in ("company", "broad"):
            site_tasks.append((r["price_level"] in PRICEY, r))
    for _, r in sorted(site_tasks, key=lambda x: x[0]):
        tasks.append(dict(phase="2", type="site", target=r["name"], url=r["url"], task_id=f"site-{slug(r['name'])}",
                          detail=f"{r['area']} | {r['price_level']}"))

    # 3 discover
    for r in sites:
        if r["tiers"] == "discovery" and r["name"] not in VILLAGE_AGGREGATORS:
            tasks.append(dict(phase="3", type="discover", target=r["name"], url=r["url"],
                              task_id=f"discover-{slug(r['name'])}", detail="find operators not in sites.csv"))

    # 4 village: A then B then C; satellite-value villages first within a grade
    villages = list(csv.DictReader((ROOT / "resorts/resorts_filtered.csv").open()))
    # Dolomiti Superski villages go after every other village (user, 2026-10-06).
    DEPRIORITISED = ("Dolomiti Superski",)
    # France first (user, 2026-10-06), then abroad; Dolomiti last of all.
    villages.sort(key=lambda v: (any(d in v["ski_area"] for d in DEPRIORITISED), v["country"] != "France", v["calibre"],
                                 not v["satellite_value"].lower().startswith("yes"),
                                 v["country"] != "France", v["ski_area"], v["village"]))
    for v in villages:
        if v["village"] in PILOT_VILLAGES:
            continue
        tasks.append(dict(phase="4", type="village", target=v["village"], url="",
                          task_id=f"village-{slug(v['country'])}-{slug(v['village'])}",
                          detail=f"{v['country']} | {v['ski_area']} | calibre {v['calibre']}"))

    # 5 fallback (deferred)
    for r in sites:
        if r["name"] in FALLBACK_PLATFORMS or r["category"] == "fallback":
            tasks.append(dict(phase="5", type="fallback", target=r["name"], url=r["url"],
                              task_id=f"fallback-{slug(r['name'])}", detail=r["area"]))

    out = []
    for i, t in enumerate(tasks, 1):
        prev = existing.pop(t["task_id"], None)
        row = {f: "" for f in FIELDS} | t | {"order": str(i)}
        if prev:
            for f in ("status", "started", "finished", "collector_file", "rows_written", "new_chalets", "issues", "notes"):
                row[f] = prev.get(f, "")
        if not row["status"]:
            row["status"] = "deferred" if t["phase"] == "5" else "pending"
        out.append(row)
    for prev in existing.values():  # tasks no longer generated
        if prev["status"] == "pending":
            continue  # never started: drop (it will be regenerated if it applies again)
        if "[no longer in plan]" not in prev.get("notes", ""):
            prev["notes"] = (prev.get("notes", "") + " [no longer in plan]").strip()
        out.append(prev)

    with QUEUE.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print(f"{len(out)} tasks:", dict(Counter((r['phase'], r['type']) for r in out)))
    print("status:", dict(Counter(r["status"] for r in out)))


if __name__ == "__main__":
    main()
