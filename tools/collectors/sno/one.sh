#!/bin/bash
# usage: one.sh <todo file> <line>
cd tools/collectors/sno
L=$(sed -n "${2}p" $1)
name=$(echo "$L"|cut -f1); path=$(echo "$L"|cut -f2); m1=$(echo "$L"|cut -f3)
smax=$(echo "$m1" | grep -o 'sleeps [0-9-]*' | grep -o '[0-9]*$')
[ -z "$smax" ] && smax=8
sh=$(( smax>10 ? 10 : smax ))
key=$(echo "$name" | sed 's/^Chalet //; s/,.*//')
echo "== #$2 $name sh=$sh  KNOWN?: $(grep -i "$key" /home/kai/Documents/Misc/ski-chalet-finder/chalets/chalets_all.csv | cut -d, -f1,4 | head -3 | tr '\n' ' ')"
python3 snodetail.py "https://www.sno.co.uk$path" $sh
echo "BEDS: $(grep -o -i '\b[0-9a-z]* \(en-suite \|ensuite \|en suite \)\?\(bedrooms\|bedroom\b\)' last.txt | sort | uniq -c | sort -rn | head -4 | tr -s ' ' | tr '\n' ';')  RoomLines: $(grep -c -i '^\(Room\|Rm\|Bedroom\) [0-9]' last.txt)"
grep -o "Number of persons[^|]*" last.txt | head -1
