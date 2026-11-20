import pandas as pd, sys, json
D = sys.argv[1]; kind = sys.argv[2]; out = sys.argv[3]
if kind == 'orig':
    cols = {'FIN':'FIN Flag Cnt','FPL':'Fwd Pkt Len Max','FSS':'Fwd Seg Size Min','LAB':'Label','PROTO':'Protocol'}
else:
    cols = {'FIN':'FIN Flag Count','FPL':'Fwd Packet Length Max','FSS':'Fwd Seg Size Min','LAB':'Label','PROTO':'Protocol'}
res = {}
for ch in pd.read_csv(D, usecols=list(cols.values()), chunksize=250000, low_memory=False):
    ch = ch.rename(columns={v:k for k,v in cols.items()})
    ch = ch[ch['LAB'].astype(str)!='Label']
    for c in ['FIN','FPL','FSS','PROTO']:
        ch[c] = pd.to_numeric(ch[c], errors='coerce')
    ch = ch[ch['PROTO']==6]
    ch['fin'] = ch['FIN']>=1
    ch['data66'] = ch['FPL']>=66
    ch['data0'] = ch['FPL']>0
    ch['zone'] = ch['fin'] & ch['data66'] & (ch['FSS']<32)
    g = ch.groupby('LAB').agg(n=('fin','size'), fin=('fin','sum'), fin_data0=('data0', lambda s: 0), zone=('zone','sum'))
    g['fin_data66'] = ch[ch['fin']&ch['data66']].groupby('LAB').size().reindex(g.index).fillna(0)
    g['fin_data0'] = ch[ch['fin']&ch['data0']].groupby('LAB').size().reindex(g.index).fillna(0)
    for lab,row in g.iterrows():
        r = res.setdefault(lab, dict(n=0,fin=0,fin_data0=0,fin_data66=0,zone=0))
        for k in r: r[k]+= int(row[k])
json.dump(res, open(out,'w'), indent=1)
print('done', out)
