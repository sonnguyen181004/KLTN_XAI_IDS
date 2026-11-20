# -*- coding: utf-8 -*-
"""Kiểm tra file test_sample100_15classes_with_label.csv (105 flow) có nằm trong test_set RQ1 không,
và có trùng train_set không. Chạy từ thư mục SELF_KLTN:
    python RQ3_IDS_System/scripts/verify_sample100_source.py
Đối chiếu ở float32 (kiểu lưu của parquet RQ1). Cần pandas và pyarrow (đã có trong môi trường của dự án)."""
import hashlib
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "RQ3_IDS_System/data/test_samples/test_sample100_15classes_with_label.csv"
TEST = ROOT / "dataset/CICID-2018_processed/test_set.parquet"
TRAIN = ROOT / "dataset/CICID-2018_processed/train_set.parquet"
CLEAN = ROOT / "RQ3_IDS_System/data/clean_holdout_set.csv"

s = pd.read_csv(SAMPLE)
feat = [c for c in s.columns if c not in ("flow_id", "label_true")]
print("Mẫu:", s.shape, "| số đặc trưng:", len(feat))

def h(df, chunk=200_000):
    """Băm từng khối nhỏ để train_set (2,8 triệu dòng) không tràn bộ nhớ."""
    out = []
    for i in range(0, len(df), chunk):
        # parquet lưu float32 còn CSV là chữ float64: ép cả hai về float32 mới so khớp đúng (round(6) trên float64 gây sai lệch)
        x = df[feat].iloc[i:i + chunk].astype("float32").to_numpy()
        out.extend(hashlib.md5(r.tobytes()).hexdigest() for r in x)
    return pd.Series(out, index=df.index)

s["h"] = h(s)
res = {}
for name, path in (("test_set", TEST), ("train_set", TRAIN)):
    d = pd.read_parquet(path, columns=feat)
    miss = [c for c in feat if c not in d.columns]
    if miss:
        print("Thiếu cột trong", name, ":", miss[:5]); continue
    res[name] = set(h(d))
    s["in_" + name] = s["h"].isin(res[name])
    print(f"{name}: {s['in_' + name].sum()} / {len(s)} dòng của mẫu có trong {name}")
c = pd.read_csv(CLEAN)
s["in_clean"] = s["h"].isin(set(h(c)))
print(f"clean_holdout (Tập B): {s['in_clean'].sum()} / {len(s)}")
if "in_test_set" in s and "in_train_set" in s:
    print("Có trong test_set mà cũng có trong train_set (trùng train):", int((s.in_test_set & s.in_train_set).sum()))
    print(s.groupby("label_true")[["in_test_set", "in_train_set", "in_clean"]].sum().to_string())
