"""So sánh hai bộ train: bộ train cũ của RQ1 (train_set) và bộ train improved dựng cho M1 (d2_train).
Chỉ dùng hai bộ này, không dùng nguồn gốc. Cả hai đều theo cùng công thức lấy mẫu RQ1, nên so sánh được trực tiếp.
Ngưỡng vùng Hulk đọc từ cấu hình RQ3. Kết quả: results/compare_train_sets.json và compare_train_by_label.csv."""
import json

import pandas as pd

from rq4_common import *

R = hulk_zone_rule()
MIN_FIN, MIN_LEN, MAX_SEG = R["min_fin_flag_cnt"], R["min_fwd_pkt_len_max"], R["below_fwd_seg_size_min"]
PROFILE = ["Flow Duration", "Tot Fwd Pkts", "Fwd Pkt Len Max", "Init Fwd Win Byts", "Init Bwd Win Byts", "Fwd Seg Size Min", "FIN Flag Cnt", "Dst Port"]
sets = {"cu": pd.read_parquet(TRAIN_OLD), "moi": pd.read_parquet(DATA / "d2_train.parquet")}
sets["cu"] = sets["cu"][sets["cu"].Label.isin(CLASSES_13)].reset_index(drop=True)
out, rows = {}, []
for k, d in sets.items():
    t = d[d.Protocol == 6]
    fin = t["FIN Flag Cnt"] >= MIN_FIN
    d66 = t["Fwd Pkt Len Max"] >= MIN_LEN
    zone = fin & d66 & (t["Fwd Seg Size Min"] < MAX_SEG)
    full = t[(t["Tot Fwd Pkts"] >= 4) & (t["Tot Bwd Pkts"] >= 4)]
    o = dict(rows=len(d), tcp_rows=len(t), classes=int(d.Label.nunique()), benign_rows=int((d.Label == "Benign").sum()),
             flag_values={c: sorted(map(float, d[c].unique()))[:6] for c in ["FIN Flag Cnt", "SYN Flag Cnt", "RST Flag Cnt", "PSH Flag Cnt", "ACK Flag Cnt"]},
             tcp_ack_ge1=int((t["ACK Flag Cnt"] >= 1).sum()), tcp_ge4pkts_each_way=len(full), tcp_ge4pkts_each_way_fin=int((full["FIN Flag Cnt"] >= MIN_FIN).sum()))
    for name, lab in [("benign", "Benign"), ("hulk", "DoS attacks-Hulk")]:
        m = t.Label == lab
        o[name] = dict(tcp_rows=int(m.sum()), fin=int((fin & m).sum()), fin_data_gt0=int((fin & m & (t["Fwd Pkt Len Max"] > 0)).sum()),
                       fin_data_ge_min=int((fin & d66 & m).sum()), zone=int((zone & m).sum()))
        o[name]["profile_median"] = {c: float(t.loc[m, c].median()) for c in PROFILE}
    # mọi lớp tấn công khác: có bao nhiêu dòng nằm trong vùng ba điều kiện
    zl = t[zone].Label.value_counts().to_dict()
    o["zone_by_label"] = {kk: int(v) for kk, v in zl.items()}
    out[k] = o
    g = pd.DataFrame({"Label": t.Label, "n": 1, "fin": fin.astype(int), "zone": zone.astype(int)}).groupby("Label").sum()
    g["all_rows"] = d.Label.value_counts()
    g["bo"] = k
    rows.append(g.reset_index())
pd.concat(rows).to_csv(RESULTS / "compare_train_by_label.csv", index=False, encoding="utf-8-sig")
json.dump(out, open(RESULTS / "compare_train_sets.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for k in out:
    print(k, {x: out[k][x] for x in ("rows", "tcp_rows", "tcp_ack_ge1", "tcp_ge4pkts_each_way", "tcp_ge4pkts_each_way_fin")})
    print("  benign", {a: b for a, b in out[k]["benign"].items() if a != "profile_median"})
    print("  hulk  ", {a: b for a, b in out[k]["hulk"].items() if a != "profile_median"})
    print("  flags", out[k]["flag_values"])
    print("  zone theo lớp", out[k]["zone_by_label"])
