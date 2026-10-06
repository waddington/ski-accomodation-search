# site-sno checkpoint

## URL patterns that work
- Resort/area chalet list: GET https://www.sno.co.uk/ski-chalets/<slug>/ ; read hidden input `hdssettings` (pipe-separated), then GET same URL with
  `?r=<f10>&t=&d=Depart&s=2&c=0&i=0&fl=1&g=0;3000&f=&p=C&b=AI.BB.CA.CC.FB.HB.RO.SC&rt=0&dr=2&n=30&pg=<page>&o=0` (server-rendered, 30 per page). /Api/ is robots-disallowed: don't use it.
- Resort slugs from sitemap.xml (`/ski-chalets/*-chalets/`). Area pages (espace-killy-chalets) do NOT include everything on resort pages (Chardons chalets missing) -> union area + resort pages.
- Detail: /ski-holidays/<slug>_<code>/ server-rendered; calendar defaults to 2 sharing (misleading whole-chalet-ish prices).
- Price for 20 Mar: POST /Accom/Search (form `asearch`, needs __RequestVerificationToken + cookies) with act=50&duration=7&sharing=N&airport=LGW&boardbasis=..&departureDate=2027-03-20&accomcode=<code>&propertytype=.. -> 302 to ?holidayid=... page with calendar for that sharing/airport.
- Images: static1.sno.co.uk/images/accom/v0/... = full size (v2 = thumbnails).
- Operator is NOT named on Sno pages (image path code is 'wlc' for all) -> operator "unknown (sold via Sno)", chalet_id prefix sno-.
- Scripts: /home/kai/.claude/jobs/44718792/tmp/site-sno/ (snolist.py, snodetail.py, mk.py, one.sh)

## Resorts done
- Espace Killy COMPLETE (espace-killy + tignes + val-d-isere pages; 114 listings; 103 rows written, 11 already known with Sno in listed_on). Todo list: tmp/site-sno/ek_todo.tsv (all 102 done).

## Workflow (per resort)
1. `python3 snolist.py <slug>` (writes lists/<slug>.tsv); union with area page; drop names already in chalets_all.csv / site-sno.csv.
2. `./one.sh <todo.tsv> <line>` -> fetch + POST 20 Mar (sharing=min(sleeps,10), LGW, fallbacks) -> compact summary, det/<code>.json.
3. `python3 mk.py <code> '<json overrides>'` (village, hot_tub, sauna, bedrooms, notes+ ...) -> appends row + saves 5 images. `fix.py <id> <field> <val|+append>` edits own rows.
- Notes: Sno often only accepts 2 sharing (per-bed pricing) -> recorded with sharing count in notes. Room-only/self-catering/half-board packages are "Without Flights". Some operator templates (Katalin/Nirmal type) give erratic 2-sharing prices -> range omitted.

- Paradiski COMPLETE (agent 2): union of paradiski/la-plagne/les-arcs pages = 67 listings (tmp/site-sno/par_all.tsv), all 67 new rows. Area page had only 22.
- Alpe d'Huez + Les 2 Alpes COMPLETE (agent 2): tmp/site-sno/adh_all.tsv, 21 + 4 listings, all 25 new rows. Many ADH catered chalets have no 20 Mar row on Sno for any airport (logged in issues).
- snodetail.py now takes optional 3rd arg airport (e.g. FOLK, MAN) to retry a different departure point.
- Next: 3 Vallées (three-valleys + courchevel, meribel, la-tania, les-menuires, val-thorens pages; union them). VIL list in snodetail.py already has 3V names.
- Agent-2 helper changes: snodetail.py now follows redirects (curl -L; some slugs 301) and rooms regex accepts '(sleeps 2-4)'; batch.sh <todo> <from> <to> runs one.sh sequentially with compact output. In zsh, loop over mk.py calls from python (not bash -c).

- Agent-3 (3 Vallées): union list tmp/site-sno/v3_all.tsv (201 listings: Les Menuires 1-14, Val Thorens 15-23, La Tania 24-39, Méribel 40-116, Courchevel 117-201). New faster path: `./run.sh <todo> <from> <to>` = one.sh + auto.py (auto-derives chalet_id (adds -<village> or -<code> on id clash), village from location text, hot_tub/sauna from page text, family-chalet note) -> appends row. For already-known chalets: `python3 auto.py <todo> <line> '{"known":true,"chalet_id":"<id>"}'`. mk.py: AO airport = 'Without Flights' (accommodation only). Dup check: tools/find_chalet.py <name> --village <v> (no 3V matches outside Les Menuires: Panicaut + In the Clouds = wens-*).

- 3 Vallées PART 1 DONE (agent 3): v3_all.tsv lines 1-116 = Les Menuires, Val Thorens, La Tania, Méribel (114 new + 2 known wens-*). NEXT: Courchevel = `./run.sh v3_all.tsv 117 201` (run in background, ~25 min), then review: villages (auto.py Courchevel mapping uses 1850/1650/1550/Le Praz/Moriond keywords in location+summary — spot-check), hot tubs ('Whirlpool bathtub' in en-suites is NOT a hot tub — now excluded), dup names (#131 Caribou, #138 Ecureuil, #143 La Grande Casse, #197 Chanterelles are different chalets from existing sno-* ids -> auto.py appends village suffix).
- auto.py lessons: Méribel location text always contains 'Meribel & Mottaret' (now stripped); Le Raffort/Nantgerel hamlets -> village 'Les Allues' + note; Sno 'AO' airport = accommodation-only price.

## Resorts left
3 Vallées: Courchevel only (v3_all.tsv 117-201), PdS (portes-du-soleil, morzine, avoriaz, les-gets, chatel), rest of France (la-rosiere, megeve, valmorel, samoens, milky-way), Austria (st-anton, lech, ischgl, solden, saalbach, hinterglemm, fieberbrunn, kirchberg, finkenberg, gerlos, skiwelt, zillertal-superski), Italy (champoluc, gressoney, madonna-di-campiglio, selva, canazei, val-gardena, alta-badia, sella-ronda, val-di-fassa, dolomiti-superski, milky-way, aosta-valley), Switzerland (verbier, nendaz, veysonnaz, four-valleys, zermatt, laax, graubunden)

- 3 Vallées COMPLETE (agent 4): Courchevel v3_all.tsv 117-201 = 85 new rows (all sno-*). Fixes via fix.py: villages (auto.py now maps 'Courchevel Village'/Proveres/Grangettes -> 1550, Jardin Alpin/Bellecôte -> 1850, ignores 'views towards 1850'); 'Full Board' -> catered (mk.py patched). Many Courchevel chalets give no quarter (village 'Courchevel').
- auto.py generalised (agent 4): ski_area from resorts_raw by village (3V names hard-wired), country from page title, Morzine/Montriond/Prodains, Châtel; other bases mapped to resorts_raw village by slug.
- NOTE: don't wait with `pgrep -f` loops (they match themselves); wait with `until grep -q '^#<last> ' out`.
