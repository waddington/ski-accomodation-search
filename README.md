# Ski Chalet Finder — March 2027

Find a catered chalet (hot tub a nice-to-have) for 8–10 people, Sat 20 – Sat 27 March 2027, about £750 per person for accommodation + catering, in a resort linked to a major Alpine ski area.

**Start with [HANDOFF.md](HANDOFF.md)**: current state, findings, how everything works and next steps. Browse the results at https://waddington.github.io/ski-accomodation-search/ (static snapshot in `docs/`).

| File | What's in it |
| --- | --- |
| [requirements.md](requirements.md) | The brief: dates, group, budget, must-haves, open questions |
| [search-plan.md](search-plan.md) | Search tiers, from catered chalet down to hotels and apartments |
| [sites/broad-search-sites.md](sites/broad-search-sites.md) | Aggregators and multi-operator search sites |
| [sites/chalet-companies.md](sites/chalet-companies.md) | Specialist catered-chalet operators (Icebreaker etc.) |
| [sites/fallback-accommodation.md](sites/fallback-accommodation.md) | Other accommodation types if no chalet fits |
| [sites/sites.csv](sites/sites.csv) | Source of truth: all 181 sites (incl. closed and official booking sites), with columns to track access and search progress |
| [sites/build_sites_md.py](sites/build_sites_md.py) | Rebuilds the three site lists from the CSV; run `python3 sites/build_sites_md.py` after editing it |
| [resorts/resorts.md](resorts/resorts.md) | Every qualifying resort/village in major linked ski areas, by country |
| [resorts/resorts_raw.csv](resorts/resorts_raw.csv) | Source data: all 207 villages. Edit `status` (keep/drop) for manual overrides |
| [resorts/filter_resorts.py](resorts/filter_resorts.py) | Filter rules; run `python3 resorts/filter_resorts.py` after any change |
| [resorts/resorts_filtered.csv](resorts/resorts_filtered.csv) | Output: villages that pass every rule |
| [resorts/resorts_removed.csv](resorts/resorts_removed.csv) | Output: dropped villages and the rule that dropped them |
| [chalets/SCHEMA.md](chalets/SCHEMA.md) | Column definitions every chalet collector follows |
| [chalets/raw/](chalets/raw/) | One CSV + progress log + issues log per collector (live while agents run) |
| [chalets/build_chalets.py](chalets/build_chalets.py) | Merge, de-duplicate, derive flags, filter; run `python3 chalets/build_chalets.py` |
| [chalets/chalets_all.csv](chalets/chalets_all.csv) | Every chalet found, with `has_hot_tub`, `under_budget`, `missing_fields` etc. |
| [chalets/chalets_filtered.csv](chalets/chalets_filtered.csv) | Chalets passing the rules (removed ones + reason in `chalets_removed.csv`) |
| [chalets/by_resort.csv](chalets/by_resort.csv) / [by_site.csv](chalets/by_site.csv) | The two views: chalets per village, chalets per site |
| [chalets/access_issues.csv](chalets/access_issues.csv) | Everything we got stuck accessing or couldn't get details for |
| `chalets/images/` | Up to 5 full-size photos per chalet (local only, gitignored, 2.9 GB); `docs/` has resized copies |
| [dashboard/](dashboard/) | Live web dashboard: `python3 dashboard/serve.py` then open http://localhost:8777/ |
| [chalets/search_queue.csv](chalets/search_queue.csv) | The search work queue (~1,150 tasks) with status; rebuild with `python3 chalets/make_queue.py` |
| [chalets/COLLECTOR_BRIEF.md](chalets/COLLECTOR_BRIEF.md) | Rules every search agent follows (one thing at a time, logging, de-duplication) |
| [chef-hire.md](chef-hire.md) | Chef-hire services for a self-catered chalet, with prices and maths |
| [tools/scrapers/](tools/scrapers/) | LLM-free scrapers (allChalets, 3 Vallées, Ingenie tourist offices, Simply Val d'Isère, MSEM, Ski Line, Iglu, Sno) + `ingest.py`; status in its README |
| [tools/collectors/](tools/collectors/) | Per-site scripts written by collector agents (Sno/Ski Line resume helpers, openbooking, browser scripts) |
| [tools/](tools/) | Queue, lookup, row/photo helpers, Playwright browser helpers, `backfill_images.py`, `build_static.py` + `redact_static.py` |
| [docs/](docs/) | Static, redacted snapshot of the dashboard for GitHub Pages; rebuild with `python3 tools/build_static.py` |
| [HANDOFF.md](HANDOFF.md) / [CLAUDE.md](CLAUDE.md) | Session handoff and standing instructions for continuing the work |
| [shortlist/](shortlist/) | For the ranked shortlist (not written yet; see HANDOFF.md §10) |

## Status (2026-10-13)

- [x] Requirements captured
- [x] Every search site and chalet company listed (181 sites)
- [x] Every appropriate resort listed (207 villages) and filtered (158 kept)
- [x] Pilot: Les Coches + Tignes Les Brévières
- [~] Full search: 4,173 properties collected, 141 make the cut. Paused 2026-10-06; 74 French villages and the partial Sno / Ski Line / Iglu sweeps remain (see HANDOFF.md)
- [x] Static site published (GitHub Pages from `docs/`)
- [ ] Dedupe across sites, fill missing ski areas, finish enrichment
- [ ] Ranked shortlist + enquiry drafts
