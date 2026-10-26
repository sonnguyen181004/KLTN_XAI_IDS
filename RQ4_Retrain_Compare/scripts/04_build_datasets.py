"""Dựng bộ train và test cho M1 từ cache của bản improved, làm đúng cách lấy dữ liệu của RQ1.

Công thức RQ1 (bộ 3,5 triệu dòng): 70 % Benign và 30 % tấn công, lớp hiếm giữ nguyên, 78 đặc trưng float32,
không Timestamp, không IP, chia stratified 80/20 với seed 42. Số mẫu mỗi lớp tấn công lấy theo thành phần của
bộ cũ (đọc từ train_set và test_set, không gõ cứng), bị chặn trên bởi số flow sẵn có trong bản improved.
Không có vùng thời gian hay bộ giữ riêng nào: lấy mẫu từ toàn bộ dữ liệu như RQ1.
"""
import json
import numpy as np
import pandas as pd
from rq4_common import *

BENIGN_SHARE = 0.70

parts = [pd.read_parquet(p) for p in sorted((DATA / "improved_parts").glob("*.parquet"))]
imp = pd.concat(parts, ignore_index=True); del parts
print("cache:", len(imp), "dòng;", imp.Label.value_counts().to_dict())
imp = imp.reset_index(drop=True)
pool = imp

# 2. số mẫu mục tiêu mỗi lớp tấn công theo thành phần bộ cũ
old = pd.concat([pd.read_parquet(TRAIN_OLD, columns=["Label"]), pd.read_parquet(TEST_OLD, columns=["Label"])])
old_counts = old.Label.value_counts()
avail = pool.Label.value_counts()
target = {}
for c in CLASSES_13:
    if c == "Benign":
        continue
    target[c] = int(min(old_counts[c], avail.get(c, 0)))
n_attack = sum(target.values())
target["Benign"] = int(round(n_attack * BENIGN_SHARE / (1 - BENIGN_SHARE)))
target["Benign"] = min(target["Benign"], int(avail["Benign"]))
print("mục tiêu:", target)

rng = np.random.default_rng(SEED)
chosen = []
for c, n in target.items():
    idx = pool.index[pool.Label == c].to_numpy()
    chosen.append(rng.choice(idx, size=n, replace=False))
chosen = np.concatenate(chosen)
sample = imp.loc[chosen]

# 3. chia stratified 80/20 như RQ1
tr_idx, te_idx = [], []
for c, g in sample.groupby("Label"):
    ix = g.index.to_numpy().copy(); rng.shuffle(ix)
    k = int(round(len(ix) * 0.8))
    tr_idx.append(ix[:k]); te_idx.append(ix[k:])
tr_idx, te_idx = np.concatenate(tr_idx), np.concatenate(te_idx)
tr_idx = rng.permutation(tr_idx); te_idx = rng.permutation(te_idx)
keep_cols = FEATURES + ["Label"]
train, test = imp.loc[tr_idx, keep_cols], imp.loc[te_idx, keep_cols]
train.to_parquet(DATA / "d2_train.parquet", index=False); test.to_parquet(DATA / "d2_test.parquet", index=False)

# 4. báo cáo thành phần và trùng lặp
def comp(df, name):
    return df.Label.value_counts().rename(name)
rep = pd.concat([comp(train, "d2_train"), comp(test, "d2_test"), 
                 comp(pd.read_parquet(TRAIN_OLD, columns=["Label"]), "old_train"), comp(pd.read_parquet(TEST_OLD, columns=["Label"]), "old_test")], axis=1).fillna(0).astype(int)
rep.to_csv(RESULTS / "dataset_composition.csv", encoding="utf-8-sig")
print(rep.to_string())


def hashes(df):
    return set(pd.util.hash_pandas_object(df[FEATURES], index=False).values.tolist())


h_tr = hashes(train)
dup = dict(
    d2_test_rows_also_in_train=int(pd.util.hash_pandas_object(test[FEATURES], index=False).isin(h_tr).sum()), d2_test_rows=len(test),
    old_test_rows_also_in_train=194149, old_test_rows=700000, old_note="Số của RQ2 (rq2_master_summary.json), dùng để so sánh.",
    targets=target)
json.dump(dup, open(RESULTS / "leakage_report.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(dup, ensure_ascii=False, indent=1))
