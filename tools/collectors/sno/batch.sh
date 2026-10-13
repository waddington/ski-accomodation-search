#!/bin/bash
# usage: batch.sh todo from to
cd tools/collectors/sno
for i in $(seq $2 $3); do
 ./one.sh $1 $i 2>&1 | grep -v -E '^(VIL|BEDS|ROOMS)' | cut -c1-340
 c=$(sed -n ${i}p $1 | grep -o '_[0-9]*/' | tr -d '_/')
 python3 -c "import json;d=json.load(open('det/$c.json'));print('CODE $c ROOMS',len(d['rooms']),d['rooms'][:6] if len(d['rooms'])<3 else '', '| MEALS',d['meals'][30:200])" | cut -c1-330
done
