"""Đánh giá chéo: mỗi mô hình trên mỗi bộ test, cùng một bộ chỉ số.

Mô hình : M0 (RQ1 gốc, 15 lớp), M0b (train cũ 13 lớp), M1 (train improved), M2_N (train cũ cộng N Benign vùng Hulk).
Bộ test : T1 test cũ, T2a test stratified của improved, T2b giữ riêng theo thời gian, T3 realtime (chỉ Benign đã xác nhận).
Chỉ số  : Macro F1 trên 13 lớp chung, FPR nhị phân (Benign bị báo thành bất kỳ lớp tấn công), recall Hulk,
          tỷ lệ Benign bị báo Hulk, và FPR tách theo Benign trong vùng ba điều kiện hay ngoài vùng.
"""
import json
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from rq4_common import *

warnings.filterwarnings("ignore")
R = hulk_zone_rule()
HULK = "DoS attacks-Hulk"

MODELS_DEF = {"M0": (REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl", REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")}
for p in sorted(MODELS.glob("*_xgboost_model.pkl")):
    n = p.name.replace("_xgboost_model.pkl", "")
    MODELS_DEF[n.upper() if n != "m0b" else "M0b"] = (p, MODELS / f"{n}_label_encoder.pkl")


def in_zone(df):
    return (df["FIN Flag Cnt"] >= R["min_fin_flag_cnt"]) & (df["Fwd Pkt Len Max"] >= R["min_fwd_pkt_len_max"]) & (df["Fwd Seg Size Min"] < R["below_fwd_seg_size_min"])


def drop_dups(df, train_df):
    """Bỏ các dòng có 78 đặc trưng giống hệt một dòng trong train (bản test sạch)."""
    h = set(pd.util.hash_pandas_object(train_df[FEATURES], index=False).tolist())
    dup = pd.util.hash_pandas_object(df[FEATURES], index=False).isin(h).to_numpy()
    return df[~dup].reset_index(drop=True), int(dup.sum())


def load_tests():
    t = {}
    old = pd.read_parquet(TEST_OLD)
    old_tr = pd.read_parquet(TRAIN_OLD, columns=FEATURES)
    t["T1_test_cu"] = old[old.Label.isin(CLASSES_13)].reset_index(drop=True)
    t["T1_test_cu_sach"], n1 = drop_dups(t["T1_test_cu"], old_tr)       # bỏ dòng trùng với train cũ
    d2_tr = pd.read_parquet(DATA / "d2_train.parquet", columns=FEATURES)
    t["T2a_improved_stratified"] = pd.read_parquet(DATA / "d2_test.parquet")
    t["T2a_improved_stratified_sach"], n2 = drop_dups(t["T2a_improved_stratified"], d2_tr)
    t["T2b_improved_thoi_gian"] = pd.read_parquet(DATA / "t2_time_holdout.parquet").drop(columns=["Day"])
    t["T2b_improved_thoi_gian_sach"], n3 = drop_dups(t["T2b_improved_thoi_gian"], d2_tr)
    print("dòng trùng đã bỏ khi làm bản sạch: T1", n1, "| T2a", n2, "| T2b", n3, flush=True)
    p3 = DATA / "t3_benign_confirmed.parquet"
    if p3.exists():
        t["T3_realtime_benign"] = pd.read_parquet(p3)
    return t


tests = load_tests()
rows = []
for mname, (mp, ep) in MODELS_DEF.items():
    model, le = joblib.load(mp), joblib.load(ep)
    classes = list(le.classes_)
    for tname, df in tests.items():
        X = df[FEATURES]
        pred = np.array(classes)[model.predict(X)]
        y = df.Label.to_numpy()
        is_b = y == "Benign"
        zone = in_zone(df).to_numpy()
        r = dict(model=mname, test=tname, n=len(df), n_benign=int(is_b.sum()))
        r["fpr_pct"] = 100 * float((pred[is_b] != "Benign").mean()) if is_b.any() else np.nan
        r["benign_called_hulk_pct"] = 100 * float((pred[is_b] == HULK).mean()) if is_b.any() else np.nan
        r["benign_zone_n"] = int((is_b & zone).sum())
        r["fpr_zone_pct"] = 100 * float((pred[is_b & zone] != "Benign").mean()) if (is_b & zone).any() else np.nan
        r["fpr_outside_zone_pct"] = 100 * float((pred[is_b & ~zone] != "Benign").mean()) if (is_b & ~zone).any() else np.nan
        hk = y == HULK
        r["hulk_n"] = int(hk.sum())
        r["hulk_recall_pct"] = 100 * float((pred[hk] == HULK).mean()) if hk.any() else np.nan
        att = ~is_b & np.isin(y, CLASSES_13)
        r["fnr_pct"] = 100 * float((pred[att] == "Benign").mean()) if att.any() else np.nan
        if len(set(y)) > 1:
            r["macro_f1_13_pct"] = 100 * f1_score(y, pred, labels=[c for c in CLASSES_13 if c in set(y)], average="macro", zero_division=0)
            r["accuracy_pct"] = 100 * float((pred == y).mean())
        rows.append(r)
        print(mname, tname, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ("model", "test")}, flush=True)
out = pd.DataFrame(rows)
out.to_csv(RESULTS / "cross_evaluation.csv", index=False, encoding="utf-8-sig")
print(out.round(3).to_string(index=False))
