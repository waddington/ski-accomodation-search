#!/usr/bin/env python3
"""Update a task in chalets/search_queue.csv (the dashboard shows it live).

    python3 tools/queue.py start  <task_id> [--file=<collector csv>]
    python3 tools/queue.py done   <task_id> --rows=N --new=N --issues=N [--notes="..."]
    python3 tools/queue.py failed <task_id> --notes="why"
    python3 tools/queue.py skipped <task_id> --notes="why"
    python3 tools/queue.py partial <task_id> --rows=N --notes="done: …; remaining: …"   # resumable
    python3 tools/queue.py release <task_id> [--notes="…"]   # back to pending (keeps notes/rows), e.g. when deprioritised
    python3 tools/queue.py next  [--lane=enrich|sites|villages]     # peek at the next task
    python3 tools/queue.py claim --lane=sites|villages|enrich      # atomically take the next task
        (marks it in_progress, sets collector_file=chalets/raw/<task_id>.csv, prints it)

Lanes: enrich = phase 1; sites = phases 2-3 (site, discover); villages = phase 4 (village);
       villages = French villages, top of the list down; villages-fr-rev = French villages, bottom up;
       villages-abroad = phase 4 villages outside France.
All writes take an exclusive lock, so parallel agents never get the same task.
"""
import csv, fcntl, sys, time
from pathlib import Path

Q = Path(__file__).resolve().parent.parent / "chalets/search_queue.csv"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
_lock = open(Q.with_suffix(".lock"), "w")
fcntl.flock(_lock, fcntl.LOCK_EX)
rows = list(csv.DictReader(Q.open()))
LANES = {"enrich": {"enrich"}, "sites": {"site", "discover"}, "villages": {"village"}, "search": {"site", "discover", "village"}, "villages-abroad": {"village"}, "villages-fr-rev": {"village"}}
ABROAD = lambda r: not r["detail"].startswith("France")
fields = list(rows[0].keys())
if not args:
    sys.exit(__doc__)
cmd = args[0]
if cmd == "next":
    lane = opts.get("lane")
    ok = lambda r: lane is None or r["type"] in LANES[lane]
    t = next((r for r in rows if r["status"] == "partial" and ok(r)), None) or \
        next((r for r in rows if r["status"] == "pending" and ok(r)), None)
    print("\t".join([t["task_id"], t["type"], t["target"], t["url"], t["detail"]]) if t else "none")
    sys.exit()
if cmd == "claim":
    types = LANES[opts["lane"]]
    lane = opts["lane"]
    fits = lambda r: r["type"] in types and (
        ABROAD(r) if lane == "villages-abroad" else
        not ABROAD(r) if lane in ("villages", "villages-fr-rev") else True)
    order = list(reversed(rows)) if lane == "villages-fr-rev" else rows
    # Each lane resumes only its own partial tasks (by type), never one another agent holds.
    t = next((r for r in order if r["status"] == "partial" and fits(r)), None) or \
        next((r for r in order if r["status"] == "pending" and fits(r)), None)
    if not t:
        print("none"); sys.exit()
    t.update(status="in_progress", started=time.strftime("%Y-%m-%d %H:%M"),
             collector_file=f"chalets/raw/{t['task_id']}.csv")
    args = [cmd, t["task_id"]]
    cmd = "claimed"
tid = args[1]
row = next((r for r in rows if r["task_id"] == tid), None)
if not row:
    sys.exit(f"no task {tid}")
now = time.strftime("%Y-%m-%d %H:%M")
if cmd == "claimed":
    pass
elif cmd == "start":
    row.update(status="in_progress", started=now, collector_file=opts.get("file", row["collector_file"]))
elif cmd == "release":
    row.update(status="pending", started="", notes=(row["notes"] + " " + opts.get("notes", "released")).strip())
elif cmd == "partial":
    row.update(status="partial", rows_written=str(int(row["rows_written"] or 0) + int(opts.get("rows", 0))),
               notes=opts.get("notes", row["notes"]))
elif cmd in ("done", "failed", "skipped"):
    row.update(status=cmd, finished=now, rows_written=opts.get("rows", row["rows_written"]),
               new_chalets=opts.get("new", row["new_chalets"]), issues=opts.get("issues", row["issues"]),
               notes=opts.get("notes", row["notes"]))
else:
    sys.exit(__doc__)
tmp = Q.with_suffix(".tmp")
with tmp.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
tmp.replace(Q)
if cmd == "claimed":
    print("\t".join([row["task_id"], row["type"], row["target"], row["url"], row["detail"]]))
else:
    print(f"{tid}: {row['status']}")
