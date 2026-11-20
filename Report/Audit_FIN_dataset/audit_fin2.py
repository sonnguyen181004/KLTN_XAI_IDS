import pandas as pd, sys, json
D, out = sys.argv[1], sys.argv[2]
hdr = pd.read_csv(D, nrows=0).columns.tolist()
def pick(names):
    for n in names:
        if n in hdr: return n
    raise SystemExit('missing %s in %s' % (names, hdr[:5]))
finname = next((n for n in ['FIN Flag Cnt','FIN Flag Count'] if n in hdr), hdr[45])
cols = {'FIN':finname,
        'FPL':pick(['Fwd Pkt Len Max','Fwd Packet Length Max']),
        'FSS':pick(['Fwd Seg Size Min']),
        'LAB':pick(['Label']),
        'PROTO':pick(['Protocol'])}
res = {}
for ch in pd.read_csv(D, usecols=list(cols.values()), chunksize=250000, low_memory=False):
    ch = ch.rename(columns={v:k for k,v in cols.items()})
    ch = ch[ch['LAB'].astype(str)!='Label']
    for c in ['FIN','FPL','FSS','PROTO']:
        ch[c] = pd.to_numeric(ch[c], errors='coerce')
    ch = ch[ch['PROTO']==6]
    fin = ch['FIN']>=1; d66 = ch['FPL']>=66; d0 = ch['FPL']>0
    zone = fin & d66 & (ch['FSS']<32)
    df = pd.DataFrame({'LAB':ch['LAB'],'n':1,'fin':fin.astype(int),'fin_data0':(fin&d0).astype(int),'fin_data66':(fin&d66).astype(int),'zone':zone.astype(int)})
    g = df.groupby('LAB').sum()
    for lab,row in g.iterrows():
        r = res.setdefault(lab, dict(n=0,fin=0,fin_data0=0,fin_data66=0,zone=0))
        for k in r: r[k]+= int(row[k])
json.dump(res, open(out,'w'), indent=1)
print('done', out)
