#!/usr/bin/env python3
"""Fetch photos for chalets that have none (LLM-free): opens each listing url once (common.fetch, max 2
requests per site), saves up to 5 photos via tools/save_images.py, records counts in chalets/raw/enrich-images.csv
(written with the full HEADER.csv schema afterwards — see HANDOFF.md).
    python3 backfill_images.py [--limit N] [--dry-run]
"""
import csv, html, re, subprocess, sys, time, urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/scrapers"))
from common import fetch, Blocked  # noqa: E402  (max 2 requests per site across all processes)

OUT = ROOT / "chalets/raw/enrich-images.csv"
SKIP = re.compile(r"logo|icon|sprite|favicon|avatar|flag|/map|plan|badge|picto|placeholder|loader|blank|"
                  r"\.svg|\.gif|1x1|pixel|tripadvisor|facebook|instagram|google", re.I)
IMG_EXT = re.compile(r"\.(jpe?g|png|webp)(\?|$)", re.I)


def candidates(page, base):
    urls = []
    for m in re.finditer(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*>', page, re.I):
        c = re.search(r'content=["\']([^"\']+)', m.group(0))
        if c:
            urls.append(c.group(1))
    for m in re.finditer(r'(?:data-src|data-lazy-src|data-original|src)=["\']([^"\']+)["\']', page, re.I):
        urls.append(m.group(1))
    for m in re.finditer(r'srcset=["\']([^"\']+)["\']', page, re.I):
        parts = [p.strip().split(" ")[0] for p in m.group(1).split(",") if p.strip()]
        if parts:
            urls.append(parts[-1])
    for m in re.finditer(r'url\(["\']?([^"\')]+\.(?:jpe?g|webp|png))', page, re.I):
        urls.append(m.group(1))
    out, seen = [], set()
    for u in urls:
        u = html.unescape(u.strip())
        if u.startswith("//"):
            u = "https:" + u
        u = urllib.parse.urljoin(base, u)
        if not u.startswith("http") or SKIP.search(u) or not IMG_EXT.search(u.split("#")[0]):
            continue
        key = re.sub(r"[?#].*$", "", u)
        if key not in seen:
            seen.add(key); out.append(u)
    return out


def main():
    dry = "--dry-run" in sys.argv
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    rows = list(csv.DictReader((ROOT / "chalets/chalets_all.csv").open(newline="")))
    url_count = Counter(r["url"] for r in rows if r["url"])
    done = {r["chalet_id"] for r in csv.DictReader(OUT.open(newline=""))} if OUT.exists() else set()
    todo = [r for r in rows
            if not ((ROOT / "chalets/images" / r["chalet_id"]).is_dir() and any((ROOT / "chalets/images" / r["chalet_id"]).glob("*.jpg")))
            and r["chalet_id"] not in done and r["url"].startswith("http") and url_count[r["url"]] == 1]
    skipped_shared = sum(1 for r in rows if url_count.get(r["url"], 0) > 1 and not (ROOT / "chalets/images" / r["chalet_id"]).is_dir())
    if limit:
        todo = todo[:limit]
    print(f"{len(todo)} chalets to try ({skipped_shared} skipped: url shared by several chalets)", flush=True)
    got = failed = 0
    t0 = time.time()
    for i, r in enumerate(todo, 1):
        cid, url = r["chalet_id"], r["url"]
        try:
            status, page, final = fetch(url)
        except Blocked as e:
            print(f"[{i}] {cid}: blocked {e}", flush=True); failed += 1; continue
        except Exception as e:
            print(f"[{i}] {cid}: fetch error {e}", flush=True); failed += 1; continue
        imgs = candidates(page, final) if status == 200 else []
        n = 0
        if imgs and not dry:
            p = subprocess.run([sys.executable, str(ROOT / "tools/save_images.py"), cid, *imgs[:12], f"--referer={final}"],
                               capture_output=True, text=True)
            try:
                n = int(p.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                n = 0
        elif imgs:
            n = min(len(imgs), 5)
        print(f"[{i}/{len(todo)}] {cid}: {status}, {len(imgs)} candidates, {n} saved", flush=True)
        if n and not dry:
            new = not OUT.exists()
            with OUT.open("a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["chalet_id", "image_count", "image_dir", "found_via", "date_checked"])
                w.writerow([cid, n, f"chalets/images/{cid}/", "enrich-images", time.strftime("%Y-%m-%d")])
            got += 1
        elif not n:
            failed += 1
    print(f"done in {time.time() - t0:.0f}s: {got} chalets got photos, {failed} without", flush=True)


if __name__ == "__main__":
    main()
