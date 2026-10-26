"""Kiểm toán cờ FIN trong CSV gốc CSE-CIC-IDS2018 (9 tệp TrafficForML). Chỉ đọc, chỉ xét giao thức TCP.
Ngưỡng của vùng Hulk đọc từ RQ3_IDS_System/config.yaml (hulk_fin_hint)."""
import json
import collections
import pandas as pd
from rq4_common import *

R = hulk_zone_rule()
MIN_FIN, MIN_LEN, MAX_SEG = R["min_fin_flag_cnt"], R["min_fwd_pkt_len_max"], R["below_fwd_seg_size_min"]
NEED = ["Protocol", "Label", "FIN Flag Cnt", "SYN Flag Cnt", "RST Flag Cnt", "PSH Flag Cnt", "ACK Flag Cnt",
        "Tot Fwd Pkts", "Tot Bwd Pkts", "Fwd Pkt Len Max", "Fwd Seg Size Min"]
by = collections.defaultdict(lambda: collections.Counter())
tot = collections.Counter()
vals = collections.defaultdict(set)
for f in sorted(ORIG_DIR.glob("*.csv")):
    day = f.name.split("_")[0]
    hdr = pd.read_csv(f, nrows=0).columns.tolist()
    ren = {}
    if "FIN Flag Cnt" not in hdr and hdr[45].strip() == "":   # tệp Thursday-15: tên cột FIN bị mất, cùng vị trí 45
        ren[hdr[45]] = "FIN Flag Cnt"
    for c in NEED:
        if c not in hdr and c not in ren.values():
            raise SystemExit(f"{f.name}: thiếu cột {c}")
        if c in hdr:
            ren[c] = c
    for ch in pd.read_csv(f, usecols=list(ren), chunksize=500_000, low_memory=False):
        ch = ch.rename(columns=ren)
        ch = ch[ch.Label.astype(str) != "Label"]
        for c in NEED[2:]:
            ch[c] = pd.to_numeric(ch[c], errors="coerce")
        ch["Protocol"] = pd.to_numeric(ch["Protocol"], errors="coerce")
        t = ch[ch.Protocol == 6]
        tot["flows_all"] += len(ch); tot["flows_tcp"] += len(t)
        for c, k in [("FIN Flag Cnt", "fin"), ("SYN Flag Cnt", "syn"), ("RST Flag Cnt", "rst"), ("ACK Flag Cnt", "ack"), ("PSH Flag Cnt", "psh")]:
            tot[f"tcp_{k}_ge1"] += int((t[c] >= 1).sum())
            vals[k] |= set(t[c].dropna().unique().tolist())
        full = t[(t["Tot Fwd Pkts"] >= 4) & (t["Tot Bwd Pkts"] >= 4)]
        tot["tcp_ge4pkts_each_way"] += len(full); tot["tcp_ge4pkts_each_way_fin"] += int((full["FIN Flag Cnt"] >= MIN_FIN).sum())
        fin = t["FIN Flag Cnt"] >= MIN_FIN
        d66 = t["Fwd Pkt Len Max"] >= MIN_LEN
        zone = fin & d66 & (t["Fwd Seg Size Min"] < MAX_SEG)
        g = pd.DataFrame({"Label": t.Label, "n": 1, "fin": fin.astype(int), "fin_data": (fin & (t["Fwd Pkt Len Max"] > 0)).astype(int),
                          "fin_data_ge_min": (fin & d66).astype(int), "zone": zone.astype(int)}).groupby("Label").sum()
        for lab, row in g.iterrows():
            by[(day, lab)].update({k: int(v) for k, v in row.items()})
    print("xong", f.name, flush=True)
rows = [dict(day=d, label=l, tcp_flows=c["n"], fin=c["fin"], fin_data_gt0=c["fin_data"], fin_data_ge_min=c["fin_data_ge_min"], zone=c["zone"]) for (d, l), c in sorted(by.items())]
pd.DataFrame(rows).to_csv(RESULTS / "audit_orig_by_label.csv", index=False, encoding="utf-8-sig")
out = dict(tot); out["flag_values_seen"] = {k: sorted(v)[:8] for k, v in vals.items()}
out["rule"] = dict(min_fin=MIN_FIN, min_fwd_pkt_len_max=MIN_LEN, below_fwd_seg_size_min=MAX_SEG)
json.dump(out, open(RESULTS / "audit_orig_flags.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(out, ensure_ascii=False, indent=1))
