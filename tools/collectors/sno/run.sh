#!/bin/bash
# usage: run.sh todo from to  -> fetch (one.sh) + write row (auto.py) per line
cd tools/collectors/sno
for i in $(seq $2 $3); do
 ./one.sh $1 $i > /tmp/sno_one.out 2>&1 || true
 head -2 /tmp/sno_one.out | tail -1 | cut -c1-120
 python3 auto.py $1 $i | cut -c1-420
done
