"""Bước 3 đến 5: gán nhãn flow Java lab theo kịch bản, chốt chia train/test theo lượt, lưu bảng cho model.

Nhãn: flow TCP giữa Kali 192.168.11.133 và Ubuntu 192.168.11.134 trên cổng đích của lượt được gán nhãn kịch bản.
Các PCAP HTTP không có request curl hoặc wget (đã kiểm bằng TShark), nên không có traffic kiểm tra lẫn vào.
Flow ngoài cặp máy lab (DHCP, máy Windows) bị tách ra, không dùng. Flow có giá trị không hữu hạn bị loại và ghi lý do.
Không lấy dự đoán của M0 làm nhãn.

Cột cờ: dữ liệu train M0 chỉ có 0/1 ở 12 cột cờ, Java V4 ghi số đếm. Bản chính (presence) đổi cột cờ thành min(số đếm, 1)
cho mọi PCAP; bản đối chứng (raw) giữ nguyên. M0 chỉ tách các cột cờ ở ngưỡng 1 nên đổi này không làm đổi dự đoán của M0
(results/extraction_audit/flag_convention.json).
"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
import sys
sys.path.insert(0, str(ROOT / "RQ4_Retrain_Compare/scripts"))
from rq4_common import FEATURES, FEATURE_MAP  # noqa: E402

SRC = ROOT / "Java_CICFlowMeter_M0_Trial/output/attack_load_report_20261118/M0"
FLAGS = ["Fwd PSH Flags", "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags", "FIN Flag Cnt", "SYN Flag Cnt", "RST Flag Cnt",
         "PSH Flag Cnt", "ACK Flag Cnt", "URG Flag Cnt", "CWE Flag Count", "ECE Flag Cnt"]
KALI, UBU = "192.168.11.133", "192.168.11.134"

# Chia theo lượt, chốt trước khi train: lượt mức tải thấp hơn (thu trước) vào train, lượt còn lại vào test.
# SSH: Hydra train, Patator test (hai công cụ khác nhau). LOIC chỉ có một lượt nên giữ toàn bộ làm test, không bổ sung LOIC vào train.
SPLIT = {"ssh_hydra": "train", "ssh_patator": "test", "goldeneye_l1": "train", "goldeneye_l2": "test",
         "hulkgo_l1": "train", "hulkgo_l2": "test", "slowloris_l1": "train", "slowloris_l2": "test", "loic_http": "test"}
NOTE = {"loic_http": "chỉ một lượt; giữ làm test; LOIC-HTTP không có ví dụ lab trong train",
        "ssh_patator": "khác công cụ với lượt train (Hydra)",
        "goldeneye_l2": "mức tải cao hơn lượt train", "hulkgo_l2": "mức tải cao hơn lượt train", "slowloris_l2": "mức tải cao hơn lượt train"}

man = pd.read_csv(HERE / "manifests/pcaps.csv")
# Hai lượt không được chồng thời gian.
iv = man[["run_id", "start_utc", "end_utc"]].assign(s=lambda d: pd.to_datetime(d.start_utc), e=lambda d: pd.to_datetime(d.end_utc)).sort_values("s")
assert (iv.s.values[1:] > iv.e.values[:-1]).all(), "hai lượt capture chồng thời gian"
assert len(set(man.sha256)) == len(man), "có PCAP trùng nội dung"

parts, rejected, skipped = [], [], []
for m in man.itertuples():
    key = m.pcap.split("/")[-1].replace(".pcapng", "").strip()
    j = pd.read_csv(SRC / f"{key}.pcap_Flow.csv")
    j.columns = j.columns.str.strip()
    lab = j["Src IP"].isin([KALI, UBU]) & j["Dst IP"].isin([KALI, UBU]) & j["Protocol"].eq(6) & (j["Dst Port"].eq(m.target_port) | j["Src Port"].eq(m.target_port))
    skipped.append(dict(run_id=m.run_id, rows_outside_lab_pair=int((~lab).sum())))
    j = j[lab].reset_index(drop=True)
    x = j[[FEATURE_MAP[f] for f in FEATURES]].copy()
    x.columns = FEATURES
    finite = np.isfinite(x.to_numpy(dtype=float)).all(axis=1)
    for i in np.where(~finite)[0]:
        rejected.append(dict(run_id=m.run_id, source_row=int(i), reason="non-finite: " + ",".join(c for c in FEATURES if not np.isfinite(float(x.iloc[i][c])))))
    pk = j["Total Fwd Packet"] + j["Total Bwd packets"]
    meta = pd.DataFrame(dict(
        run_id=m.run_id, scenario=m.scenario, label=m.expected_label, label_source="scenario_verified_ip_port", pcap_sha256=m.sha256,
        split=SPLIT[m.run_id], flow_id=j["Flow ID"], src_ip=j["Src IP"], src_port=j["Src Port"], timestamp=j["Timestamp"],
        packets=pk, starts_from_attacker=j["Src IP"].eq(KALI), short_flow=pk.le(2)))
    parts.append(pd.concat([meta, x], axis=1)[finite])

df = pd.concat(parts, ignore_index=True)
# Bảng theo hai quy ước cờ; cột quản lý không nằm trong 78 đặc trưng.
raw = df.copy()
pres = df.copy()
pres[FLAGS] = pres[FLAGS].clip(upper=1)
(HERE / "data/labeled").mkdir(parents=True, exist_ok=True)
raw.to_parquet(HERE / "data/labeled/lab_flows_raw.parquet", index=False)
pres.to_parquet(HERE / "data/labeled/lab_flows_presence.parquet", index=False)
pd.DataFrame(rejected, columns=["run_id", "source_row", "reason"]).to_csv(HERE / "results/extraction_audit/rejected_flows.csv", index=False)

summ = df.groupby("run_id").agg(flows=("label", "size"), short_flows=("short_flow", "sum"), from_target_side=("starts_from_attacker", lambda s: int((~s).sum())))
sp = man[["run_id", "scenario", "expected_label", "load_from_runbook"]].assign(split=lambda d: d.run_id.map(SPLIT), note=lambda d: d.run_id.map(NOTE).fillna(""))
sp = sp.merge(summ, on="run_id").merge(pd.DataFrame(skipped), on="run_id")
sp.to_csv(HERE / "manifests/splits.csv", index=False, encoding="utf-8")
print(sp.to_string(index=False))
print("rejected", len(rejected))
h = hashlib.sha256(pres[FEATURES].to_numpy().tobytes()).hexdigest()
print("presence feature sha256", h)
