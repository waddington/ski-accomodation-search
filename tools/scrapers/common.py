"""Shared helpers for the LLM-free scrapers in tools/scrapers/.

- Polite HTTP: <= SLOTS_PER_HOST requests in flight per website across all processes, each slot
  >= DELAY seconds between its requests (see host_slot),
  browser UA, cookie jar, gzip, simple retry on network errors (never on 403/429).
- Row helpers: SCHEMA columns (chalets/raw/HEADER.csv), emit() prints one JSON line.
"""
import argparse, gzip, html, http.cookiejar, json, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLUMNS = (ROOT / "chalets/raw/HEADER.csv").read_text().strip().split(",")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
DELAY = 2.0
TODAY = time.strftime("%Y-%m-%d")

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_last = [0.0]
STATS = {"requests": 0}


class Blocked(Exception):
    pass


LOCK_DIR = ROOT / "tools/scrapers/.hostlocks"


SLOTS_PER_HOST = 2  # user: up to 2 concurrent requests per website


class host_slot:
    """Cross-process politeness: at most SLOTS_PER_HOST requests in flight per host across ALL scraper
    processes (several agents may scrape the same site at once), each slot >= DELAY s between its requests.
    A slot is an flock on a per-host-per-slot file that stores that slot's last request time."""

    def __init__(self, url):
        LOCK_DIR.mkdir(exist_ok=True)
        host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
        base = re.sub(r"[^a-z0-9.-]", "_", host)
        self.paths = [LOCK_DIR / f"{base}.{i}.lock" for i in range(SLOTS_PER_HOST)]

    def __enter__(self):
        import fcntl, random
        self.f = None
        while self.f is None:
            for path in random.sample(self.paths, len(self.paths)):  # take any free slot
                f = open(path, "a+")
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.f = f
                    break
                except BlockingIOError:
                    f.close()
            if self.f is None:
                time.sleep(0.2)
        self.f.seek(0)
        try:
            last = float(self.f.read().strip() or 0)
        except ValueError:
            last = 0.0
        wait = DELAY - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        return self

    def __exit__(self, *exc):
        import fcntl
        self.f.seek(0); self.f.truncate(); self.f.write(str(time.time())); self.f.flush()
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()
        _last[0] = time.time()
        return False


def fetch(url, data=None, headers=None, method=None, retries=2, timeout=40):
    """GET (or POST if data) -> (status, text, final_url). Sleeps to keep DELAY between requests."""
    h = {"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip, deflate",
         "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"}
    h.update(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data, doseq=True)
    if isinstance(data, str):
        data = data.encode()
    for attempt in range(retries + 1):
        STATS["requests"] += 1
        try:
            req = urllib.request.Request(url, data=data, headers=h, method=method)
            with host_slot(url):
                r = _opener.open(req, timeout=timeout)
                raw = r.read()
            enc = r.headers.get("Content-Encoding", "")
            if enc == "gzip":
                raw = gzip.decompress(raw)
            elif enc == "deflate":
                raw = zlib.decompress(raw)
            cs = r.headers.get_content_charset() or "utf-8"
            return r.status, raw.decode(cs, errors="replace"), r.geturl()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503):
                raise Blocked(f"{e.code} {url}")
            if e.code == 404:
                return 404, "", url
            if attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries:
                raise
            time.sleep(5)


def cookies():
    return _jar


def text(s):
    """HTML fragment -> single-spaced plain text."""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\s*\n\s*", "\n", s)).strip()


def oneline(s):
    return re.sub(r"\s+", " ", text(s)).strip()


def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def words(s, n=40):
    w = (s or "").split()
    return " ".join(w[:n]) + (" ..." if len(w) > n else "")


def num(s):
    """'£7,500.00' -> 7500 (int if whole)."""
    s = re.sub(r"[\s\u00a0\u202f]", "", str(s or ""))
    m = re.search(r"\d[\d,.]*", s)
    if not m:
        return None
    v = m.group(0).rstrip(".,")
    if re.search(r",\d{1,2}$", v) and "." not in v:  # French decimal comma
        v = v.replace(",", ".")
    v = v.replace(",", "")
    try:
        f = float(v)
    except ValueError:
        return None
    return int(f) if f == int(f) else round(f, 2)


CURRENCY = {"£": "GBP", "€": "EUR", "CHF": "CHF", "GBP": "GBP", "EUR": "EUR"}


def row(**kw):
    """Schema row (all columns, blanks for unknown) + extra keys 'images' and '_source'."""
    r = {c: "" for c in COLUMNS}
    for k, v in kw.items():
        r[k] = "" if v is None else v
    r.setdefault("images", [])
    r["date_checked"] = r.get("date_checked") or TODAY
    return r


def emit(r):
    print(json.dumps(r, ensure_ascii=False), flush=True)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def base_args(desc):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("--limit", type=int, default=0, help="stop after N listings (0 = all)")
    p.add_argument("--dry-run", action="store_true",
                   help="list stage only: print listing-level rows without fetching detail/price pages")
    p.add_argument("--delay", type=float, default=DELAY, help="seconds between requests (default 2)")
    return p


def setup(args):
    global DELAY
    DELAY = max(1.0, args.delay)


def hot_tub_from_text(txt, listed=False, whole_property=True):
    """Classify hot tub from free text (+ whether a facility list includes it)."""
    t = (txt or "").lower()
    kw = r"(hot[ -]?tubs?|jac+u+z+is?|spa bath|whirlpool|bains? nordiques?|nordic bath|outdoor spa|bains? (?:à|a) remous|baignoire balnéo)"
    if not (re.search(kw, t) or listed):
        return ""
    sents = [x for x in re.split(r"(?<=[.!?;])\s+|\s+-\s*(?=\w)|\n", t) if re.search(kw, x)]
    near = " ".join(sents)
    SH = r"(shared|communal|collective|collectif|commun|partagée?)"
    if (re.search(SH + r"\s+(?:outdoor\s+|indoor\s+|heated\s+)?" + kw, near)
            or re.search(kw + r"[^.;]{0,25}\b" + SH, near)
            or re.search(r"(residence|hotel|building)'?s? (spa|wellness)", near)) \
            and not re.search(r"private|privatif|privé", near):
        return "shared"
    if re.search(r"outdoor|outside|terrace|terrasse|balcon|garden|jardin|deck|open[- ]air|ext[ée]rieur", near):
        return "private-outdoor" if whole_property else "yes-type-unknown"
    if re.search(r"indoor|inside|spa room|wellness room|int[ée]rieur", near):
        return "private-indoor" if whole_property else "yes-type-unknown"
    return "private (location not stated)" if whole_property else "yes-type-unknown"
