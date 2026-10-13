#!/usr/bin/env python3
# usage: auto.py <todo.tsv> <line> [json extra overrides]
# derives chalet_id/village/ski_area/hot_tub/sauna from det/<code>.json then calls mk.py
import json, sys, re, csv, subprocess, unicodedata
D = 'tools/collectors/sno'
ROOT = '/home/kai/Documents/Misc/ski-chalet-finder'
todo, ln = sys.argv[1], int(sys.argv[2])
extra = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
L = open(f'{D}/{todo}').read().split('\n')[ln - 1].split('\t')
code = re.search(r'_(\d+)/', L[1]).group(1)
d = json.load(open(f'{D}/det/{code}.json'))
def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')
parts = [p.strip() for p in d['title'].split('|')[0].split(',')]
name, base = parts[0], (parts[1] if len(parts) > 2 else '')
loc = re.sub(r'm[eé]ribel (&|&amp;) mottaret', '', (d['location'].split('\n',2)[-1] + ' ' + d['summary']).lower())
full = open(f'{D}/last.txt').read().lower() if False else (d['location'] + d['summary'] + d['features'] + d['communal'] + ' '.join(d['ht'])).lower()
loc = re.sub(r'(view|views|looking|up to|towards|overlook\w*)[^.]{0,40}1850', ' ', loc)
RA = {}; RV = {}
for r in csv.DictReader(open(f'{ROOT}/resorts/resorts_raw.csv')):
    RA.setdefault(r['village'], r['ski_area']); RV.setdefault(slug(r['village']), r['village'])
def vil():
    b = base
    if 'Menuires' in b:
        if 'reberty' in loc: return 'Les Menuires: Reberty 2000'
        if 'bruy' in loc: return 'Les Menuires: Les Bruyères'
        if 'saint martin' in loc or 'st martin' in loc: return 'St-Martin-de-Belleville'
        return 'Les Menuires'
    if 'Meribel' in b or 'Méribel' in b:
        if 'mottaret' in loc: return 'Méribel-Mottaret'
        if 'altiport' in loc: return 'Méribel Altiport'
        if 'meribel village' in loc or 'méribel village' in loc or 'meribel-village' in loc: return 'Méribel Village'
        if 'les allues' in loc: return 'Les Allues'
        if 'brides' in loc: return 'Brides-les-Bains'
        return 'Méribel (centre)'
    if 'Courchevel' in b:
        if 'la tania' in loc and '1850' not in loc: return 'La Tania'
        if 'le praz' in loc or '1300' in loc: return 'Courchevel Le Praz (1300)'
        if '1650' in loc or 'moriond' in loc: return 'Courchevel 1650 (Moriond)'
        if '1550' in loc or 'courchevel village' in loc or 'proveres' in loc or 'provères' in loc: return 'Courchevel 1550 (Village)'
        if '1850' in loc or 'jardin alpin' in loc or 'bellecôte' in loc or 'bellecote' in loc: return 'Courchevel 1850'
        return 'Courchevel'
    if 'Tania' in b: return 'La Tania'
    if 'Thorens' in b: return 'Val Thorens'
    if 'Morzine' in b:
        if 'montriond' in loc: return 'Montriond'
        if 'prodains' in loc: return 'Prodains'
        return 'Morzine'
    if 'Chatel' in b or 'Châtel' in b: return 'Châtel'
    return RV.get(slug(b), b)
v = vil()
d['ht'] = [x for x in d['ht'] if re.search(r'hot.?tub|whirlpool(?! bath)|nordic|jacuzzi(?! bath)', x, re.I)]
ht = ' '.join(d['ht']).lower()
if not ht and 'hot tub' not in full: hot = 'none'
elif re.search(r'(shared|communal)( outdoor| indoor)? (hot tub|jacuzzi)|hot tub[^.]{0,30}(shared|communal)|residence', ht): hot = 'yes-type-unknown'
elif re.search(r'outdoor|outside|terrace|balcony|garden|open-air|open air', ht): hot = 'private-outdoor'
elif re.search(r'indoor|spa room|basement|ground floor|wellness|spa area', ht): hot = 'private-indoor'
else: hot = 'private (location not stated)'
sauna = 'yes' if 'sauna' in full else 'no'
cid = 'sno-' + slug(name)
ids = {r['chalet_id'] for r in csv.DictReader(open(f'{ROOT}/chalets/chalets_all.csv'))}
ids |= {r['chalet_id'] for r in csv.DictReader(open(f'{ROOT}/chalets/raw/site-sno.csv'))}
if cid in ids and not extra.get('known'):
    cid = cid + '-' + slug(v.split(':')[-1].split('(')[0])
    if cid in ids: cid = cid + '-' + code
ov = {'chalet_id': cid, 'village': v, 'ski_area': 'Les 3 Vallées' if any(k in base for k in ('Menuires','Meribel','Méribel','Courchevel','Tania','Thorens')) else RA.get(v, ''), 'country': parts[-1].split('|')[0].strip() or 'France', 'hot_tub': hot, 'sauna': sauna}
if extra.get('known'): ov = {'chalet_id': extra['chalet_id']}
nn = []
if '"family" chalet' in d['summary'] or 'family chalet' in d['summary'].lower(): nn.append('family chalet: bookings must include at least one child/teen')
st = ' '.join(re.findall(r'[^.|\n]*sauna[^.|\n]*', full))
if re.search(r'residence|complex|building|shared|share|all guests|wellness spa', st): nn.append('sauna appears shared (residence/complex), not private')
if d['ht']: nn.append('hot tub: ' + d['ht'][0][:120])
if nn and not extra.get('known'): ov['notes+'] = '; '.join(nn)
if 'notes+' in extra and 'notes+' in ov: extra['notes+'] = ov['notes+'] + '; ' + extra['notes+']
ov.update(extra)
r = subprocess.run(['python3', f'{D}/mk.py', code, json.dumps(ov)], cwd=ROOT, capture_output=True, text=True)
print(f'#{ln}', v, '| ht:', hot, '| sauna:', sauna, '|', r.stdout.strip().split('\n')[-1][:300], r.stderr.strip()[-300:])
