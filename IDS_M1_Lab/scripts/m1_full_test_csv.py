"""Thử CSV đầy đủ: gửi toàn bộ Tập B (236 dòng, có nhãn thật) vào /predict, đối chiếu nhãn."""
import sys, collections, joblib, pandas as pd, requests
sys.stdout.reconfigure(encoding='utf-8')
API = 'http://127.0.0.1:8000'
names = list(joblib.load('models/m1_xgboost_model.pkl').feature_names_in_)
df = pd.read_csv('data/clean_holdout_set.csv')
ok = 0; conf = collections.Counter(); err = 0
for _, r in df.iterrows():
    resp = requests.post(API + '/predict', json={k: float(r[k]) for k in names},
                         params={'source': 'csv_upload', 'run_name': 'full_csv_B236'})
    if resp.status_code != 200: err += 1; continue
    p = resp.json().get('predicted_label'); t = r['label_true']
    ok += p == t
    if p != t: conf[(t, p)] += 1
print(f'{len(df)} flow, lỗi gửi {err}, đúng {ok} ({ok/len(df):.1%})')
for (t, p), n in conf.most_common(): print(f'  {t} -> {p}: {n}')
