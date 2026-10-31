"""Quét độ rộng kernel của LIME trên 313 flow thật (290 flow thực, 21 flow duyệt web, 2 flow SSH đã xác nhận nhãn).

Hai cấu hình: M0 với nền gốc, và M1 với nền lấy từ dữ liệu đã sửa. Giữ nguyên 1.000 mẫu nhiễu, 2.000 flow nền và hạt giống RQ2.
Với mỗi độ rộng ghi: số flow có cỡ mẫu hiệu dụng (ESS) dưới 2, số flow qua ngưỡng R2 từ 0,3, ESS trung vị, R2 trung vị.
Kết quả: results/lab_m1/lime_kernel_sweep.csv và lime_kernel_sweep_summary.json."""
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
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "RQ3_IDS_System" / "app"))
from feeder import row_to_payload  # noqa: E402
from normalize import normalize_flow  # noqa: E402
from predict import Detector  # noqa: E402
from explain_lime import LimeExplainer  # noqa: E402

cfg = yaml.safe_load(open(REPO / "RQ3_IDS_System/config.yaml", encoding="utf-8"))
OUT = REPO / "RQ4_Retrain_Compare/results/lab_m1"
M0 = Detector(REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl", REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")
M1 = Detector(REPO / "IDS_M1_Lab/models/m1_xgboost_model.pkl", REPO / "IDS_M1_Lab/models/m1_label_encoder.pkl")
WIDTHS = [3.312, 30, 300, 3000, 30000]
KEEP = ["A07", "B03", "WEB-B01"]

payloads = []
for case in KEEP:
    with open(OUT / f"flows_{case}.csv", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            payloads.append((f"lab_{case}", row_to_payload(r, rd.fieldnames, True)))
con = sqlite3.connect("file:" + str(REPO / "IDS_M1_Lab/data/ids_system.db") + "?mode=ro", uri=True)
for (fj,) in con.execute("select features_json from FlowRecord where source='feeder_live'"):
    payloads.append(("windows_live", {k: float(v) for k, v in json.loads(fj).items() if k in M0.feature_names}))
print("flow:", len(payloads), flush=True)

rows = []
for name, det, bgp in (("M0_nen_goc", M0, REPO / "RQ3_IDS_System/data/lime_background.npy"), ("M1_nen_da_sua", M1, REPO / "IDS_M1_Lab/data/lime_background.npy")):
    bg = np.load(bgp)
    X = [normalize_flow(p, det.feature_names, convert_seconds_to_microseconds=False) for _, p in payloads]
    pred = [det.predict_flow(x)["predicted_label"] for x in X]
    for kw in WIDTHS:
        c = dict(cfg["lime"]); c["kernel_width"] = kw
        lx = LimeExplainer(det.model, det.feature_names, det.class_names, bg, c, cfg["seed"])
        for k, (x, p) in enumerate(zip(X, pred)):
            r = lx.explain(x, p, k + 1, top_k=5)
            d = r["diagnostics"]
            rows.append(dict(model=name, kernel_width=kw, source=payloads[k][0], status=r["status"], ess=d["effective_sample_size"],
                             r2=d["raw_local_r2"], passed=bool(r["status"] == "ok" and r["local_r2"] is not None and r["local_r2"] >= 0.3)))
        print(name, kw, "xong", flush=True)
df = pd.DataFrame(rows)
df.to_csv(OUT / "lime_kernel_sweep.csv", index=False)
summ = {}
for (m, kw), g in df.groupby(["model", "kernel_width"]):
    summ[f"{m}|{kw}"] = dict(n=len(g), ess_below_2=int((g.ess < 2).sum()), passed_r2_0_3=int(g.passed.sum()), ess_median=round(float(g.ess.median()), 1),
                             r2_median=round(float(g.r2.dropna().median()), 3) if g.r2.notna().any() else None)
json.dump(summ, open(OUT / "lime_kernel_sweep_summary.json", "w", encoding="utf-8"), indent=1)
for k, v in summ.items():
    print(k, v)
