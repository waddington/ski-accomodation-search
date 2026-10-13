#!/bin/bash
# spot.sh <run-slug> <name regex> : scraped values + live page facts
D=tools/collectors/skiline
U=$(grep -i "\"chalet_name\": \"[^\"]*$2" $D/runs/$1.jsonl | head -1 | python3 -c "
import sys,json
r=json.loads(sys.stdin.read()); print({k:r[k] for k in ['chalet_name','operator','sleeps_max','bedrooms','board','hot_tub','sauna','price_week_20_27_mar_2027','available_20_27_mar']}, file=sys.stderr); print(r['url'])")
$D/chk.sh "$U" "spot-$(basename $U)" ${3:-10}
