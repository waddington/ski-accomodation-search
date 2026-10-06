# Scraper backlog

Sources collectors worked out that are worth turning into READY scrapers. Next maintenance agent: take from the top.

| Priority | Source | Covers | What's known | Working script |
| --- | --- | --- | --- | --- |
| 1 | openbooking.ch (Région Dents du Midi) | Champéry, Val-d'Illiez, Les Crosets, Champoussin, Morgins | POST api.openbooking.ch/whitelabel/list?limit=200, header api-key 4BA615F77D1B41C7A5E2CFAEFC7D77C1, body {lang, places:[rddm-1873-1/-2/-3, rddm-1874-1, rddm-1875-1]}; GET /accommodations/<id>?lang=en (facts.apartment maxAdults/bedrooms); GET /availabilities/<id> (YYMMDD) | /home/kai/.claude/jobs/44718792/tmp/openbooking_rddm.py <task> <place> <village> |
| 2 | resa-morzine.com (Morzine tourist office) | Morzine, Montriond, Avoriaz? | Ingenie platform: mid=3, cid=3, type G — add a site entry to ingenie.py | /home/kai/.claude/jobs/44718792/tmp/ingenie_extra.py |
| 3 | lesarcs-reservation.com | Les Arcs, Bourg-St-Maurice, Villaroger, Peisey? | list pages embed all cards (area tags, max capacity, 7-night from price); village filter is JS | tools/scratch/village-france-bourg-st-maurice-arcs.mjs |
| 4 | Host Savoie (checkfront) | Morzine, Montriond, Avoriaz | hostsavoie.checkfront.com/reserve/inventory/?start_date=20270320&end_date=20270327 → JSON prices for the week | — |
| 5 | Leman Mountains Explore | La Chapelle d'Abondance, Abondance, Bernex, Thollon | msem.py --resort-id 30016 --channel LEMAN_MOUNTAINS (5 bookable); full list in sitemap-1..9.xml /offres/ | — |
| 6 | AliKats, Alptitude | Morzine/Montriond | price + availability tables in static HTML | — |
| 7 | accommodation.alpedhuez.com | Alpe d'Huez | separate JS app (not Ingenie) | — |
