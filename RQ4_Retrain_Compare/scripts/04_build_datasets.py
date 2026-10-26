"""Dựng bộ dữ liệu cho M1 và M2 từ cache của bản improved, theo công thức của bộ 3,5 triệu dòng RQ1.

Công thức RQ1 (báo cáo dataset 3,5 triệu dòng): tỷ lệ 70 % Benign và 30 % tấn công, lớp hiếm giữ nguyên,
78 đặc trưng float32, không Timestamp, chia stratified 80/20. Số mẫu mỗi lớp tấn công lấy theo thành phần của
bộ cũ (đọc từ train_set và test_set, không gõ cứng), bị chặn trên bởi số flow sẵn có trong bản improved.

Khác biệt có chủ đích so với RQ1, nhằm tránh lỗi trùng train và test đã ghi nhận ở bộ cũ:
 - Mỗi lớp được sắp theo Timestamp. 78 % đầu là "vùng lấy mẫu", 20 % cuối là "vùng giữ riêng theo thời gian",
   2 % ở giữa bị bỏ để một kết nối không nằm ở cả hai phía.
 - Bộ 3,5 triệu dòng (train 80 %, test 20 % stratified) chỉ lấy từ vùng lấy mẫu.
 - T2 giữ riêng theo thời gian lấy từ vùng cuối.
"""
import json
import numpy as np
import pandas as pd
from rq4_common import *

LOW, HIGH = 0.78, 0.80
BENIGN_SHARE = 0.70
TAIL_CAP_ATTACK, TAIL_CAP_BENIGN = 50_000, 200_000
M2_SIZES = [10_000]

parts = [pd.read_parquet(p) for p in sorted((DATA / "improved_parts").glob("*.parquet"))]
imp = pd.concat(parts, ignore_index=True); del parts
print("cache:", len(imp), "dòng;", imp.Label.value_counts().to_dict())
imp = imp.dropna(subset=["Timestamp"]).reset_index(drop=True)

# 1. vùng lấy mẫu / vùng giữ riêng theo thời gian, tính riêng từng lớp
imp["rank"] = imp.groupby("Label")["Timestamp"].rank(method="first", pct=True)
pool = imp[imp["rank"] <= LOW]
tail = imp[imp["rank"] > HIGH]

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

# 4. T2: giữ riêng theo thời gian
tl = []
for c, g in tail.groupby("Label"):
    cap = TAIL_CAP_BENIGN if c == "Benign" else TAIL_CAP_ATTACK
    ix = g.index.to_numpy()
    tl.append(rng.choice(ix, size=min(cap, len(ix)), replace=False))
tl = np.concatenate(tl)
holdout = imp.loc[tl, FEATURES + ["Label", "Day"]]
holdout.to_parquet(DATA / "t2_time_holdout.parquet", index=False)

# 5. hàng Benign thêm cho M2: nằm trong vùng ba điều kiện, lấy từ vùng lấy mẫu nhưng KHÔNG thuộc bộ 3,5 triệu
R = hulk_zone_rule()
left = pool[(pool.Label == "Benign") & (~pool.index.isin(chosen))]
zone = left[(left["FIN Flag Cnt"] >= R["min_fin_flag_cnt"]) & (left["Fwd Pkt Len Max"] >= R["min_fwd_pkt_len_max"]) & (left["Fwd Seg Size Min"] < R["below_fwd_seg_size_min"])]
print("Benign trong vùng ba điều kiện còn dư để thêm vào M2:", len(zone))
for n in M2_SIZES:
    pick = zone.sample(n=min(n, len(zone)), random_state=SEED)
    pick[FEATURES + ["Label"]].to_parquet(DATA / f"m2_add_{n}.parquet", index=False)

# 6. báo cáo thành phần và trùng lặp
def comp(df, name):
    return df.Label.value_counts().rename(name)
rep = pd.concat([comp(train, "d2_train"), comp(test, "d2_test"), comp(holdout, "t2_holdout"),
                 comp(pd.read_parquet(TRAIN_OLD, columns=["Label"]), "old_train"), comp(pd.read_parquet(TEST_OLD, columns=["Label"]), "old_test")], axis=1).fillna(0).astype(int)
rep.to_csv(RESULTS / "dataset_composition.csv", encoding="utf-8-sig")
print(rep.to_string())


def hashes(df):
    return set(pd.util.hash_pandas_object(df[FEATURES], index=False).values.tolist())


h_tr, h_te, h_ho = hashes(train), hashes(test), hashes(holdout)
dup = dict(
    d2_test_rows_also_in_train=int(pd.util.hash_pandas_object(test[FEATURES], index=False).isin(h_tr).sum()), d2_test_rows=len(test),
    t2_holdout_rows_also_in_train=int(pd.util.hash_pandas_object(holdout[FEATURES], index=False).isin(h_tr).sum()), t2_holdout_rows=len(holdout),
    old_test_rows_also_in_train=194149, old_test_rows=700000, old_note="Số của RQ2 (rq2_master_summary.json), dùng để so sánh.",
    time_ranks=dict(pool_upto=LOW, gap_until=HIGH), targets=target)
json.dump(dup, open(RESULTS / "leakage_report.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(dup, ensure_ascii=False, indent=1))
