import sys, re
sys.path.insert(0, "/home/kai/Documents/Misc/ski-chalet-finder/tools/scrapers")
import ingenie
ingenie.SITES["les2alpes"] = dict(host="https://booking.les2alpes.com", mid=2, cid=2, tp="G", qcrit="GTYPRE",
    village="Les 2 Alpes", ski_area="Les 2 Alpes", country="France", site="Les 2 Alpes Réservation (booking.les2alpes.com)",
    quarters={})
if "--chalets-only" in sys.argv:
    sys.argv.remove("--chalets-only")
    orig = ingenie.undated
    ingenie.undated = lambda *a, **k: [u for u in orig(*a, **k) if re.search(r"\bchalet\b", u["name"], re.I)]
sys.argv[0] = "ingenie.py"
ingenie.main()
