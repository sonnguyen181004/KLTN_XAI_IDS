"""Evaluate M0 held-out HOIC/LOIC-HTTP; export deterministic UI samples."""
from pathlib import Path
import json,hashlib
import joblib,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).resolve().parent
source=ROOT/'dataset/CICID-2018_processed/test_set.parquet';modelpath=ROOT/'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl'
m=joblib.load(modelpath);encoder=joblib.load(modelpath.parent/'label_encoder.pkl');df=pd.read_parquet(source)
outdir=HERE/'output/dataset_ddos_test';outdir.mkdir(parents=True,exist_ok=True)
result={'model_sha256':hashlib.sha256(modelpath.read_bytes()).hexdigest(),'source':str(source),'scope':'Held-out dataset rows only; no PCAP extraction, no live attack, no FPR estimate','classes':{}}
for label,filename in [('DDOS attack-HOIC','hoic_test_100.csv'),('DDoS attacks-LOIC-HTTP','loic_http_test_100.csv')]:
 rows=df.loc[df.Label==label].copy();x=rows[list(m.feature_names_in_)];finite=np.isfinite(x).all(axis=1);pred=encoder.inverse_transform(m.predict(x.loc[finite]).astype(int));counts=pd.Series(pred).value_counts();sample=rows.sample(n=min(100,len(rows)),random_state=42);sample.to_csv(outdir/filename,index=False)
 sample_pred=encoder.inverse_transform(m.predict(sample[list(m.feature_names_in_)]).astype(int));detail=sample.copy();detail['Predicted']=sample_pred;detail.to_csv(outdir/filename.replace('.csv','_with_predictions.csv'),index=False)
 result['classes'][label]={'rows':len(rows),'invalid_rows':int((~finite).sum()),'correct_class':int((pred==label).sum()),'wrong_class':int((pred!=label).sum()),'class_recall':float((pred==label).mean()),'predictions':counts.to_dict(),'sample_path':str(outdir/filename),'sample_predictions':pd.Series(sample_pred).value_counts().to_dict()}
(HERE/'dataset_ddos_test_20261118.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
