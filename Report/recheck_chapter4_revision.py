"""Recheck missing RQ2 evaluations in an isolated report run, preserving originals."""
from pathlib import Path
import sys,shutil,json
import pandas as pd
R=Path(__file__).resolve().parents[1]; S=R/'RQ2/runs/20261009'; O=R/'Report/chapter4_assets/revision_rq2'
O.mkdir(exist_ok=True)
for folder in ['gd3_cohorts','gd4_shap_per_flow','gd6_lime_per_flow']:
    dest=O/folder;dest.mkdir(exist_ok=True)
    for path in (S/folder).glob('*.csv'):shutil.copy2(path,dest/path.name)
sys.path.insert(0,str(R/'RQ2/scripts'))
import stage09_stability_robustness as stage
stage.latest_run_dir=lambda:O
stage.main()
checks={}
for name in ['rq2_2_stability_lime_per_flow.csv','rq2_2_noise_robustness.csv','rq2_2_lime_convergence.csv']:
    old=pd.read_csv(S/'gd9_stability_robustness'/name);new=pd.read_csv(O/'gd9_stability_robustness'/name)
    cols=[c for c in old.select_dtypes('number') if 'time' not in c]
    checks[name]={'rows':len(new),'max_difference':float((new[cols]-old[cols]).abs().max().max())}
agreement=pd.read_csv(S/'gd7_agreement/rq2_1_agreement_per_flow.csv')
checks['agreement_reaggregated']=agreement.groupby('k').mean(numeric_only=True).reset_index().to_dict('records')
dom=pd.read_csv(S/'gd11_domain_validation/rq2_4_domain_precision_detail.csv')
checks['domain_reaggregated']=dom.groupby(['scope','method'])[['precision_at_5','recall','f1']].mean().reset_index().to_dict('records')
tune=pd.read_csv(R/'RQ1_Model_Training_xboost/results/bang_1_ket_qua_quet_tham_so_thuc_te.csv')
checks['xgb_tuning_saved_max']=tune.loc[tune['Test F1 (%) [Sub-1.1]'].idxmax()].to_dict()
(O/'recheck.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print('Revision recheck complete',flush=True)
