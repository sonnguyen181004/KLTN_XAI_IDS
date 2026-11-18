"""Offline, repeatable audit of saved lab packets. Never starts traffic or changes models."""
from pathlib import Path
import sys, json, subprocess, hashlib, io
import pandas as pd
import numpy as np
import joblib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'RQ4_Retrain_Compare/scripts'))
from rq4_common import FEATURES, FEATURE_MAP
from runtime_profile import resolve
from run_java_live_m0 import java_environment

def run(args,**kw):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600,**kw)
    if r.returncode: raise RuntimeError(r.stderr[-3000:]+r.stdout[-3000:])
    return r.stdout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out=HERE/'output/attack_load_report_20261118'
out.mkdir(parents=True,exist_ok=True)
inputs=out/'pcaps';inputs.mkdir(exist_ok=True)
names=['ssbrute','ss2','dos_oldeney','oldeneye2','hulk-go','hulk2','slowloris1','slowloris2 ','LOIC']
report={'scope':'Offline re-extraction of saved PCAP; label shares are not ground-truth accuracy. No live capture.','pcaps':{},'models':{}}
target=HERE/'attack_load_audit_20261118.json'
def save():target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
fields=['frame.time_epoch','frame.len','tcp.stream','ip.src','ip.dst','tcp.srcport','tcp.dstport','http.request.method','http.response.code','http.connection','tcp.flags.syn','tcp.flags.fin','tcp.flags.reset','tcp.window_size_value']
for n in names:
    src=HERE/(n+'.pcapng'); key=n.strip()
    run([r'C:\Program Files\Wireshark\editcap.exe','-F','pcap',src,inputs/(key+'.pcap')])
    args=[r'C:\Program Files\Wireshark\tshark.exe','-r',src,'-Y','ip.addr==192.168.11.133 && ip.addr==192.168.11.134 && tcp','-T','fields','-E','separator=,','-E','quote=d','-E','occurrence=f']
    for f in fields:args+=['-e',f]
    text=run(args)
    d=pd.read_csv(io.StringIO(text),names=fields)
    d.to_csv(out/(key+'_packets.csv'),index=False)
    t=d[fields[0]];req=d['http.request.method'].notna()
    seconds=float(t.max()-t.min())
    report['pcaps'][key]={'file':src.name,'sha256':sha(src),'lab_tcp_packets':len(d),'tcp_streams':int(d['tcp.stream'].nunique()),'first_epoch':float(t.min()),'last_epoch':float(t.max()),'span_seconds':seconds,'http_requests':int(req.sum()),'http_requests_per_capture_second':float(req.sum()/seconds),'http_responses':d['http.response.code'].dropna().astype(int).astype(str).value_counts().to_dict(),'request_connection':d.loc[req,'http.connection'].fillna('(absent)').value_counts().to_dict(),'syn_windows':d.loc[d['tcp.flags.syn'].eq(1),'tcp.window_size_value'].value_counts().to_dict(),'profiles':{}}
    print('PACKETS',key,len(d),flush=True);save()
for m,folder,modelname,encoder in [('M0','RQ1_Model_Training_xboost/saved_models','best_xgboost_model.pkl','label_encoder.pkl'),('M1','IDS_M1_Lab/models','m1_xgboost_model.pkl','m1_label_encoder.pkl')]:
    modelpath=ROOT/folder/modelname
    model=joblib.load(modelpath);classes=joblib.load(modelpath.with_name(encoder)).classes_
    report['models'][m]={'sha256':sha(modelpath),'classes':classes.tolist()}
    project,profile=resolve(m);dest=out/m;dest.mkdir(exist_ok=True)
    log=run([project/'gradlew.bat','exeCMD','-PtrialInput='+str(inputs),'-PtrialOutput='+str(dest),'--offline','--no-daemon','--console=plain'],cwd=project,env=java_environment())
    (dest/'java.log').write_text(log,encoding='utf-8')
    for n in names:
        key=n.strip();raw=pd.read_csv(dest/(key+'.pcap_Flow.csv'))
        raw.columns=raw.columns.str.strip()
        x=raw[[FEATURE_MAP[f] for f in FEATURES]].copy();x.columns=FEATURES
        ipcols=[c for c in raw if c.lower() in ['src ip','dst ip','source ip','destination ip']]
        assert len(ipcols)==2,raw.columns.tolist()
        mask=raw[ipcols].isin(['192.168.11.133','192.168.11.134']).all(axis=1)&x['Protocol'].eq(6)&(x['Dst Port'].isin([22,80])|raw.get('Src Port',pd.Series(0,index=raw.index)).isin([22,80]))
        finite=np.isfinite(x.to_numpy()).all(axis=1);valid=mask&finite
        p=model.predict_proba(x.loc[valid]);labels=classes[p.argmax(axis=1)]
        x['lab_target']=mask;x['finite']=finite;x['prediction']='invalid_or_outside';x.loc[valid,'prediction']=labels
        x.to_csv(dest/(key+'_features_predictions.csv'),index=False)
        item={'profile':profile,'all_flows':len(raw),'lab_flows':int(mask.sum()),'lab_invalid':int((mask&~finite).sum()),'lab_valid':int(valid.sum()),'labels':pd.Series(labels).value_counts().to_dict(),'lab_flow_packet_sum':int((x.loc[mask,'Tot Fwd Pkts']+x.loc[mask,'Tot Bwd Pkts']).sum()),'medians':{f:float(x.loc[valid,f].median()) for f in ['Flow Duration','Tot Fwd Pkts','Tot Bwd Pkts','TotLen Bwd Pkts','Init Fwd Win Byts','FIN Flag Cnt','PSH Flag Cnt']}}
        report['pcaps'][key]['profiles'][m]=item
        print('MODEL',m,key,item['labels'],flush=True);save()
print('DONE',target,flush=True)
