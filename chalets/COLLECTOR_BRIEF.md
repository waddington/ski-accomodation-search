# Collector brief (read fully before starting a task)

Project: `/home/kai/Documents/Misc/ski-chalet-finder`. We are finding every chalet that could suit a group of 8–10, catered, hot tub, Sat 20 – Sat 27 March 2027, ~£750pp — but **collect everything you find** (any size, price, board, hot tub or not). Filtering happens later in `chalets/build_chalets.py`.

## Hard rules

1. **One thing at a time.** One site, one page, one chalet at a time. No parallel requests, no parallel sub-agents, no background jobs. The user has local LLM limits and sites rate-limit.
2. **Be polite to sites.** At most 2 requests to the same website at once across ALL agents (user rule); the scrapers enforce this automatically via tools/scrapers/common.py. When browsing by hand, wait ~2 s between page loads on a site. If you get 429/403/captcha: stop that site, log it in issues, move on.
3. **Write as you go.** Append each chalet the moment it's done; the user watches a live dashboard.
4. **Only write your own files** (named below). Never use helper scripts in `/tmp` you didn't write; keep scratch files in `/home/kai/.claude/jobs/44718792/tmp/<task_id>/`. Browser scripts go in `tools/scratch/<task_id>-*.mjs`.
5. **Capacity = the operator's stated figure** ("sleeps 6", "6 guests", the guest count prices are quoted for). Never add sofa beds or extra beds to `sleeps_max`; mention them in `notes`.
6. **Don't guess.** Leave a cell blank if unknown. Record evidence for anything non-obvious in `notes`.
7. **Don't rely on WebSearch** — its budget is shared and small. Navigate sites directly (their own search, menus, sitemaps, pagination).

## Files (per task, `<task_id>` from the queue)

| File | How |
| --- | --- |
| `chalets/raw/<task_id>.csv` | chalet rows: `python3 tools/append_row.py chalets/raw/<task_id>.csv '<json>'` — columns in `chalets/SCHEMA.md` |
| `chalets/raw/<task_id>.issues.csv` | everything you got stuck on: `python3 tools/append_row.py chalets/raw/<task_id>.issues.csv '<json>' --header=chalets/raw/ISSUES_HEADER.csv` |
| `chalets/raw/<task_id>.sites.csv` | one row per site you searched (yield): `--header` with columns `collector,site,search_url,listings_found,new_chalets,already_known,access,notes` — create the header file in your scratch dir |
| images | `python3 tools/save_images.py <chalet_id> <url1> <url2> … [--referer=<page>]` → prints count for `image_count`; prefer exterior, hot tub, living room, bedroom, view |

Queue status (dashboard shows it):
- start: `python3 tools/queue.py start <task_id> --file=chalets/raw/<task_id>.csv`
- finish: `python3 tools/queue.py done <task_id> --rows=N --new=N --issues=N --notes="one line summary"`
- or `failed` / `skipped` with `--notes`.

## Avoiding duplicates

Before adding a chalet, look it up with `python3 tools/find_chalet.py <name> [--village <village>]` (fast; includes rows other agents wrote seconds ago). Don't read the whole of `chalets/chalets_all.csv` into context. If the chalet is already there (same operator + name, or clearly the same property): **reuse its `chalet_id`** and write a row with that id containing only what you add — at minimum `chalet_id`, `listed_on` (your site name) and `found_via` — plus any fields that were blank. Probable-but-unsure duplicates: new row, and put the other id in `same_as`.

`chalet_id` = `<operator-slug>-<chalet-name-slug>`, lowercase, hyphens. If the operator is unknown use the site slug.

## Getting the data

- Operator sites: find every chalet; for each open its page; get the price **for the week starting Sat 20 Mar 2027** (or Sun 21 Mar if they change over on Sundays — set `changeover_day`) and availability. Also the 2026/27 low/high price range.
- JS booking widgets: first look for the data endpoint the widget calls (network/JSON/JSONP, e.g. chaletmanager, mychaletbooking, ninja-tables, smoobu) and fetch it directly; else drive it with Playwright (`tools/README.md`, `tools/example-navigate.mjs`): click month tabs, pick dates, set guests 8–10, paginate.
- `node tools/browse.mjs <url> <scratch outdir> [--click=sel]` renders a page and dumps text, html, image URLs, links, screenshot.
- Hot tub: look in descriptions, facilities lists, floorplans, image captions/alt text and the photos themselves, reviews.

## Finish

Return a short report: chalets written (new vs already known), how many catered / hot tub / sleeps 8–10 / free 20 Mar, any near-fits (catered + hot tub + available, any size), access problems, anything the user should know.

## Big sites (site tasks)

Only collect chalets in villages listed in `resorts/resorts_raw.csv` (the full list; filtering is later). Work through the site resort by resort. Keep a checkpoint at `chalets/raw/<task_id>.checkpoint.md` (resorts done, resorts left, URL patterns that work). If the site is large and you've done a solid chunk (~40 chalets or your context is getting heavy), stop at a clean point and run `python3 tools/queue.py partial <task_id> --rows=N --notes="done: …; remaining: …"` — the next agent resumes from the checkpoint. If a checkpoint already exists when you start, read it and continue from it.

## Village tasks

For one village, search in this order (one at a time):
1. **Local operators**: companies in `sites/sites.csv` whose `area` mentions the village/resort, plus any you discover (resort guide sites, the official site's partner lists).
2. **allChalets** village/location search (best aggregator in the pilot).
3. **The official resort / ski-area booking site** — most big areas have one, e.g. reservation.les3vallees.com (3 Vallées), booking.tignes.net, booking.serre-chevalier.com, and the La Plagne / Les Arcs / Val d'Isère / Val Thorens / Alpe d'Huez / Les 2 Alpes / Morzine-Avoriaz / Portes du Soleil tourist-office booking sites. Find it from the resort's official tourist-office site. Filter to the village; chalets AND apartments (board will say self-catered).
4. **Resort guide sites** (See Tignes / See Morzine family etc.) for small independents.
5. ChaletFinder / Chalets Direct only to add `listed_on` to chalets already found (pilot: almost no new ones).

Any site not already in `sites/sites.csv` that you used or discovered: log it to `chalets/raw/<task_id>.newsites.csv` with header `name,url,category,area,notes` (category: company / broad / fallback / official).

## Lanes (parallel agents)

Up to three agents may run at once, one per lane, each doing one thing at a time:
- **enrich** (phase 1) · **sites** (phases 2–3: site, discover) · **villages** (phase 4, France first) · **villages-abroad** (phase 4, Austria/Italy/Switzerland only).
- Take work only with `python3 tools/queue.py claim --lane=<your lane>` — it atomically marks the task in_progress and prints `task_id, type, target, url, detail`. Never `start` a task you didn't claim. Do ONE claimed task, finish it (`done`/`partial`/`failed`), then return your report.
- **Villages lane: don't use the big multi-resort sites the sites lane works on** (Sno, Ski Line, Iglu, Heidi, Erna Low, package operators) — stick to the village sources listed under "Village tasks". This keeps the two lanes off the same websites.
- Sibling villages (e.g. "Les Menuires" vs "Les Menuires: Reberty 2000"): write every chalet you find with its exact village; the sibling task will reuse your chalet_ids from chalets_all.csv rather than redo them.

## Speed: two passes (overnight target)

Coverage first, depth second — never skip a chalet.
- **Pass 1 (your task):** record EVERY chalet/property you find with the fields visible on its listing or detail page (name, village, operator, sleeps, bedrooms, board, hot tub, sauna, price range or "from" price, url, `listed_on`). Get the exact 20 Mar price/availability and photos **where the site makes it cheap** (one extra request, a dated search page, a calendar endpoint). If a chalet needs slow work (driving a widget, several requests) to get the exact week: skip that step and put `pass2: exact-week price` (or `pass2: photos`, etc.) in `notes`.
- **Pass 2** is done later by the enrich lane for all chalets, current fits first — so nothing is lost.
- **Time box:** a village task ~30 min, a site chunk ~45 min. At the limit, finish the chalet you're on, then `done` (village) or `partial` + checkpoint (site).

## Scrapers: scrape, spot-check, move on

`tools/scrapers/README.md` has a status table. For every source of your task whose scraper is marked **READY**:
1. Run `python3 tools/scrapers/ingest.py <task_id> <scraper> <args>` — it appends all rows for the village and downloads images.
2. **Spot-check 2 items yourself**: pick 2 rows it wrote (one catered/hot-tub one if any), open their pages in the browser and compare sleeps, board, hot tub, price/availability. If both match, move on. If anything is wrong: correct those rows (append a fixing row with the same chalet_id, or add to chalets/corrections.csv), log the mismatch in your issues file with `problem=scraper-mismatch`, and check 3 more.
3. Browse only for sources with no READY scraper. When you work a new site out, put its URL patterns/endpoints in your report so it can become a scraper.
