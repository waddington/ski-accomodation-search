#!/usr/bin/env python3
"""Build a static, shareable snapshot of the dashboard (for GitHub Pages or any static host).

    python3 tools/build_static.py [outdir]        # default: static_site/

The output folder is self-contained: index.html at the root plus the CSVs it reads and
downsized photos. No server needed. To keep it small enough for GitHub Pages (~1 GB limit):
  - every chalet gets 1 thumbnail (480 px wide)
  - chalets that make the cut get up to 5 photos (1000 px wide)
Private individuals' contact names, emails and phone numbers are redacted (the
site is public). Re-run it after the data changes; it rebuilds the folder from scratch (images are cached
between runs, so only new ones are resized).
"""
import csv
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "static_site"
THUMB_W, FULL_W, FULL_N = 480, 1000, 5

# Files the page reads, at the same relative paths as under the live server.
DATA_FILES = ["chalets/search_queue.csv", "chalets/access_issues.csv", "chalets/site_yield.csv",
              "dashboard/history.csv"]


NAME = r"[A-Z][\w'’-]+(?:\s(?:&|and)\s[A-Z][\w'’-]+)?(?:\s[A-Z][\w'’-]+)?"
REDACT = [
    (re.compile(r"\b((?:enquiry |advertiser |owner )?contact(?: name)?:?\s*)" + NAME), r"\1[name removed]"),
    (re.compile(r"\(([^()]*?)\b(?:Scott|Sophie|Martin|Toorna)\b[^()]*\)"), "(private owner)"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[email removed]"),
    (re.compile(r"(?<!\d)(?:\+|00)\d[\d\s().-]{7,}\d"), "[phone removed]"),
]


def redact(text):
    """Strip private individuals' names, emails and phone numbers before publishing."""
    for rx, rep in REDACT:
        text = rx.sub(rep, text)
    return text


def resize(src, dst, width):
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return True
    try:
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)))
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "JPEG", quality=72, optimize=True, progressive=True)
        return True
    except Exception as e:
        print(f"  skip {src}: {e}", file=sys.stderr)
        return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ("chalets", "dashboard"):
        (OUT / sub).mkdir(exist_ok=True)

    # Page: same dashboard, in snapshot mode (no auto-refresh, snapshot label).
    html = (ROOT / "dashboard/index.html").read_text()
    html = html.replace("<body>", '<body data-static="1">', 1)
    (OUT / "index.html").write_text(html)

    for f in DATA_FILES:
        if (ROOT / f).exists():
            shutil.copy2(ROOT / f, OUT / f)
    stamp = (ROOT / "dashboard/last_build.txt").read_text().splitlines()[0] if (ROOT / "dashboard/last_build.txt").exists() else ""
    import time
    (OUT / "dashboard/last_build.txt").write_text(f"snapshot {time.strftime('%Y-%m-%d %H:%M')}\n")

    # Chalets: rewrite image_count to what the snapshot actually ships.
    rows = list(csv.DictReader((ROOT / "chalets/chalets_all.csv").open(newline="")))
    fields = list(rows[0].keys())
    keep = set()
    shipped = 0
    for r in rows:
        src_dir = ROOT / "chalets/images" / r["chalet_id"]
        srcs = sorted(src_dir.glob("*.jpg")) if src_dir.is_dir() else []
        passes = not r["removed_by"]
        n = 0
        for i, src in enumerate(srcs[: FULL_N if passes else 1], 1):
            dst = OUT / "chalets/images" / r["chalet_id"] / f"{i:02d}.jpg"
            if resize(src, dst, FULL_W if passes else THUMB_W):
                n = i
                keep.add(dst)
        r["image_count"] = str(n)
        for k in ("operator", "notes", "description", "catering_detail"):
            r[k] = redact(r[k])
        shipped += n
    with (OUT / "chalets/chalets_all.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Drop images from earlier builds that are no longer shipped.
    for p in (OUT / "chalets/images").rglob("*.jpg"):
        if p not in keep:
            p.unlink()
    for d in sorted((OUT / "chalets/images").glob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    (OUT / ".nojekyll").write_text("")  # serve files as-is on GitHub Pages
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"{OUT}: {len(rows)} chalets, {shipped} images, {size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
