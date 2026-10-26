"""Huấn luyện XGBoost cho M0b và M1 với đúng siêu tham số đã chọn ở RQ1 (2_train_optimal_model.py):
XGBClassifier(n_estimators=100, max_depth=8, learning_rate=0.08, tree_method='hist', random_state=42, n_jobs=-1).
Không quét lại tham số, để mọi khác biệt giữa các mô hình chỉ đến từ dữ liệu huấn luyện.
LabelEncoder và các chỉ số (Accuracy, Macro P/R/F1, FPR, FNR bằng ids_detection_metrics) như RQ1.

  python 05_train_models.py m0b      train cũ giới hạn 13 lớp
  python 05_train_models.py m1       train lấy từ bản improved
"""
import argparse
import json
import sys
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from rq4_common import *

sys.path.insert(0, str(REPO / "RQ1_Model_Training_xboost"))
from ids_metrics import ids_detection_metrics  # noqa: E402

# Cấu hình RQ1 đã chọn (bang_1_ket_qua_quet_tham_so_thuc_te.csv, 2_train_optimal_model.py). Không đổi.
RQ1_CONFIG = (8, 0.08, "Cấu hình tối ưu đã chọn ở RQ1")

ap = argparse.ArgumentParser()
ap.add_argument("name")
a = ap.parse_args()
out = RESULTS / a.name
out.mkdir(parents=True, exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)


def old13(path):
    d = pd.read_parquet(path)
    return d[d.Label.isin(CLASSES_13)].reset_index(drop=True)


if a.name == "m0b":
    train, test = old13(TRAIN_OLD), old13(TEST_OLD)
elif a.name == "m1":
    train, test = pd.read_parquet(DATA / "d2_train.parquet"), pd.read_parquet(DATA / "d2_test.parquet")
else:
    raise SystemExit("tên mô hình không hợp lệ")

X_train, X_test = train[FEATURES], test[FEATURES]
le = LabelEncoder()
y_train, y_test = le.fit_transform(train.Label), le.transform(test.Label)
benign_idx = list(le.classes_).index("Benign")
print(f"{a.name}: train {len(train):,} | test {len(test):,} | {len(le.classes_)} lớp", flush=True)

configs = [RQ1_CONFIG]


def evaluate(model, X, y):
    p = model.predict(X)
    acc = accuracy_score(y, p) * 100
    pr, rc, f1, _ = precision_recall_fscore_support(y, p, average="macro", zero_division=0)
    cm = confusion_matrix(y, p, labels=np.arange(len(le.classes_)))
    return p, acc, pr * 100, rc * 100, f1 * 100, cm


rows, best = [], None
for i, (depth, lr, desc) in enumerate(configs, 1):
    t0 = time.time()
    m = XGBClassifier(n_estimators=100, max_depth=depth, learning_rate=lr, tree_method="hist", random_state=SEED, n_jobs=-1)
    m.fit(X_train, y_train)
    dur = time.time() - t0
    _, _, _, _, train_f1, _ = evaluate(m, X_train, y_train)
    p, acc, pr, rc, f1, cm = evaluate(m, X_test, y_test)
    det = ids_detection_metrics(cm, benign_idx)
    rows.append({"Cấu hình": f"Depth={depth}, LR={lr}", "Thời gian (s)": round(dur, 2), "Train F1 (%)": round(train_f1, 2), "Test Acc (%)": round(acc, 2),
                 "Test Prec (%) [Sub-1.1]": round(pr, 2), "Test F1 (%) [Sub-1.1]": round(f1, 2), "FPR Benign (%) [Sub-1.2]": round(det["fpr_pct"], 4),
                 "FNR Attack (%)": round(det["fnr_pct"], 4), "FP (Benign thành Attack)": det["fp"], "TN (Benign thành Benign)": det["tn"],
                 "FN (Attack thành Benign)": det["fn"], "TP (Attack thành Attack)": det["tp"], "Ghi chú": desc})
    print(f"  [{i}/{len(configs)}] depth={depth} lr={lr}: {dur:.0f}s | Acc {acc:.2f} | F1 {f1:.2f} | FPR {det['fpr_pct']:.4f}", flush=True)
    if best is None or f1 > best["f1"]:
        best = dict(f1=f1, depth=depth, lr=lr, model=m, p=p, acc=acc, pr=pr, rc=rc, cm=cm, det=det, dur=dur)

pd.DataFrame(rows).to_csv(out / "bang_1_cau_hinh_da_dung.csv", index=False, encoding="utf-8-sig")
b = best
json.dump(dict(max_depth=b["depth"], learning_rate=b["lr"], n_estimators=100, random_state=SEED, source="RQ1, giữ nguyên"),
          open(out / "config_used.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
pd.DataFrame(b["cm"], index=le.classes_, columns=le.classes_).to_csv(out / "confusion_matrix_values.csv", encoding="utf-8-sig")
rep = classification_report(y_test, b["p"], target_names=le.classes_, output_dict=True, zero_division=0)
pd.DataFrame(rep).transpose().to_csv(out / "bang_chi_tiet_lop.csv", encoding="utf-8-sig")
det = b["det"]
summary = pd.DataFrame({"Chỉ số Đánh giá": ["Độ chính xác toàn cục (Accuracy)", "Macro Precision", "Macro Recall", "Macro F1-score",
                                            "Tỷ lệ Cảnh báo sai FPR trên Benign", "Tỷ lệ bỏ sót tấn công FNR (Attack thành Benign)", "Thời gian Huấn luyện"],
                        f"Kết quả {a.name}": [f"{b['acc']:.2f}%", f"{b['pr']:.2f}%", f"{b['rc']:.2f}%", f"{b['f1']:.2f}%",
                                              f"{det['fpr_pct']:.4f}% (FP={det['fp']}, TN={det['tn']})", f"{det['fnr_pct']:.4f}% (FN={det['fn']}, TP={det['tp']})",
                                              f"{b['dur']/60:.2f} phút"]})
summary.to_csv(out / "bang_2_ket_qua_chinh_thuc.csv", index=False, encoding="utf-8-sig")
joblib.dump(b["model"], MODELS / f"{a.name}_xgboost_model.pkl")
joblib.dump(le, MODELS / f"{a.name}_label_encoder.pkl")
print(summary.to_string(index=False))
print("đã lưu mô hình:", MODELS / f"{a.name}_xgboost_model.pkl")
