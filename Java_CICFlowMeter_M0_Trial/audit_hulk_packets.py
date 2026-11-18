"""Packet and training evidence, no capture or model modifications."""
from pathlib import Path
import subprocess,io,json,hashlib
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;pcap=HERE/'hulk-go.pcapng'
fields=['frame.time_epoch','ip.src','tcp.stream','tcp.flags.syn','tcp.flags.ack','tcp.flags.fin','tcp.flags.reset','tcp.window_size_value','http.request.method','http.connection','http.response.code']
args=[r'C:\Program Files\Wireshark\tshark.exe','-r',str(pcap),'-Y','ip.addr == 192.168.11.133 && ip.addr == 192.168.11.134 && tcp.port == 80','-T','fields']
for f in fields:args+=['-e',f]
r=subprocess.run(args,capture_output=True,text=True,check=True);df=pd.read_csv(io.StringIO(r.stdout),sep='\t',names=fields,dtype=str).fillna('');req=df[df['http.request.method']!=''];counts=req.groupby('tcp.stream').size();syn=df[(df['ip.src']=='192.168.11.133')&(df['tcp.flags.syn'].isin(['1','True']))&(df['tcp.flags.ack'].isin(['0','False']))]
out={'pcap':str(pcap),'sha256':hashlib.sha256(pcap.read_bytes()).hexdigest(),'tcp_packets':len(df),'capture_seconds':float(df['frame.time_epoch'].astype(float).max()-df['frame.time_epoch'].astype(float).min()),'tcp_streams':df['tcp.stream'].nunique(),'http_requests':len(req),'request_connection_headers':req['http.connection'].value_counts().to_dict(),'request_streams':len(counts),'streams_multiple_requests':int((counts>1).sum()),'requests_per_stream_median':float(counts.median()),'requests_per_stream_max':int(counts.max()),'syn_raw_window':syn['tcp.window_size_value'].value_counts().to_dict(),'fin_packets':int((df['tcp.flags.fin'].isin(['1','True'])).sum()),'rst_packets':int((df['tcp.flags.reset'].isin(['1','True'])).sum()),'http_status':df.loc[df['http.response.code']!='','http.response.code'].value_counts().to_dict()}
cols=['Label','Init Fwd Win Byts','Flow Duration','Tot Fwd Pkts','TotLen Bwd Pkts'];train=pd.read_parquet(ROOT/'dataset/CICID-2018_processed/train_set.parquet',columns=cols);out['train']={}
for label in ['DoS attacks-Hulk','DDOS attack-HOIC','Benign']:
 t=train[train.Label==label];out['train'][label]={'rows':len(t),'window_top':{str(k):int(v) for k,v in t['Init Fwd Win Byts'].value_counts().head(6).items()},'window_64240':int((t['Init Fwd Win Byts']==64240).sum()),'quantiles':{c:{str(k):float(v) for k,v in t[c].quantile([.1,.5,.9]).items()} for c in cols[2:]}}
import sys
sys.path.insert(0,str(ROOT/'RQ4_Retrain_Compare/scripts'))
from rq4_common import FEATURE_MAP
live=pd.read_csv(HERE/'output/dashboard_577f5569fe20.csv');live=live[(live['Src IP']=='192.168.11.133')&(live['Dst Port']==80)]
out['live_csv_medians']={c:float(live[FEATURE_MAP[c]].median()) for c in cols[1:]}
(HERE/'hulk_packet_train_audit_20261118.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
