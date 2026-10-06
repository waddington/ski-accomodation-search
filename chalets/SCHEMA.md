# Chalet CSV schema

Every collector writes rows with exactly these columns (header row first), one file per collector in `chalets/raw/`.
Include **every** chalet found — out of budget, too big, no hot tub, whatever. Filtering is done later by script.
Leave a cell blank if unknown; never guess.

| Column | Meaning / format |
| --- | --- |
| chalet_id | slug: `<operator>-<chalet-name>`, lowercase, hyphens (e.g. `icebreaker-lisiere-du-bois`) |
| chalet_name | as the operator names it |
| operator | company running/letting it |
| village | village name matching `resorts/resorts_raw.csv` `village` where possible |
| ski_area | e.g. Paradiski, Espace Killy |
| country | France / Austria / Switzerland / Italy |
| sleeps_min | integer (blank if one number given) |
| sleeps_max | integer |
| bedrooms | integer |
| bathrooms | integer |
| property_type | chalet / apartment / chalet-hotel / hotel / combined-booking / room |
| board | catered / half-board / breakfast-only / self-catered / chalet-hotel / catered-or-self |
| catering_detail | e.g. "breakfast, afternoon tea, 6x 3-course dinners, unlimited wine" |
| hot_tub | private-outdoor / private-indoor / private (location not stated) / shared / yes-type-unknown / none / unknown |
| sauna | yes / no / unknown |
| other_facilities | short list: steam, pool, boot warmers, games room, fireplace |
| distance_to_lift_m | integer metres if stated |
| ski_in_out | yes / no / partial / unknown |
| changeover_day | Saturday / Sunday / flexible / unknown |
| price_week_20_27_mar_2027 | price for the week starting 20 Mar (or 21 Mar if changeover is Sunday) if shown (number only) |
| price_basis | per-person / whole-chalet |
| price_currency | GBP / EUR / CHF |
| price_type | exact-week / season-from / season-range / quote-needed |
| price_range_low | lowest published 2026/27 price (number), same basis/currency |
| price_range_high | highest published 2026/27 price |
| price_per_bed | per-person/per-bed price if the operator also sells by the bed (number, same currency) |
| price_includes | e.g. "flights, transfers, drinks" or "accommodation + catering only" |
| available_20_27_mar | yes / no / unknown |
| combines | for combined-booking rows: chalet_ids it is made of, `;`-separated |
| same_as | chalet_ids of probable duplicates under another name (judgement call), `;`-separated |
| description | ≤ 40 words, factual |
| url | the chalet's own page |
| listed_on | semicolon-separated site names where this chalet appears (operator site + aggregators) |
| found_via | collector name, e.g. `pilot-les-coches` |
| image_count | number of images downloaded |
| image_dir | `chalets/images/<chalet_id>/` |
| date_checked | YYYY-MM-DD |
| notes | anything else useful (e.g. "price shown only via booking widget") |

Images: save up to 5 per chalet to `chalets/images/<chalet_id>/01.jpg` … (exterior, hot tub, living area, bedroom, view preferred). Skip logos/icons. Keep originals' extension.

## Derived columns (added by the merge script, not by collectors)

`has_hot_tub`, `has_private_hot_tub`, `has_sauna`, `is_catered`, `sleeps_8_to_10`, `has_exact_week_price`, `price_pp_gbp_est`, `under_budget` — yes/no flags computed from the columns above so every collector is treated the same.

## Browser access

If WebFetch can't read a site (JS-only prices, booking widgets, 403s, search forms, pagination), use the local browser: see `tools/README.md`.

## Access issues log (required)

Each collector also writes `raw/<collector>.issues.csv` (header: `raw/ISSUES_HEADER.csv`), one row per thing it got stuck on:

| Column | Meaning |
| --- | --- |
| collector | e.g. pilot-les-coches |
| site | site name |
| url | page that failed |
| chalet_id | if it concerns one chalet, else blank |
| problem | blocked-403 / js-widget / login-required / captcha / no-price-published / no-detail-page / timeout / other |
| missing | what we couldn't get, e.g. "price for 20 Mar week; bedrooms" |
| tried | webfetch / browse.mjs / navigate-script / search |
| date | YYYY-MM-DD |

The merge script also adds a `missing_fields` column to each chalet listing key fields left blank.
