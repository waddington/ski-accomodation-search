#!/bin/bash
# run.sh "<API resort>" <sitemap-slug|-> : scrape -> fix -> ingest
set -e
cd /home/kai/Documents/Misc/ski-chalet-finder
D=tools/collectors/skiline/runs
S=$(echo "$1" | tr ' A-Z' '-a-z' | tr -d "'")
SM=()
[ "$2" != "-" ] && [ -n "$2" ] && SM=(--sitemap "$2")
python3 tools/scrapers/skiline.py "$1" "${SM[@]}" > $D/$S.raw.jsonl 2> $D/$S.err
tail -2 $D/$S.err
python3 tools/collectors/skiline/fix.py $D/$S.raw.jsonl $D/$S.jsonl
python3 tools/scrapers/ingest.py site-ski-line skiline --from-jsonl $D/$S.jsonl 2>&1 | tail -15
echo "--- hot tub check:"; python3 tools/collectors/skiline/nf.py $S | grep -A2 "^SHARED\|corrected"
