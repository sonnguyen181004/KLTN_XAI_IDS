"""Bước 2 (tiếp): so quy ước 12 cột cờ TCP giữa train M0 và flow Java lab, và ngưỡng tách của M0 trên các cột đó.

Ghi results/extraction_audit/flag_convention.json. Chỉ đọc.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SRC = ROOT / "Java_CICFlowMeter_M0_Trial/output/attack_load_report_20261118/M0"
FLAGS = ["Fwd PSH Flags", "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags", "FIN Flag Cnt", "SYN Flag Cnt", "RST Flag Cnt",
         "PSH Flag Cnt", "ACK Flag Cnt", "URG Flag Cnt", "CWE Flag Count", "ECE Flag Cnt"]

tr = pd.read_parquet(ROOT / "dataset/CICID-2018_processed/train_set.parquet", columns=FLAGS)
man = pd.read_csv(HERE / "manifests/pcaps.csv")
lab = []
for p in man.pcap:
    k = p.split("/")[-1].replace(".pcapng", "").strip()
    d = pd.read_csv(SRC / f"{k}_features_predictions.csv")
    lab.append(d[d.lab_target])
lab = pd.concat(lab)

m = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl")
t = m.get_booster().trees_to_dataframe()
t = t[t.Feature != "Leaf"]

out = {"train_rows": len(tr), "lab_rows": len(lab), "columns": {}}
for f in FLAGS:
    out["columns"][f] = dict(
        train_values=sorted(map(float, tr[f].unique())), lab_values_top={str(k): int(v) for k, v in lab[f].value_counts().head(8).items()},
        lab_rows_above_1=int((lab[f] > 1).sum()), m0_splits=int((t.Feature == f).sum()), m0_thresholds=sorted(map(float, t.loc[t.Feature == f, "Split"].unique())))
out["train_identities"] = {
    "Fwd PSH Flags == SYN Flag Cnt": bool((tr["Fwd PSH Flags"] == tr["SYN Flag Cnt"]).all()),
    "RST Flag Cnt == ECE Flag Cnt (share)": float((tr["RST Flag Cnt"] == tr["ECE Flag Cnt"]).mean()),
    "Fwd URG Flags == CWE Flag Count": bool((tr["Fwd URG Flags"] == tr["CWE Flag Count"]).all()),
}
out["lab_identities"] = {
    "Fwd PSH Flags == SYN Flag Cnt (share)": float((lab["Fwd PSH Flags"] == lab["SYN Flag Cnt"]).mean()),
    "RST Flag Cnt == ECE Flag Cnt (share)": float((lab["RST Flag Cnt"] == lab["ECE Flag Cnt"]).mean()),
}
# M0 chỉ tách các cột cờ tại ngưỡng 1, nên đổi số đếm >= 1 thành 1 không đổi dự đoán của M0. Kiểm tra trực tiếp:
x = lab[list(m.feature_names_in_)].replace([np.inf, -np.inf], np.nan).dropna()
xb = x.copy()
xb[FLAGS] = xb[FLAGS].clip(upper=1)
out["m0_prediction_change_if_flags_clipped_to_1"] = int((m.predict(x) != m.predict(xb)).sum())
out["m0_max_abs_proba_change"] = float(np.abs(m.predict_proba(x) - m.predict_proba(xb)).max())
json.dump(out, open(HERE / "results/extraction_audit/flag_convention.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for f, v in out["columns"].items():
    print(f, v["train_values"], v["lab_rows_above_1"], v["m0_thresholds"])
print(out["train_identities"], out["lab_identities"], out["m0_prediction_change_if_flags_clipped_to_1"], out["m0_max_abs_proba_change"])
