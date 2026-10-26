"""Ghi bảng ánh xạ đặc trưng và nhãn thành CSV để đối chiếu và đưa vào báo cáo."""
import pandas as pd
from rq4_common import *

oh = pd.read_csv(ORIG_DIR / "Friday-16-02-2018_TrafficForML_CICFlowMeter.csv", nrows=0).columns.tolist()
ih = pd.read_csv(IMPROVED_DIR / "Friday-16-02-2018.csv", nrows=0).columns.tolist()
feat = pd.DataFrame({"stt": range(1, len(FEATURES) + 1), "ten_rq1_csv_goc": FEATURES,
                     "ten_ban_improved": [FEATURE_MAP[f] for f in FEATURES]})
feat["co_trong_csv_goc"] = feat.ten_rq1_csv_goc.isin(oh)
feat["co_trong_improved"] = feat.ten_ban_improved.isin(ih)
feat["doi_ten"] = feat.ten_rq1_csv_goc != feat.ten_ban_improved
feat.to_csv(RESULTS / "mapping_features.csv", index=False, encoding="utf-8-sig")
extra = [c for c in ih if c not in set(feat.ten_ban_improved)]
(RESULTS / "improved_extra_columns.txt").write_text("\n".join(extra), encoding="utf-8")
print("78 đặc trưng:", int(feat.co_trong_csv_goc.sum()), "có ở CSV gốc,", int(feat.co_trong_improved.sum()), "có ở improved,", int(feat.doi_ten.sum()), "phải đổi tên")
print("Cột improved không thuộc 78 đặc trưng:", extra)

import json
lab = json.load(open(RESULTS / "label_counts_scan.json", encoding="utf-8"))
li, lo = lab["i"], lab["o"]
out = []
for k, n in li.items():
    out.append(dict(nhan_improved=k, so_flow_improved=n, nhan_rq1=LABEL_MAP.get(k, ""), xu_ly="giữ" if k in LABEL_MAP else "bỏ"))
pd.DataFrame(out).to_csv(RESULTS / "mapping_labels_improved.csv", index=False, encoding="utf-8-sig")
out2 = [dict(nhan_rq1=k, so_flow_csv_goc=n, trong_13_lop="không" if k in DROPPED_OLD_CLASSES else "có") for k, n in lo.items() if k != "Label"]
pd.DataFrame(out2).to_csv(RESULTS / "mapping_labels_old.csv", index=False, encoding="utf-8-sig")
print(pd.DataFrame(out).to_string(index=False))
