# Ski Chalet Finder — March 2027

Find a catered chalet with a hot tub for 8 people, Sat 20 – Sat 27 March 2027, about £750 per person, in a resort linked to a major Alpine ski area.

| File | What's in it |
| --- | --- |
| [requirements.md](requirements.md) | The brief: dates, group, budget, must-haves, open questions |
| [search-plan.md](search-plan.md) | Search tiers, from catered chalet down to hotels and apartments |
| [sites/broad-search-sites.md](sites/broad-search-sites.md) | Aggregators and multi-operator search sites |
| [sites/chalet-companies.md](sites/chalet-companies.md) | Specialist catered-chalet operators (Icebreaker etc.) |
| [sites/fallback-accommodation.md](sites/fallback-accommodation.md) | Other accommodation types if no chalet fits |
| [sites/sites.csv](sites/sites.csv) | Source of truth: all 150 sites (incl. closed), with columns to track access and search progress |
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
| [chalets/images/](chalets/images/) | Up to 5 photos per chalet, one folder per `chalet_id` |
| [dashboard/](dashboard/) | Live web dashboard: `python3 dashboard/serve.py` then open http://localhost:8777/ |
| [chalets/search_queue.csv](chalets/search_queue.csv) | The full search's work queue (289 tasks) with status; rebuild with `python3 chalets/make_queue.py` |
| [chalets/COLLECTOR_BRIEF.md](chalets/COLLECTOR_BRIEF.md) | Rules every search agent follows (one thing at a time, logging, de-duplication) |
| [chef-hire.md](chef-hire.md) | Chef-hire services for a self-catered chalet, with prices and maths |
| [tools/](tools/) | Local Playwright browser helpers for JS/blocked sites |
| [shortlist/](shortlist/) | Candidate chalets (search not started yet) |

## Status

- [x] Requirements captured
- [x] List every search site and chalet company
- [x] List every appropriate resort/area (207 villages, 34 ski areas)
- [ ] Trim resorts to a shortlist
- [x] Pilot chalet collection: Les Coches + Tignes Les Brévières (102 chalets, see chalets/PILOT_REPORT.md)
- [ ] Full search (running one task at a time — see dashboard): enrich → sites → directories → villages; fallback deferred
