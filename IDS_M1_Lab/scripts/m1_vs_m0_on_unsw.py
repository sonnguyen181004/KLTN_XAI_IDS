"""Thử M0 và M1 trên CIC-UNSW-NB15 (cùng bộ 78 đặc trưng CICFlowMeter, khác nhãn và khác môi trường).
Chỉ đánh giá nhị phân: báo động (nhãn khác Benign) hay không, vì 2 bộ nhãn khác nhau."""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'IDS_M1_Lab' / 'app'))
from predict import Detector
M0 = Detector(REPO / 'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl', REPO / 'RQ1_Model_Training_xboost/saved_models/label_encoder.pkl')
M1 = Detector(REPO / 'IDS_M1_Lab/models/m1_xgboost_model.pkl', REPO / 'IDS_M1_Lab/models/m1_label_encoder.pkl')
assert M0.feature_names == M1.feature_names
names = M1.feature_names
SRC = REPO / 'dataset/CIC-UNSW-NB15/CIC-UNSW-NB15/CICFlowMeter_out.csv'
head = pd.read_csv(SRC, nrows=1)
unsw = [c for c in head.columns if c not in ['Flow ID', 'Src IP', 'Src Port', 'Dst IP', 'Timestamp', 'Label']]
assert len(unsw) == len(names) == 78
rename = dict(zip(unsw, names))            # cùng thứ tự CICFlowMeter, chỉ khác tên cột
CAP, BEN_FRAC, rng = 4000, 0.02, np.random.default_rng(42)
parts = []
for ch in pd.read_csv(SRC, chunksize=300_000, low_memory=False):
    for lab, g in ch.groupby('Label'):
        frac = BEN_FRAC if lab == 'Benign' else 1.0
        parts.append(g.sample(frac=frac, random_state=int(rng.integers(1e9))) if frac < 1 else g)
df = pd.concat(parts)
cnt = df.Label.value_counts()
keep = []
for lab, g in df.groupby('Label'):
    keep.append(g if lab == 'Benign' or len(g) <= CAP else g.sample(CAP, random_state=42))
df = pd.concat(keep).reset_index(drop=True)
X = df[unsw].rename(columns=rename)[names].apply(pd.to_numeric, errors='coerce').replace([np.inf, -np.inf], 3e38)
print('Mẫu dùng:', df.Label.value_counts().to_dict())
for name, det in [('M0', M0), ('M1', M1)]:
    pr = det.model.predict_proba(X); lab = np.array(det.class_names)[pr.argmax(1)]
    df['pred_' + name] = lab
print('\nTỉ lệ báo động (nhãn dự đoán ≠ Benign), theo nhãn thật của UNSW:')
rows = []
for lab, g in df.groupby('Label'):
    rows.append(dict(label=lab, n=len(g), M0_alert=round((g.pred_M0 != 'Benign').mean() * 100, 1), M1_alert=round((g.pred_M1 != 'Benign').mean() * 100, 1)))
print(pd.DataFrame(rows).to_string(index=False))
print('\nNhãn M1 hay gán cho flow tấn công:'); a = df[df.Label != 'Benign']; print(a.pred_M1.value_counts().head(6).to_dict())
print('Nhãn M0 hay gán cho flow tấn công:'); print(a.pred_M0.value_counts().head(6).to_dict())
print('Nhãn M1 hay gán cho Benign báo nhầm:'); b = df[(df.Label == 'Benign') & (df.pred_M1 != 'Benign')]; print(b.pred_M1.value_counts().head(5).to_dict())
print('Nhãn M0 hay gán cho Benign báo nhầm:'); b = df[(df.Label == 'Benign') & (df.pred_M0 != 'Benign')]; print(b.pred_M0.value_counts().head(5).to_dict())
out = REPO / 'IDS_M1_Lab/data/unsw_eval_sample.csv'
df[['Label', 'pred_M0', 'pred_M1']].assign(**{'Dst Port': X['Dst Port'], 'Protocol': X['Protocol'], 'Fwd Seg Size Min': X['Fwd Seg Size Min']}).to_csv(out, index=False)
print('\nĐã ghi', out)
