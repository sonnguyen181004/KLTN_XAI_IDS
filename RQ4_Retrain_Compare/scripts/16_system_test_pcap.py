"""Test M0 và M1 trên các PCAP kịch bản của người dùng (ids-lab) bằng đúng đường của hệ thống RQ3:
PCAP -> CICFlowMeter (scripts/run_live_capture.py --pcap-input) -> 78 đặc trưng -> POST /predict (source pcap_replay) -> bảng so sánh.

Các PCAP này chưa có nhãn từng flow. Nhãn kịch bản (ví dụ hydra, SQL injection) chỉ là ngữ cảnh, không phải nhãn từng flow,
nên kết quả chỉ cho thấy hai mô hình báo gì, không tính đúng sai. Kết quả: results/system_test_pcap.csv."""
import argparse
import csv
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests

from rq4_common import *

RQ3 = REPO / "RQ3_IDS_System"
sys.path.insert(0, str(RQ3 / "app"))
from feeder import row_to_payload  # noqa: E402
from flow_metadata import row_metadata  # noqa: E402

PCAPS = {"A07": "ids-lab/A07/A07_traffic.pcapng", "B03": "ids-lab/B03/B03_traffic.pcapng", "C01": "ids-lab/C01/traffic.pcapng",
         "D01": "ids-lab/D01/D01_traffic.pcapng", "SQL-I01": "ids-lab/SQL-I01/SQL-I01-traffic.pcapng", "WEB-B01": "ids-lab/WEB-B01/WEB-B01_traffic.pcapng"}
ap = argparse.ArgumentParser()
ap.add_argument("--send", action="store_true")
ap.add_argument("--api", default="http://127.0.0.1:8000")
a = ap.parse_args()
py = RQ3 / ".venv_capture/Scripts/python.exe"
offset = datetime.now().astimezone().strftime("%z")
tz = offset[:3] + ":" + offset[3:]
M = {"M0": (joblib.load(REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl"), joblib.load(REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")),
     "M1": (joblib.load(MODELS / "m1_xgboost_model.pkl"), joblib.load(MODELS / "m1_label_encoder.pkl"))}
rows = []
for name, rel in PCAPS.items():
    with tempfile.TemporaryDirectory(prefix="ids_pcap_") as folder:
        out = Path(folder) / "flows.csv"
        proc = subprocess.run([str(py), str(RQ3 / "scripts/run_live_capture.py"), "--pcap-input", str(REPO / rel), "--output", str(out)],
                              cwd=RQ3, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if proc.returncode or not out.exists():
            print(name, "không trích được:", (proc.stdout + proc.stderr)[-300:], flush=True)
            continue
        text = out.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    recs = list(reader)
    payloads = [row_to_payload(r, reader.fieldnames, True) for r in recs]
    df = pd.DataFrame(payloads)
    res = {"pcap": name, "flows": len(df)}
    for k, (model, le) in M.items():
        pred = np.array(le.classes_)[model.predict(df[list(model.feature_names_in_)])]
        res[k + "_attack"] = int((pred != "Benign").sum())
        res[k + "_labels"] = "; ".join(f"{c} {n}" for c, n in pd.Series(pred).value_counts().items())
    rows.append(res)
    print(name, res, flush=True)
    if a.send:
        run_id, run_name = str(uuid.uuid4()), "TEST PCAP " + name
        for r, p in zip(recs, payloads):
            params = {"source": "pcap_replay", **row_metadata(r, run_id, run_name, tz)}
            requests.post(a.api + "/predict", params=params, json=p, timeout=15).raise_for_status()
        print("  đã gửi", len(recs), "flow:", run_name, flush=True)
pd.DataFrame(rows).to_csv(RESULTS / "system_test_pcap.csv", index=False, encoding="utf-8-sig")
print("xong")
