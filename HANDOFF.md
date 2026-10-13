# Handoff: ski chalet search (state as of 2026-10-13)

Read this first in any new session. It replaces the context of the first working session (5–6 Oct 2026, one long Claude Code session that ran up to 10 agents in parallel). Everything needed to continue is in this repo, apart from the original full-size photos, which stay local in `chalets/images/` (gitignored, 2.9 GB).

**Live site:** https://waddington.github.io/ski-accomodation-search/ (GitHub Pages, served from `main` / `docs/`)
**Repo:** `git@github.com:waddington/ski-accomodation-search.git`. PR #1 (initial import) and PR #2 (photo backfill) are both merged.

---

## 1. TL;DR

- **Goal:** a catered ski chalet in the Alps for 8–10 people, Sat 20 – Sat 27 March 2027, about £750pp for accommodation + catering.
- **Data so far:** 4,173 properties, of which 141 make the cut. Only **26** are confirmed catered, free that week and priced. The rest pass because something is still unknown.
- **Best confirmed options found:**
  - **Marmottes residence chalet-apartments, Plagne 1800:** Crétier, Deneriaz, Montillet, Piccard, Bonlieu. ~£519–592pp, sleep 8–10, chalet catering, shared residence hot tub + sauna. Sold via Sno and also by "The Alpine Generation" (Ski Line); these duplicates aren't merged yet.
  - **White Horizon Chalet Neus, Tignes Les Brévières:** sleeps 10, private outdoor hot tub, £653pp.
  - **Others:** Chalet Choucas/Zibeline (Will I Ski, La Plagne, ~£600–625pp, no hot tub), Hattiers Apartment 1 (Chalet Chardons, Brévières, sleeps 8, ~£602pp, no hot tub), Chalet Pom de Pin (Châtel, £652), Toubkal 2 (La Tania, £728), Chelmer (Morzine, sleeps 13, hot tub, £738).
- **Collection stopped on 2026-10-06** at the user's request, after a usage-limit outage. Nothing is running. Every task can resume from `chalets/search_queue.csv`.
- **France:** 23 village tasks done, plus the 4 pilot villages. **74 French villages remain**, and the abroad villages wait behind them.

---

## 2. The brief (and how it changed)

| Item | Current rule | Changes |
| --- | --- | --- |
| Dates | Sat 20 – Sat 27 Mar 2027 (7 nights). Sunday-changeover operators: the 21–28 Mar week counts, flagged via `changeover_day` | — |
| Group | 8 people; 10-person chalets also fine at the same £pp | 10 added 05 Oct |
| Budget | ~£750pp for **accommodation + catering only**. Flights/transfers excluded | Confirmed 06 Oct. Package prices get a £250pp travel allowance (£40 if transfers only) subtracted |
| Board | **Catered** (chalet catering, half/full-board hotel, chalet-hotel). Breakfast-only doesn't count | Catered hotels added 06 Oct |
| Hot tub | **Nice-to-have**, not required | Was a must-have until 05 Oct |
| Ski area | Must be attached to a **major linked ski area** (Les Coches → Paradiski, Tignes Les Brévières → Espace Killy are the user's reference examples) | — |
| Calibre | Benchmark resorts: high Tignes, Val Thorens, Alpe d'Huez, Les 2 Alpes, Morzine, Avoriaz, Sölden, Val d'Isère | — |
| Priority | **France first** (all French villages before any abroad). **Dolomiti Superski villages last** of all | 06 Oct |
| Fallback | If no chalet fits, broaden to other accommodation; self-catered + hired chef is an option (`chef-hire.md`) | — |
| History | Has booked Icebreaker Chalets (Les Coches) before | — |

Resort filtering (in `resorts/filter_resorts.py`, applied to `resorts/resorts_raw.csv` with 207 villages; 158 kept):
- drop C-grade villages with no satellite value
- drop villages below 950 m, unless a major town or snow pocket
- drop areas with less than 1,000 m vertical
- drop `price_level = premium`

---

## 3. How the user wants to work (standing preferences, all stated by the user)

1. **Outputs go in this project folder as files**, never Claude Docs/Artifacts.
2. **Collect everything; filter with scripts.** Raw CSV → script → filtered CSV. Never leave data out at collection time (out-of-budget, too big, no hot tub: all kept). Requirements change; the data should already be there.
3. **Never block data collection on a question.** Restart idle agents first and ask alongside; make a sensible default and log it. Speed-ups reorder work (two-pass), never skip data.
4. **Parallelism:** the user has asked for up to 10 agents. In practice **8 agents exhausted the Claude usage limit in ~2.5 h** (all died with HTTP 429 "session limit"). **Use about 4–5 agents.** Each agent does one thing at a time.
5. **Websites:** at most **2 concurrent requests per site across all agents**. Enforced by `tools/scrapers/common.py::host_slot`.
6. **Scrapers first, LLM second:** once a scraper is validated READY, agents run it, **spot-check 2 items in the browser**, then move on. LLM browsing only for sites with no scraper.
7. **Visibility:** the user likes watching live progress on the dashboard (`python3 dashboard/serve.py`, http://localhost:8777/). Keep it updated.
8. **Git:** worktree + branch + PR per change (`~/.claude/git-workflow.md`). Merge commits. Never commit `chalets/images/`. The user merges PRs.
9. **Repo is public.** The user is fine with the public contact details in the raw data. The **static site stays redacted** (handled automatically by `tools/build_static.py` → `tools/redact_static.py`). **Keep the openbooking API key** (user's decision).
10. Be direct; give recommendations, not surveys; short answers to short questions.

---

## 4. Architecture

```
resorts/resorts_raw.csv ──filter_resorts.py──▶ resorts_filtered.csv ─┐
sites/sites.csv (181 sites) ──────────────────────────────────────────┼─▶ chalets/make_queue.py ─▶ chalets/search_queue.csv
                                                                      │       (phases: 1 enrich · 2 site · 3 discover · 4 village · 5 fallback=deferred)
agents / scrapers ── one CSV per task ──▶ chalets/raw/<task_id>.csv (+ .issues/.sites/.newsites/.changes/.checkpoint.md)
                                            │
                                            ▼
                         chalets/build_chalets.py  (merge by chalet_id, derive flags, apply RULES, corrections.csv, overrides.csv)
                                            │
          chalets_all.csv (removed_by = all failed rules) · chalets_filtered.csv · chalets_removed.csv
          by_resort.csv · by_site.csv · access_issues.csv · site_yield.csv
                                            │
              dashboard/index.html (live, dashboard/serve.py rebuilds every 60 s)
              tools/build_static.py ──▶ docs/ (static snapshot for GitHub Pages, resized photos, redacted)
```

### Key files

| Path | Purpose |
| --- | --- |
| `requirements.md`, `search-plan.md`, `chef-hire.md` | Brief, tier plan, chef-hire research |
| `resorts/` | 207 villages with stats + calibre; `filter_resorts.py` (re-runnable rules) |
| `sites/sites.csv` | 181 sites (companies, broad, fallback, official booking sites, closed). `build_sites_md.py` makes the md lists; `merge_newsites.py` folds in `chalets/raw/*.newsites.csv` |
| `chalets/SCHEMA.md` | Column definitions (38 collected + derived) |
| `chalets/COLLECTOR_BRIEF.md` | **Rules every collector agent follows**: lanes, two passes, scrapers + spot-check, village sources, dedupe |
| `chalets/build_chalets.py` | Merge + derive + filter. Knobs at top: `GROUP_MIN/MAX`, `BUDGET_PP_GBP`, `TO_GBP`, travel allowances, `RULES` (hot-tub rule switched off) |
| `chalets/corrections.csv` | `chalet_id,field,value,note`: fixes applied after merge (e.g. Hattiers capacities, Les Mélèzes listed_on) |
| `chalets/overrides.csv` | (optional) `chalet_id,status` keep/drop |
| `chalets/make_queue.py` | Rebuilds the queue, keeping statuses. Order: France first, Dolomiti last; enrich tasks only once the finding task is done |
| `chalets/PILOT_REPORT.md`, `chalets/OVERNIGHT_LOG.md` | Pilot write-up; event log of the unattended run |
| `tools/queue.py` | `claim --lane=…` (atomic, file-locked), `done/partial/failed/skipped/release`, `next` |
| `tools/find_chalet.py` | Fast duplicate lookup: `find_chalet.py <name> --village <v>` |
| `tools/append_row.py`, `tools/save_images.py` | Schema-checked row append; photo download + resize to 1600 px |
| `tools/scrapers/` | **LLM-free scrapers** (see §6) + `ingest.py`, `validate.py`, `match.py`, `common.py`, `README.md`, `VALIDATION.md`, `BACKLOG.md` |
| `tools/collectors/` | Rescued per-site scripts from the agents (Sno/Ski Line resume helpers, openbooking, browser scripts). See its README |
| `tools/browse.mjs`, `tools/example-navigate.mjs` | Playwright helpers (system Chrome via `channel: "chrome"`; `cd tools && npm i` restores node_modules) |
| `tools/backfill_images.py` | LLM-free photo backfill for chalets with none |
| `tools/build_static.py` → `tools/redact_static.py` | Build `docs/` (default) and redact it |
| `dashboard/` | `serve.py` (port 8777, rebuilds data every 60 s, records `history.csv`), `index.html` (filters, ignore-rule toggles, per-agent chart, batched cards) |

### Derived columns (build_chalets.py)
`type` (inferred if blank), `missing_fields`, `has_hot_tub`, `has_private_hot_tub`, `has_sauna`, `is_catered`, `sleeps_8_to_10` (hotels: capacity ≥ 8 and minimum group ≤ 10), `has_exact_week_price`, `price_pp_gbp_est` (exact week, else top of range; whole-chalet ÷ min(max(sleeps,8),10); nightly ×7), `price_pp_gbp_accom_est` (minus travel allowance), `under_budget`, and finally `removed_by` (every failed rule). **"Unknown" passes every rule**: drop only on evidence.

**Merge priority:** raw files whose names start with `enrich` (`enrich.csv`, `enrich2.csv`, `enrich-images.csv`, `enrich-fix-*.csv`) are merged first, and their non-blank values win. That's how enrichment and the scraper repair pass override collector values.

---

## 5. Coverage and queue state

`chalets/search_queue.csv`: 1,149 tasks.
- **enrich:** 220 done, 607 pending (mostly `pass2:` deferred photos/exact prices).
- **village:** 25 done, 4 partial, 125 pending.
- **site:** 3 partial, 105 pending.
- **discover:** 7 pending. **fallback:** 42 deferred.

**Partial (resume first, `claim` returns them first):**
- `site-sno`: done Espace Killy, Paradiski, Alpe d'Huez, Les 2 Alpes, Les Menuires, Val Thorens, La Tania, Méribel. **Next: Courchevel**, then Portes du Soleil, rest of France, abroad. Checkpoint + `tools/collectors/sno/`.
- `site-ski-line`: API mapped; partly run. Checkpoint + `tools/collectors/skiline/`; prefer `tools/scrapers/skiline.py`.
- `site-iglu-ski`: patterns worked out, 0 rows. Use `tools/scrapers/igluski.py`.
- `village-france-méribel-centre`, `-méribel-mottaret`, `-val-thorens`, `-st-colomban-des-villards`: interrupted by the usage limit; check existing rows in `chalets/raw/<task>.csv` before redoing.

**French villages done (23 + pilot 4):**
- **Pilot:** Les Coches, Montchavin, Tignes Les Brévières, Les Boisses.
- **Les Menuires:** Les Menuires, Les Bruyères, Reberty 2000.
- **Espace Killy:** La Daille, Le Fornet, Tignes 1800, Le Lac, Le Lavachet, Val Claret, Val d'Isère.
- **Others:** Alpe d'Huez, Les 2 Alpes, Courchevel 1650, St-Jean-d'Arves, Bourg-St-Maurice, La Chapelle d'Abondance, Montriond, Torgon*, Val d'Illiez*, Briançon, Combloux, St-Gervais, St-Nicolas-de-Véroce. (*Swiss: written with country=Switzerland though the queue labels them France.)

**French villages left (74):**
- Most of Paradiski (the Plagne and Arc villages, Peisey/Vallandry, Villaroger, Montalbert, Champagny)
- Most of Portes du Soleil (Avoriaz, Morzine, Les Gets, Châtel…)
- Rest of the 3 Vallées (Val Thorens, Méribel ×3, Les Allues, Courchevel 1550/Le Praz, La Tania, St-Martin)
- The other areas: Grand Massif (9), Sybelles (5), Alpe d'Huez satellites (5), Espace Diamant (5), Grand Domaine (4), Serre Chevalier (3), plus Mont-de-Lans, Montgenèvre, St-Gervais Le Bettex, La Rosière, Risoul, Vars.

**Abroad:** done Breuil-Cervinia and Arabba (Corvara partial/released). Catered chalets abroad are rare: hotels or self-catered. **Abroad villages are all after France; Dolomiti last.**

---

## 6. Scrapers (tools/scrapers/, all validated: see VALIDATION.md)

| Scraper | Source | Status |
| --- | --- | --- |
| `allchalets.py` | allChalets (best aggregator) | READY. Bugs fixed 06 Oct (board, village, pool, names, changeover, escaping) |
| `les3vallees.py` | reservation.les3vallees.com (Orchestra); `--site combloux` for reservation.combloux.com | READY |
| `ingenie.py` | Ingenie tourist-office sites: `lesmenuires`, `tignes`, `serrechevalier`, `valdisere` (uses `ZONEGEO`, e.g. `FRRASAVADAILL`) | READY (Serre Chevalier limited). Hot-tub icon bug fixed |
| `simplyvaldisere.py` | Simply Val d'Isère (names operators via rate-table codes) | READY |
| `msem.py` | MSEM tourist-office API (`stgervais`; `--resort-id/--channel` for others, e.g. Leman Mountains 30016) | READY |
| `skiline.py` | Ski Line JSON API (names operators) | READY for structure fields |
| `igluski.py` | Iglu Ski | limited |
| `sno.py` | Sno | READY (slow: ~9 s/chalet) |

`ingest.py <task_id> <scraper> <args> [--override] [--ingest-dry-run] [--no-images]` writes the rows. It reuses existing ids on a URL or name+area match, keeps per-source prices in notes, and saves photos. `--override` is the repair mode: write into `enrich-fix-<source>-<village>` so corrected values win. **The repair pass ran into 21 `enrich-fix-*` files before the usage limit killed it, without a final report.** Re-run any set if unsure; it's idempotent. **Backlog** of sources worth scripting: `tools/scrapers/BACKLOG.md` (openbooking.ch, resa-morzine.com, lesarcs-reservation.com, Host Savoie checkfront, Leman Mountains, AliKats/Alptitude, Alpe d'Huez official).

---

## 7. Findings worth knowing (for the decision, not just the data)

- **The week before Easter (Easter Sunday 28 Mar 2027) is filling fast.** Many catered chalets were already booked in early October: all of Alpine365, most of Icebreaker, 4 of 6 White Horizon, the Reberty/Bruyères family chalets, Montriond's Bizet/Debussy/Ferme à Jules.
- **Enquiry-only private listings worth a message:**
  - allChalets 24443, Les Menuires 1800: catered, private hot tub, ski-in/out, sleeps 10.
  - Chalet Vithos / Gabrielle / Delphine, Les Bruyères: catered, jacuzzi + sauna.
  - Martin Bright's allChalets listings: Eagle, Tignes V, des Neiges V, Pierre.
  - Snowed Inn Chalets, Briançon: Briançon, Flocon, Pearl.
- **Near-fits by flexibility:** Host Savoie Chalet Le Vionnet (Montriond, sleeps 8, hot tub, free; "Flexi-Catered" £3,710/week ≈ £464pp). Club Alpine Montchavin chalets (sleep 12, £7,700/wk, Sunday changeover). White Horizon Ibex (sleeps 12, £665pp).
- **Over budget but strong:**
  - Val d'Isère: YSE Chalet des Pentes / La Maison du Rocher, Chalet Davos, La Marsa, Atacama (whole-chalet £10–16k).
  - Méribel: Brioche, Aline, Laëtitia, Mariefleur (~£1.3–1.65k accommodation after allowance).
- **Self-catered with hot tub, free (chef-hire candidates):** La Nia (St-Nicolas, 12, €5,870), Valia (St-Gervais, 10, €6,820), Bichette (Combloux, 8, €4,800), Le Bettex Edelweiss (Les Menuires, 12, €6,161). Chef hire costs about €83pp per meal via Take a Chef (`chef-hire.md`).

---

## 8. Known data problems / tech debt

1. **Cross-site duplicates aren't fully merged:** e.g. Sno "Chalet Crétier" vs Ski Line "Chalet-Apartment Crétier" (The Alpine Generation). Needs a dedupe pass (name similarity within village + capacity + price), writing `same_as` or corrections.
2. **`ski_area` blank on 725 rows, `country` blank on 125:** mostly scraper rows. Fill by mapping `village` → `resorts/resorts_raw.csv`.
3. **Passing chalets with unknowns:** 112 of 141 lack a price and 111 lack availability. Use dashboard filters "Price known" / "Free 20–27 Mar" for confirmed-only. Enrich backlog: 607.
4. **Price basis noise:** per-bed vs whole-chalet, "2 sharing" Sno prices, fixed FX (`TO_GBP` EUR 0.86, CHF 0.93), assumed £250 travel allowance.
5. **36 chalets still have no photos** (their pages have none usable).
6. The queue labels Swiss Portes du Soleil villages (Torgon, Val d'Illiez, Champéry, Morgins…) as France. Collectors write `country=Switzerland`.
7. **Repair pass completeness unknown** (see §6).

---

## 9. Lessons and gotchas

- **Claude usage limit:** 8 agents for ~2.5 h → HTTP 429 for every agent. Resets after ~1–5 h. Plan 4–5 agents. When it hits, set interrupted tasks to `partial` (`tools/queue.py partial <id>`).
- **WebSearch budget:** 200 per session, exhausted early. DuckDuckGo html and Bing now block the headless browser. Navigate sites directly (sitemaps, site search, tourist-office lists).
- **Blocked sites:**
  - Heidi: 429 / empty render.
  - Crystal Ski: Access Denied.
  - YSE: 429.
  - Cervinia regional booking: Vertical Booking / Cloudflare captcha.
  - Seasonworkers: 403.
- **Capacity:** use the operator's stated figure. Never add sofa beds (the Hattiers apartments were wrong because of this).
- **A "whirlpool bath" in an en-suite is not a hot tub.** The "Sauna/Jacuzzi/Steam" icon on Ingenie sites is not a hot tub.
- **Watch for Sunday changeovers, per-night prices, flight-inclusive packages, and group houses with large minimum groups.**
- **JS booking widgets:** look for the data endpoint (chaletmanager JSONP, mychaletbooking HTML, ninja-tables AJAX, Smoobu, checkfront, openbooking) before driving the UI with Playwright.
- **Agents must keep helper scripts in their own folder:** a shared `/tmp/log.sh` once crossed two agents' logs.
- **Git:** the project folder became a repo mid-session. A local-only `.gitignore` commit on an unborn `main` made `.gitignore` vanish on branch switch, which nearly staged 2.9 GB of photos. Always check `git diff --cached --stat` before committing.
- **Background sessions:** edits in the main checkout are blocked unless done in a worktree (`.claude/worktrees/`, gitignored).
- **GitHub Pages** serves only the repo root or `/docs`. Pages from a private repo needs a paid plan and is still public.
- **The static site must be served over http** (`python3 -m http.server --directory docs`); `file://` blocks `fetch()`. "All" renders in batches of 60 with lazy photos.

---

## 10. Next steps (recommended order)

1. **Dedupe pass** across sites (§8.1) and **fill ski_area/country** from village (§8.2). Both are small scripts and need no LLM.
2. **Verify/finish the repair pass:** re-run `ingest.py --override` for any `enrich-fix-*` set that looks short, then rebuild.
3. **Resume French villages** with ~4 agents: the villages lane (top) ×2 and villages-fr-rev ×1, plus 1 sites agent on `site-sno` (Courchevel next) or `site-ski-line` via `skiline.py`. Use READY scrapers + 2 spot-checks. Each agent claims about 5 tasks per run.
4. **Enrichment for current fits:** `make_queue.py` puts fits first; 1 enrich agent.
5. **Build backlog scrapers** (openbooking, resa-morzine, lesarcs-reservation, Host Savoie) before their villages come up.
6. **Shortlist + enquiries:** produce a ranked shortlist doc from `chalets_filtered.csv` (confirmed fits first), plus enquiry message drafts for the enquiry-only listings. The user sends them; never send anything.
7. Abroad villages (Austria/Switzerland/Italy, Dolomiti last), then `discover-*`, then fallback only if needed.
8. **After data changes:** `python3 chalets/build_chalets.py && python3 tools/build_static.py` (builds `docs/` and redacts), then commit `docs/` via a PR. Pages redeploys on merge.

### Commands

```bash
python3 resorts/filter_resorts.py                # resort rules → resorts_filtered.csv
python3 chalets/make_queue.py                    # refresh queue (keeps statuses)
python3 tools/queue.py claim --lane=villages     # lanes: villages | villages-fr-rev | villages-abroad | sites | enrich
python3 tools/scrapers/ingest.py <task> allchalets "<village>"     # + spot-check 2 rows
python3 tools/find_chalet.py <name> --village "<v>"
python3 chalets/build_chalets.py                 # merge + filter
python3 dashboard/serve.py                       # live dashboard → http://localhost:8777/
python3 tools/backfill_images.py                 # photos for chalets with none (LLM-free)
python3 tools/build_static.py                    # docs/ snapshot (+ redaction)
python3 -m http.server 8790 --directory docs     # preview the static site
cd tools && npm i                                # restore Playwright (uses system Chrome)
```

### Agent prompt template (worked well)

> You are a VILLAGES-lane agent (French villages, top of the list) of the chalet search; N other agents run in parallel. Don't touch other agents' files or the big multi-resort sites (Sno, Ski Line, Iglu, Heidi, Erna Low, package operators). Read `chalets/COLLECTOR_BRIEF.md` fully (Village tasks, Lanes, Speed: two passes, Scrapers), `chalets/SCHEMA.md`, `tools/scrapers/README.md` and `BACKLOG.md`, then follow them exactly. No WebSearch/DuckDuckGo. Loop: re-read the scraper README → `python3 tools/queue.py claim --lane=villages` → READY scrapers via `ingest.py` (+2 spot-checks per source), browse only where none exists (pass 1, `pass2:` for slow detail, record booked units) → `queue.py done …`. Dedupe with `find_chalet.py`. ~30 min per village; ~5 villages per run; then return a combined report (rows, new, near-fits = catered + free 20 Mar, mismatches, access problems).

Variants: `--lane=villages-fr-rev` (bottom-up), `--lane=villages-abroad`, `--lane=sites` (resume the partial task from its checkpoint; stop with `partial` after 1–2 resorts), `--lane=enrich` (one row per chalet into `chalets/raw/enrich*.csv`, changes logged to `enrich.changes.csv`).
