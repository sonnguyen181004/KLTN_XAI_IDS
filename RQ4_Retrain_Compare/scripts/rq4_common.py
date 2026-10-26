"""Hằng số và hàm dùng chung cho RQ4: danh sách 78 đặc trưng, bảng đổi tên giữa CSV gốc và bản improved,
bảng ánh xạ nhãn, và định nghĩa "vùng Hulk" lấy từ cấu hình RQ3 (không gõ cứng ở nơi khác)."""
from __future__ import annotations

import sys
from pathlib import Path

import pyarrow.parquet as pq

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

RQ4 = Path(__file__).resolve().parents[1]
REPO = RQ4.parent
DATA = RQ4 / "data"
MODELS = RQ4 / "models"
RESULTS = RQ4 / "results"
ORIG_DIR = REPO / "dataset" / "CICID-2018_original_csv"
IMPROVED_DIR = REPO / "dataset" / "CSECICIDS2018_improved"
TRAIN_OLD = REPO / "dataset" / "CICID-2018_processed" / "train_set.parquet"
TEST_OLD = REPO / "dataset" / "CICID-2018_processed" / "test_set.parquet"
SEED = 42

# 78 đặc trưng theo đúng thứ tự cột của train_set.parquet (nguồn sự thật của RQ1).
FEATURES = [c for c in pq.read_schema(TRAIN_OLD).names if c != "Label"]

# Tên đặc trưng của RQ1 (CSV gốc) -> tên cột trong bản improved. Cột không có trong bảng giữ nguyên tên.
_RENAME = {
    "Tot Fwd Pkts": "Total Fwd Packet", "Tot Bwd Pkts": "Total Bwd packets",
    "TotLen Fwd Pkts": "Total Length of Fwd Packet", "TotLen Bwd Pkts": "Total Length of Bwd Packet",
    "Flow Byts/s": "Flow Bytes/s", "Flow Pkts/s": "Flow Packets/s",
    "Fwd IAT Tot": "Fwd IAT Total", "Bwd IAT Tot": "Bwd IAT Total",
    "Fwd Header Len": "Fwd Header Length", "Bwd Header Len": "Bwd Header Length",
    "Fwd Pkts/s": "Fwd Packets/s", "Bwd Pkts/s": "Bwd Packets/s", "Pkt Len Var": "Packet Length Variance",
    "CWE Flag Count": "CWR Flag Count", "ECE Flag Cnt": "ECE Flag Count", "Pkt Size Avg": "Average Packet Size",
    "Fwd Seg Size Avg": "Fwd Segment Size Avg", "Bwd Seg Size Avg": "Bwd Segment Size Avg",
    "Fwd Byts/b Avg": "Fwd Bytes/Bulk Avg", "Fwd Pkts/b Avg": "Fwd Packet/Bulk Avg", "Fwd Blk Rate Avg": "Fwd Bulk Rate Avg",
    "Bwd Byts/b Avg": "Bwd Bytes/Bulk Avg", "Bwd Pkts/b Avg": "Bwd Packet/Bulk Avg", "Bwd Blk Rate Avg": "Bwd Bulk Rate Avg",
    "Subflow Fwd Pkts": "Subflow Fwd Packets", "Subflow Fwd Byts": "Subflow Fwd Bytes",
    "Subflow Bwd Pkts": "Subflow Bwd Packets", "Subflow Bwd Byts": "Subflow Bwd Bytes",
    "Init Fwd Win Byts": "FWD Init Win Bytes", "Init Bwd Win Byts": "Bwd Init Win Bytes",
}
for _d in ("Fwd", "Bwd"):
    for _s in ("Max", "Min", "Mean", "Std"):
        _RENAME[f"{_d} Pkt Len {_s}"] = f"{_d} Packet Length {_s}"
for _s in ("Min", "Max", "Mean", "Std"):
    _RENAME[f"Pkt Len {_s}"] = f"Packet Length {_s}"
for _f in ("FIN", "SYN", "RST", "PSH", "ACK", "URG"):
    _RENAME[f"{_f} Flag Cnt"] = f"{_f} Flag Count"
FEATURE_MAP = {f: _RENAME.get(f, f) for f in FEATURES}

# Nhãn bản improved -> nhãn dùng trong RQ1 (13 lớp chung). Nhãn không có trong bảng bị bỏ (Attempted, FTP).
LABEL_MAP = {
    "BENIGN": "Benign", "Botnet Ares": "Bot",
    "DoS Hulk": "DoS attacks-Hulk", "DoS GoldenEye": "DoS attacks-GoldenEye", "DoS Slowloris": "DoS attacks-Slowloris",
    "DDoS-HOIC": "DDOS attack-HOIC", "DDoS-LOIC-HTTP": "DDoS attacks-LOIC-HTTP", "DDoS-LOIC-UDP": "DDOS attack-LOIC-UDP",
    "SSH-BruteForce": "SSH-Bruteforce",
    "Web Attack - Brute Force": "Brute Force -Web", "Web Attack - XSS": "Brute Force -XSS", "Web Attack - SQL": "SQL Injection",
    "Infiltration - NMAP Portscan": "Infilteration", "Infiltration - Communication Victim Attacker": "Infilteration",
    "Infiltration - Dropbox Download": "Infilteration",
}
CLASSES_13 = sorted(set(LABEL_MAP.values()))
DROPPED_OLD_CLASSES = ["FTP-BruteForce", "DoS attacks-SlowHTTPTest"]


def hulk_zone_rule() -> dict:
    """Ngưỡng của vùng ba điều kiện, đọc từ cấu hình RQ3 để không gõ cứng thêm một bản."""
    import yaml
    cfg = yaml.safe_load((REPO / "RQ3_IDS_System" / "config.yaml").read_text(encoding="utf-8"))
    return cfg["hulk_fin_hint"]
