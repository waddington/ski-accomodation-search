#!/usr/bin/env python3
"""Local dashboard for the chalet search.

    python3 dashboard/serve.py [port]      # default 8777, then open http://localhost:8777/

Serves the project folder read-only and re-runs chalets/build_chalets.py every
REBUILD_SECONDS so the CSVs the page reads are always fresh. The page itself
re-fetches them every 30 seconds.
"""
import csv
import functools
import re
import http.server
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
REBUILD_SECONDS = 60


def rebuild_forever():
    while True:
        r = subprocess.run([sys.executable, str(ROOT / "chalets/build_chalets.py")],
                           capture_output=True, text=True, cwd=ROOT)
        stamp = time.strftime("%H:%M:%S")
        if r.returncode == 0:
            record_history(r.stdout)
        (ROOT / "dashboard/last_build.txt").write_text(
            f"{stamp}\n{r.stdout}{r.stderr}" if r.returncode == 0 else f"{stamp} BUILD FAILED\n{r.stderr}")
        time.sleep(REBUILD_SECONDS)


LANES = ["pilot", "enrich", "sites", "villages", "villages_abroad"]
HIST_FIELDS = ["time", "raw_rows", "chalets", "passing", "tasks_done", "source"] + [f"lane_{l}" for l in LANES]


def lane_of(name):
    if name.startswith("pilot-"):
        return "pilot"
    if name.startswith("enrich"):
        return "enrich"
    if name.startswith(("site-", "discover-")):
        return "sites"
    if name.startswith("village-france-"):
        return "villages"
    if name.startswith("village-"):
        return "villages_abroad"
    return None


def lane_counts():
    """Unique chalet_ids per lane (a chalet found by two lanes counts for both)."""
    ids = {l: set() for l in LANES}
    for p in (ROOT / "chalets/raw").glob("*.csv"):
        lane = lane_of(p.name)
        if not lane or p.name.endswith((".issues.csv", ".sites.csv", ".changes.csv", ".newsites.csv")):
            continue
        try:
            ids[lane] |= {r["chalet_id"] for r in csv.DictReader(p.open(newline="")) if r.get("chalet_id")}
        except Exception:
            pass
    return [str(len(ids[l])) for l in LANES]


def ensure_history_header(hist):
    """Upgrade an older history.csv to the current columns (old rows get blanks)."""
    if not hist.exists():
        return
    rows = list(csv.reader(hist.open(newline="")))
    if rows and rows[0] != HIST_FIELDS:
        with hist.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(HIST_FIELDS)
            for r in rows[1:]:
                w.writerow(r + [""] * (len(HIST_FIELDS) - len(r)))


def record_history(build_out):
    """Append one snapshot per rebuild to dashboard/history.csv (only when something changed)."""
    m = re.search(r"(\d+) raw rows -> (\d+) chalets; (\d+) pass", build_out)
    if not m:
        return
    q = ROOT / "chalets/search_queue.csv"
    done = sum(r["status"] in ("done", "failed", "skipped") for r in csv.DictReader(q.open())) if q.exists() else 0
    hist = ROOT / "dashboard/history.csv"
    ensure_history_header(hist)
    row = [time.strftime("%Y-%m-%d %H:%M"), *m.groups(), str(done), "live", *lane_counts()]
    rows = list(csv.reader(hist.open(newline=""))) if hist.exists() else []
    last = rows[-1] if len(rows) > 1 else []
    if last[1:5] == row[1:5] and last[6:] == row[6:]:
        return
    with hist.open("a", newline="") as f:
        csv.writer(f).writerow(row)


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/dashboard/index.html"
        return super().do_GET()


if __name__ == "__main__":
    threading.Thread(target=rebuild_forever, daemon=True).start()
    handler = functools.partial(Handler, directory=str(ROOT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler) as httpd:
        print(f"Chalet dashboard: http://localhost:{PORT}/")
        httpd.serve_forever()
