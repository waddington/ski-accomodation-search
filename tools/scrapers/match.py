"""Match scraped rows to chalets already collected (chalets_all.csv + chalets/raw/*.csv).

Order: 1) same url (normalised); 2) same normalised name within the same ski area
(village -> ski_area via resorts/resorts_raw.csv, falling back to the row's ski_area / village prefix).
"""
import csv, re
from pathlib import Path
from common import ROOT, slug

SKIP = ("HEADER.csv", ".issues.csv", ".sites.csv", ".changes.csv", ".newsites.csv")
GENERIC = {"", "chalet", "apartment", "appartement", "studio"}


ID_PARAMS = ("s_pid", "pid", "id_accom", "product_id", "slug")  # query params that identify the listing (Orchestra /product?s_pid=N)


def nurl(u):
    u = (u or "").strip()
    keep = [f"{k}={v}" for k, v in re.findall(r"[?&](?:amp;)?(%s)=([^&#]+)" % "|".join(ID_PARAMS), u)]
    u = re.sub(r"[#?].*$", "", u).rstrip("/").lower()
    u = u.replace("http://", "https://").replace("://www.", "://").replace("://cdn.", "://")
    return u + ("?" + "&".join(sorted(keep)) if keep else "")


def nname(n):
    s = slug(n)
    s = re.sub(r"-(family|adults-only|catered|self-catered)$", "", s)
    s = re.sub(r"^(chalet|chalets|le|la|les|l|hotel|apartment|appartement|residence)-", "", s)
    s = re.sub(r"^(chalet|le|la|les|l)-", "", s)
    return s


def _area_map():
    m = {}
    try:
        for r in csv.DictReader((ROOT / "resorts/resorts_raw.csv").open(newline="")):
            v = slug(r.get("village"))
            if v:
                m[v] = slug(r.get("ski_area"))
    except FileNotFoundError:
        pass
    return m


AREA = _area_map()
EXTRA = {"reberty-2000": "les-3-vallees", "st-martin-de-belleville": "les-3-vallees", "mottaret": "les-3-vallees",
         "montchavin": "paradiski", "les-coches": "paradiski", "la-plagne": "paradiski", "les-arcs": "paradiski",
         "peisey-nancroix": "paradiski", "val-d-isere": "espace-killy", "tignes": "espace-killy"}


def area_of(village, ski_area=""):
    v = slug(village)
    if v in AREA:
        return AREA[v]
    for k, a in list(AREA.items()) + list(EXTRA.items()):
        if k and v and (v.startswith(k) or (k.startswith(v) and len(v) > 4) or k in v):
            return a
    return slug(ski_area)[:12] or v.split("-")[0]


class Known:
    def __init__(self):
        self.rows = {}
        files = [ROOT / "chalets/chalets_all.csv"] + sorted((ROOT / "chalets/raw").glob("*.csv"))
        for p in files:
            if p.name.endswith(SKIP):
                continue
            try:
                for r in csv.DictReader(p.open(newline="")):
                    cid = r.get("chalet_id")
                    if not cid:
                        continue
                    m = self.rows.setdefault(cid, {"_urls": set(), "_listed": set()})
                    for k, v in r.items():
                        if k and v and not m.get(k):
                            m[k] = v
                    if r.get("url"):
                        m["_urls"].add(nurl(r["url"]))
                    for x in (r.get("listed_on") or "").split(";"):
                        if x.strip():
                            m["_listed"].add(x.strip())
                    for u in re.findall(r"https?://\S+", r.get("notes") or ""):
                        m["_urls"].add(nurl(u.rstrip(").,;")))
            except Exception:
                pass
        self.by_url, self.by_name = {}, {}
        for cid, r in self.rows.items():
            for u in r["_urls"]:
                if u:
                    self.by_url.setdefault(u, cid)
            n = nname(r.get("chalet_name"))
            if n not in GENERIC and len(n) >= 3:
                self.by_name.setdefault((n, area_of(r.get("village"), r.get("ski_area"))), []).append(cid)

    def match(self, s):
        """-> (chalet_id or None, how, [other candidate ids])"""
        cid = self.by_url.get(nurl(s.get("url")))
        if cid:
            return cid, "url", []
        n = nname(s.get("chalet_name"))
        if (s.get("village") or s.get("ski_area")):
            c = self.by_name.get((n, area_of(s.get("village"), s.get("ski_area"))), [])
        else:  # no village known (e.g. Sno): accept a name that is unique across all areas
            c = [x for (nm, _), ids in self.by_name.items() if nm == n for x in ids]
        if not c:
            return None, "", []
        # a known row that already has a different url on the same site is a different listing
        host = re.sub(r"^https://([^/]+).*", r"\1", nurl(s.get("url")))
        c = [x for x in c if not any(u.startswith("https://" + host + "/") for u in self.rows[x]["_urls"])]
        if not c:
            return None, "", []
        # prefer same operator when known
        op = slug(s.get("operator"))
        best = [x for x in c if op and op in slug(self.rows[x].get("operator"))] or c
        if len(best) == 1:
            return best[0], "name", []
        return None, "ambiguous", best
