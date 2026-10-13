#!/bin/bash
# Re-scrape allChalets (LLM-free) for villages collected before the scraper existed.
cd /home/kai/Documents/Misc/ski-chalet-finder
for v in "les-menuires" "les-coches" "montchavin" "Tignes Les Brévières" "Tignes Les Boisses" "La Daille" "Le Fornet" "Tignes 1800" "Alpe d'Huez" "Combloux" "Saint-Gervais-les-Bains" "Saint-Nicolas-de-Véroce"; do
  echo "=== $(date +%H:%M) $v"
  python3 tools/scrapers/ingest.py rescrape-allchalets allchalets "$v" 2>&1 | tail -6
done
echo "=== $(date +%H:%M) ALL DONE"
