#!/usr/bin/env python3
"""Run a scraper and append its rows to chalets/raw/<task_id>.csv (one command per source per village).

    python3 tools/scrapers/ingest.py <task_id> <scraper> <scraper args...> [--ingest-dry-run] [--no-images]
    e.g.
    python3 tools/scrapers/ingest.py village-france-les-menuires allchalets les-menuires
    python3 tools/scrapers/ingest.py village-france-tignes skiline "Tignes" --chalets-only
    python3 tools/scrapers/ingest.py village-france-tignes-les-brevieres ingenie tignes --quarter IBREVIERES,IVILLARET
    python3 tools/scrapers/ingest.py <task> <scraper> --from-jsonl saved.jsonl   # reuse a saved scraper run

For each scraped row:
  * already known (same url, or same name in the same ski area; tools/scrapers/match.py): writes a row with the
    existing chalet_id, listed_on=<source>, found_via=<task_id>, plus only the fields that are blank in the known
    row; the source's own price/availability goes into notes (prices from different sites are not mixed);
  * new: chalet_id = <operator-slug or source>-<name-slug> (made unique), all fields, images via
    tools/save_images.py (up to 5) -> image_count / image_dir;
  * rows already written by this task with the same chalet_id + listed_on are skipped (safe to re-run).
--ingest-dry-run prints what would be written (no CSV writes, no image downloads). Prints a summary at the end.
--override (repair pass, use task id enrich-fix-<source>-<village>): for known rows whose url is on the scraper's site,
  also writes the scraper's non-blank structural fields (OVERRIDE_FIELDS; village only when the scraper derived a
  specific village or the old one is blank/escaped/the resort crumb; chalet_name only over placeholders; url only over a
  url shared by several chalets) - never prices, never blanks, never fields set in corrections.csv / enrich*.csv or
  already corrected by an appended row.
Scraper options such as --limit / --dry-run are passed through to the scraper.
"""
import csv, json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, COLUMNS, slug, TODAY
from match import Known

HERE = Path(__file__).resolve().parent
PREFIX = {"allchalets": "allchalets", "skiline": "skiline", "igluski": "iglu", "sno": "sno",
          "ingenie-tignes": "tignesreservation", "ingenie-lesmenuires": "lesmenuires",
          "ingenie-serrechevalier": "serrechevalier-reservation", "les3vallees": "les3vallees",
          "ingenie-valdisere": "ingenie-valdisere", "simplyvaldisere": "simplyvaldisere",
          "orchestra-combloux": "combloux", "msem-stgervais": "msemstg"}
SOURCE_PRICE = ["price_week_20_27_mar_2027", "price_basis", "price_currency", "price_type", "price_range_low",
                "price_range_high", "price_includes", "available_20_27_mar", "changeover_day"]


OVERRIDE_FIELDS = ["village", "sleeps_min", "sleeps_max", "bedrooms", "bathrooms", "property_type", "board",
                   "catering_detail", "hot_tub", "sauna", "other_facilities", "changeover_day", "description"]
PLACEHOLDER_NAME = re.compile(r"^(?:(?:chalet|apartment|studio)\s+)?details?$|^(?:chalet|apartment|studio|residence|hotel)\s+\d+$", re.I)
HT_RANK = {"private-outdoor": 3, "private-indoor": 3, "shared": 3, "private (location not stated)": 2, "yes-type-unknown": 1}


def less_specific(k, old, new):
    """True when the scraper value only says less than the existing one (collectors often refine from photos/other sites)."""
    if k == "hot_tub":
        return old in HT_RANK and new in HT_RANK and HT_RANK[new] < HT_RANK[old] and not (old == "shared" and new.startswith("private"))
    if k == "board":
        return new == "catered-or-self" and old in ("catered", "self-catered", "half-board", "breakfast-only")
    return False


def resort_villages():
    try:
        return {slug(r.get("village")) for r in csv.DictReader((ROOT / "resorts/resorts_raw.csv").open(newline=""))}
    except FileNotFoundError:
        return set()


KEEP_VALUES = {"property_type": ("combined-booking", "chalet-hotel", "hotel"), "board": ("chalet-hotel",)}


def protected_fields():
    """-> (protected, deliberate).
    protected: chalet_id -> fields set deliberately in corrections.csv / enrich*.csv (not enrich-fix-*; those win in the
      build anyway), or set to different values by different raw files (unclear which is right: left alone).
    deliberate: (chalet_id, field) -> value of a collector's appended correction row (same file, later row, different
      value). build_chalets keeps the FIRST non-blank value, so those corrections never took effect; the repair writes them."""
    prot, deliberate = {}, {}
    corr = ROOT / "chalets/corrections.csv"
    if corr.exists():
        for c in csv.DictReader(corr.open(newline="")):
            prot.setdefault(c["chalet_id"], set()).add(c["field"])
    seen = {}
    for p in sorted((ROOT / "chalets/raw").glob("*.csv")):
        if p.name.endswith(("HEADER.csv", ".issues.csv", ".sites.csv", ".changes.csv", ".newsites.csv")) or p.name.startswith("enrich-fix-"):
            continue
        manual = p.name.startswith("enrich")
        for r in csv.DictReader(p.open(newline="")):
            cid = r.get("chalet_id")
            if not cid:
                continue
            for k in OVERRIDE_FIELDS + ["chalet_name", "url"]:
                v = (r.get(k) or "").strip()
                if not v:
                    continue
                if manual:
                    prot.setdefault(cid, set()).add(k)
                seen.setdefault((cid, k), []).append((p.name, v))
    for (cid, k), vals in seen.items():
        if len({v.lower() for _, v in vals}) < 2:
            continue
        files = {f for f, _ in vals}
        last_file = vals[-1][0]
        same = [v for f, v in vals if f == last_file]
        if len({v.lower() for v in same}) > 1 and all(v.lower() in {x.lower() for x in same} for _, v in vals):
            deliberate[(cid, k)] = same[-1]  # correction appended in the same file as the original
        else:
            prot.setdefault(cid, set()).add(k)
    return prot, deliberate


def base_rows():
    """Merged rows as build_chalets.py would make them WITHOUT any enrich-fix-* file (chalets_all.csv may already contain
    an earlier repair run): enrich* first, first non-blank/non-unknown wins, then corrections.csv."""
    out = {}
    raw = ROOT / "chalets/raw"
    for p in sorted(raw.glob("*.csv"), key=lambda p: (not p.name.startswith("enrich"), p.name)):
        if p.name.endswith(("HEADER.csv", ".issues.csv", ".sites.csv", ".changes.csv", ".newsites.csv")) or p.name.startswith("enrich-fix-"):
            continue
        for r in csv.DictReader(p.open(newline="")):
            cid = r.get("chalet_id")
            if not cid:
                continue
            cur = out.setdefault(cid, {})
            for k, v in r.items():
                if k and v and cur.get(k, "") in ("", "unknown"):
                    cur[k] = v
    corr = ROOT / "chalets/corrections.csv"
    if corr.exists():
        for c in csv.DictReader(corr.open(newline="")):
            if c["chalet_id"] in out:
                out[c["chalet_id"]][c["field"]] = c["value"]
    return out


def host(u):
    return re.sub(r"^https?://(?:www\.)?([^/]+).*", r"\1", (u or "").lower())


def main():
    argv = sys.argv[1:]
    dry = "--ingest-dry-run" in argv
    noimg = "--no-images" in argv
    src_file = None
    if "--from-jsonl" in argv:
        i = argv.index("--from-jsonl"); src_file = argv[i + 1]; del argv[i:i + 2]
    override = "--override" in argv
    argv = [a for a in argv if a not in ("--ingest-dry-run", "--no-images", "--override")]
    if len(argv) < 2:
        sys.exit(__doc__)
    task, scraper, sargs = argv[0], argv[1], argv[2:]
    out = ROOT / "chalets/raw" / f"{task}.csv"
    if src_file:
        lines = Path(src_file).read_text().splitlines()
    else:
        p = subprocess.run([sys.executable, str(HERE / f"{scraper}.py")] + sargs, stdout=subprocess.PIPE, text=True)
        lines = p.stdout.splitlines()
    rows = [json.loads(l) for l in lines if l.strip().startswith("{")]
    K = Known()
    mine = set()
    if out.exists():
        for r in csv.DictReader(out.open(newline="")):
            mine.add((r.get("chalet_id"), r.get("listed_on")))
    used_ids = set(K.rows)
    prot, deliberate = protected_fields() if override else ({}, {})
    RV = resort_villages()
    BASE = base_rows() if override else {}
    url_count = {}
    msem_ids = {}
    for kcid, kr in K.rows.items():
        if kr.get("url"):
            url_count[kr["url"]] = url_count.get(kr["url"], 0) + 1
        m = re.search(r"MSEM lodging id (\d+)", kr.get("notes") or "")
        if m:
            msem_ids.setdefault(m.group(1), kcid)
        elif "MSEM" in (kr.get("listed_on") or "") and re.search(r"-(\d{4,6})$", kcid):
            msem_ids.setdefault(re.search(r"-(\d{4,6})$", kcid).group(1), kcid)
    for p in sorted((ROOT / "chalets/raw").glob("*.csv")):  # merged notes keep only the first row's text
        if p.name.endswith(("HEADER.csv", ".issues.csv", ".sites.csv", ".changes.csv", ".newsites.csv")):
            continue
        for r in csv.DictReader(p.open(newline="")):
            m = re.search(r"MSEM lodging id (\d+)", r.get("notes") or "")
            if m and r.get("chalet_id") in K.rows:
                msem_ids.setdefault(m.group(1), r["chalet_id"])
    import collections
    st = dict(changed=collections.Counter(), repaired=0, new=0, known=0, skipped=0, catered=0, hot_tub=0, s8_10=0, free=0, near=[], ambiguous=0)
    for s in rows:
        imgs = s.pop("images", []) or []
        if isinstance(imgs, str):  # hand-edited / re-serialised jsonl: "url1 url2" or "url1;url2"
            imgs = re.split(r"[\s;|,]+(?=https?://)|\s+", imgs.strip())
        imgs = [u.strip() for u in imgs if isinstance(u, str) and u.strip().startswith("http")]
        src = s.get("_source", scraper)
        cid, how, cands = K.match(s)
        if src.startswith("msem") and s.get("_source_id"):  # collector rows share the bare booking-page url
            cid = msem_ids.get(str(s["_source_id"])) or cid
            how = "msem-id" if msem_ids.get(str(s["_source_id"])) else how
        if how == "ambiguous":
            st["ambiguous"] += 1
        clean = {k: s.get(k, "") for k in COLUMNS}
        clean["found_via"] = task
        clean["date_checked"] = clean.get("date_checked") or TODAY
        if cid:
            kn = dict(K.rows[cid])
            if (kn.get("operator") or "").lower().startswith("unknown"):
                kn["operator"] = ""  # e.g. "unknown (sold via Sno)": let a source that names the operator fill it
            rec = {k: v for k, v in clean.items() if v not in ("", None) and not kn.get(k) and k not in SOURCE_PRICE}
            rec.update(chalet_id=cid, listed_on=clean["listed_on"], found_via=task, date_checked=clean["date_checked"])
            if not kn.get("url"):
                rec["url"] = clean["url"]
            if override:
                kn = {**kn, **BASE.get(cid, {})}
            if override and host(kn.get("url")) == host(clean["url"]):
                # repair pass: this source's own earlier row -> its (fixed) structural values win, never blanks
                pf = prot.get(cid, set())
                for k in OVERRIDE_FIELDS:
                    v = clean.get(k)
                    if (cid, k) in deliberate and not (deliberate[(cid, k)] == "unknown" and v not in ("", None, "unknown")):
                        # the collector's own correction beats the scraper (a corrected 'unknown' yields to a real value)
                        # always written (chalets_all.csv may already contain an earlier enrich-fix value)
                        v = deliberate[(cid, k)]
                        rec[k] = v
                        st["changed"][k + " (collector correction)"] += v != (kn.get(k) or "")
                        continue
                    if v in ("", None, "unknown") or k in pf:
                        continue
                    if (kn.get(k) or "") in KEEP_VALUES.get(k, ()) or less_specific(k, kn.get(k) or "", str(v)):
                        continue
                    if k == "village" and slug(kn.get(k)) in RV and slug(v) not in RV:
                        continue  # e.g. 'Briançon' (resorts_raw spelling) vs the scraper's 'Serre Chevalier: Briançon (1200)'
                    if k == "village" and not (not kn.get(k) or "&#" in kn[k] or s.get("_village_specific")
                                               or slug(kn[k]) == slug(s.get("_village_crumb") or "-")):
                        continue
                    rec[k] = v
                    st["changed"][k] += str(v) != (kn.get(k) or "")
                if "chalet_name" not in pf and PLACEHOLDER_NAME.search(kn.get("chalet_name") or "") and clean["chalet_name"] \
                        and not PLACEHOLDER_NAME.search(clean["chalet_name"]):
                    rec["chalet_name"] = clean["chalet_name"]; st["changed"]["chalet_name"] += 1
                if "url" not in pf and url_count.get(kn.get("url"), 0) > 1 and clean["url"] != kn.get("url"):
                    rec["url"] = clean["url"]; st["changed"]["url"] += 1
                st["repaired"] += any(k in rec for k in OVERRIDE_FIELDS + ["chalet_name", "url"])
            bits = [f"{clean['listed_on']}: {clean['url']}"]
            if clean["price_week_20_27_mar_2027"]:
                bits.append(f"20 Mar {clean['price_currency']} {clean['price_week_20_27_mar_2027']} {clean['price_basis']}")
            if clean["price_range_low"] != "":
                bits.append(f"range {clean['price_currency']} {clean['price_range_low']}-{clean['price_range_high']} {clean['price_basis']}")
            if clean["available_20_27_mar"] not in ("", "unknown"):
                bits.append(f"available 20 Mar: {clean['available_20_27_mar']}")
            if clean["operator"] and not kn.get("operator"):
                bits.append(f"operator per {clean['listed_on']}: {clean['operator']}")
            rec["notes"] = "; ".join(bits)
            # fill price columns only if the known row has no price info at all
            if not any(kn.get(k) for k in ("price_week_20_27_mar_2027", "price_range_low", "price_type")):
                rec.update({k: clean[k] for k in SOURCE_PRICE if clean[k] not in ("", None)})
            if (cid, rec["listed_on"]) in mine:
                st["skipped"] += 1
                continue
            st["known"] += 1
            if not dry and imgs and not noimg and not (kn.get("image_count") and kn["image_count"] not in ("0", "")):
                n = save_images(cid, imgs, clean["url"])
                if n:
                    rec["image_count"], rec["image_dir"] = n, f"chalets/images/{cid}/"
            write(out, rec, dry, f"KNOWN({how}) {cid}")
            r = {**kn, **{k: v for k, v in clean.items() if v}}
        elif override:
            st["new_skipped"] = st.get("new_skipped", 0) + 1  # repair pass: new units belong to village collectors
            continue
        else:
            pre = slug(clean["operator"]) if clean["operator"] and src in ("skiline", "igluski") else PREFIX.get(src, slug(src))
            base = f"{pre}-{slug(clean['chalet_name'])}".strip("-")[:80]
            cid = base
            if cid in used_ids:
                cid = f"{base}-{slug(str(s.get('_source_id', '')))}" if s.get("_source_id") else base
                k = 2
                while cid in used_ids:
                    cid = f"{base}-{k}"; k += 1
            used_ids.add(cid)
            if cands:
                clean["same_as"] = ";".join(cands)
            clean["chalet_id"] = cid
            if (cid, clean["listed_on"]) in mine:
                st["skipped"] += 1
                continue
            st["new"] += 1
            if not dry and imgs and not noimg:
                n = save_images(cid, imgs, clean["url"])
                clean["image_count"] = n
                clean["image_dir"] = f"chalets/images/{cid}/" if n else ""
            write(out, {k: v for k, v in clean.items() if v not in ("", None)}, dry, f"NEW {cid}")
            r = clean
        cat = r.get("board") in ("catered", "catered-or-self", "chalet-hotel")
        ht = (r.get("hot_tub") or "").startswith(("private", "yes"))
        try:
            s810 = 8 <= int(float(r.get("sleeps_max") or 0)) <= 12
        except ValueError:
            s810 = False
        free = clean.get("available_20_27_mar") == "yes"
        st["catered"] += cat; st["hot_tub"] += ht; st["s8_10"] += s810; st["free"] += free
        if cat and ht and free:
            st["near"].append(r.get("chalet_id") or cid)
    print(f"\n{task} <- {scraper} {' '.join(sargs)}: {len(rows)} scraped | new {st['new']} | known {st['known']} | "
          f"skipped (already in file) {st['skipped']} | catered {st['catered']} | private/possible hot tub {st['hot_tub']} | "
          f"sleeps 8-12 {st['s8_10']} | free 20 Mar {st['free']}"
          + (f" | override: new units not written {st.get('new_skipped', 0)}; repaired {st['repaired']} rows, fields changed {dict(st['changed'])}" if override else "") + (f" | ambiguous name matches {st['ambiguous']}" if st["ambiguous"] else ""))
    if st["near"]:
        print("catered + hot tub + free 20 Mar:", ", ".join(st["near"]))
    if dry:
        print("(ingest dry run: nothing written)")


def save_images(cid, urls, ref):
    """Each URL is its own argv entry (save_images.py <cid> <url> <url> ... --referer=<page>). -> number saved."""
    p = subprocess.run([sys.executable, str(ROOT / "tools/save_images.py"), cid, *urls[:8], f"--referer={ref}"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        n = int(p.stdout.strip().split("\n")[-1])
    except ValueError:
        n = 0
    if not n:
        print(f"  images: none saved for {cid} ({len(urls)} urls){': ' + p.stderr.strip().splitlines()[-1][:160] if p.stderr.strip() else ''}",
              file=sys.stderr)
    return n


def write(out, rec, dry, tag):
    if dry:
        print(tag, json.dumps({k: v for k, v in rec.items() if k not in ("description",)}, ensure_ascii=False)[:400])
        return
    subprocess.run([sys.executable, str(ROOT / "tools/append_row.py"), str(out), json.dumps(rec, ensure_ascii=False)],
                   check=True, stdout=subprocess.DEVNULL)
    print(tag)


if __name__ == "__main__":
    main()
