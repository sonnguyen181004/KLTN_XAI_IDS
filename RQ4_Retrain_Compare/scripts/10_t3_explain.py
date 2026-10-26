"""Trên 784 flow Benign realtime (T3): SHAP của M0 và M1 cho 148 flow nằm trong vùng ba điều kiện, và thử phản thực
đặt FIN Flag Cnt = 0 (cùng thử đặt Fwd Pkt Len Max = 0 hoặc Fwd Seg Size Min = 32) với M0."""
import json
import joblib
import numpy as np
import pandas as pd
import shap
from rq4_common import *

R = hulk_zone_rule()
t3 = pd.read_parquet(DATA / "t3_benign_confirmed.parquet")
X = t3[FEATURES]
zone = (X["FIN Flag Cnt"] >= R["min_fin_flag_cnt"]) & (X["Fwd Pkt Len Max"] >= R["min_fwd_pkt_len_max"]) & (X["Fwd Seg Size Min"] < R["below_fwd_seg_size_min"])
Z = X[zone].reset_index(drop=True)
out = {"t3_flows": len(X), "t3_zone_flows": int(zone.sum())}
for name, mp, ep in [("M0", REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl", REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl"),
                     ("M1", MODELS / "m1_xgboost_model.pkl", MODELS / "m1_label_encoder.pkl")]:
    m, le = joblib.load(mp), joblib.load(ep)
    cls = list(le.classes_)
    pred = np.array(cls)[m.predict(Z)]
    ex = shap.TreeExplainer(m)
    sv = ex.shap_values(Z)
    sv = np.stack(sv, axis=-1) if isinstance(sv, list) else sv      # (n, 78, classes)
    idx = np.array([cls.index(p) for p in pred])
    own = sv[np.arange(len(Z)), :, idx]                              # SHAP của lớp được dự đoán
    s = pd.Series(own.mean(axis=0), index=FEATURES)
    top = s.reindex(s.abs().sort_values(ascending=False).index).head(8)
    out[name] = dict(predicted=pd.Series(pred).value_counts().to_dict(), mean_shap_of_predicted_class_top8={k: round(float(v), 3) for k, v in top.items()})
    print(name, out[name], flush=True)
    if name == "M0":
        base = np.array(cls)[m.predict(X)]
        out["M0_all784_attack_flagged"] = int((base != "Benign").sum())
        for lab, edit in [("FIN=0", {"FIN Flag Cnt": 0}), ("Fwd Pkt Len Max=0", {"Fwd Pkt Len Max": 0}), ("Fwd Seg Size Min=32", {"Fwd Seg Size Min": 32}),
                          ("Init Fwd Win Byts=64240", {"Init Fwd Win Byts": 64240}), ("Dst Port=80", {"Dst Port": 80})]:
            Y = X.copy()
            for k, v in edit.items():
                Y[k] = v
            p = np.array(cls)[m.predict(Y)]
            out.setdefault("M0_counterfactual_all784", {})[lab] = dict(attack_flagged=int((p != "Benign").sum()), changed_labels=int((p != base).sum()))
        print("phản thực M0:", out["M0_counterfactual_all784"], flush=True)
json.dump(out, open(RESULTS / "t3_explain.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
