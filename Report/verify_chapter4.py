"""Read-only empirical recheck for Chapter 4; outputs only under Report."""
from pathlib import Path
import json, time, sys, hashlib, platform
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import confusion_matrix, classification_report

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Report/chapter4_assets'
OUT.mkdir(exist_ok=True)
RUN=ROOT/'RQ2/runs/20261009'
report={'checked_at':time.strftime('%Y-%m-%d %H:%M:%S'), 'python':sys.version, 'platform':platform.platform(), 'scope':'RQ1-RQ3, no training, no live capture, no production database changes'}
def save():
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
def log(s): print(s,flush=True)

log('Loading original train/test and fixed model')
train=pd.read_parquet(ROOT/'dataset/CICID-2018_processed/train_set.parquet')
test=pd.read_parquet(ROOT/'dataset/CICID-2018_processed/test_set.parquet').reset_index(drop=True)
features=[c for c in train if c!='Label']
modelpath=ROOT/'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl'
model=joblib.load(modelpath)
encoder=joblib.load(modelpath.with_name('label_encoder.pkl'))
classes=list(encoder.classes_)
counts=pd.concat([train.Label.value_counts().rename('train'),test.Label.value_counts().rename('test')],axis=1).fillna(0).astype(int)
counts.to_csv(OUT/'class_counts.csv')
nonfinite={}
for name,df in [('train',train),('test',test)]:
    nonfinite[name]=sum(int((~np.isfinite(df.iloc[i:i+100000][features].to_numpy())).sum()) for i in range(0,len(df),100000))
hashtrain=pd.util.hash_pandas_object(train[features],index=False)
hashtest=pd.util.hash_pandas_object(test[features],index=False)
duplicates=int(hashtest.isin(hashtrain).sum())
report['data']={'train_rows':len(train),'test_rows':len(test),'features':len(features),'classes':len(classes),'nonfinite_values':nonfinite,'test_features_in_train':duplicates,'overlap_fraction':duplicates/len(test),'model_sha256':hashlib.sha256(modelpath.read_bytes()).hexdigest()}
log('Full test inference: 700000 rows')
t=time.perf_counter()
pred=np.concatenate([model.predict(test.iloc[i:i+10000][features]) for i in range(0,len(test),10000)])
predlabels=encoder.inverse_transform(pred.astype(int))
cm=confusion_matrix(test.Label,predlabels,labels=classes)
old=pd.read_csv(ROOT/'RQ1_Model_Training_xboost/results/confusion_matrix_values.csv',index_col=0).loc[classes,classes].to_numpy()
metrics=classification_report(test.Label,predlabels,labels=classes,output_dict=True,zero_division=0)
bi=classes.index('Benign'); tn=int(cm[bi,bi]); fp=int(cm[bi].sum()-tn); fn=int(cm[:,bi].sum()-tn); tp=int(cm.sum()-tn-fp-fn)
report['rq1']={'inference_seconds':time.perf_counter()-t,'confusion_equal_saved':bool(np.array_equal(cm,old)),'different_cells':int((cm!=old).sum()),'accuracy':metrics['accuracy'],'macro':metrics['macro avg'],'TN':tn,'FP':fp,'FN':fn,'TP':tp,'FPR':fp/(fp+tn),'FNR':fn/(fn+tp),'metrics':metrics,'boosting_rounds':model.get_booster().num_boosted_rounds(),'total_trees':len(model.get_booster().get_dump())}
pd.DataFrame(cm,index=classes,columns=classes).to_csv(OUT/'confusion_matrix.csv')
pd.DataFrame(metrics).T.to_csv(OUT/'classification_report.csv')
save();log('RQ1 complete, exact matrix match='+str(report['rq1']['confusion_equal_saved']))

import shap, xgboost
from lime.lime_tabular import LimeTabularExplainer
sys.path.insert(0,str(ROOT/'RQ2/scripts'))
from lib.common import set_lime_explainer_seed
cohort=pd.read_csv(RUN/'gd3_cohorts/cohort_ids.csv')
ids=cohort.flow_id.astype(int).to_numpy()
cx=test.iloc[ids][features]
proba=model.predict_proba(cx); idx=proba.argmax(axis=1)
explainer=shap.TreeExplainer(model)
t=time.perf_counter(); exp=explainer(cx,check_additivity=False); shap_seconds=time.perf_counter()-t
phi=exp.values[np.arange(len(ids)),:,idx]
base=exp.base_values[np.arange(len(ids)),idx]
margin=model.get_booster().predict(xgboost.DMatrix(cx),output_margin=True)[np.arange(len(ids)),idx]
savedshap=pd.read_csv(RUN/'gd4_shap_per_flow/shap_per_flow_long.csv').pivot(index='flow_id',columns='feature',values='shap_value').loc[ids,features].to_numpy()
report['rq2']={'cohort_rows':len(ids),'cohort_all_correct':bool(np.all(predlabels[ids]==test.iloc[ids].Label.to_numpy())),'shap_full_rerun_seconds':shap_seconds,'shap_max_saved_difference':float(np.abs(phi-savedshap).max()),'shap_max_additivity_error':float(np.abs(base+phi.sum(axis=1)-margin).max())}
save();log('SHAP all cohort complete')
bg=train[features].sample(n=2000,random_state=42).to_numpy()
lime=LimeTabularExplainer(bg,feature_names=features,class_names=classes,discretize_continuous=False,kernel_width=3.312,random_state=42)
savedlime=pd.read_csv(RUN/'gd6_lime_per_flow/lime_per_flow_long.csv').pivot(index='flow_id',columns='feature_desc',values='lime_weight')
top=pd.read_csv(RUN/'gd6_lime_per_flow/lime_per_flow_topk.csv').drop_duplicates('flow_id').set_index('flow_id')
def predict(a): return model.predict_proba(pd.DataFrame(a,columns=features))
rows=[]; t=time.perf_counter()
for n,(fid,row) in enumerate(cx.iterrows()):
    fid=int(fid); pi=int(idx[n]); set_lime_explainer_seed(lime,(42*1000003+fid)%(2**31-1))
    e=lime.explain_instance(row.to_numpy(),predict,num_features=78,num_samples=1000,labels=[pi])
    w=dict(e.as_list(label=pi)); r2=float(e.score[pi] if isinstance(e.score,dict) else e.score)
    diff=max(abs(w[f]-savedlime.loc[fid,f]) for f in features)
    st=set(np.array(features)[np.argsort(-np.abs(phi[n]))[:5]])
    lt=set(sorted(w,key=lambda f:abs(w[f]),reverse=True)[:5])
    rows.append({'flow_id':fid,'pred_class':classes[pi],'local_r2':r2,'weight_max_difference':diff,'r2_difference':abs(r2-float(top.loc[fid,'local_r2'])),'jaccard5':len(st&lt)/len(st|lt)})
    if (n+1)%200==0: log(f'LIME rechecked {n+1}/{len(ids)}')
lr=pd.DataFrame(rows);lr.to_csv(OUT/'lime_rerun.csv',index=False)
report['rq2'].update({'lime_full_rerun_seconds':time.perf_counter()-t,'lime_max_weight_difference':float(lr.weight_max_difference.max()),'lime_max_r2_difference':float(lr.r2_difference.max()),'lime_median_r2':float(lr.local_r2.median()),'lime_mean_r2':float(lr.local_r2.mean()),'lime_pass_count':int((lr.local_r2>=.3).sum()),'lime_pass_fraction':float((lr.local_r2>=.3).mean()),'jaccard5_rerun_mean':float(lr.jaccard5.mean())})
agreement=pd.read_csv(RUN/'gd7_agreement/rq2_1_agreement_per_flow.csv')
report['rq2']['agreement_reaggregated']=agreement.groupby('k').jaccard.mean().to_dict()
save();log('Complete: '+str(OUT/'verification.json'))
