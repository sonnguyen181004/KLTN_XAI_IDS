"""Kiểm tra M1 như một mô hình độc lập, không so với M0.

 1. Nguồn: đối chiếu dòng trong cache với tệp CSV gốc của bản improved (nhãn và đặc trưng có đúng không).
 2. Nhãn mâu thuẫn: có cặp dòng giống hệt về 78 đặc trưng nhưng khác nhãn không.
 3. Nhãn xáo trộn: huấn luyện lại với nhãn bị xáo ngẫu nhiên; nếu điểm vẫn cao thì có rò rỉ.
 4. Đường cong học: điểm trên test khi chỉ dùng 0,1 %, 1 %, 10 % dữ liệu train.
 5. Mô hình đơn giản: cây quyết định nông.
 6. Gần giống nhau: khoảng cách từ dòng test tới dòng train gần nhất (đặc trưng chuẩn hóa).
Kết quả ghi vào results/m1_standalone_audit.json."""
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pc
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier, export_text
from xgboost import XGBClassifier

from rq4_common import *

out = {}
tr = pd.read_parquet(DATA / "d2_train.parquet")
te = pd.read_parquet(DATA / "d2_test.parquet")
le = LabelEncoder().fit(tr.Label)
ytr, yte = le.transform(tr.Label), le.transform(te.Label)
PARAMS = dict(n_estimators=100, max_depth=8, learning_rate=0.08, tree_method="hist", random_state=SEED, n_jobs=-1)


def score(model, X, y):
    p = model.predict(X)
    return dict(accuracy=float((p == y).mean() * 100), macro_f1=float(f1_score(y, p, average="macro", zero_division=0) * 100))


# ---- 1. đối chiếu với tệp CSV gốc của bản improved
cache_parts = {p.stem: p for p in (DATA / "improved_parts").glob("*.parquet")}
check = {}
for day in ["Friday-16-02-2018", "Wednesday-21-02-2018", "Wednesday-14-02-2018"]:
    part = pd.read_parquet(cache_parts[day])
    samp = part.sample(frac=1.0, random_state=SEED).groupby("Label").head(150).reset_index(drop=True)
    need = ["Timestamp", "Label", FEATURE_MAP["Flow Duration"], FEATURE_MAP["Tot Fwd Pkts"], FEATURE_MAP["Tot Bwd Pkts"], FEATURE_MAP["TotLen Fwd Pkts"], FEATURE_MAP["Fwd Pkt Len Max"], FEATURE_MAP["Dst Port"]]
    raw = pc.read_csv(IMPROVED_DIR / f"{day}.csv", read_options=pc.ReadOptions(block_size=1 << 27),
                      convert_options=pc.ConvertOptions(include_columns=need, column_types={c: pa.float64() for c in need if c not in ("Timestamp", "Label")} | {"Timestamp": pa.string(), "Label": pa.string()},
                                                         null_values=["", "NaN", "Infinity", "-Infinity"], strings_can_be_null=True)).to_pandas()
    raw["Timestamp"] = pd.to_datetime(raw.Timestamp, errors="coerce")
    ren = {FEATURE_MAP[f]: f for f in ["Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts", "TotLen Fwd Pkts", "Fwd Pkt Len Max", "Dst Port"]}
    raw = raw.rename(columns=ren).rename(columns={"Label": "RawLabel"})
    key = ["Timestamp", "Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts", "TotLen Fwd Pkts", "Fwd Pkt Len Max", "Dst Port"]
    m = samp.merge(raw.drop_duplicates(key), on=key, how="left")
    ok_found = int(m.RawLabel.notna().sum())
    mapped = m.RawLabel.map(LABEL_MAP)
    check[day] = dict(sampled=len(samp), found_in_raw=ok_found, label_matches_mapping=int((mapped == m.Label).sum()))
    print("đối chiếu", day, check[day], flush=True)
out["provenance_check"] = check

# ---- 2. nhãn mâu thuẫn
allx = pd.concat([tr, te], ignore_index=True)
h = pd.util.hash_pandas_object(allx[FEATURES], index=False)
lab_per_hash = allx.assign(h=h.values).groupby("h").Label.nunique()
out["conflicting_label_groups"] = int((lab_per_hash > 1).sum())
out["identical_feature_groups"] = int(len(lab_per_hash))
print("nhóm dòng giống hệt về đặc trưng nhưng khác nhãn:", out["conflicting_label_groups"], "trên", out["identical_feature_groups"], flush=True)

# ---- 3. nhãn xáo trộn
rng = np.random.default_rng(SEED)
m_sh = XGBClassifier(**PARAMS).fit(tr[FEATURES], rng.permutation(ytr))
out["shuffled_labels"] = score(m_sh, te[FEATURES], yte)
out["majority_baseline_accuracy"] = float((yte == np.bincount(yte).argmax()).mean() * 100)
print("nhãn xáo trộn:", out["shuffled_labels"], "| chỉ đoán lớp đông nhất:", out["majority_baseline_accuracy"], flush=True)

# ---- 4. đường cong học
curve = {}
for frac in (0.001, 0.01, 0.1):
    shuf = tr.sample(frac=1.0, random_state=SEED)
    k = shuf.groupby("Label").Label.transform("size").mul(frac).clip(lower=3).round()
    sub = shuf[shuf.groupby("Label").cumcount() < k]
    m = XGBClassifier(**PARAMS).fit(sub[FEATURES], le.transform(sub.Label))
    curve[str(frac)] = dict(train_rows=len(sub), **score(m, te[FEATURES], yte))
    print("đường cong học", frac, curve[str(frac)], flush=True)
out["learning_curve"] = curve

# ---- 5. cây quyết định nông
trees = {}
for d in (2, 3, 5):
    t = DecisionTreeClassifier(max_depth=d, random_state=SEED).fit(tr[FEATURES], ytr)
    trees[str(d)] = score(t, te[FEATURES], yte)
    if d == 3:
        trees["depth3_rules"] = export_text(t, feature_names=FEATURES, max_depth=3)
    print("cây độ sâu", d, trees[str(d)], flush=True)
out["shallow_trees"] = trees

# ---- 6. khoảng cách gần nhất từ test tới train
mu, sd = tr[FEATURES].mean(), tr[FEATURES].std().replace(0, 1)
def z(df):
    return np.clip(((df[FEATURES] - mu) / sd).to_numpy(dtype="float32"), -50, 50)
tr_s = tr.sample(n=600_000, random_state=SEED)
te_s = te.sample(frac=1.0, random_state=SEED).groupby("Label").head(300)
A, B = z(te_s), z(tr_s)
bn = (B ** 2).sum(1)
dmin = np.empty(len(A), dtype="float32")
for i in range(0, len(A), 500):
    a = A[i:i + 500]
    d2 = (a ** 2).sum(1)[:, None] + bn[None, :] - 2 * a @ B.T
    dmin[i:i + 500] = np.sqrt(np.maximum(d2.min(1), 0))
out["nearest_neighbor"] = dict(n_test=len(A), n_train_pool=len(B), median=float(np.median(dmin)), p90=float(np.quantile(dmin, 0.9)),
                               frac_below_0_01=float((dmin < 0.01).mean() * 100), frac_below_0_1=float((dmin < 0.1).mean() * 100))
print("khoảng cách gần nhất (độ lệch chuẩn):", out["nearest_neighbor"], flush=True)

json.dump(out, open(RESULTS / "m1_standalone_audit.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("xong")
