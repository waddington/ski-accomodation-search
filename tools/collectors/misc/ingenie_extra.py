#!/usr/bin/env python3
"""Wrapper: register extra Ingenie sites then run tools/scrapers/ingenie.py main (no edits to that file)."""
import sys
sys.path.insert(0, "/home/kai/Documents/Misc/ski-chalet-finder/tools/scrapers")
import ingenie
ingenie.SITES["morzine"] = dict(host="https://www.resa-morzine.com", mid=int(__import__('os').environ.get('MID', '3')), cid=3, tp="G",
    village="Morzine", ski_area="Portes du Soleil", country="France", site="Morzine Réservation (resa-morzine.com)",
    quarters={})
ingenie.main()
