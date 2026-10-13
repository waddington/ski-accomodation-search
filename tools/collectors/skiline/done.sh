#!/bin/bash
# done.sh "<resort line>" : record resort in checkpoint
F=/home/kai/Documents/Misc/ski-chalet-finder/chalets/raw/site-ski-line.checkpoint.md
python3 - "$1" "$F" <<'P'
import sys
line,f=sys.argv[1],sys.argv[2]; s=open(f).read()
s=s.replace("## Resorts left", "- "+line+"\n\n## Resorts left",1).replace("\n\n- "+line,"\n- "+line)
open(f,'w').write(s)
P
