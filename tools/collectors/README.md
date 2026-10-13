# Collector scripts (preserved from the October 2026 session)

Working scripts the LLM collector agents wrote for specific sources. They were rescued from a
temporary scratch folder before the session ended. They're less polished than `tools/scrapers/`
(which are validated and READY — prefer those), but they encode working URL patterns and are the
fastest way to resume the two big partial site tasks.

Run them from the **repo root**. Some still contain the absolute project path
`/home/kai/Documents/Misc/ski-chalet-finder`; former scratch paths were rewritten to
`tools/collectors/<site>/` or `/tmp/chalet-scratch/`. Read a script before running it.

| Folder | What | Resume notes |
| --- | --- | --- |
| `sno/` | Sno (sno.co.uk) scripted collector: `snolist.py <slug>` lists a resort, `snodetail.py` fetches a chalet, `mk.py <code> '<json>'` writes a row + 5 photos, `auto.py` + `run.sh <todo.tsv> <from> <to>` do fetch + 20 Mar price + row + photos in one go. `*_all.tsv` are resort todo lists (`v3_all.tsv` = 3 Vallées; Courchevel = lines 117–201 still to do). | Task `site-sno` is **partial**. Checkpoint: `chalets/raw/site-sno.checkpoint.md`. `tools/scrapers/sno.py` (READY) packages the same logic. |
| `skiline/` | Ski Line JSON API helpers (`sl_list.py`, `sl_one.py`, `run.sh`), sitemap URL lists. | Task `site-ski-line` is **partial**. Checkpoint: `chalets/raw/site-ski-line.checkpoint.md`. `tools/scrapers/skiline.py` (READY) is the preferred path. |
| `misc/openbooking_rddm.py` | Région Dents du Midi (openbooking.ch API): `<task> <place> <village>` for Champéry, Val-d'Illiez, Les Crosets, Champoussin, Morgins. | Candidate for a proper scraper (see `tools/scrapers/BACKLOG.md`). |
| `misc/ingenie_extra.py` | Runs `tools/scrapers/ingenie.py` against resa-morzine.com (Morzine tourist office) without editing the scraper. | Fold into `ingenie.py` as a site config. |
| `misc/rescrape.sh` | The LLM-free allChalets re-scrape of early villages. | Done; kept as an example of running `ingest.py` in a loop. |
| `browser/` | Playwright scripts agents wrote (booking widgets, XHR capture, dashboard screenshots/tests). Need `tools/node_modules` (`cd tools && npm i`) and Google Chrome. | Reference for sites without a scraper. |
