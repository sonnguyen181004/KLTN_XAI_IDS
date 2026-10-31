"""Dự đoán M0 và M1 trên flow trích từ 6 PCAP lab bằng đúng bộ trích đặc trưng và chuẩn hóa của hệ thống."""
import csv
import sys
from pathlib import Path

import pandas as pd

REPO = Path(r"C:\Users\LOQ\Downloads\SELF_KLTN")
sys.path.insert(0, str(REPO / "RQ3_IDS_System" / "app"))
from feeder import row_to_payload  # noqa: E402
from normalize import normalize_flow  # noqa: E402
from predict import Detector  # noqa: E402

M0 = Detector(REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl",
              REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")
M1 = Detector(REPO / "IDS_M1_Lab/models/m1_xgboost_model.pkl", REPO / "IDS_M1_Lab/models/m1_label_encoder.pkl")
OUT = REPO / "RQ4_Retrain_Compare/results/lab_m1"
rows = []
for case in ["A07", "B03", "C01", "D01", "SQL-I01", "WEB-B01"]:
    path = OUT / f"flows_{case}.csv"
    with open(path, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        header = rd.fieldnames
        for r in rd:
            payload = row_to_payload(r, header, convert_units=True)
            x0 = normalize_flow(payload, M0.feature_names, convert_seconds_to_microseconds=False)
            x1 = normalize_flow(payload, M1.feature_names, convert_seconds_to_microseconds=False)
            p0, p1 = M0.predict_flow(x0), M1.predict_flow(x1)
            rows.append(dict(
                case=case, src_ip=r.get("src_ip"), dst_ip=r.get("dst_ip"), src_port=r.get("src_port"),
                dst_port=r.get("dst_port"), timestamp=r.get("timestamp"),
                duration_s=float(r.get("flow_duration", 0)), fwd_pkts=r.get("tot_fwd_pkts"), bwd_pkts=r.get("tot_bwd_pkts"),
                fin=r.get("fin_flag_cnt"), fwd_seg_min=r.get("fwd_seg_size_min"), init_fwd_win=r.get("init_fwd_win_byts"),
                M0_label=p0["predicted_label"], M0_conf=round(max(p0["probabilities"].values()), 4),
                M1_label=p1["predicted_label"], M1_conf=round(max(p1["probabilities"].values()), 4),
                end_reason=r.get("flow_end_reason")))
df = pd.DataFrame(rows)
df.to_csv(OUT / "lab_predictions_m0_m1.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_rows", 200)
print("so flow theo ca:", df.groupby("case").size().to_dict())
for m in ("M0_label", "M1_label"):
    print("\n" + m); print(pd.crosstab(df["case"], df[m]).to_string())
print(df[["case", "src_ip", "dst_ip", "dst_port", "duration_s", "fwd_pkts", "bwd_pkts", "fin", "fwd_seg_min", "M0_label", "M0_conf", "M1_label", "M1_conf", "end_reason"]].head(60).to_string())
