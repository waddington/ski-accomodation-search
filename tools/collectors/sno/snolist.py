import re,sys,html,time,subprocess,urllib.parse
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def get(url):
    time.sleep(2.5)
    return subprocess.run(['curl','-s','-A',UA,'-b','cj','-c','cj',url],capture_output=True,text=True).stdout
def parse(h):
    out=[]
    for it in h.split('<div class="hol-item-wrapper">')[1:]:
        u=re.search(r'href="(/ski-holidays/[^"?]+)',it).group(1)
        n=html.unescape(re.search(r'<h3><a[^>]*>([^<]+)',it).group(1))
        m1=re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',re.search(r'class="m1">(.*?)</div>',it,re.S).group(1))).strip()
        feat=re.findall(r'</span><span>([^<]+)</span>',it)
        p=re.search(r'class="px">([\d,]+)',it)
        d=re.search(r'hidden-sm">([^<]+)',it)
        out.append([n,u,m1,p.group(1) if p else '',re.sub(r'\s+',' ',d.group(1)) if d else '','|'.join(feat)])
    return out
slug=sys.argv[1]
base=f"https://www.sno.co.uk/ski-chalets/{slug}/"
h=get(base)
s=re.search(r'id="hdssettings" type="hidden" value="([^"]*)"',h)
if not s: print("NO SETTINGS"); sys.exit(1)
n=s.group(1).split('|')
cnt=re.search(r'There are (\d+) holidays',h)
total=int(cnt.group(1)) if cnt else 0
rows=[]
pg=1
while True:
    q=dict(r=n[10],t=n[11],d=n[12],s=n[0],c=n[1],i=n[2],fl=n[9],g=n[3],f=n[4],p=n[5],b=n[6],rt=n[7],dr=n[8],n=30,pg=pg,o=0)
    h2=get(base+'?'+urllib.parse.urlencode(q))
    r=parse(h2)
    rows+=r
    if not r or len(rows)>=total: break
    pg+=1
with open(f'lists/{slug}.tsv','w') as f:
    for r in rows: f.write('\t'.join(r)+'\n')
print(slug,'settings',s.group(1),'total',total,'got',len(rows),'unique',len({r[1] for r in rows}))
