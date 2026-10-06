# Scraper validation (2026-10-06)

Method: run the scraper on villages already collected by LLM agents, then `python3 tools/scrapers/validate.py <run.jsonl> --source-url <host> [--village x] -v`.
Rows are matched to existing chalets by URL, else by normalised name within the same ski area (`match.py`).
Agreement = equal values where both sides are non-blank; `unknown` availability/hot-tub type is skipped.
**Price, currency, changeover and availability are only compared against rows whose own URL is on the same site**
(a chalet first collected from its operator's site has operator prices; comparing those with an aggregator's price is meaningless).
`has_hot_tub` / `has_sauna` = the yes/no flags the filter actually uses (`hot_tub` = exact type, `sauna` = exact value incl. no vs unknown).

"Coverage" = known rows with a URL on that site in the tested villages that the scraper did NOT return (target 0).

## allchalets.py — READY

Villages: Les Menuires (108 listings / 6 pages), Les Coches, Montchavin, Tignes Les Brévières, Tignes Les Boisses, Cervinia (final code).
Scraped 181 (105 + 21 + 18 + 26 + 5 + 6) · matched existing 83 · new 98 · coverage: 0 known allChalets rows missed in these villages.

| field | agree | % |
| --- | --- | --- |
| sleeps_max | 79/83 | 95 |
| bedrooms | 81/82 | 99 |
| board | 58/64 | 91 |
| has_hot_tub | 74/78 | 95 |
| hot_tub (exact type) | 56/78 | 72 |
| has_sauna | 78/83 | 94 |
| price 20 Mar | 14/15 | 93 |
| price currency | 25/25 | 100 |
| price range low / high | 21/25, 22/25 | 84 / 88 |
| changeover | 10/10 | 100 |
| available 20 Mar | 17/17 | 100 |

Disagreements, by cause: hot-tub *location* (collectors used photos/other sites → private-outdoor/indoor; the scraper says "private (location not stated)" unless the text says where);
listings with both catered and self-catered rates (scraper uses catered, collector sometimes self-catered: Les Coches V, Chalet Refuge — the other rate is in notes);
residence apartments whose facility list includes the residence jacuzzi/sauna (Le Boulier: scraper `yes-type-unknown`, collector `none`); one €16,100 per-person typo rate (now dropped as an outlier, noted).
**Big coverage finding: allChalets Les Menuires has 108 listings; the browser-scroll collector found 20** (pagination `/page:N` was missed). Among the 86 new rows: 6 catered + hot tub + free 20 Mar (dry-run ingest).

## les3vallees.py — READY

Village: Les Menuires `--min-pax 8` (105 units, 36 bookable 20-27 Mar for 8). Matched 34 · new 71 (units not free on 20 Mar, which the collector skipped) · coverage: 0 missed.

| field | agree | % |
| --- | --- | --- |
| sleeps_max | 34/34 | 100 |
| bedrooms | 11/12 | 92 |
| board | 34/34 | 100 |
| has_hot_tub | 5/6 | 83 (the 1 "miss" is Chalet Necou: page lists "Spa / Hammam / Jacuzzi", collector said none) |
| has_sauna | 34/34 | 100 |
| price 20 Mar | 21/21 | 100 |
| available 20 Mar | 34/34 | 100 |
| changeover | 21/21 | 100 |

## ingenie.py — READY (lesmenuires, tignes); serrechevalier limited

- Les Menuires, quarter IBRUYERES, `--min-sleeps 8 --adults 8`: 268 units in quarter, 38 rows 8+. Matched 34 · new 4 · coverage 0 missed (after fixing capacity: P&V Valmonts card says 7 but title "8 pers" → kept).
  sleeps 33/34 (97) · board 33/33 (100) · has_hot_tub 6/6 · hot_tub type 6/6 · has_sauna 31/31 · price 20 Mar 5/5 · available 5/5 · changeover 5/5.
- Tignes, quarter IBREVIERES (run before the multi-quarter fix): 42 units. Matched 19 · new 23 · coverage: 1 missed (Chalet du Sarrasin is in quarter **IVILLARET** "Villaret des Brévières" → use `--quarter IBREVIERES,IVILLARET`; now 43 units incl. Sarrasin).
  sleeps 17/19 (89: Lo Soli 12 vs 10 and Sachette 14 vs 12 — capacities differ between sources) · bedrooms 16/18 · board 10/12 (Sources de la Davie "chef on request at extra cost" — fixed: optional catering no longer sets catered; Sachette sold catered by Skiworld but self-catered here) · has_hot_tub 15/15 · has_sauna 18/19 · price 20 Mar 6/6 · available 6/6.
- Availability: units not in the dated search are now `unknown` (+ "pass2: weekly planning"), because Chalet Vithos/Delphine were free in their weekly planning but absent from the dated 8-adult search.
- Serre Chevalier: smoke-tested only (Le Monêtier 8+: 19 rows from 671 units); no collected village to compare against.

### ingenie.py re-validation after the 2026-10-06 spa fix

- Tignes 1800 (I1800, 48 units): matched 48 · coverage 0 missed · sleeps 47/48 · bedrooms 39/39 · board 48/48 · sauna 48/48 ·
  price/availability/changeover 12/12. hot_tub 18/48 against the merged rows — expected: the merged view still shows the
  first (buggy) values; the collector's corrections agree with the new output (Altaviva → `shared` from "bains à remous",
  CGH Kalinda/Lodge des Neiges spa residences → `shared`, chalets Merveilles/Monts → `none` + sauna yes).
  Lodge des Neiges C01/C06/C19 (agency AIROCBLANC): text lists only "sauna, steam room and swimming pool" → `none` (collector: shared).
- Tignes Le Lac (IALMES,IROSSET,IBECROUGE, 373 units): sleeps 75/75 · bedrooms 75/75 · board 75/75 · price/avail 8/8;
  Yéti / CGH Télémark residence jacuzzis now `shared` (were yes-type-unknown); Ski Famille chalets La Perle / Lys Martagon
  now `none` (were private-outdoor from the picto; Sno: no hot tub, steam room only).
- Les Brévières and Les Menuires Bruyères: no regressions (has_hot_tub 16/16 and 6/6, sleeps 90/97 %, prices 100 %);
  sauna differences are now `no` where collectors had `unknown`.

### ingenie.py valdisere (booking.valdisere.com) — READY

La Daille + Le Fornet (`--quarter FRRASAVADAILL,FRRASAVAFORNE`): 102 units (77 La Daille, 25 Le Fornet), 24 bookable 20-27 Mar
for 2 adults. Only 5 overlap with earlier rows (sleeps 5/5, board 5/5, has_hot_tub 5/5). The collector's search returned
nothing because Val d'Isère uses ZONEGEO, not IQUART. Rows ingested by the Val d'Isère collector *before* the detail-layout
fix have blank bedrooms (now 51/102 filled from "(N bedroom)") and sauna `unknown` (site boilerplate "Wellness").

## simplyvaldisere.py — READY

La Daille & Le Crêt + Le Fornet & Laisinant (48 pages) and all areas (495 pages): matched 86 existing rows, coverage 0
(the 11 "missing" in validate.py are rows whose Simply URL is only in notes — all scraped).

| field | agree | % |
| --- | --- | --- |
| sleeps_max | 81/85 | 95 |
| board | 74/86 | 86 (most "misses" are the same chalet sold catered by one operator and self-catered on booking.valdisere.com) |
| has_hot_tub | 54/60 | 90 |
| has_sauna | 82/86 | 95 |
| price 20 Mar | 18/18 | 100 |
| available 20 Mar | 18/18 | 100 |
| price currency | 28/28 | 100 |
| changeover | 29/36 | 81 (all 7 "misses" are collector `unknown`) |
| price range low / high | 15/28, 16/28 | 54 / 57 — the scraper uses the 2026-27 table min/max, collectors used the "Pricing Guide" sentence |

Operator codes seen (2026-10-06): OOAK 21, VAG 38, COV 25, CIM 16, VIP 16, CON 14, YSE 18, Le Ski 13, VLO 12, CT/MC 12, HIP 13,
SF 12, BMST 10, Bramble 10, Purple 3, SW 3, ING 1 (+ tables without a code). Unmapped: COV, VAG, VLO, CT, CT/MC, OOAK.

## les3vallees.py --site combloux — READY

Combloux (`--capacity-scan`): 107 units, matched 107/107 collector rows (by `s_pid` URL after the match.py fix), coverage 1
missed (product 106310 no longer in the SERP). sleeps 102/103 (99) · bedrooms 4/4 · board 107/107 · has_hot_tub 36/36 ·
price 20 Mar 83/83 · available 107/107. Sauna `unknown` where collectors wrote `no` (product pages rarely mention wellness).
SERP "total" counts offers (dated 89 offers = 83 units), so passes stop when a pass adds nothing.

## msem.py — READY (St-Gervais)

St-Gervais (resort 569): 81 lodgings, 50 bookable 20-27 Mar for 2 adults. Joined to the collector's 75 MSEM rows by lodging id
(their URLs were all the bare booking page, so validate.py cannot match them):
sleeps 62/62 · bedrooms 61/61 · board 57/57 · operator 75/75 · available 45/45 · property type 59/62 · village 58/62 (collector
placed 3 Cimalpes chalets in Le Bettex without an MSEM sector) · price 20 Mar 27/30 within 6 % (collector prices include
tourist tax; the API price does not).

## allchalets.py re-check after the 2026-10-06 fixes

Spot-checked listings from the collectors' reports: Les Sources de l'Isère 48354 → sleeps 14 (desc), bedrooms 7, bathrooms
blank, hot_tub private-outdoor; La Daille 40703/12551 studios → sleeps 4; 40704/62057 → self-catered (was catered-or-self /
blank); village "Val d'Isère"/"La Daille" unescaped; St Gervais 46911/47005/48125 → St-Gervais Le Bettex, 34713 → St-Nicolas-de-Véroce,
changeover `flexible`, unnamed Cimalpes listings → "Chalet 46911"; 20750 no longer gets "swimming pool" from the public pool line.
Full Val d'Isère run (`allchalets.py val-d-isere`, 160 listings): villages Val d'Isère 141 / Le Fornet 11 / La Daille 8, no escaped
text, no blank sleeps. Matched 46: sleeps 39/46 (85; Build My Ski Trip / Ski France quote 8-12 where allChalets says 10-14) ·
bedrooms 40/42 · board 27/44 (61: listings that offer catered **and** self-catered → `catered-or-self`, collectors took the
Sno/operator board; catered vs half-board/B&B) · has_hot_tub 43/46 · price 20 Mar 6/6 · range 10/10 · available 10/10 · changeover 5/5.

## skiline.py — READY for structure fields; prices unvalidated against collectors

No collector had written Ski Line rows, so prices could not be compared (they come straight from the API's departure list).
Villages: Les Menuires (21), Reberty 2000 (9), Tignes (16), La Plagne `--chalets-only` (53). Matched existing (other sources, by name + ski area) 19 · new 80.
sleeps 18/19 (95) · board 18/19 (95) · has_hot_tub 17/18 (94) · has_sauna 16/19 (84) · bedrooms 2/2 (only when stated in text).
Ski Line names the operator (e.g. Chalet Katie 1/2 = Ski Famille, sold anonymously on Sno) — ingest fills operators that were "unknown".

## igluski.py — limited

Villages: Les Menuires (22), Reberty (7), Tignes (22 chalets). Matched 40 (other sources) · new 11.
sleeps 32/40 (80) · bedrooms 6/9 · board 37/40 (92) · has_hot_tub 36/40 (90) · has_sauna 35/40 (88).
Sleeps disagree mostly because Iglu quotes different capacities than the operator/Sno (e.g. Le Corbeau/Aigle/Faucon 17 vs 15).
Prices: only the 20/21 Mar departure price (often "based on 2 sharing"), no season range; not validated (no prior Iglu rows).

## sno.py — READY

Village: Tignes (`sno.py tignes --limit 14`). Matched 14/14 (all already collected by the site-sno agent).
sleeps 13/14 (93) · bedrooms 7/7 · board 14/14 · has_hot_tub 14/14 · has_sauna 13/14 · price 20 Mar 7/8 (88; the miss is £1353 vs £1363 — Sno prices moved since yesterday) ·
range low/high 8/9, 7/9 (same drift) · available 11/11 · changeover 11/12.

## ingest.py

Dry-run tested on every run above (`--ingest-dry-run`): known chalets reuse their ids (URL or name match), new ids are
`<source>-<name>` following the collectors' prefixes (`allchalets-…`, `les3vallees-…`, `tignesreservation-…`, `lesmenuires-…`, `iglu-…`, `sno-…`; Ski Line/Iglu use the operator slug when named),
re-runs skip rows already in the task file. Not run against a real task file by this agent (tooling agent writes only under tools/scrapers/).
