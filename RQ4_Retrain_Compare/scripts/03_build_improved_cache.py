"""Quét 10 tệp của bản improved (khoảng 35 GB) một lần duy nhất.
 - Kiểm toán cờ FIN trên toàn bộ flow TCP, trước khi lấy mẫu hay bỏ nhãn.
 - Giữ toàn bộ flow của 12 lớp tấn công chung và một phần ngẫu nhiên của Benign.
 - Đổi 78 đặc trưng về tên RQ1, ép float32, bỏ dòng có NaN hoặc vô cực.
Kết quả: data/improved_parts/<ngày>.parquet và results/audit_improved_by_label.csv."""
import json
import collections
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pc
from rq4_common import *

BENIGN_RATE = 0.07
R = hulk_zone_rule()
MIN_FIN, MIN_LEN, MAX_SEG = R["min_fin_flag_cnt"], R["min_fwd_pkt_len_max"], R["below_fwd_seg_size_min"]
inv = {v: k for k, v in FEATURE_MAP.items()}
cols_imp = [FEATURE_MAP[f] for f in FEATURES]
(DATA / "improved_parts").mkdir(parents=True, exist_ok=True)

NULLS = ["", "NaN", "nan", "NAN", "Infinity", "-Infinity", "inf", "-inf", "Inf", "-Inf"]
ctypes = {c: pa.float64() for c in cols_imp}
ctypes.update({"Label": pa.string(), "Timestamp": pa.string()})
audit = collections.defaultdict(collections.Counter)
raw_counts = collections.Counter()
drop_nan = collections.Counter()
kept = collections.Counter()

for fi, f in enumerate(sorted(IMPROVED_DIR.glob("*.csv"))):
    day = f.stem
    rd = pc.open_csv(f, read_options=pc.ReadOptions(block_size=1 << 27),
                     convert_options=pc.ConvertOptions(include_columns=cols_imp + ["Label", "Timestamp"], column_types=ctypes,
                                                       null_values=NULLS, strings_can_be_null=True))
    parts = []
    rng = np.random.default_rng(SEED + fi)
    for batch in rd:
        df = batch.to_pandas()
        raw_counts.update(df.Label.value_counts().to_dict())
        # kiểm toán trên flow TCP, mọi nhãn
        t = df[df[FEATURE_MAP["Protocol"]] == 6]
        fin = t[FEATURE_MAP["FIN Flag Cnt"]] >= MIN_FIN
        ln = t[FEATURE_MAP["Fwd Pkt Len Max"]]
        zone = fin & (ln >= MIN_LEN) & (t[FEATURE_MAP["Fwd Seg Size Min"]] < MAX_SEG)
        g = pd.DataFrame({"Label": t.Label, "n": 1, "fin": fin.astype(int), "fin_data": (fin & (ln > 0)).astype(int),
                          "fin_data_ge_min": (fin & (ln >= MIN_LEN)).astype(int), "zone": zone.astype(int)}).groupby("Label").sum()
        for lab, row in g.iterrows():
            audit[(day, lab)].update({k: int(v) for k, v in row.items()})
        # ánh xạ nhãn, lấy mẫu Benign
        lab = df.Label.map(LABEL_MAP)
        df = df[lab.notna()].copy(); df["Label"] = lab[lab.notna()].values
        df = df[(df.Label != "Benign") | (rng.random(len(df)) < BENIGN_RATE)]
        X = df[cols_imp].to_numpy(dtype="float64")
        ok = np.isfinite(X).all(axis=1)
        drop_nan.update(df.Label[~ok].value_counts().to_dict())
        df = df[ok]
        out = pd.DataFrame(X[ok].astype("float32"), columns=[inv[c] for c in cols_imp])
        out["Label"] = df.Label.values
        out["Timestamp"] = pd.to_datetime(df.Timestamp.values, errors="coerce")
        out["Day"] = day
        kept.update(out.Label.value_counts().to_dict())
        parts.append(out)
    pd.concat(parts, ignore_index=True).to_parquet(DATA / "improved_parts" / f"{day}.parquet", index=False)
    print("xong", day, "giữ", sum(len(p) for p in parts), flush=True)

rows = [dict(day=d, label=l, tcp_flows=c["n"], fin=c["fin"], fin_data_gt0=c["fin_data"], fin_data_ge_min=c["fin_data_ge_min"], zone=c["zone"]) for (d, l), c in sorted(audit.items())]
pd.DataFrame(rows).to_csv(RESULTS / "audit_improved_by_label.csv", index=False, encoding="utf-8-sig")
json.dump(dict(raw_label_counts=dict(raw_counts), dropped_nan_or_inf=dict(drop_nan), kept_in_cache=dict(kept), benign_rate=BENIGN_RATE,
               rule=dict(min_fin=MIN_FIN, min_fwd_pkt_len_max=MIN_LEN, below_fwd_seg_size_min=MAX_SEG)),
          open(RESULTS / "improved_scan_summary.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(dict(kept), ensure_ascii=False, indent=1)); print("bỏ do NaN/inf:", dict(drop_nan))
