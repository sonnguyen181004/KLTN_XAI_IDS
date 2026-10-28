"""Test M0 và M1 trên các CSV mẫu có nhãn thật của hệ thống RQ3 (RQ3_IDS_System/data/test_samples), 7 đến 8 flow mỗi lớp.

 - test_sample100_15classes_with_label.csv: mẫu của bộ test CSE-CIC-IDS2018 cũ (nguồn của M0).
 - test_sample_with_label.csv: mẫu 13 lớp chung.
Đo: tấn công bị báo thành Benign, Benign bị báo thành tấn công, và đúng lớp trên các lớp chung của hai mô hình.
Với --send, gửi thêm bản không nhãn của cùng file lên API (source csv_upload) để hiện ở tab «Đối chiếu M0 / M1». Kết quả: results/system_test_csv.csv."""
import argparse
import csv
import sys
import uuid

import joblib
import numpy as np
import pandas as pd
import requests

from rq4_common import *

RQ3 = REPO / "RQ3_IDS_System"
SAMPLES = RQ3 / "data" / "test_samples"
sys.path.insert(0, str(RQ3 / "app"))
from feeder import row_to_payload  # noqa: E402
from flow_metadata import row_metadata  # noqa: E402

FILES = [("test_sample100_15classes_with_label.csv", "test_sample100_15classes_no_label.csv", "Mẫu CSE-CIC-2018 cũ, 15 lớp"),
         ("test_sample_with_label.csv", "test_sample_no_label.csv", "Mẫu 13 lớp chung"),
         ]
ap = argparse.ArgumentParser()
ap.add_argument("--send", action="store_true")
ap.add_argument("--api", default="http://127.0.0.1:8000")
a = ap.parse_args()

M = {"M0": (joblib.load(REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl"), joblib.load(REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")),
     "M1": (joblib.load(MODELS / "m1_xgboost_model.pkl"), joblib.load(MODELS / "m1_label_encoder.pkl"))}
common = set(M["M0"][1].classes_) & set(M["M1"][1].classes_)
rows, detail = [], []
for with_label, no_label, title in FILES:
    d = pd.read_csv(SAMPLES / with_label)
    y = d.label_true.to_numpy()
    for k, (model, le) in M.items():
        pred = np.array(le.classes_)[model.predict(d[list(model.feature_names_in_)])]
        att = y != "Benign"
        ben = ~att
        known = np.isin(y, list(common))
        r = dict(file=with_label, tap=title, model=k, n=len(d), n_attack=int(att.sum()), n_benign=int(ben.sum()),
                 attack_flagged_as_benign=int((pred[att] == "Benign").sum()), benign_flagged_as_attack=int((pred[ben] != "Benign").sum()),
                 exact_class_correct_common=int((pred[known] == y[known]).sum()), n_common=int(known.sum()))
        rows.append(r)
        detail.append(pd.DataFrame({"file": with_label, "model": k, "true": y, "pred": pred}))
        print(f"{title:40s} {k}: tấn công bị báo Benign {r['attack_flagged_as_benign']}/{r['n_attack']} | Benign báo tấn công {r['benign_flagged_as_attack']}/{r['n_benign']} | đúng lớp {r['exact_class_correct_common']}/{r['n_common']}", flush=True)
pd.DataFrame(rows).to_csv(RESULTS / "system_test_csv.csv", index=False, encoding="utf-8-sig")
pd.concat(detail).to_csv(RESULTS / "system_test_csv_detail.csv", index=False, encoding="utf-8-sig")

if a.send:
    for _, no_label, title in FILES:
        text = (SAMPLES / no_label).read_text(encoding="utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        run_id, name, ok = str(uuid.uuid4()), "TEST so sánh M0 M1 · " + title, 0
        for row in reader:
            payload = row_to_payload(row, reader.fieldnames, False)
            params = {"source": "csv_upload", **row_metadata(row, run_id, name, None)}
            requests.post(a.api + "/predict", params=params, json=payload, timeout=15).raise_for_status()
            ok += 1
        print("đã gửi", ok, "flow:", name, flush=True)
