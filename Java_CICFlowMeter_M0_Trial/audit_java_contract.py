"""Reproducible dataset/Java contract audit. No model training or live capture.

Published improved source is pinned to a 2022 commit, not asserted to be the
exact unpublished dataset-generation commit. Never edits upstream/runtime.
"""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import confusion_matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT/'RQ4_Retrain_Compare/scripts'))
sys.path.insert(0, str(ROOT/'RQ3_IDS_System/app'))
from rq4_common import FEATURES, FEATURE_MAP
from feeder import row_to_payload
from run_java_live_m0 import java_environment
from extract_java_dataset import prepare

PIN = '13a061520b862d605eea746c79ca4033b30d98fc'
REFERENCE_URL = 'https://github.com/GintsEngelen/CICFlowMeter.git'


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(args, **kwargs):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=300, **kwargs)
    if p.returncode:
        raise RuntimeError(p.stdout[-2500:] + p.stderr[-2500:])
    return p.stdout


def canonical(raw):
    x = raw[[FEATURE_MAP[n] for n in FEATURES]].copy()
    x.columns = FEATURES
    return x


def predictions(x):
    valid = np.isfinite(x.to_numpy()).all(axis=1)
    result = {'rows':len(x), 'invalid_rows':int((~valid).sum()), 'models': {}}
    for name,(model, classes) in models.items():
        if not valid.any():
            result['models'][name] = {'labels':{}, 'reason':'no_finite_rows'}
            continue
        p = model.predict_proba(x.loc[valid, FEATURES])
        labels = classes[p.argmax(axis=1)]
        result['models'][name] = {'labels':pd.Series(labels).value_counts().to_dict()}
        ssh = x.loc[valid, 'Dst Port'].eq(22).to_numpy() & x.loc[valid,'Protocol'].eq(6).to_numpy()
        result['models'][name]['port22_labels'] = pd.Series(labels[ssh]).value_counts().to_dict()
        result['models'][name]['port22_ssh_probabilities'] = p[ssh,list(classes).index('SSH-Bruteforce')].tolist()
    return result


out = HERE/'output'/('contract_'+uuid.uuid4().hex[:8])
out.mkdir(parents=True)
report = {'scope':'offline; no exact historical PCAP/CSV pairs found under dataset/',
          'artifacts':str(out.relative_to(ROOT)), 'improved_reference':{'repository':REFERENCE_URL,'commit':PIN,
          'status':'published 2022 candidate, not certified exact dataset commit'},
          'models':{}, 'datasets':{}, 'pcaps':{}, 'lab_csv':{}}
target = HERE/'java_contract_audit_20261118.json'
previous = json.loads(target.read_text(encoding='utf-8')) if '--reuse-dataset-results' in sys.argv and target.exists() else None


def checkpoint():
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


models={}
for name,folder,filename,encoder in [
    ('M0','RQ1_Model_Training_xboost/saved_models','best_xgboost_model.pkl','label_encoder.pkl'),
    ('M1','IDS_M1_Lab/models','m1_xgboost_model.pkl','m1_label_encoder.pkl')]:
    path=ROOT/folder/filename
    model=joblib.load(path); classes=joblib.load(path.with_name(encoder)).classes_
    assert list(model.feature_names_in_) == FEATURES
    assert len(classes)==model.n_classes_
    models[name]=(model,classes)
    report['models'][name]={'path':str(path.relative_to(ROOT)), 'sha256':digest(path),
        'encoder_sha256':digest(path.with_name(encoder)), 'classes':classes.tolist(), 'feature_order_ok':True}
report['models']['M1']['research_artifact_sha256']=digest(ROOT/'RQ4_Retrain_Compare/models/m1_xgboost_model.pkl')
report['models']['M1']['current_matches_research_artifact'] = report['models']['M1']['sha256']==report['models']['M1']['research_artifact_sha256']
if previous:
    assert previous['models']==report['models'], 'Models changed; rerun dataset tests'
    for n,d in previous['datasets'].items():
        assert digest(ROOT/d['train_path'])==d['train_sha256']
        assert digest(ROOT/d['test_path'])==d['test_sha256']
    report['datasets']=previous['datasets']
checkpoint()

# All features are scanned over full training tables, not sampled extrema.
for name,train,test in [
    ('M0_original','dataset/CICID-2018_processed/train_set.parquet','dataset/CICID-2018_processed/test_set.parquet'),
    ('M1_improved_reference','RQ4_Retrain_Compare/data/d2_train.parquet','RQ4_Retrain_Compare/data/d2_test.parquet')]:
    if name in report['datasets']:
        print('DATASET CHECKSUM VERIFIED REUSE', name, flush=True)
        continue
    stats={n:{'min':None,'max':None,'nonfinite':0} for n in FEATURES}
    rows=0; labels={}
    for batch in pq.ParquetFile(ROOT/train).iter_batches(batch_size=65536,columns=FEATURES+['Label']):
        d=batch.to_pandas(); rows+=len(d)
        for lab,c in d.Label.value_counts().items(): labels[lab]=labels.get(lab,0)+int(c)
        for n in FEATURES:
            a=d[n].to_numpy(); ok=np.isfinite(a); stats[n]['nonfinite']+=int((~ok).sum())
            if ok.any():
                lo,hi=float(a[ok].min()),float(a[ok].max())
                stats[n]['min']=lo if stats[n]['min'] is None else min(lo,stats[n]['min'])
                stats[n]['max']=hi if stats[n]['max'] is None else max(hi,stats[n]['max'])
    result={'train_path':train,'train_sha256':digest(ROOT/train),'train_rows':rows,
            'label_counts':labels,'all_78_statistics':stats,'test_path':test,'test_sha256':digest(ROOT/test),'test_models':{}}
    # Score entire stored test partition; this is not proof of independence for rebuilt M1.
    matrices={m:np.zeros((len(c),len(c)),dtype=np.int64) for m,(_,c) in models.items()}
    unknown={m:0 for m in models}; invalid=0; testrows=0
    for batch in pq.ParquetFile(ROOT/test).iter_batches(batch_size=32768,columns=FEATURES+['Label']):
        d=batch.to_pandas();testrows+=len(d)
        ok=np.isfinite(d[FEATURES].to_numpy()).all(axis=1);invalid+=int((~ok).sum());d=d.loc[ok]
        for m,(model,classes) in models.items():
            known=d.Label.isin(classes);unknown[m]+=int((~known).sum());sub=d.loc[known]
            if len(sub):
                pred=classes[model.predict_proba(sub[FEATURES]).argmax(axis=1)]
                matrices[m]+=confusion_matrix(sub.Label,pred,labels=classes)
    result['test_rows']=testrows;result['test_nonfinite_rows']=invalid
    for m,cm in matrices.items():
        classes=models[m][1]; bi=list(classes).index('Benign'); tn=int(cm[bi,bi]);fp=int(cm[bi].sum()-tn)
        result['test_models'][m]={'evaluated_known_labels':int(cm.sum()),'excluded_unknown_labels':unknown[m],
            'accuracy':float(np.trace(cm)/cm.sum()),'benign_fpr':float(fp/(tn+fp)) if tn+fp else None,
            'per_class_recall':{str(c):float(cm[i,i]/cm[i].sum()) if cm[i].sum() else None for i,c in enumerate(classes)},
            'confusion_matrix':cm.tolist()}
    report['datasets'][name]=result;checkpoint();print('DATASET DONE',name,rows,testrows,flush=True)

# Build author's 2022 Java source using local Windows build/dependency wrapper.
ref=HERE/'output/improved_reference'
assert run(['git','-C',ref,'rev-parse',PIN]).strip()==PIN
improved, build_provenance = prepare()
report['improved_reference']['build_provenance'] = build_provenance
# Keep author's jnetpcap library: its TCP segmentation fix is part of the reference.
print('REFERENCE prepared',flush=True)
inputs=out/'pcaps';inputs.mkdir()
sources=[ROOT/'test.pcapng',ROOT/'tesst2.pcapng',HERE/'ssbrute.pcapng',HERE/'ss2.pcapng',
         ROOT/'ddos/HTTP-CPU025-02.pcapng',ROOT/'ddos/restore.pcapng']
for source in sources:
    run([r'C:\Program Files\Wireshark\editcap.exe','-F','pcap',source,inputs/(source.stem+'.pcap')])
run([ROOT/'RQ3_IDS_System/.venv_capture/Scripts/python.exe',HERE/'audit_lab_and_semantics.py','--fixture',inputs/'numeric_fixture.pcap'])
for version,project in [('current',HERE/'upstream'),('improved_2022',improved)]:
    dest=out/version;dest.mkdir()
    log=run([project/'gradlew.bat','exeCMD','-PtrialInput='+str(inputs),'-PtrialOutput='+str(dest),
             '--offline','--no-daemon','--console=plain'],cwd=project,env=java_environment())
    (dest/'java.log').write_text(log,encoding='utf-8')
    print('EXTRACTED',version,flush=True)
    for csv in sorted(dest.glob('*_Flow.csv')):
        raw=pd.read_csv(csv);x=canonical(raw)
        item=predictions(x)
        item['packet_sum']=int((x['Tot Fwd Pkts']+x['Tot Bwd Pkts']).sum())
        item['schema_all_78']=True
        item['feature_ranges']={n:{'min':float(x[n].replace([np.inf,-np.inf],np.nan).min()) if x[n].replace([np.inf,-np.inf],np.nan).notna().any() else None,
                                  'max':float(x[n].replace([np.inf,-np.inf],np.nan).max()) if x[n].replace([np.inf,-np.inf],np.nan).notna().any() else None} for n in FEATURES}
        report['pcaps'].setdefault(csv.name,{})[version]=item
    checkpoint()

for kind,session in [('hulk','ff8f0fa5051b45389a9393023effc083'),('ssh','a10c3bc274594a00be959997bf552236')]:
    path=ROOT/'IDS_M1_Lab/data/capture_sessions'/session/'flows.csv'
    raw=pd.read_csv(path)
    x=pd.DataFrame([row_to_payload(r,list(raw.columns),True) for r in raw.to_dict('records')]).reindex(columns=FEATURES)
    report['lab_csv'][kind]={'source':str(path.relative_to(ROOT)),'sha256':digest(path),
                           'scope':'Python CSV inference, not Java re-extraction',**predictions(x)}
    checkpoint()
report['status']='complete'
checkpoint()
print('COMPLETE',target,flush=True)
