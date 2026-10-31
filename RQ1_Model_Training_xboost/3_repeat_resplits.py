"""Lặp lại RQ1: gộp train+test (3,5 triệu flow), chia lại phân tầng 80/20 với 5 seed, huấn luyện lại XGBoost
đúng siêu tham số RQ1, đo trên test thường và test đã loại các dòng trùng với train."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

sys.path.insert(0, r"C:\Users\LOQ\Downloads\SELF_KLTN\RQ1_Model_Training_xboost")
from ids_metrics import ids_detection_metrics  # noqa: E402

D = Path(r"C:\Users\LOQ\Downloads\SELF_KLTN\dataset\CICID-2018_processed")
OUT = Path(r"C:\Users\LOQ\Downloads\SELF_KLTN\RQ1_Model_Training_xboost\results\repeat_runs")
OUT.mkdir(parents=True, exist_ok=True)
SEEDS = [1, 2, 3]

pool = pd.concat([pd.read_parquet(D / "train_set.parquet"), pd.read_parquet(D / "test_set.parquet")], ignore_index=True)
X = pool.drop(columns=["Label"]).astype("float32")
le = LabelEncoder()
y = le.fit_transform(pool["Label"])
benign = list(le.classes_).index("Benign")
del pool
print("pool", X.shape, "classes", len(le.classes_), flush=True)
hashes = pd.util.hash_pandas_object(X, index=False).to_numpy()


def metrics(y_true, y_pred):
    acc = accuracy_score(y_true, y_pred) * 100
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, labels=np.arange(len(le.classes_)), average="macro", zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=np.arange(len(le.classes_)))
    d = ids_detection_metrics(cm, benign)
    return dict(n=int(len(y_true)), accuracy=acc, macro_precision=p * 100, macro_recall=r * 100, macro_f1=f * 100,
                fpr=d["fpr_pct"], fnr=d["fnr_pct"], fp=d["fp"], fn=d["fn"])


rows = []
for s in SEEDS:
    idx_tr, idx_te = train_test_split(np.arange(len(y)), test_size=0.2, stratify=y, random_state=s)
    t0 = time.time()
    m = XGBClassifier(n_estimators=100, max_depth=8, learning_rate=0.08, tree_method="hist", random_state=s, n_jobs=-1)
    m.fit(X.iloc[idx_tr], y[idx_tr])
    train_s = time.time() - t0
    pred = m.predict(X.iloc[idx_te])
    full = metrics(y[idx_te], pred)
    keep = ~np.isin(hashes[idx_te], hashes[idx_tr])
    dedup = metrics(y[idx_te][keep], pred[keep])
    rec = dict(seed=s, train_seconds=round(train_s, 1), test_rows=len(idx_te), duplicated_with_train=int((~keep).sum()),
               full=full, dedup=dedup)
    rows.append(rec)
    json.dump(rec, open(OUT / f"seed_{s}.json", "w"), indent=1)
    print(f"seed {s}: {train_s/60:.1f} min | full acc {full['accuracy']:.3f} f1 {full['macro_f1']:.2f} fpr {full['fpr']:.3f} fnr {full['fnr']:.3f}"
          f" | dedup n={dedup['n']} acc {dedup['accuracy']:.3f} f1 {dedup['macro_f1']:.2f} fpr {dedup['fpr']:.3f}", flush=True)

summ = {}
for part in ("full", "dedup"):
    df = pd.DataFrame([r[part] for r in rows])
    summ[part] = {c: dict(mean=float(df[c].mean()), std=float(df[c].std(ddof=1)), min=float(df[c].min()), max=float(df[c].max()))
                  for c in ["accuracy", "macro_precision", "macro_recall", "macro_f1", "fpr", "fnr"]}
summ["duplicated_share_pct"] = float(np.mean([r["duplicated_with_train"] / r["test_rows"] * 100 for r in rows]))
json.dump(summ, open(OUT / "summary.json", "w"), indent=1)
print(json.dumps(summ, indent=1), flush=True)
