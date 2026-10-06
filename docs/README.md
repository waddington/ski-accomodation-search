# Chalet Search, 20–27 March 2027

A static snapshot of a personal search for a catered ski chalet in the Alps for a group of 8–10. Open `index.html` (or the GitHub Pages URL) to browse every property found, filter them, and see why each one did or didn't make the cut.

- **Data:** `chalets/chalets_all.csv`. One row per property; `removed_by` says why a property was filtered out.
- **Snapshot date:** shown at the top of the page.
- **To update:** in the main project, run `python3 tools/build_static.py <this folder>`, then commit and push.

## Third-party content

Listing details, prices and photos were collected from public listing pages of the operators and booking sites named on each property's `listed_on` and `url`. They belong to their respective owners. They're reproduced here only to compare options for a private trip, and may be out of date. Always check prices and availability with the operator. Private individuals' contact details have been removed.

The code (the HTML page and build scripts) is covered by the repository's LICENSE. The third-party content above is not.
