import json,sys,re,subprocess,datetime
ROOT='/home/kai/Documents/Misc/ski-chalet-finder'
OUT='chalets/raw/site-sno.csv'
code=sys.argv[1]; ov=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
d=json.load(open(f'tools/collectors/sno/det/{code}.json'))
name=d['title'].split(',')[0].strip()
tr=[t for t in d['tries'] if t]
best=None
for t in tr:
    v=t['cal'].get('20 Mar 2027') or t['cal'].get('21 Mar 2027')
    if v and 'price' in v: best=t;break
if not best and tr: best=tr[-1]
def calv(t):
    return (t['cal'].get('20 Mar 2027') or t['cal'].get('21 Mar 2027') or {}) if t else {}
v=calv(best)
row={'chalet_id':ov.get('chalet_id')}
known=ov.pop('known',False)
ap={'LGW':'Gatwick','LHR':'Heathrow','STN':'Stansted','MAN':'Manchester','BHX':'Birmingham','FOLK':'Eurotunnel self-drive','LTN':'Luton','BRS':'Bristol','EDI':'Edinburgh','AO':'no flights (accommodation only)'}
pnote=''
if best:
    apn=ap.get(best['airport'],best['airport'])
    if 'price' in v: pnote=f"Sno 20 Mar 2027: £{v['price']}pp with {best['sharing']} sharing from {apn}"
    elif v.get('status'): pnote=f"Sno 20 Mar 2027: {v['status']}"
    elif v: pnote=f"Sno 20 Mar 2027: listed as available but not priced for {best['sharing']} sharing/{apn} (other options: airports {v.get('airports')}, sharing {v.get('sharing')})"
    else: pnote='Sno: no 20 Mar 2027 departure listed'
sno_url=d.get('url') or (best['url'].split('?')[0] if best else '')
if known:
    row.update({'listed_on':'Sno','found_via':'site-sno','date_checked':str(datetime.date.today()),'notes':(pnote+f"; Sno page {sno_url}").strip('; ')})
    for k,val in ov.items(): row[k]=val
else:
    bl=d['boardline']
    m=re.search(r'sleeps (\d+)(?:-(\d+))?',bl)
    smin,smax=(m.group(1),m.group(2)) if m and m.group(2) else (None,m.group(1) if m else None)
    b=bl.lower()
    board='self-catered' if 'room only' in b else 'catered' if (b.startswith('catered') or b.startswith('full board')) else 'self-catered' if 'self' in b else 'half-board' if 'half' in b else 'breakfast-only' if 'b&b' in b or 'bed & breakfast' in b else ''
    meals=[x.strip() for x in d['meals'].split('|') if x.strip() and not x.strip().startswith('MEALS AT') and x.strip() not in ('Chalet Board',)]
    feats=[x.strip() for x in d['features'].split('|')[1:] if x.strip()]
    fe=[]
    for x in feats:
        if x=='Chalet Service' or x.startswith('MEALS AT') or x.startswith('BEDROOMS'): break
        fe.append(x)
    dl=re.search(r'Ski lift • ([\d.]+)(k?m)',d['loc_dists'])
    dist=None
    if dl: dist=int(float(dl.group(1))*(1000 if dl.group(2)=='km' else 1))
    sio='yes' if ('Piste • Ski In/Out' in d['loc_dists'] or 'Ski In/Out' in fe) else ''
    prices=[x['price'] for t in tr if t['sharing']==(best or {}).get('sharing') for x in t['cal'].values() if 'price' in x]
    cd='Saturday' if best and '20 Mar 2027' in best['cal'] else 'Sunday' if best and '21 Mar 2027' in best['cal'] else 'Saturday' if '20 Mar 2027' in d['cal_default'] else 'Sunday' if best and '21 Mar 2027' in best['cal'] else ''
    inc=(best or {}).get('included','')
    incl=[x.strip() for x in inc.split('|')[1:] if x.strip() and not x.strip().startswith('No ')]
    summ=re.sub(r'\s+',' ',d['summary'].replace(' Summary\n','',1)).strip()
    words=summ.split()
    desc=' '.join(words[:40])
    fj=' | '.join(fe)
    nb=re.search(r'(\d+) Bedrooms',fj); nba=re.search(r'(\d+) Bathrooms',fj)
    row.update({'chalet_name':name,'bathrooms':int(nba.group(1)) if nba else None,'operator':'unknown (sold via Sno)','country':'France',
      'sleeps_min':smin,'sleeps_max':smax,'bedrooms':len(d['rooms']) or (int(nb.group(1)) if nb else None),'property_type':'chalet-hotel' if 'hotel' in name.lower() else 'chalet',
      'board':board,'catering_detail':'; '.join(meals)[:300],'other_facilities':', '.join(fe)[:200],'distance_to_lift_m':dist,'ski_in_out':sio or 'unknown',
      'changeover_day':cd or 'unknown','price_week_20_27_mar_2027':v.get('price'),'price_basis':'per-person','price_currency':'GBP',
      'price_type':'exact-week' if v.get('price') else ('season-range' if prices else ''),'price_range_low':min(prices) if prices else None,'price_range_high':max(prices) if prices else None,
      'price_includes':('package via Sno: '+', '.join(incl)) if incl else '','available_20_27_mar':'yes' if v.get('price') else 'no' if v.get('status','').lower().startswith('sold') else 'unknown',
      'description':desc,'url':sno_url,'listed_on':'Sno','found_via':'site-sno','date_checked':str(datetime.date.today()),
      'notes':pnote+(f"; price range = Sno dates priced for {best['sharing']} sharing from {ap.get(best['airport'],best['airport'])}" if prices else '')+"; operator not named on Sno (image code "+','.join(d['opcode'])+")"})
    for k,val in ov.items():
        if k=='notes+': row['notes']=row['notes']+'; '+val
        else: row[k]=val
    row.pop('notes+',None)
    if ov.get('imgs',True) is not False and d['imgs']:
        n=subprocess.run(['python3','tools/save_images.py',row['chalet_id']]+[u.replace('/v2/','/v0/') for u in d['imgs']]+[f'--referer={sno_url}'],cwd=ROOT,capture_output=True,text=True).stdout.strip().split('\n')[-1]
        try: row['image_count']=int(re.findall(r'\d+',n)[-1]); row['image_dir']=f"chalets/images/{row['chalet_id']}/"
        except: pass
    row.pop('imgs',None)
r=subprocess.run(['python3','tools/append_row.py',OUT,json.dumps(row)],cwd=ROOT,capture_output=True,text=True)
print(r.stdout.strip(),r.stderr.strip()); print({k:row.get(k) for k in ['chalet_id','sleeps_max','bedrooms','board','hot_tub','price_week_20_27_mar_2027','available_20_27_mar','price_range_low','price_range_high','image_count']})
