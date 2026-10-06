# Pilot report — Les Coches + Tignes Les Brévières

_Run 2026-10-05 · 2 collectors · ~35 min each_

**Result:** 102 chalets/properties collected (42 Les Coches/Montchavin, 60 Brévières/Boisses), 99 with photos (284+ images, 232 MB). 10 pass the current filters; only 3 of those are confirmed catered + available with a price: **Neus** (White Horizon, sleeps 10, private hot tub, £653pp), **Hattiers Apartment 1 and 2** (Chalet Chardons, sleeps 8–10, ~£450–480pp, hot tub unknown). The other 7 pass only because key fields are unknown.

Live data: `chalets_all.csv` (with `removed_by`), `chalets_filtered.csv`, `access_issues.csv`, `site_yield.csv`.

## Near misses worth a look

| Chalet | Why it's out | Detail |
| --- | --- | --- |
| Club Alpine Caribou / Lièvre Blanc / Myrtille (Montchavin) | sleeps 12; Sunday changeover | £7,700 whole chalet ≈ £770pp for 10; private hot tubs |
| Ibex (White Horizon, Brévières) | sleeps 12 | £665pp for 12 (£7,975 whole), available, private hot tub |
| Club Alpine Edelweiss / Snowflake | sleeps 12+ | £8,700 whole chalet, available |
| Coeur des Brévières (Chardons) | sleeps 40, shared | €849pp by the room, hot tub, available |

## Availability

The week before Easter is filling: 30 of 102 are already booked, including all of Alpine365, most of Icebreaker (Castor, Mont Rosset, Jardin Alpin 1, Vieille Grange, Belle Vue) and 4 of 6 White Horizon chalets.

## Which sources were worth it (site_yield.csv)

| Source type | Yield | Verdict for the full run |
| --- | --- | --- |
| Operator's own site | All new, best data (exact-week prices, availability) | Always do first |
| allChalets | 38 + 30 found, 35 new | Best aggregator by far — use for every village |
| Official resort booking site (Tignes Réservation) | 23 found, 18 new (mostly self-catered) | Use per resort where one exists |
| Alpine Answers, See Tignes, Tignes Spirit | 1–2 new each | Worth a quick pass |
| ChaletFinder, Chalets Direct | 25 + 29 found, 1 new | Mostly duplicates — use only to fill `listed_on` |
| Sno, Ski Line | 0–1 new; no village filter | Low value per village; check once per ski area |
| Heidi | blocked (HTTP 429, empty render) | Needs a different approach (headed browser) |

## Access lessons

- Most JS widgets were bypassed by calling the widget's data endpoint directly (chaletmanager JSONP, ninja-tables AJAX, Smoobu, mychaletbooking HTML).
- Ice and Fire (403) and SkiAffinity/Skiworld month tabs needed Playwright — scripts kept in `tools/scratch/`.
- The shared WebSearch budget (200) ran out in both collectors; at scale, collectors should rely on browsing site search pages, not WebSearch.
- Collectors must keep helper scripts in their own private temp folder (a shared `/tmp` helper briefly cross-wrote logs).

## Schema changes made after the pilot

Added `property_type`, `changeover_day`, `price_per_bed`, `combines`, `same_as`; new values `hot_tub = private` / `yes-type-unknown` and `board = breakfast-only`. Pilot rows have these blank (details are in `notes`) — backfill in an enrichment pass.

## For the full run

- Images: ~2.3 MB per chalet → ~3.5 GB for 1,500 chalets. Consider resizing to ~1600 px wide on download.
- Per village: operators present there → allChalets → official resort booking site → resort guide site. Aggregators with no village filter (Sno, Ski Line, Iglu, Heidi) once per ski area, assigning village per listing.
