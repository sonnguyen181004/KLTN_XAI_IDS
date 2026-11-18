"""Offline replay of the user's SSH demo through both extractors and frozen models."""
import argparse
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
import uuid
import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT/'RQ3_IDS_System/app'))
sys.path.insert(0, str(ROOT/'RQ4_Retrain_Compare/scripts'))
from feeder import row_to_payload
from rq4_common import FEATURE_MAP
from explain_shap import ShapExplainer
from run_java_live_m0 import java_environment

def run(args, **kwargs):
    p = subprocess.run(list(map(str,args)), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=180, **kwargs)
    if p.returncode:
        raise RuntimeError(p.stdout[-1000:]+p.stderr[-1000:])
    return p.stdout

parser = argparse.ArgumentParser()
parser.add_argument('--pcap', type=Path, default=HERE/'ssbrute.pcapng')
parser.add_argument('--output', type=Path, default=HERE/'ssh_pcap_audit_20261118.json')
parser.add_argument('--live-csv', type=Path)
args = parser.parse_args()
source = args.pcap.resolve()
out = HERE/'output'/('ssh_replay_'+uuid.uuid4().hex[:8])
out.mkdir(parents=True)
pcap = out/'ssbrute.pcap'
run([r'C:\Program Files\Wireshark\editcap.exe','-F','pcap',source,pcap])
fields = ['frame.time_epoch','ip.src','ip.dst','tcp.srcport','tcp.dstport','tcp.stream','tcp.len','tcp.flags.syn','tcp.flags.fin','tcp.flags.reset']
cmd=[r'C:\Program Files\Wireshark\tshark.exe','-n','-r',source,'-Y','ip && tcp','-T','fields','-E','header=y','-E','separator=,']
for f in fields: cmd += ['-e',f]
packets=pd.read_csv(io.StringIO(run(cmd)))
ssh=packets[(packets['tcp.dstport']==22)|(packets['tcp.srcport']==22)]
streams=[]
for stream,g in ssh.groupby('tcp.stream'):
    streams.append({'stream':int(stream),'packets':len(g),'start_epoch':float(g['frame.time_epoch'].min()),
                    'duration_seconds':float(g['frame.time_epoch'].max()-g['frame.time_epoch'].min()),
                    'client_ports':sorted(set(int(v) for v in g.loc[g['tcp.dstport']==22,'tcp.srcport'])),
                    'fin_packets':int(g['tcp.flags.fin'].sum()),'syn_packets':int(g['tcp.flags.syn'].sum()),
                    'rst_packets':int(g['tcp.flags.reset'].sum())})
log=run([HERE/'upstream/gradlew.bat','exeCMD',f'-PtrialInput={pcap}',f'-PtrialOutput={out}',
         '--offline','--no-daemon','--console=plain'],cwd=HERE/'upstream',env=java_environment())
(out/'java.log').write_text(log,encoding='utf-8')
log=run([ROOT/'RQ3_IDS_System/.venv_capture/Scripts/python.exe',ROOT/'RQ3_IDS_System/scripts/run_live_capture.py',
         '--pcap-input',pcap,'--output',out/'python.csv','--extractor','project'])
(out/'python.log').write_text(log,encoding='utf-8')
models={}; model_hashes={}
for name,folder,filename in [('M0','RQ1_Model_Training_xboost/saved_models','best_xgboost_model.pkl'),('M1','IDS_M1_Lab/models','m1_xgboost_model.pkl')]:
    path=ROOT/folder/filename
    model_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    models[name]=(joblib.load(path),joblib.load(path.with_name('label_encoder.pkl' if name=='M0' else 'm1_label_encoder.pkl')).classes_)
names=list(models['M0'][0].feature_names_in_)
report={'model_sha256':model_hashes,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'all_tcp_packets':len(packets),'ssh_packets':len(ssh),
        'tcp_streams':streams,'extractors':{},'comparison':{},'artifacts':str(out.relative_to(ROOT))}
frames={};raws={}
for kind,path in [('java',out/'ssbrute.pcap_Flow.csv'),('python',out/'python.csv')]:
    raw=pd.read_csv(path);raws[kind]=raw
    if kind=='java':
        x=raw[[FEATURE_MAP[n] for n in names]].copy();x.columns=names
    else:
        x=pd.DataFrame([row_to_payload(r,list(raw.columns),True) for r in raw.to_dict('records')]).reindex(columns=names)
    frames[kind]=x
    protocol_col, port_col = ('Protocol', 'Dst Port') if kind=='java' else ('protocol', 'dst_port')
    ssh_mask = (raw[protocol_col] == 6) & (raw[port_col] == 22)
    valid=np.isfinite(x.to_numpy()).all(axis=1)
    item={'rows':len(x),'invalid':int((~valid).sum()),'packet_sum':int((x['Tot Fwd Pkts']+x['Tot Bwd Pkts']).sum()),'models':{}}
    item['ssh_rows'] = int(ssh_mask.sum())
    item['ssh_packet_sum'] = int((x.loc[ssh_mask,'Tot Fwd Pkts'] + x.loc[ssh_mask,'Tot Bwd Pkts']).sum())
    for name,(model,classes) in models.items():
        p=model.predict_proba(x.loc[valid,list(model.feature_names_in_)]);labels=classes[p.argmax(axis=1)]
        explainer=ShapExplainer(model,list(classes)); examples=[]
        for pos,i in enumerate(x.index[valid]):
            examples.append({'row':int(i)+1,'label':str(labels[pos]),'confidence':float(p[pos].max()),
                'ssh_probability':float(p[pos,list(classes).index('SSH-Bruteforce')]),
                'shap_for_prediction':explainer.explain(x.loc[[i]],str(labels[pos])),
                'shap_for_ssh':explainer.explain(x.loc[[i]],'SSH-Bruteforce')})
        item['models'][name]={'labels':pd.Series(labels).value_counts().to_dict(),'examples':examples}
        item['models'][name]['ssh_labels'] = pd.Series(labels[ssh_mask.loc[valid].to_numpy()]).value_counts().to_dict()
    report['extractors'][kind]=item

# Compare only unique directional 5-tuples; do not pair by row position.
keys={}
for kind,raw in raws.items():
    cols=['Src IP','Dst IP','Src Port','Dst Port','Protocol'] if kind=='java' else ['src_ip','dst_ip','src_port','dst_port','protocol']
    group={}
    for i,row in raw.iterrows():
        k=tuple(str(row[c]) for c in cols)
        group.setdefault(k,[]).append(i)
    keys[kind]=group
pairs=[(keys['java'][k][0],keys['python'][k][0]) for k in keys['java'].keys() & keys['python'].keys()
       if len(keys['java'][k])==len(keys['python'][k])==1]
report['comparison']['unique_tuple_pairs']=len(pairs)
report['comparison']['differences']={n:{'pairs_different':sum(not np.isclose(frames['java'].at[a,n],frames['python'].at[b,n],rtol=1e-5,atol=1e-5) for a,b in pairs),
    'java_values':[float(frames['java'].at[a,n]) for a,b in pairs],
    'python_values':[float(frames['python'].at[b,n]) for a,b in pairs]} for n in names}
if args.live_csv:
    live=pd.read_csv(args.live_csv)
    j=raws['java']; feats=[FEATURE_MAP[n] for n in names]
    identity=['Src IP','Dst IP','Src Port','Dst Port','Protocol']
    merged=j.merge(live,on=identity,suffixes=('_offline','_live'),validate='one_to_one')
    report['java_live_replay']={'matched_rows':len(merged),'all_78_features_equal':all(np.allclose(merged[n+'_offline'],merged[n+'_live'],rtol=1e-9,atol=1e-6,equal_nan=True) if n not in identity else True for n in feats)}
    report['java_live_replay']['different_features_max_abs_delta'] = {
        name: float(np.max(np.abs(merged[col+'_offline']-merged[col+'_live'])))
        for name,col in FEATURE_MAP.items() if col not in identity
        and not np.allclose(merged[col+'_offline'],merged[col+'_live'],rtol=1e-9,atol=1e-6,equal_nan=True)
    }
else:
    report['java_live_replay'] = {'status': 'not_checked_no_live_csv_supplied'}

target=args.output
target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({**{k:v for k,v in report.items() if k not in ('extractors','comparison')},'extractors':{k:{**{n:v for n,v in r.items() if n!='models'},'models':{n:m['labels'] for n,m in r['models'].items()}} for k,r in report['extractors'].items()}},indent=2))
