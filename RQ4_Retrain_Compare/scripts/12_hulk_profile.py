"""Hồ sơ đặc trưng của Hulk và Benign (flow TCP, ngày Friday-16-02-2018) trong CSV gốc và bản improved.
Dùng trung vị. Mục đích: cho thấy Hulk của hai bản là hai kiểu lưu lượng khác nhau."""
import pandas as pd
from rq4_common import *

FEATS = ["Flow Duration", "Tot Fwd Pkts", "Fwd Pkt Len Max", "Init Fwd Win Byts", "Init Bwd Win Byts", "Fwd Seg Size Min", "FIN Flag Cnt", "Dst Port"]
rows = []

# CSV gốc
f = ORIG_DIR / "Friday-16-02-2018_TrafficForML_CICFlowMeter.csv"
o = pd.read_csv(f, usecols=FEATS + ["Protocol", "Label"], low_memory=False)
o = o[o.Label != "Label"]
for c in FEATS + ["Protocol"]:
    o[c] = pd.to_numeric(o[c], errors="coerce")
o = o[o.Protocol == 6]
for lab, name in [("DoS attacks-Hulk", "Hulk"), ("Benign", "Benign")]:
    d = o[o.Label == lab]
    rows.append(dict(ban="CSV gốc", lop=name, so_flow_tcp=len(d), **{c: float(d[c].median()) for c in FEATS}))

# bản improved
f = IMPROVED_DIR / "Friday-16-02-2018.csv"
need = [FEATURE_MAP[c] for c in FEATS] + ["Protocol", "Label"]
im = pd.read_csv(f, usecols=need, low_memory=False)
im = im[im.Protocol == 6]
for lab, name in [("DoS Hulk", "Hulk"), ("BENIGN", "Benign")]:
    d = im[im.Label == lab]
    rows.append(dict(ban="Bản improved", lop=name, so_flow_tcp=len(d), **{c: float(d[FEATURE_MAP[c]].median()) for c in FEATS}))

out = pd.DataFrame(rows)
out.to_csv(RESULTS / "hulk_profile_friday16.csv", index=False, encoding="utf-8-sig")
print(out.to_string(index=False))
