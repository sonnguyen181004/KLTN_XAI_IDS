"""1) Phản chứng (đặt FIN = 0) trên flow lab; 2) thử giả thuyết LIME: M0 + nền cũ so với M1 + nền M1, trên flow thật."""
import csv
import json
import sqlite3
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore")
REPO = Path(r"C:\Users\LOQ\Downloads\SELF_KLTN")
sys.path.insert(0, str(REPO / "RQ3_IDS_System" / "app"))
from feeder import row_to_payload  # noqa: E402
from normalize import normalize_flow  # noqa: E402
from predict import Detector  # noqa: E402
from explain_lime import LimeExplainer  # noqa: E402
from explain_shap import ShapExplainer  # noqa: E402

cfg = yaml.safe_load(open(REPO / "RQ3_IDS_System/config.yaml", encoding="utf-8"))
M0 = Detector(REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl",
              REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")
M1 = Detector(REPO / "IDS_M1_Lab/models/m1_xgboost_model.pkl", REPO / "IDS_M1_Lab/models/m1_label_encoder.pkl")
OUT = REPO / "RQ4_Retrain_Compare/results/lab_m1"

# ---- gom flow thật: lab (offline) + feeder_live (Windows, từ cơ sở dữ liệu lab M1, chỉ đọc)
payloads = []
for case in ["A07", "B03", "C01", "D01", "SQL-I01", "WEB-B01"]:
    with open(OUT / f"flows_{case}.csv", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            payloads.append((f"lab_{case}", row_to_payload(r, rd.fieldnames, True)))
con = sqlite3.connect("file:" + str(REPO / "IDS_M1_Lab/data/ids_system.db") + "?mode=ro", uri=True)
for (fj,) in con.execute("select features_json from FlowRecord where source='feeder_live'"):
    payloads.append(("windows_live", {k: float(v) for k, v in json.loads(fj).items() if k in M0.feature_names}))
print("tong flow:", pd.Series([s for s, _ in payloads]).value_counts().to_dict(), flush=True)

X0 = [normalize_flow(p, M0.feature_names, convert_seconds_to_microseconds=False) for _, p in payloads]
X1 = [normalize_flow(p, M1.feature_names, convert_seconds_to_microseconds=False) for _, p in payloads]
src = [s for s, _ in payloads]
pred0 = [M0.predict_flow(x)["predicted_label"] for x in X0]
pred1 = [M1.predict_flow(x)["predicted_label"] for x in X1]
res = pd.DataFrame(dict(source=src, M0=pred0, M1=pred1))
print("\nM0 theo nguon:"); print(pd.crosstab(res.source, res.M0).to_string())
print("\nM1 theo nguon:"); print(pd.crosstab(res.source, res.M1).to_string(), flush=True)

# ---- phản chứng trên các flow M0 gọi Hulk
idx = [i for i, p in enumerate(pred0) if p == "DoS attacks-Hulk"]
cf = {}
for name, edit in [("FIN Flag Cnt=0", {"FIN Flag Cnt": 0.0}), ("Fwd Pkt Len Max=0", {"Fwd Pkt Len Max": 0.0}),
                   ("Fwd Seg Size Min=32", {"Fwd Seg Size Min": 32.0})]:
    still = 0
    for i in idx:
        x = X0[i].copy()
        for k, v in edit.items():
            x[k] = v
        still += int(M0.predict_flow(x)["predicted_label"] == "DoS attacks-Hulk")
    cf[name] = dict(n=len(idx), still_hulk=still, changed=len(idx) - still)
print("\nphan chung M0 tren", len(idx), "flow bi goi Hulk:", json.dumps(cf, ensure_ascii=False), flush=True)

# ---- SHAP: đặc trưng đóng góp lớn nhất cho nhãn Hulk của M0 (trên các flow lab)
sh = ShapExplainer(M0.model, M0.class_names)
acc = {}
for i in idx[:60]:
    for it in sh.explain(X0[i], "DoS attacks-Hulk", top_k=5)["top_k"]:
        acc.setdefault(it["feature"], []).append(it["phi"])
top = sorted(((np.mean(v), len(v), k) for k, v in acc.items()), key=lambda t: -abs(t[0]))[:6]
print("SHAP M0 (Hulk) trung binh phi:", [(k, round(m, 2), n) for m, n, k in top], flush=True)

# ---- LIME: nền cũ + M0 so với nền M1 + M1
def run_lime(det, bg_path, X, preds, tag):
    bg = np.load(bg_path)
    lx = LimeExplainer(det.model, det.feature_names, det.class_names, bg, cfg["lime"], cfg["seed"])
    rows = []
    for k, (x, p) in enumerate(zip(X, preds)):
        r = lx.explain(x, p, k + 1, top_k=5)
        d = r["diagnostics"]
        rows.append(dict(source=src[k], status=r["status"], ess=d["effective_sample_size"], nonzero=d["nonzero_weights"],
                         raw_r2=d["raw_local_r2"], r2=r["local_r2"]))
    df = pd.DataFrame(rows)
    df["pass_r2_0.3"] = (df.status == "ok") & (df.r2 >= 0.3)
    df.to_csv(OUT / f"lime_validity_{tag}.csv", index=False)
    return df


sel = list(range(len(X0)))
a = run_lime(M0, REPO / "RQ3_IDS_System/data/lime_background.npy", X0, pred0, "M0_nen_cu")
print("\nLIME M0 + nen cu: status", a.status.value_counts().to_dict(), "| pass R2>=0.3:", int(a["pass_r2_0.3"].sum()), "/", len(a),
      "| ESS trung vi:", round(float(a.ess.median()), 2), flush=True)
print(a.groupby("source")["pass_r2_0.3"].agg(["sum", "count"]).to_string())
b = run_lime(M1, REPO / "IDS_M1_Lab/data/lime_background.npy", X1, pred1, "M1_nen_M1")
print("\nLIME M1 + nen M1: status", b.status.value_counts().to_dict(), "| pass R2>=0.3:", int(b["pass_r2_0.3"].sum()), "/", len(b),
      "| ESS trung vi:", round(float(b.ess.median()), 2))
print(b.groupby("source")["pass_r2_0.3"].agg(["sum", "count"]).to_string())
