import re,sys,html,time,subprocess,json
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
OPS=["Ski Total","Crystal","Inghams","Skiworld","Ski World","Esprit","Mark Warner","Neilson","Ski Beat","VIP SKI","VIP Ski","Le Ski","Ski Famille","Ski Independence","Powder White","Supertravel","Scott Dunn","Alpine Elements","Skibound","Ski Freshtracks","Club Med","Ski Peak","Purple Ski","Ski Line","Leo Trippi","Snowcrystal","Bramble","Simon Butler","Chalet Chardons","White Horizon","SkiWeekends","Ski Solutions","Firefly","TOPS","Zenith","Ski Club"]
def run(args):
    return subprocess.run(['curl','-s','-L','-A',UA,'-b','cj','-c','cj']+args,capture_output=True,text=True).stdout
def get(url):
    time.sleep(2.5); return run([url])
def txt(h):
    h=re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',h))
    return re.sub(r'[ \t]+',' ',re.sub(r'\n\s*\n+','\n',t))
def cal(h):
    rows={}
    i=h.find('AVAILABILITY &amp; PRICE')
    if i<0: i=h.find('AVAILABILITY & PRICE')
    segs=h[i:].split('<td class="c0">')[1:]
    for s in segs:
        d=re.search(r'hidden-xxs">\w+ (\d\d \w+ \d{4})',s)
        if not d: continue
        d=d.group(1)
        c1=re.search(r'class="c1">(.*?)</td>',s,re.S)
        df=re.findall(r'data-df="([A-Z]+)"',s); do=re.findall(r'data-do="(\d+)"',s); dn=re.findall(r'data-dn="(\d+)"',s)
        if df or do or dn:
            rows[d]={'avail':'other','airports':df,'sharing':do,'nights':dn}
        elif c1:
            v=re.sub(r'<[^>]+>','',c1.group(1)).strip(); v=html.unescape(v)
            m=re.search(r'£([\d,]+)',v)
            rows[d]={'price':int(m.group(1).replace(',','')) } if m else {'status':v}
        if d.endswith('2027') and 'Apr' in d and '17 Apr' in d: break
    return rows
def section(t,a,b,maxlen=1500):
    i=t.find(a)
    if i<0: return ''
    j=t.find(b,i+len(a)) if b else -1
    s=t[i:j if j>0 else i+maxlen]
    return s[:maxlen]
url=sys.argv[1].split('?')[0]; want=int(sys.argv[2]) if len(sys.argv)>2 else 8
code=re.search(r'_(\d+)/$',url).group(1)
h=get(url)
t=txt(h)
open('last.txt','w').write(t)
out={'url':url}
out['title']=re.search(r'<title>([^<]*)',h).group(1).strip()
m=re.search(r'\n(\w[\w -]*?) (chalet|hotel|apartment|chalet hotel)[^\n]*\(sleeps ([\d-]+)\)',t,re.I)
out['boardline']=re.search(r'\n([^\n]*\(sleeps[^\n]*\))',t).group(1) if '(sleeps' in t else ''
out['loc_dists']=' ; '.join(re.findall(r'\n((?:Town centre|Ski school|Ski lift|Piste|Bus stop|Lift|Shops)[^\n]*•[^\n]*)',t))
out['location']=section(t,'\nLocation of','\nDistance of',1200)
out['summary']=section(t,' Summary\n','WHY YOU WILL LOVE',1500)
out['features']=section(t,'FEATURES & FACILITIES','\nImportant Info',1200).replace('\n',' | ')
out['meals']=section(t,'\nMEALS AT','\nBEDROOMS',900).replace('\n',' | ')
bed=section(t,'\nBEDROOMS','AVAILABILITY & PRICE',4000)
out['rooms']=re.findall(r'\n([^\n|]{0,60}\(sleeps [\d-]+\))',bed)
out['communal']=section(bed,'Communal Facilities','zzzz',1200).replace('\n',' | ')
ops=[o for o in OPS if re.search(r'\b'+re.escape(o)+r'\b',t)]
out['op_mentions']=ops
imgs=[]
for u in re.findall(r'https://static1\.sno\.co\.uk/images/accom/v2/[a-z0-9]+/[0-9a-f-]+\.(?:jpg|jpeg|png|webp)',h):
    if u not in imgs: imgs.append(u)
out['imgs']=imgs[:8]
out['opcode']=sorted(set(re.findall(r'images/accom/v\d/([a-z0-9]+)/',h)))
out['cal_default']=cal(h)
# POST for 20 Mar
def post(sharing,airport,act='50',date='2027-03-20'):
    tok=re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]*)"',h).group(1)
    bb=re.search(r'id="sv-boardbasis" value="([^"]*)"',h).group(1)
    pt=re.search(r'id="sv-propertytype" value="([^"]*)"',h).group(1)
    time.sleep(2.5)
    hdr=subprocess.run(['curl','-s','-A',UA,'-b','cj','-c','cj','-D','-','-o','/dev/null','-e',url,'--data-urlencode',f'__RequestVerificationToken={tok}','-d',f'act={act}&duration=7&sharing={sharing}&airport={airport}&boardbasis={bb}&departureDate={date}&accomcode={code}&propertytype={pt}','https://www.sno.co.uk/Accom/Search'],capture_output=True,text=True).stdout
    loc=re.search(r'location: (\S+)',hdr,re.I)
    if not loc: return None,None
    u2='https://www.sno.co.uk'+loc.group(1).split('#')[0]
    h2=get(u2)
    sh=re.search(r'id="sv-sharing" value="([^"]*)"',h2); ap=re.search(r'id="sv-airport" value="([^"]*)"',h2)
    inc=section(txt(h2),"WHAT'S INCLUDED",'SHOW MORE',400).replace('\n',' | ')
    return {'url':u2,'sharing':sh.group(1) if sh else '','airport':ap.group(1) if ap else '','cal':cal(h2),'included':inc},h2
dc=out['cal_default']
DATE='2027-03-21' if ('21 Mar 2027' in dc and '20 Mar 2027' not in dc) else '2027-03-20'
defap=re.search(r'id="sv-airport" value="([^"]*)"',h).group(1)
AP0=sys.argv[3] if len(sys.argv)>3 else 'LGW'
r,h2=post(want,AP0,date=DATE)
if not r and defap!='LGW': r,h2=post(want,defap,date=DATE)
tries=[r]
if r:
    m=r['cal'].get('20 Mar 2027') or r['cal'].get('21 Mar 2027') or {}
    if m.get('avail')=='other':
        if m['airports']:
            r2,_=post(want,m['airports'][0],date=DATE); tries.append(r2)
        elif m['sharing']:
            r2,_=post(max(int(x) for x in m['sharing']),r['airport'] or 'LGW',date=DATE); tries.append(r2)
out['tries']=tries
json.dump(out,open(f'det/{code}.json','w'),indent=1)
# compact print
prop=t[:t.find('AVAILABILITY & PRICE')] if 'AVAILABILITY & PRICE' in t else t
prop=prop[prop.find('WHAT\'S INCLUDED'):] if "WHAT'S INCLUDED" in prop else prop
VIL=['Val Claret','Le Lac','Lavachet','Tignes 1800','Les Boisses','Brévières','Brevieres','La Daille','Le Fornet','Fornet','Joseray','Le Laisinant','Laisinant','Le Crêt','La Legettaz','Legettaz','Les Richardes','Manchet','Le Châtelard','Chatelard','La Thovex','Le Coin','Solaise','Bellevarde','Le Rogoney','Rogoney','La Daille','Front de Neige','Les Brevières','Plagne Centre','Plagne Villages','Plagne Soleil','Aime 2000','Aime-la-Plagne','Aime la Plagne','Plagne Bellecote','Bellecote','Plagne 1800','Belle Plagne','Plagne 2000','Plagne Montalbert','Montalbert','Champagny','Les Coches','Montchavin','Arc 1600','Arc 1800','Arc 1950','Arc 2000','Peisey','Vallandry','Plan Peisey','Villaroger','Bourg St Maurice','Bourg-Saint-Maurice','Le Villaret','Charvet','Chantel','Villards','Courchevel','Meribel','Méribel','La Tania','Les Menuires','Val Thorens','Saint Martin','St Martin','Mottaret','Brides','Le Praz','Moriond','1850','1650','1550','Val Thorens','Reberty','Croisette','Vaujany','Oz-en-Oisans','Oz en Oisans','Auris','Villard-Reculas','Villard Reculas','Huez','Venosc','Vénosc','Mont-de-Lans','Les Bergers','Vieil Alpe','Eclose','Sardonne','Signal','Les Jardins','Pied Moutet','Rond-Point','Le Village']
out['vil']=sorted({v for v in VIL if v.lower() in prop.lower()})
ht=[re.sub(r'\s+',' ',x.strip())[:220] for x in re.findall(r'[^.\n|]*(?:hot tub|jacuzzi|whirlpool|hot-tub|spa bath|nordic bath)[^.\n|]*',prop,re.I)]
out['ht']=list(dict.fromkeys(ht))[:5]
json.dump(out,open(f'det/{code}.json','w'),indent=1)
print(out['title'],'|',out['boardline'],'|',out['loc_dists'],'| ops',out['op_mentions'],out['opcode'])
print('VIL:',out['vil'])
print('LOC:',re.sub(r'\s+',' ',out['location'])[60:560])
print('SUM:',re.sub(r'\s+',' ',out['summary'])[9:450])
print('HT:',out['ht'])
print('FEAT:',out['features'][24:400])
print('ROOMS:',len(out['rooms']),'| COMM:',out['communal'][22:260])
for tr in tries:
    if not tr: print('POST failed'); continue
    c=tr['cal']; pr=[v['price'] for v in c.values() if 'price' in v]
    print('DEFAULT(2sh):',{k:v for k,v in dc.items() if 'Mar' in k}) if not any(tries) else None
    print('TRY',tr['sharing'],tr['airport'],'20Mar:',c.get('20 Mar 2027') or c.get('21 Mar 2027'),'range',min(pr) if pr else None,max(pr) if pr else None,'| inc',tr['included'][18:120])
    print('  MAR:',{k[:6]:(v.get('price') or v.get('status') or 'other') for k,v in c.items() if 'Mar 2027' in k or 'Apr 2027' in k})
