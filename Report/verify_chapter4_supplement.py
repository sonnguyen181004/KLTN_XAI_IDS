"""Independent perturbation recheck and historical-log aggregation."""
from pathlib import Path
import sys,json,time
import numpy as np,pandas as pd,joblib
R=Path(__file__).resolve().parents[1]; O=R/'Report/chapter4_assets'; S=R/'RQ2/runs/20261009'
sys.path.insert(0,str(R/'RQ2/scripts'))
from stage10_faithfulness import deletion_curve,insertion_curve
train=pd.read_parquet(R/'dataset/CICID-2018_processed/train_set.parquet')
test=pd.read_parquet(R/'dataset/CICID-2018_processed/test_set.parquet')
features=[f for f in train if f!='Label']; ids=pd.read_csv(S/'gd3_cohorts/cohort_ids.csv').flow_id.to_numpy()
X=test.iloc[ids][features].reset_index(drop=True)
m=joblib.load(R/'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl'); ix=m.predict_proba(X).argmax(axis=1)
bases={'global_median':train[features].median().to_numpy(),'global_mean':train[features].mean().to_numpy(),'benign_median':train.loc[train.Label=='Benign',features].median().to_numpy()}
ranks={}
for method,folder,prefix in [('SHAP','gd4_shap_per_flow','shap'),('LIME','gd6_lime_per_flow','lime')]:
    d=pd.read_csv(S/folder/(prefix+'_per_flow_topk.csv')); d=d[d.k==10].set_index('flow_id');ranks[method]=[d.loc[f,'top_features'].split(';') for f in ids]
rng=np.random.default_rng(42);ranks['Random']=[rng.permutation(features)[:10].tolist() for _ in ids]
rows=[]
for b,v in bases.items():
    for method,rank in ranks.items():
        deletion,_=deletion_curve(m,X,ix,rank,features,v,list(range(1,11)))
        insertion=insertion_curve(m,X,ix,rank,features,v,list(range(1,11)))
        rows.append({'baseline':b,'method':method,'comprehensiveness_auc':float(np.mean([z.mean() for z in deletion.values()])),'sufficiency_auc':float(np.mean([z.mean() for z in insertion.values()]))})
        print(b,method,'done',flush=True)
df=pd.DataFrame(rows);df.to_csv(O/'faithfulness_rerun.csv',index=False)
saved=pd.read_csv(S/'gd10_faithfulness/rq2_3_faithfulness_auc_summary.csv')
merged=df.merge(saved,on=['baseline','method'],suffixes=('_new','_old'))
errors={c:float((merged[c+'_new']-merged[c+'_old']).abs().max()) for c in ['comprehensiveness_auc','sufficiency_auc']}
st=pd.read_csv(S/'gd9_stability_robustness/rq2_2_stability_lime_per_flow.csv')
live=json.loads((R/'RQ3_IDS_System/docs/live_20min_ht3_retry_20261018.json').read_text(encoding='utf-8'))
samples=live.pop('samples');live['sample_count']=len(samples)
live['peak_sampled_rss_mib']={p:max(s['processes'][p]['rss_bytes'] for s in samples)/2**20 for p in ['api','capture','feeder']}
live['last_sample_cpu_seconds']={p:samples[-1]['processes'][p]['cpu_seconds'] for p in ['api','capture','feeder']}
live['max_sampled_queue']=max(s['queue']['qsize'] for s in samples)
pd.DataFrame([{'elapsed_seconds':s['elapsed_seconds'],'api_flows':s['api_flows'],'queue':s['queue']['qsize'],**{p+'_rss_mib':s['processes'][p]['rss_bytes']/2**20 for p in ['api','capture','feeder']}} for s in samples]).to_csv(O/'live_historical_timeline.csv',index=False)
mask=(train['FIN Flag Cnt']>=1)&(train['Fwd Pkt Len Max']>=66)&(train['Fwd Seg Size Min']<32)
report={'faithfulness_max_saved_difference':errors,'stability_reaggregated_only':{'n_flows':len(st),'mean':float(st.mean_pairwise_jaccard5.mean()),'median':float(st.mean_pairwise_jaccard5.median())},'fin_region_train_counts':train.loc[mask,'Label'].value_counts().to_dict(),'flag_ranges':{f:[float(train[f].min()),float(train[f].max())] for f in features if 'Flag Cnt' in f},'historical_live':live}
(O/'supplement.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Supplement complete',flush=True)
