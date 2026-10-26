"""Vì sao M1 đạt gần 100 % trên dữ liệu improved? Kiểm tra ba hướng, chỉ đọc dữ liệu đã dựng.
 1. Trùng lặp: đánh giá lại trên phần test không có dòng giống hệt (78 đặc trưng) trong train.
 2. Dựa vào đặc trưng nào: tổng gain của XGBoost, so với M0.
 3. Bỏ đặc trưng gắn với môi trường lab (cổng đích, giao thức, cửa sổ nhận ban đầu, Fwd Seg Size Min):
    huấn luyện lại cùng siêu tham số rồi đo trên test và trên bộ giữ riêng theo thời gian."""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from rq4_common import *

ENV = ["Dst Port", "Protocol", "Init Fwd Win Byts", "Init Bwd Win Byts", "Fwd Seg Size Min"]
tr, te = pd.read_parquet(DATA / "d2_train.parquet"), pd.read_parquet(DATA / "d2_test.parquet")
ho = pd.read_parquet(DATA / "t2_time_holdout.parquet")
m1, le1 = joblib.load(MODELS / "m1_xgboost_model.pkl"), joblib.load(MODELS / "m1_label_encoder.pkl")
out = {}

# 1. trùng lặp
h_tr = set(pd.util.hash_pandas_object(tr[FEATURES], index=False).tolist())
for name, df in [("test_stratified", te), ("holdout_thoi_gian", ho)]:
    dup = pd.util.hash_pandas_object(df[FEATURES], index=False).isin(h_tr).to_numpy()
    nd = df[~dup]
    pred = np.array(le1.classes_)[m1.predict(nd[FEATURES])]
    out[f"M1_{name}_khong_trung"] = dict(rows=int(len(nd)), removed=int(dup.sum()), accuracy=float((pred == nd.Label).mean() * 100),
        macro_f1=float(f1_score(nd.Label, pred, average="macro", zero_division=0) * 100),
        by_class_recall={c: float((pred[nd.Label.to_numpy() == c] == c).mean() * 100) for c in sorted(nd.Label.unique())})
    print(name, "bỏ", int(dup.sum()), "dòng trùng ->", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[f"M1_{name}_khong_trung"].items() if k != "by_class_recall"})

# 2. tầm quan trọng
def top(model, n=10):
    g = model.get_booster().get_score(importance_type="total_gain")
    s = pd.Series(g).sort_values(ascending=False)
    return (s / s.sum() * 100).round(2).head(n).to_dict()
out["importance_M1"] = top(m1)
out["importance_M0"] = top(joblib.load(REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl"))
print("Top gain M1:", out["importance_M1"]); print("Top gain M0:", out["importance_M0"])

# 3. bỏ đặc trưng môi trường
feats = [f for f in FEATURES if f not in ENV]
le = LabelEncoder(); y = le.fit_transform(tr.Label)
m = XGBClassifier(n_estimators=100, max_depth=8, learning_rate=0.08, tree_method="hist", random_state=SEED, n_jobs=-1).fit(tr[feats], y)
for name, df in [("test_stratified", te), ("holdout_thoi_gian", ho)]:
    pred = np.array(le.classes_)[m.predict(df[feats])]
    b = df.Label.to_numpy() == "Benign"
    out[f"M1_bo_dac_trung_moi_truong_{name}"] = dict(accuracy=float((pred == df.Label).mean() * 100),
        macro_f1=float(f1_score(df.Label, pred, average="macro", zero_division=0) * 100), fpr=float((pred[b] != "Benign").mean() * 100),
        hulk_recall=float((pred[df.Label.to_numpy() == "DoS attacks-Hulk"] == "DoS attacks-Hulk").mean() * 100))
    print("bỏ đặc trưng môi trường", ENV, name, {k: round(v, 3) for k, v in out[f"M1_bo_dac_trung_moi_truong_{name}"].items()})
out["env_features_removed"] = ENV
json.dump(out, open(RESULTS / "diagnose_m1.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
