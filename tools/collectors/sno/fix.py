import csv,sys
p='/home/kai/Documents/Misc/ski-chalet-finder/chalets/raw/site-sno.csv'
cid,field,val=sys.argv[1:4]
rows=list(csv.DictReader(open(p))); fn=list(rows[0].keys())
for r in rows:
    if r['chalet_id']==cid: r[field]=val if not val.startswith('+') else (r[field]+'; '+val[1:])
w=csv.DictWriter(open(p,'w',newline=''),fieldnames=fn); w.writeheader(); w.writerows(rows)
