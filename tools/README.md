# Tools

Local browser (Playwright 1.63, using the system Google Chrome) for sites that WebFetch can't read: JS booking widgets, bot-blocking, search forms, pagination.

- `node tools/browse.mjs <url> [outdir] [--wait=ms] [--click="selector"]... [--headed]`
  Renders the page and writes page.txt, page.html, images.txt (largest first), links.txt, shot.png.
- `tools/example-navigate.mjs` — template for interactive scraping (type a search, click, paginate). Copy to `tools/scratch/<name>.mjs` and run with `node`.
  Scripts must live under `tools/` so the `playwright` import resolves.

Be polite: a few seconds between page loads, no parallel hammering of one site.
