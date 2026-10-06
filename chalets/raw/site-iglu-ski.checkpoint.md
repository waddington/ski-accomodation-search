# site-iglu-ski checkpoint

Status: recon only, 0 chalets written. No resorts done yet. All resorts left.

## URL patterns that work (plain curl, no JS needed, no blocking seen)
- Resort page: https://www.igluski.com/ski-resorts/<country>/<resort> -> links to per-village listings
  e.g. /ski-holidays/meribel-ski-chalets, /ski-holidays/meribel-mottaret-ski-chalets, /ski-holidays/meribel-village-ski-chalets (also -ski-apartments, -ski-hotels)
- Listing, 10 per page (perpage capped at 10), paginate with page=N:
  /ski-holidays/<village>-ski-chalets?&flex=2&nts=7&ad=2&ch=0&perpage=10&page=1&sort=0&state=4
- Dated search for our week (returns departures 20 or 21 Mar 2027 = exact-week package price):
  add &date=20032027&flex=2 ; ad=8 gives price "based on 8 people sharing" (some cards still say 2/3 sharing)
  Meribel: 46 chalets undated, 29 with date ad=2, 24 with ad=8.
- Card data attrs: data-title, data-price (£pp, PACKAGE incl. flights from a UK airport), data-departuredate, data-supplier (operator code: ING=Inghams; 021, 078, 108 unknown - check property page), data-resort; card text has Sleeps, Board (Catered etc.), lift distance, Sauna/hot tub icons.
- Property page: /ski-resorts/<country>/<village>/<chalet-slug>_<propertyid>
- Strategy: undated listing per village (all chalets, sleeps, board) + dated ad=8 listing for 20 Mar price/availability (absent from dated = unknown, not necessarily unavailable).
- Scratch: tools/scratch/site-iglu-ski-xhr.mjs (network capture), search JS param names: date (ddmmyyyy), flex, nts, ad, ch, board, sleeps, resort, ao=y (acc only).
