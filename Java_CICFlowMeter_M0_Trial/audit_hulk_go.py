"""Read-only snapshot audit of the user's Hulk-Go live run."""
from pathlib import Path
import sys,json,hashlib,io
import pandas as pd,numpy as np,joblib
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'RQ4_Retrain_Compare/scripts'));from rq4_common import FEATURE_MAP
sys.path.insert(0,str(ROOT/'RQ3_IDS_System/app'));from explain_shap import ShapExplainer
source=HERE/'output/dashboard_577f5569fe20.csv';raw=source.read_bytes();df=pd.read_csv(io.BytesIO(raw));m=joblib.load(ROOT/'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl');enc=joblib.load(ROOT/'RQ1_Model_Training_xboost/saved_models/label_encoder.pkl');x=df[[FEATURE_MAP[n] for n in m.feature_names_in_]].copy();x.columns=m.feature_names_in_;valid=np.isfinite(x).all(axis=1);proba=m.predict_proba(x.loc[valid]);labels=enc.inverse_transform(proba.argmax(axis=1));idx=x.index[valid];pred=pd.Series(labels,index=idx);ex=ShapExplainer(m,list(enc.classes_));examples=[]
for label in ['DDOS attack-HOIC','DoS attacks-GoldenEye','Benign']:
 ids=pred[(pred==label) & (df.loc[pred.index,'Src IP']=='192.168.11.133') & (df.loc[pred.index,'Dst Port']==80)].index
 if not len(ids):continue
 ranked=sorted(ids,key=lambda i:proba[list(idx).index(i),list(enc.classes_).index(label)],reverse=True)
 for i in ranked[:2]:
  probs=dict(zip(enc.classes_,map(float,proba[list(idx).index(i)])))
  examples.append({'csv_row':int(i+1),'src':str(df.loc[i,'Src IP']),'dst':str(df.loc[i,'Dst IP']),'prediction':label,'probabilities_top':dict(sorted(probs.items(),key=lambda t:-t[1])[:4]),'hulk_probability':probs['DoS attacks-Hulk'],'shap':ex.explain(x.loc[[i]],label,8),'hulk_shap':ex.explain(x.loc[[i]],'DoS attacks-Hulk',5)})
out={'source':str(source),'sha256_snapshot':hashlib.sha256(raw).hexdigest(),'snapshot_rows':len(df),'invalid_rows':int((~valid).sum()),'labels':pred.value_counts().to_dict(),'lab_labels':pred[(df.loc[pred.index,'Src IP']=='192.168.11.133') & (df.loc[pred.index,'Dst Port']==80)].value_counts().to_dict(),'target_pairs':df.groupby(['Src IP','Dst IP','Dst Port']).size().to_string(),'capture_finished_in_log':'BUILD SUCCESSFUL' in source.with_suffix('.log').read_text(errors='replace'),'examples':examples,'limits':'Snapshot, not PCAP audit. SHAP explains model scores, not attack ground truth or proof of training cause.'}
(HERE/'hulk_go_audit_20261118.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=True))
