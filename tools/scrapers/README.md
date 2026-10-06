# Scrapers

Reusable, LLM-free scrapers (python3 stdlib only, no browser). Each prints **JSON lines** to stdout whose keys are
the `chalets/SCHEMA.md` columns (blank = unknown) plus `images` (list of URLs) and a few private `_source*` keys.
Progress goes to stderr. Polite: one request at a time, 2 s between requests (`--delay`), stops on 403/429.
Every scraper takes `--limit N` and `--dry-run` (list stage only, no detail/price requests).
Validation against already-collected villages: `VALIDATION.md`.

## One command per source: `ingest.py`

```
python3 tools/scrapers/ingest.py <task_id> <scraper> <scraper args...> [--ingest-dry-run] [--no-images]
```
Runs the scraper and appends to `chalets/raw/<task_id>.csv` through `tools/append_row.py`:
known chalets (same URL, or same normalised name in the same ski area, `match.py`) get a row with the existing
`chalet_id` + `listed_on` + `found_via` + only the fields that were blank, and this source's price/availability
in `notes` (prices from different sites are never mixed into the known row's price columns); new chalets get
`<source or operator>-<name>` ids, all fields, and up to 5 images via `tools/save_images.py`. Re-running is safe
(rows already in the task file are skipped). Prints a summary (new / known / catered / hot tub / sleeps 8-12 /
free 20 Mar, and catered + hot tub + free near-fits). Try `--ingest-dry-run` first. You still log the site in
`<task_id>.sites.csv` and do `queue.py done` yourself. Village is taken from the source; check it for sources
that only know the resort (Sno: blank, pass `--village-default`; Ski Line: API resort name; Ingenie/3V: quarter map).

**Repair pass** (`--override`, task id `enrich-fix-<source>-<village>`): for known rows whose url is on the scraper's own
site, writes the scraper's non-blank structural fields (village only when specific, names only over placeholders, url only
over a url shared by several chalets; never prices, never blanks). Fields set in `corrections.csv` / `enrich*.csv` are left
alone; a collector's appended correction row (same file, later row) is written instead of the scraper value, because
`build_chalets.py` keeps the *first* non-blank value and those corrections had never taken effect. New units are not written.

## Status

| scraper | source(s) | status | usage | known gaps |
| --- | --- | --- | --- | --- |
| `allchalets.py` | allChalets.com | **READY** (fixes 2026-10-06, see below) | `allchalets.py les-menuires` (location slug or village name; `--contact` adds advertiser name, +1 req/listing) | operator rarely named (advertiser contact only with `--contact`); hot-tub *location* often "private (location not stated)"; when a listing has catered **and** self-catered rates the catered rate is used (other in notes); calendars are sometimes unmaintained (then `unknown`); satellite village only when the headline or the listing's own 'Location Details' names it (Val d'Isère→La Daille/Le Fornet, Alpe d'Huez→Vaujany/Oz/Auris/Villard-Reculas/Huez, St Gervais→Le Bettex/St-Nicolas), otherwise the resort crumb |
| `les3vallees.py` | Orchestra tourist-office sites: reservation.les3vallees.com (default), `--site combloux` (reservation.combloux.com) | **READY** (les3vallees, combloux 2026-10-06) | `les3vallees.py les_menuires --min-pax 8` (stations: Courchevel, LA_TANIA, meribel, Brides-les-Bains, Saint-Martin-de-Bell, les_menuires, Val_Thorens, Orelle); `les3vallees.py --site combloux --capacity-scan` (no station) | no season range (only "from" + 20 Mar stay price); agencies not named (ref + image host in notes); "rooms" in titles are pièces not bedrooms; sauna `unknown` unless mentioned; Combloux product pages have no capacity → `--capacity-scan` (PAX filter passes, ~+60 requests); Combloux SERP total counts duplicate offers (89 offers = 83 units) — passes rotate sort orders until stable |
| `ingenie.py` | Ingenie-platform tourist-office sites: `lesmenuires` (locationlesmenuires.com), `tignes` (booking.tignes.net), `serrechevalier` (booking.serre-chevalier.com), `valdisere` (booking.valdisere.com, 2026-10-06) | **READY** (lesmenuires, tignes, valdisere) / limited (serrechevalier: untested beyond smoke test) | `ingenie.py tignes --quarter IBREVIERES,IVILLARET` (Brévières = 2 quarters); `ingenie.py lesmenuires --quarter IBRUYERES --min-sleeps 8 --adults 8`; `ingenie.py valdisere --quarter FRRASAVADAILL` (La Daille; Le Fornet = `FRRASAVAFORNE`; other codes are Val d'Isère); `--list-quarters`, `--sites` | no season range (weekly planning is a JS widget); units not in the dated search are `unknown` (+ pass2 note); Les Menuires detail pages lack structured capacity for some units (regex on description); hot tub only from explicit text (the combined 'Sauna/Jacuzzi/Steam room' picto is not a hot tub); residence apartments' jacuzzi = `shared` unless text says private; Val d'Isère has no 'type' field (chalet/apartment from the name) |
| `skiline.py` | Ski Line JSON API (api.skiline.co.uk) + property pages | **READY** (structure ≥94%; prices straight from API, no collector rows to compare) | `skiline.py "Les Menuires"` (API resort name; `--list-resorts`), `--chalets-only`, `--sitemap les-menuires` adds sitemap-only pages | names the operator; prices are GBP pp packages (usually with flights) so they never match operator/aggregator prices; "Les Arcs" includes Peisey-Nancroix (flagged in notes); bedrooms only when stated in text |
| `igluski.py` | Iglu Ski listing pages | limited (usable; sleeps agree only 80% with other sources, prices unvalidated) | `igluski.py les-menuires` (Iglu village slug; `--kind apartments|hotels`) | price only for 20/21 Mar departures (dated search, ad=8 but often "based on 2 sharing"); no season range; operator = supplier code (ING = Inghams); sleeps can differ from operator figure |
| `sno.py` | Sno (sno.co.uk) | **READY** | `sno.py tignes` (Sno list slug, `-chalets` optional; area slugs like `espace-killy` miss chalets: run resort slugs too) | slow (3-4 requests/chalet incl. the 20 Mar POST; `--no-price` = 1); operator never named; village blank (notes list villages mentioned; pass `--village-default`); Sno often prices only 2 sharing (noted). Sites lane only — village collectors shouldn't use Sno |
| `simplyvaldisere.py` | Simply Val d'Isère (simplyvaldisere.com, agent for YSE, Le Ski, VIP, Consensio, Cimalpes...) (2026-10-06) | **READY** | `simplyvaldisere.py la-daille-le-cret` (areas: la-daille-le-cret, le-fornet-laisinant, resort-centre, legettaz, joseray-chatelard; aliases daille, fornet, centre, all; `--list-codes`) | operator from the rate-table code (YSE, BMST=Build My Ski Trip, HIP=Hip Hideouts, Le Ski, CIM=Cimalpes, SF=Ski France, VIP, SW=Skiworld, ING=Inghams, CON=Consensio, Bramble, Purple; COV/VAG/VLO/CT/MC/OOAK unmapped → notes); range = min/max of the 2026-27 table (collectors used the 'Pricing Guide' text, which is often narrower); weeks missing from a table → availability `unknown`; 'La Daille & Le Cret' area: Le Crêt/Cacholet units → Val d'Isère; images are often < 400 px (save_images skips them) |
| `msem.py` | MSEM tourist-office booking API (services.msem.tech): `stgervais` (resort 569, saintgervais.com) (2026-10-06) | **READY** (St-Gervais) | `msem.py stgervais [--adults 8]`; other offices: `--resort-id N --channel OT-N --page-url <booking page> --village X` (ids are in the page's `MseM.lodging` options; none found cheaply besides 569) | no season range (dated offer only); offer price excludes tourist tax (collectors' rows include it: +3-10 %); private owners → operator "Private owner" (billing names are people, never copied), agencies → billingName (e.g. CIMALPES); url = `<booking page>?slug=<slug>` (match.py keys on `slug`); village from MSEM sector/description head only |

### Fixed 2026-10-06 (collector spot-checks)

- `ingenie.py`: picto/label "Sauna/Jacuzzi/Steam room" (IEQUIP-ISPAS) no longer counts as a hot tub (it set residence
  apartments to yes-type-unknown and chalets Merveilles/Monts/La Perle/Lys Martagon to private); it now means sauna=yes unless the
  detail line "Pool, Steam room, Sauna : ..." lists what is really there; jacuzzi/hot tub/spa bath/**bains à remous**/whirlpool/
  bain nordique in text = hot tub, `shared` for residence apartments (Altaviva, Denali, Yéti, CGH) unless the text says private.
  New `valdisere` site (ZONEGEO areas, NBMAXI capacity, Val d'Isère detail layout; boilerplate "Aquasportif (Wellness...)" and
  footer no longer make every unit's sauna `unknown`).
- `allchalets.py`: header parsed only after the listing id (menu text made self-catered listings `catered-or-self`); studios
  ("Sleeps 4, 1 bathroom", no bedrooms) get sleeps; inconsistent headers (Les Sources de l'Isère "Sleeps 7, 7 bedrooms,
  14 bathrooms") take sleeps from the description and drop the swapped bathroom count; all text fields HTML-unescaped
  (Val d&#39;Isere); satellite villages (see table); `Chalet Details` style non-names → `<Type> <id>`; changeover only
  Saturday/Sunday/flexible (all check-in days in notes); public/distance pools ("public swimming pool 1500 m") ignored.
- `common.hot_tub_from_text`: matches "bains à remous"/"bains nordiques"; splits " - " bullet lists into sentences (a
  "communal toilets" bullet made a terrace hot tub `shared`).
- `ingest.py` / `tools/save_images.py`: image URLs are separate argv entries (a "url1 url2" string from a hand-edited jsonl
  is split); save_images prints why images were skipped (< 15 kB or < 400 px wide), ingest reports "images: none saved".
- `match.py` / `validate.py`: URLs keep listing-id query params (`s_pid`, `slug`, ...) — all Orchestra
  `/product?s_pid=N` pages used to normalise to the same URL.

Not built: accommodation.alpedhuez.com (Next.js app, not Ingenie; needs browser or its JSON API worked out),
Vertical Booking (Cervinia, Cloudflare captcha).

## Speed (measured, 2 s/request)

| scraper | example | time |
| --- | --- | --- |
| allchalets | Les Menuires, 105 listings (detail + calendar each) | 7 min 10 s (~4 s/listing); Les Coches 21 listings ~1.5 min |
| les3vallees | Les Menuires `--min-pax 8`, 105 units | 3 min 50 s |
| ingenie | Tignes Les Brévières, 42 units | ~1.5 min; Les Menuires Bruyères 8+ (15 units) 34 s |
| skiline | Les Menuires, 21 properties | 84 s; Reberty 2000 (9) 36 s |
| igluski | Les Menuires, 22 chalets | ~1 min |
| sno | Tignes, per chalet | ~8-10 s (POST + redirect + retries) |
| simplyvaldisere | La Daille + Le Fornet, 48 pages | 1 min 54 s (1 request/page); all 495 pages ~17 min |
| msem | St-Gervais, 81 lodgings (detail each) | ~3 min (83 requests) |
| les3vallees `--site combloux --capacity-scan` | 107 units | ~6-7 min (186 requests) |
| ingenie valdisere | La Daille + Le Fornet, 102 units | ~4 min (113 requests) |

## Files

- `common.py` — polite HTTP (`fetch`), HTML-to-text, schema `row()`, `emit()`, `hot_tub_from_text()` classifier.
- `match.py` — known-chalet matcher (URL incl. listing-id query params, then normalised name within the same ski area via `resorts/resorts_raw.csv`).
- `validate.py <jsonl> [--source-url host] [--village x] [-v]` — compare a scraper run with existing rows
  (price/availability fields only against rows whose url is on the same site).
- `ingest.py` — see above.

## Notes per source (URL patterns)

- **allChalets**: search `/search/location:<slug>/page:N` (static, 20/page, total in "Has returned N holiday rentals").
  Detail `/holiday-rentals/<id>-<type>-in-<loc>-<country>`: rate table (From/To/Check-in/Catering/Pricing/Weekly/nightly),
  facility list. Calendar: `GET /calendar/<slug>?from=2026-12-01&months=5` with `X-Requested-With: XMLHttpRequest`
  (rails UJS JS; `td.day` classes booked/available/changeover-*, check-in tooltips with price). Enquiry page
  `/holiday-rentals/<slug>/enquiry` names the advertiser contact. Residence parent listings are skipped by default.
  **Les Menuires has 108 listings (6 pages) — the browser-scroll collector found only 20.**
- **3 Vallées**: `/en/serp?s_c.ACCOMMODATION=apartment,chalet&s_c.Station=<code>[&s_c.PAX=N]&page=N` (20/page; byPage>20 breaks);
  dated: add `&s_dpda=2027-03-20&s_minMan=7&adultsNumber=N&childrenNumber=0`. Product page `/en/product-<id>-...` static.
- **Ingenie** (Les Menuires, Tignes, Serre Chevalier): undated `/search?mid=<m>&action=result&sans_dates=1&type_prestataire=<T>&affiner=1&criteres[]=IQUART[<code>[<T>&ordre_type=alphabetique&page=N`
  (**default order is random per request — always add `ordre_type=alphabetique`**), dated `/booking?cid=<c>&MOTEUR_TYPES_PRESTATAIRE=MOTEUR_HEBERGEMENT&action=result&type_prestataire=<T>&datedeb=20/03/2027&datefin=27/03/2027&duree=7&adultes=N&enfants=0...`.
  Serre Chevalier has no area criterion: cards carry `SECTEUR-<code>` classes and are filtered client-side.
- **Val d'Isère (Ingenie)**: same URLs as Tignes with mid=cid=3, type G, area criterion `criteres[]=ZONEGEO[<code>[G` (not IQUART;
  the collector's IQUART search returned nothing). Cards: `ZONEGEO-<code>-G` spans (several per card), `NBMAXI-<n>PERS`.
- **Combloux (Orchestra)**: `/serp?lang=en_US&s_c.ACCOMMODATION=apartment,chalet,appartement_chalet,chalet_mitoyen&type=...` (no /en,
  no Station), sorts `s_st=base_price|base_price_desc|c.LIFTS_CBX`; product `/product?lang=en_US&s_pid=N`.
- **Simply Val d'Isère**: `/sitemap.xml` → `/accom/<area>/<slug>` (static); rate tables `<div class="bf-priceavail">` titled
  "<CODE> 2026-27 <name>", rows day/month/year spans, price, availability.
- **MSEM**: see `msem.py` docstring (lodgings GET, offers POST, detail POST `/api/lodging/accomodation/<slug>`).
- **Ski Line**: `https://api.skiline.co.uk/?page=0&page_size=100&...&resorts[]=<name>&showAccommodationOnly=1&showAllResorts=true` (+`boards[]=`),
  `/prices?ext_node_id=<id>&date_min=..&date_max=..` (all departures), `/options?...` (resort facet). Browser UA + Referer.
- **Iglu**: `/ski-holidays/<village>-ski-chalets?&flex=2&nts=7&ad=2&ch=0&perpage=10&page=N&sort=0&state=4` (+`&date=20032027&ad=8`).
- **Sno**: see `chalets/raw/site-sno.checkpoint.md`.
