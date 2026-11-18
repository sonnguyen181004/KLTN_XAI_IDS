"""Independent numeric-fixture expectations and raw-dataset convention checks."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pc
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'RQ4_Retrain_Compare/scripts'))
from rq4_common import FEATURES, FEATURE_MAP

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
report=json.loads((HERE/'java_contract_audit_20261118.json').read_text(encoding='utf-8'))
out=ROOT/report['artifacts']
# Hand-calculated from five payloads [10,20,30,40,50], alternating F/B,
# at 0,.1,.2,.3,.4 sec, TCP header 20, window F=1000, B=2000 then3000.
expected={n:0.0 for n in FEATURES}
expected.update({'Dst Port':443,'Protocol':6,'Flow Duration':400000,
    'Tot Fwd Pkts':3,'Tot Bwd Pkts':2,'TotLen Fwd Pkts':90,'TotLen Bwd Pkts':60,
    'Fwd Pkt Len Max':50,'Fwd Pkt Len Min':10,'Fwd Pkt Len Mean':30,'Fwd Pkt Len Std':20,
    'Bwd Pkt Len Max':40,'Bwd Pkt Len Min':20,'Bwd Pkt Len Mean':30,'Bwd Pkt Len Std':np.sqrt(200),
    'Flow Byts/s':375,'Flow Pkts/s':12.5,'Flow IAT Mean':100000,'Flow IAT Max':100000,'Flow IAT Min':100000,
    'Fwd IAT Tot':400000,'Fwd IAT Mean':200000,'Fwd IAT Max':200000,'Fwd IAT Min':200000,
    'Bwd IAT Tot':200000,'Bwd IAT Mean':200000,'Bwd IAT Max':200000,'Bwd IAT Min':200000,
    'Fwd PSH Flags':3,'Bwd PSH Flags':2,'Fwd Header Len':60,'Bwd Header Len':40,
    'Fwd Pkts/s':7.5,'Bwd Pkts/s':5,'Pkt Len Min':10,'Pkt Len Max':50,'Pkt Len Mean':30,
    'Pkt Len Std':np.sqrt(250),'Pkt Len Var':250,'PSH Flag Cnt':5,'ACK Flag Cnt':5,
    'Down/Up Ratio':2/3,'Pkt Size Avg':30,'Fwd Seg Size Avg':30,'Bwd Seg Size Avg':30,
    'Init Fwd Win Byts':1000,'Init Bwd Win Byts':2000,'Fwd Act Data Pkts':3,'Fwd Seg Size Min':20})
# Baseline network interpretation. The pinned 2022 source has legacy behavior
# for subflows, backward window and first-packet active-data count (below).
published_expected = dict(expected)
published_expected.update({'Subflow Fwd Byts':18,'Subflow Bwd Byts':12,
                           'Init Bwd Win Byts':3000,'Fwd Act Data Pkts':2})
checks={}
for version in ('current','improved_2022'):
    frame=pd.read_csv(out/version/'numeric_fixture.pcap_Flow.csv')
    row=frame[frame['Src Port']==40001].iloc[0]
    checks[version]={n:{'expected_network_baseline':float(expected[n]),
        'expected_published_2022':float(published_expected[n]), 'actual':float(row[FEATURE_MAP[n]]),
        'matches_network_baseline':bool(np.isclose(expected[n],row[FEATURE_MAP[n]],rtol=1e-6,atol=1e-6)),
        'matches_published_2022':bool(np.isclose(published_expected[n],row[FEATURE_MAP[n]],rtol=1e-6,atol=1e-6))} for n in FEATURES}
assert all(c['matches_published_2022'] for c in checks['improved_2022'].values())

relations={}
relation_cols=['Tot Fwd Pkts','Tot Bwd Pkts','TotLen Fwd Pkts','TotLen Bwd Pkts',
               'Subflow Fwd Pkts','Subflow Bwd Pkts','Subflow Fwd Byts','Subflow Bwd Byts',
               'Pkt Len Mean','Pkt Size Avg','Down/Up Ratio','Protocol','Init Fwd Win Byts','Init Bwd Win Byts']
for name,path in [('M0',ROOT/'dataset/CICID-2018_processed/train_set.parquet'),
                  ('M1_reference',ROOT/'RQ4_Retrain_Compare/data/d2_train.parquet')]:
    counters={}
    def check(key,eligible,actual,wanted):
        a,b=counters.get(key,(0,0)); counters[key]=(a+int(eligible.sum()),b+int((eligible & np.isclose(actual,wanted,rtol=2e-5,atol=1e-3)).sum()))
    for batch in pq.ParquetFile(path).iter_batches(batch_size=65536,columns=relation_cols):
        d=batch.to_pandas();f=d['Tot Fwd Pkts'];b=d['Tot Bwd Pkts'];n=f+b;ok=n>0
        for direction in ['Fwd','Bwd']:
            for word,total in [('Pkts',d['Tot '+direction+' Pkts']),('Byts',d['TotLen '+direction+' Pkts'])]:
                check('subflow_'+direction+'_'+word+'_floor_total_div_packets',ok,d['Subflow '+direction+' '+word],np.floor(total/n.where(ok,1)))
                check('subflow_'+direction+'_'+word+'_equals_total',ok,d['Subflow '+direction+' '+word],total)
            check('udp_'+direction+'_window_minus_one',d.Protocol==17,d['Init '+direction+' Win Byts'],-1)
            check('udp_'+direction+'_window_zero',d.Protocol==17,d['Init '+direction+' Win Byts'],0)
        fractional=(f>0)&(b/f.where(f>0,1)%1!=0)
        check('ratio_floor',fractional,d['Down/Up Ratio'],np.floor(b/f.where(f>0,1)))
        check('ratio_real',fractional,d['Down/Up Ratio'],b/f.where(f>0,1))
        check('mean_equals_size',ok,d['Pkt Len Mean'],d['Pkt Size Avg'])
        check('size_n_equals_mean_n_plus_1',ok,d['Pkt Size Avg']*n,d['Pkt Len Mean']*(n+1))
    relations[name]={key:{'eligible':a,'matches':b} for key,(a,b) in counters.items()}

# Scan the original raw day containing SSH, not only the processed parquet.
raw_checks={}
cols=['FIN Flag Cnt','SYN Flag Cnt','RST Flag Cnt','PSH Flag Cnt','ACK Flag Cnt','URG Flag Cnt',
      'Fwd PSH Flags','Bwd PSH Flags','Init Bwd Win Byts','Pkt Len Mean','Pkt Size Avg','Down/Up Ratio']
for name,path,improved in [
    ('M0_raw_day14',ROOT/'dataset/CICID-2018_original_csv/Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv',False),
    ('M1_improved_raw_day14',ROOT/'dataset/CSECICIDS2018_improved/Wednesday-14-02-2018.csv',True)]:
    mapping={n:FEATURE_MAP[n] if improved else n for n in cols}
    opts=pc.ConvertOptions(include_columns=list(mapping.values())+['Label'],
        column_types={**{c:pa.float64() for c in mapping.values()},'Label':pa.string()},
        null_values=['','NaN','nan','Infinity','inf','-Infinity','-inf'])
    reader=pc.open_csv(path,read_options=pc.ReadOptions(block_size=1<<24),convert_options=opts)
    stats={n:{'min':None,'max':None,'above_one':0} for n in cols};nr=0;ssh=0
    for batch in reader:
        d=batch.to_pandas();nr+=len(d);ssh+=int(d.Label.isin(['SSH-Bruteforce','SSH-BruteForce']).sum())
        for n,c in mapping.items():
            a=d[c].to_numpy();a=a[np.isfinite(a)]
            if len(a):
                st=stats[n];lo,hi=float(a.min()),float(a.max())
                st['min']=lo if st['min'] is None else min(st['min'],lo)
                st['max']=hi if st['max'] is None else max(st['max'],hi)
                st['above_one']+=int((a>1).sum())
    raw_checks[name]={'rows':nr,'ssh_rows':ssh,'source':str(path.relative_to(ROOT)),'statistics':stats}
    print('RAW DONE',name,nr,flush=True)

result={'fixture_scope':'all 78 outputs on one numeric fixture; zeros do not validate positive bulk/idle/URG cases',
        'fixture_checks':checks,'raw_day14_checks':raw_checks,
        'full_train_relations':relations,
        'historical_pair_limit':'No original dataset PCAP paired with CSV found locally; exact historical equivalence remains unverified.'}
(HERE/'java_contract_verification_20261118.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
matrix=[]
for n in FEATURES:
    m0=report['datasets']['M0_original']['all_78_statistics'][n]
    m1=report['datasets']['M1_improved_reference']['all_78_statistics'][n]
    matrix.append({'feature':n,'java_column':FEATURE_MAP[n],
        'M0_train_min':m0['min'],'M0_train_max':m0['max'],
        'M1_reference_train_min':m1['min'],'M1_reference_train_max':m1['max'],
        'fixture_current':checks['current'][n]['actual'],
        'fixture_improved2022':checks['improved_2022'][n]['actual'],
        'fixture_expected_published2022':published_expected[n],
        'fixture_matches_published2022':checks['improved_2022'][n]['matches_published_2022'],
        'scope':'numeric fixture + full train ranges; not historical PCAP/CSV equivalence'})
pd.DataFrame(matrix).to_csv(HERE/'java_78_feature_contract_20261118.csv',index=False,encoding='utf-8-sig')
print({v:sum(not c['matches_published_2022'] for c in data.values()) for v,data in checks.items()})
