"""Bước 1: kiểm kê M0 và 9 PCAP tấn công lab. Chỉ đọc, không sửa model hay PCAP.

Ghi manifests/pcaps.csv và results/extraction_audit/inventory.json.
Số packet, stream và thời gian lấy từ audit TShark ngày 18/11 (attack_load_audit_20261118.json)
sau khi kiểm lại mã băm PCAP. Thông tin công cụ lấy từ sổ tay chạy lab, ghi rõ nguồn.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
import xgboost

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
JAVA = ROOT / "Java_CICFlowMeter_M0_Trial"
sys.path.insert(0, str(ROOT / "RQ4_Retrain_Compare/scripts"))
from rq4_common import FEATURES  # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# run_id, file, scenario, tool, mức tải theo sổ tay, cổng đích, nhãn kịch bản dự kiến
RUNS = [
    ("ssh_hydra", "ssbrute.pcapng", "SSH brute force", "Hydra, 1 task", "20 mật khẩu sai", 22, "SSH-Bruteforce"),
    ("ssh_patator", "ss2.pcapng", "SSH brute force", "Patator 1.1.0, 1 thread", "20 ứng viên", 22, "SSH-Bruteforce"),
    ("goldeneye_l1", "dos_oldeney.pcapng", "GoldenEye", "GoldenEye", "mức 1, 30 s", 80, "DoS attacks-GoldenEye"),
    ("goldeneye_l2", "oldeneye2.pcapng", "GoldenEye", "GoldenEye", "mức 2, 30 s", 80, "DoS attacks-GoldenEye"),
    ("hulkgo_l1", "hulk-go.pcapng", "Hulk-Go", "grafov/hulk (Go)", "HULKMAXPROCS=3, 30 s", 80, "DoS attacks-Hulk"),
    ("hulkgo_l2", "hulk2.pcapng", "Hulk-Go", "grafov/hulk (Go)", "HULKMAXPROCS=6, 30 s", 80, "DoS attacks-Hulk"),
    ("slowloris_l1", "slowloris1.pcapng", "Slowloris", "Slowloris (Python)", "mức 1, 60 s", 80, "DoS attacks-Slowloris"),
    ("slowloris_l2", "slowloris2 .pcapng", "Slowloris", "Slowloris (Python)", "mức 2, 60 s", 80, "DoS attacks-Slowloris"),
    ("loic_http", "LOIC.pcapng", "LOIC HTTP", "LOIC (NewEraCracker, Mono)", "Threads=5, Sockets/Thread=25", 80, "DDoS attacks-LOIC-HTTP"),
]

audit = json.load(open(JAVA / "attack_load_audit_20261118.json", encoding="utf-8"))
model_path = ROOT / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl"
enc_path = model_path.with_name("label_encoder.pkl")
model = joblib.load(model_path)
classes = list(joblib.load(enc_path).classes_)

rows = []
for run_id, fname, scen, tool, load, port, label in RUNS:
    p = JAVA / fname
    key = fname.replace(".pcapng", "").strip()
    a = audit["pcaps"][key]
    h = sha(p)
    assert h == a["sha256"], f"{fname}: mã băm khác audit 18/11"
    assert label in classes, label
    rows.append(dict(
        run_id=run_id, pcap=str(p.relative_to(ROOT)).replace("\\", "/"), sha256=h, bytes=p.stat().st_size,
        scenario=scen, tool=tool, load_from_runbook=load, attacker_ip="192.168.11.133", target_ip="192.168.11.134",
        target_port=port, lab_tcp_packets=a["lab_tcp_packets"], tcp_streams=a["tcp_streams"],
        start_utc=datetime.fromtimestamp(a["first_epoch"], timezone.utc).isoformat(timespec="seconds"),
        end_utc=datetime.fromtimestamp(a["last_epoch"], timezone.utc).isoformat(timespec="seconds"),
        span_s=round(a["span_seconds"], 2), http_requests=a["http_requests"], expected_label=label,
        evidence="Java_CICFlowMeter_M0_Trial/attack_load_audit_20261118.json; README so tay 18/11",
    ))
pd.DataFrame(rows).to_csv(HERE / "manifests/pcaps.csv", index=False, encoding="utf-8")

train_cols = pd.read_parquet(ROOT / "dataset/CICID-2018_processed/train_set.parquet", columns=None).columns.tolist()
inv = dict(
    model=dict(path=str(model_path.relative_to(ROOT)), sha256=sha(model_path), encoder_sha256=sha(enc_path),
               classes=classes, n_classes=len(classes), params={k: v for k, v in model.get_params().items() if v is not None and k != "missing"},
               boosted_rounds=model.get_booster().num_boosted_rounds()),
    features=dict(n=len(FEATURES), model_order_equals_rq4_list=list(model.feature_names_in_) == FEATURES,
                  train_parquet_order_equals_model=[c for c in train_cols if c != "Label"] == list(model.feature_names_in_)),
    libraries=dict(python=sys.version.split()[0], xgboost=xgboost.__version__, sklearn=sklearn.__version__, pandas=pd.__version__),
    train_script="RQ1_Model_Training_xboost/2_train_optimal_model.py (n_estimators=100, max_depth=8, lr=0.08, hist, seed 42; X = train_set.parquet bỏ cột Label, không chuẩn hóa)",
    java_extractor=dict(path="Java_CICFlowMeter_M0_Trial/upstream", commit="98a5eba", profile="m0-current-unverified"),
)
json.dump(inv, open(HERE / "results/extraction_audit/inventory.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(pd.DataFrame(rows)[["run_id", "lab_tcp_packets", "tcp_streams", "span_s", "expected_label"]].to_string(index=False))
print(json.dumps(inv["features"]), inv["model"]["boosted_rounds"], inv["libraries"])
