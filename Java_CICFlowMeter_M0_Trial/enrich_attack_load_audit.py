"""Recheck HTTP occurrence counts and explain deterministic representative flows."""
from pathlib import Path
import json,sys,subprocess
import pandas as pd
import joblib
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'RQ4_Retrain_Compare/scripts'))
sys.path.insert(0,str(ROOT/'RQ3_IDS_System/app'))
from rq4_common import FEATURES
from explain_shap import ShapExplainer
p=HERE/'attack_load_audit_20261118.json';d=json.loads(p.read_text(encoding='utf-8'))
for k,v in d['pcaps'].items():
    cmd=[r'C:\Program Files\Wireshark\tshark.exe','-r',str(HERE/v['file']),'-Y','ip.addr==192.168.11.133 && ip.addr==192.168.11.134 && http.request','-T','fields','-e','http.request.method','-E','occurrence=a']
    text=subprocess.check_output(cmd,text=True)
    count=sum(len(line.split(',')) for line in text.splitlines() if line)
    v['http_request_occurrences_verified']=count
    assert count==v['http_requests'],(k,count,v['http_requests'])
for m,folder,mfile,efile in [('M0','RQ1_Model_Training_xboost/saved_models','best_xgboost_model.pkl','label_encoder.pkl'),('M1','IDS_M1_Lab/models','m1_xgboost_model.pkl','m1_label_encoder.pkl')]:
    model=joblib.load(ROOT/folder/mfile);classes=joblib.load(ROOT/folder/efile).classes_.tolist()
    ex=ShapExplainer(model,classes)
    for k in ['oldeneye2','hulk2','slowloris2','LOIC','ss2']:
        x=pd.read_csv(HERE/'output/attack_load_report_20261118'/m/(k+'_features_predictions.csv'))
        x=x.loc[x.lab_target & x.finite]
        samples=[]
        for label in x.prediction.value_counts().index[:3]:
            row=x.loc[x.prediction.eq(label)].iloc[[0]]
            samples.append({'csv_row_zero_based':int(row.index[0]),'label':label,'shap':ex.explain(row[FEATURES],label)})
        d['pcaps'][k]['profiles'][m]['representative_shap']=samples
        print(m,k,flush=True)
p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
