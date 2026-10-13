#!/bin/bash
# chk.sh <url> <name> : browse a Ski Line page and grep key facts
cd /home/kai/Documents/Misc/ski-chalet-finder
T=tools/collectors/skiline/sc/$2
node tools/browse.mjs "$1" $T >/dev/null 2>&1
grep -i -n "sleeps\|hot tub\|hot-tub\|jacuzzi\|spa \|sauna\|bedroom\|catered" $T/page.txt | grep -v "per child\|Helmet" | cut -c1-260 | head -${3:-20}
echo "--- 20/21 Mar:"; grep -o "date=S[au][tn]%202[01]%20Mar%202027[^	]*price=[0-9.]*" $T/links.txt | sed 's/.*price=/price=/' | head -3
