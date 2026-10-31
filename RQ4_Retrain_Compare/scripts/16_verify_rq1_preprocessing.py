"""Kiểm tra tập train và test của RQ1 được tạo từ 10 tệp Parquet nguồn như thế nào.

 1. Cột: tập train có đúng 78 đặc trưng, bỏ cột nào so với nguồn.
 2. Giá trị: mỗi dòng train và test có xuất hiện nguyên vẹn (float32) trong nguồn không, nghĩa là có bị chuẩn hóa hay đổi giá trị không.
 3. Làm sạch: nguồn và tập train có NaN, vô cực, giá trị âm không, và bao nhiêu dòng trùng đặc trưng.
 4. Lấy mẫu: số flow mỗi lớp ở nguồn so với train cộng test, và tỷ lệ train trên test mỗi lớp (kiểm tra chia phân tầng).
Kết quả: results/rq1_preprocessing_check.json."""
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from rq4_common import *

SRC = REPO / "dataset" / "CICID-2018"
out = {}
tr = pd.read_parquet(TRAIN_OLD)
te = pd.read_parquet(TEST_OLD)
feats = [c for c in tr.columns if c != "Label"]
files = sorted(SRC.glob("*.parquet"))
sch = pq.ParquetFile(files[0]).schema_arrow
src_cols = [f.name for f in sch]
out["columns"] = dict(source_n=len(src_cols), source_dtypes={f.name: str(f.type) for f in sch if f.name in ("Timestamp", "Label", "Dst Port", "Protocol", "Flow Duration")},
                      removed_from_source=[c for c in src_cols if c not in feats], not_in_source=[c for c in feats if c not in src_cols],
                      n_features=len(feats), train_dtypes=sorted({str(t) for t in tr[feats].dtypes}), same_order_as_source=[c for c in src_cols if c in feats] == feats)
print(out["columns"], flush=True)

hashes, labels, nan_inf, neg = [], [], dict(nan=0, inf=0, rows=0), {}
for f in files:
    pf = pq.ParquetFile(f)
    for batch in pf.iter_batches(batch_size=500_000, columns=feats + ["Label"]):
        d = batch.to_pandas()
        x = d[feats].astype("float64")
        nan_inf["rows"] += len(d)
        nan_inf["nan"] += int(x.isna().to_numpy().sum())
        nan_inf["inf"] += int(np.isinf(x.to_numpy()).sum())
        for c in feats:
            n = int((x[c] < 0).sum())
            if n:
                neg[c] = neg.get(c, 0) + n
        hashes.append(pd.util.hash_pandas_object(d[feats].astype("float32"), index=False).to_numpy())
        labels.append(d["Label"].astype(str).to_numpy())
    print("đọc xong", f.name, flush=True)
H = np.concatenate(hashes); L = np.concatenate(labels)
out["source"] = dict(rows=int(len(H)), nan=nan_inf["nan"], inf=nan_inf["inf"], columns_with_negative_values=len(neg), negative_examples={k: neg[k] for k in sorted(neg, key=neg.get, reverse=True)[:6]},
                     unique_feature_vectors=int(len(np.unique(H))), duplicate_rows_by_features=int(len(H) - len(np.unique(H))))
print(out["source"], flush=True)

Hs = np.sort(np.unique(H))
for name, d in (("train", tr), ("test", te)):
    h = pd.util.hash_pandas_object(d[feats].astype("float32"), index=False).to_numpy()
    pos = np.searchsorted(Hs, h)
    pos[pos == len(Hs)] = 0
    found = Hs[pos] == h
    x = d[feats].astype("float64")
    out[name] = dict(rows=len(d), rows_found_unchanged_in_source=int(found.sum()), nan=int(x.isna().to_numpy().sum()), inf=int(np.isinf(x.to_numpy()).sum()),
                     columns_with_negative_values=int(((x < 0).sum() > 0).sum()), duplicate_rows_within=int(len(h) - len(np.unique(h))))
    print(name, out[name], flush=True)

src_c = pd.Series(L).value_counts()
trc, tec = tr.Label.value_counts(), te.Label.value_counts()
tab = pd.DataFrame({"source": src_c, "train": trc, "test": tec}).fillna(0).astype(int)
tab["kept_pct"] = (100 * (tab.train + tab.test) / tab.source).round(2)
tab["train_share_pct"] = (100 * tab.train / (tab.train + tab.test)).round(2)
tab.to_csv(RESULTS / "rq1_sampling_by_class.csv", encoding="utf-8-sig")
out["sampling"] = json.loads(tab.to_json(orient="index"))
print(tab.to_string(), flush=True)
json.dump(out, open(RESULTS / "rq1_preprocessing_check.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("xong")
