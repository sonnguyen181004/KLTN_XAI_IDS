"""Đánh giá M1 bằng phép chia chặt hơn phép chia ngẫu nhiên của RQ1: chia theo khối thời gian liên tục trong từng lớp.

Cùng dữ liệu mẫu và cùng số mẫu mỗi lớp như 04_build_datasets.py (cùng seed, cùng mã chọn mẫu), nhưng thay vì xáo ngẫu nhiên:
 - Mỗi lớp được sắp theo Timestamp và cắt thành 5 đoạn thời gian liên tục (fold 0..4).
 - Ở lượt k, test là đoạn k của mọi lớp, train là bốn đoạn còn lại.
 - Vùng đệm: bỏ khỏi train các dòng nằm trong 1% thứ hạng thời gian sát hai đầu đoạn test (theo từng lớp),
   để một kết nối kéo dài không nằm ở cả hai phía.
 - Bản "sạch": bỏ khỏi test mọi dòng có 78 đặc trưng giống hệt một dòng train.
Cấu hình XGBoost là cấu hình RQ1, không đổi. Kết quả: results/blocked_cv_m1.csv và blocked_cv_m1_by_class.csv."""
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from rq4_common import *

sys.path.insert(0, str(REPO / "RQ1_Model_Training_xboost"))
from ids_metrics import ids_detection_metrics  # noqa: E402

BENIGN_SHARE, K, GAP = 0.70, 5, 0.01
parts = [pd.read_parquet(p) for p in sorted((DATA / "improved_parts").glob("*.parquet"))]
imp = pd.concat(parts, ignore_index=True); del parts
imp = imp.reset_index(drop=True)
pool = imp
old = pd.concat([pd.read_parquet(TRAIN_OLD, columns=["Label"]), pd.read_parquet(TEST_OLD, columns=["Label"])])
old_counts = old.Label.value_counts()
avail = pool.Label.value_counts()
target = {c: int(min(old_counts[c], avail.get(c, 0))) for c in CLASSES_13 if c != "Benign"}
target["Benign"] = min(int(round(sum(target.values()) * BENIGN_SHARE / (1 - BENIGN_SHARE))), int(avail["Benign"]))
rng = np.random.default_rng(SEED)
chosen = np.concatenate([rng.choice(pool.index[pool.Label == c].to_numpy(), size=n, replace=False) for c, n in target.items()])
s = imp.loc[chosen, FEATURES + ["Label", "Timestamp"]].copy()
del imp
print("mẫu:", len(s), flush=True)
s = s.dropna(subset=["Timestamp"])
s["rank"] = s.groupby("Label")["Timestamp"].rank(method="first", pct=True)
s["fold"] = np.minimum((s["rank"] * K).astype(int), K - 1)
lo = s["fold"] / K
hi = (s["fold"] + 1) / K

le = LabelEncoder().fit(CLASSES_13)
rows, byc = [], []
for k in range(K):
    te = s[s.fold == k]
    a, b = k / K, (k + 1) / K
    tr = s[(s.fold != k) & ~((s["rank"] > a - GAP) & (s["rank"] < b + GAP))]
    h_tr = set(pd.util.hash_pandas_object(tr[FEATURES], index=False).tolist())
    dup = pd.util.hash_pandas_object(te[FEATURES], index=False).isin(h_tr).to_numpy()
    classes_tr = set(tr.Label.unique())
    m = XGBClassifier(n_estimators=100, max_depth=8, learning_rate=0.08, tree_method="hist", random_state=SEED, n_jobs=-1)
    le_k = LabelEncoder().fit(tr.Label)
    m.fit(tr[FEATURES], le_k.transform(tr.Label))
    for name, d in [("khoi_thoi_gian", te), ("khoi_thoi_gian_sach", te[~dup])]:
        # lớp có trong test mà không có trong train (lớp rất nhỏ) tính là dự đoán sai
        pred = np.array(le_k.classes_)[m.predict(d[FEATURES])]
        y = d.Label.to_numpy()
        labs = list(le.classes_)
        cm = confusion_matrix(y, pred, labels=labs)
        det = ids_detection_metrics(cm, labs.index("Benign"))
        pr, rc, f1, _ = precision_recall_fscore_support(y, pred, labels=labs, average="macro", zero_division=0)
        rows.append(dict(fold=k, bo=name, n_train=len(tr), n_test=len(d), accuracy=accuracy_score(y, pred) * 100, macro_f1=f1 * 100,
                         macro_recall=rc * 100, fpr_pct=det["fpr_pct"], fnr_pct=det["fnr_pct"], dup_removed=int(dup.sum()) if name.endswith("sach") else 0,
                         classes_missing_in_train=";".join(sorted(set(d.Label.unique()) - classes_tr))))
        rec = pd.Series({c: float((pred[y == c] == c).mean() * 100) for c in sorted(set(y))})
        byc.append(pd.DataFrame({"fold": k, "bo": name, "class": rec.index, "recall_pct": rec.values, "n_test": [int((y == c).sum()) for c in rec.index]}))
        print(f"fold {k} {name}: n_test {len(d):,} | Acc {rows[-1]['accuracy']:.2f} | Macro F1 {rows[-1]['macro_f1']:.2f} | FPR {det['fpr_pct']:.4f} | FNR {det['fnr_pct']:.4f}", flush=True)
res = pd.DataFrame(rows)
res.to_csv(RESULTS / "blocked_cv_m1.csv", index=False, encoding="utf-8-sig")
pd.concat(byc).to_csv(RESULTS / "blocked_cv_m1_by_class.csv", index=False, encoding="utf-8-sig")
print(res.groupby("bo")[["accuracy", "macro_f1", "macro_recall", "fpr_pct", "fnr_pct"]].agg(["mean", "min", "max"]).round(3).to_string())
print("xong")
