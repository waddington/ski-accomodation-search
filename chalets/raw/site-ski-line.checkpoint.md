# site-ski-line checkpoint

## Method (2026-10-06, sites agent #2)
READY scraper: per resort `/home/kai/.claude/jobs/44718792/tmp/site-ski-line/run.sh "<API resort>" <sitemap-slug>`
= skiline.py (all boards: chalets, apartments, hotels; --sitemap adds sitemap-only chalet/residence pages) -> fix.py
(maps API resort -> resorts_raw village + ski_area; blanks bedrooms on apartments/hotels; notes residence hot tubs
as probably shared) -> ingest.py --from-jsonl. Spot-check with chk.sh <url> <name>.
Known scraper issues: bedroom regex grabs "two bedrooms" from suite text (Ski Famille chalets -> 2, real 6);
hot_tub flag on residences = shared spa (scraper writes yes-type-unknown). Corrections in chalets/corrections.csv.
Sitemap-only resorts not in API (skipped): Morillon, St-Francois-Longchamp, Les Orres, Pralognan, Isola 2000, Val Cenis,
Ste-Foy, Chamonix, La Clusaz (last 4 not in resorts_raw anyway).

## Resorts done
- Les Menuires (29 rows, 22 new)
- Reberty 2000 (9, all known Sno), St-Martin-de-Belleville (18, 16 new), Mottaret (11, 5 new); spot-checks OK (Caseblanche sitemap page text describes 'Chalet Selini sleeps 6' - Ski Line page content muddled)
- Val Thorens (72, 63 new; Ski Beat/Chalet des Neiges + Bonhomme hot tubs = shared residence, corrected), La Tania (31, 18 new). nf.py hot-tub check run on all done resorts (Katie 2 shared).
- Courchevel (55, 38 new), Meribel (65, 37 new), Brides les Bains (4). Hot-tub checker mostly false positives ('Communal Facilities' = chalet's own); bedroom fixes in corrections.csv
- Tignes (98, 59 new); Catherine + hotels hot tub shared (corrections)
- Val d'Isere (140, 64 new); Le Ski Cacholet chalets' hot tubs shared (corrections)

## Resorts left
France: Reberty 2000, St-Martin-de-Belleville, Mottaret, Val Thorens, La Tania, Courchevel, Meribel, Brides les Bains,
Tignes, Val d'Isere, La Plagne, Les Arcs, Bourg Saint Maurice, Avoriaz, Morzine, Les Gets, Chatel, Les Crosets,
Alpe d'Huez, Auris-en-Oisans, Vaujany, Les Deux-Alpes, Montgenevre, La Toussuire, Le Corbier, St Sorlin d'Arves,
Flaine, Les Carroz, Samoens, Serre-Chevalier, Megeve, Saint-Gervais, Risoul, Vars, Valmorel, La Rosiere,
Les Saisies, Pra Loup, Valloire, Valmeinier.
Then Austria (St Anton, St Christoph, Lech, Zurs, Ischgl, Solden, Hochsolden, Saalbach, Hinterglemm & Fieberbrunn,
Leogang, Kitzbuhel, Serfaus, Konigsleiten, Gerlos, Mayrhofen, Finkenberg, Soll, Westendorf, Ellmau, Montafon),
Switzerland (Verbier, Zermatt, Laax, St Moritz), Italy (Cervinia, Sestriere, Sauze d'Oulx, Pragelato, Madonna Di Campiglio,
Folgarida, Pinzolo, La Thuile, Champoluc, Gressoney), Dolomiti last (Selva, Arabba, Corvara, Colfosco, Canazei,
St Cristina, La Villa (Sella Ronda), San Cassiano, Ortisei).
