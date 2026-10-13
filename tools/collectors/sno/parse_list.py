import re,sys,html
h=open(sys.argv[1],encoding='utf-8').read()
items=h.split('<div class="hol-item-wrapper">')[1:]
for it in items:
    u=re.search(r'href="(/ski-holidays/[^"?]+)',it).group(1)
    n=html.unescape(re.search(r'<h3><a[^>]*>([^<]+)',it).group(1))
    m1=re.sub(r'<[^>]+>','',re.search(r'class="m1">(.*?)</div>',it,re.S).group(1)).strip()
    m1=re.sub(r'\s+',' ',m1)
    feat=re.findall(r'</span><span>([^<]+)</span>',it)
    p=re.search(r'class="px">([\d,]+)',it)
    d=re.search(r'hidden-sm">([^<]+)',it)
    print('\t'.join([n,u,m1,p.group(1) if p else '',d.group(1) if d else '','|'.join(feat)]))
