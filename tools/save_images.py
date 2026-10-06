#!/usr/bin/env python3
"""Download up to 5 images for a chalet, skip tiny ones, resize to max 1600px wide, save as JPEG.

    python3 tools/save_images.py <chalet_id> <url> [<url> ...] [--referer=<page url>]

Saves chalets/images/<chalet_id>/01.jpg ... and prints the number saved (use it for image_count).
Existing images for that chalet are kept; numbering continues after them.
"""
import io, sys, time, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MAX_W, MAX_N, MIN_BYTES = 1600, 5, 15_000
# a single quoted "url1 url2 ..." argument is split into separate URLs (used to be read as one bad URL)
args = [x for a in sys.argv[1:] if not a.startswith("--") for x in a.split()]
ref = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--referer=")), None)
if len(args) < 2:
    sys.exit(__doc__)
cid, urls = args[0], args[1:]
d = ROOT / "chalets/images" / cid
d.mkdir(parents=True, exist_ok=True)
have = sorted(d.glob("*.jpg"))
n = len(have)
for u in urls:
    if n >= MAX_N:
        break
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", **({"Referer": ref} if ref else {})})
        data = urllib.request.urlopen(req, timeout=30).read()
        if len(data) < MIN_BYTES:
            print(f"skip {u[:80]}: too small ({len(data)} bytes)", file=sys.stderr)
            continue
        im = Image.open(io.BytesIO(data)).convert("RGB")
        if im.width < 400:
            print(f"skip {u[:80]}: only {im.width}px wide", file=sys.stderr)
            continue
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)))
        n += 1
        im.save(d / f"{n:02d}.jpg", "JPEG", quality=82)
        time.sleep(0.5)
    except Exception as e:
        print(f"skip {u[:80]}: {e}", file=sys.stderr)
print(n)
