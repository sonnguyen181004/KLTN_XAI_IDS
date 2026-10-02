"""BUOC 3 - Sub-RQ 2.2: Domain Precision@5 cho ca SHAP va LIME tren CUNG cohort.

Dung bang "Expected signals" 15 lop (Bang 8, Ke_Hoach_Thuc_Thi_RQ2_SHAP_LIME_Chi_Tiet.docx)
lam tap dac trung ky vong hop ly ve mien (domain) cho tung loai tan cong/luu luong.
Domain Precision@5 cua mot flow = (so feature trong Top-5 theo |shap_value| hoac |weight|
khop voi tap expected-signals cua LOP THAT cua flow do) / 5.

Tinh rieng cho SHAP va LIME tren CUNG 1.339 flow de so sanh cong bang hai phia, gop theo
true_label (mean, median, N) roi macro-average khong trong so tren 15 lop.

QUAN TRONG - gioi han phuong phap: bang expected-signals la kien thuc mien duoc suy luan
tu co che tan cong (khong phai chuyen gia SOC doc lap cham diem), va van ban goc trong
Bang 8 dung dang rut gon (vi du "Fwd/Packet Len Max/Mean", "Dst Port 80/443"). Script nay
dich rut gon do sang ten cot chinh xac trong 78 feature cua model (DOMAIN_SIGNALS ben
duoi) mot cach RO RANG, co the kiem tra lai; day la doi chieu djnh tinh co cau truc,
KHONG phai ty le "dung" tuyet doi ve mat an ninh mang.

Chay tu goc du an:
    python RQ2_LIME/evaluate_domain.py

Output (RQ2_LIME/rq2_domain/<timestamp>/):
  per_flow_domain_precision.csv  - sample_id, true_label, shap_precision_at_5, lime_precision_at_5, matched features
  summary_by_class.csv           - mean/median/N SHAP vs LIME theo 15 lop
  summary_macro.csv              - macro-average khong trong so tren 15 lop
  domain_signals_used.json       - bang anh xa expected-signals -> ten feature dung de kiem tra lai
  run_info.json
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import platform
import sys

import numpy as np
import pandas as pd


# Anh xa tu Bang 8 (Ke_Hoach_Thuc_Thi_RQ2_SHAP_LIME_Chi_Tiet.docx) sang ten feature CHINH XAC
# trong danh sach 78 feature cua model. Gia tri cu the trong van ban goc (vi du "Dst Port
# 80/443") duoc dich ve TEN COT "Dst Port" (khong kiem tra gia tri cu the, vi Top-5 chi so
# sanh ten feature). Cac muc dang "A/B Len Max/Mean" duoc dich thanh nhieu bien the hop ly
# (vi du ca "Fwd Pkt Len Max" lan "Pkt Len Max") de khong bo sot cach doc hop ly cua ban goc.
DOMAIN_SIGNALS = {
    "Bot": ["Flow IAT Min", "Flow IAT Mean", "Bwd Pkts/s", "Fwd Pkt Len Min", "Dst Port"],
    "Brute Force -Web": ["Dst Port", "Flow Pkts/s", "Flow IAT Min", "Fwd Header Len"],
    "Brute Force -XSS": ["Dst Port", "Fwd Pkt Len Max", "Fwd Pkt Len Mean", "Pkt Len Max", "Pkt Len Mean", "Fwd Header Len"],
    "DDOS attack-HOIC": ["Flow Pkts/s", "Flow Byts/s", "Flow IAT Mean", "Flow IAT Min", "Pkt Len Mean"],
    "DDOS attack-LOIC-UDP": ["Protocol", "Flow Pkts/s", "Pkt Len Std", "Pkt Len Mean", "Flow Duration"],
    "DDoS attacks-LOIC-HTTP": ["Protocol", "Dst Port", "Flow Pkts/s", "Fwd Pkts/s", "Flow IAT Min"],
    "DoS attacks-GoldenEye": ["Dst Port", "Flow Duration", "Flow IAT Std", "Init Fwd Win Byts"],
    "DoS attacks-Hulk": ["Dst Port", "Flow Pkts/s", "Flow IAT Mean", "Fwd Pkt Len Mean"],
    "DoS attacks-SlowHTTPTest": ["Flow Duration", "Flow Byts/s", "Flow Pkts/s", "Flow IAT Mean"],
    "DoS attacks-Slowloris": ["Flow Duration", "Fwd Pkt Len Min", "Flow IAT Mean", "Bwd Pkts/s"],
    "FTP-BruteForce": ["Dst Port", "Protocol", "Fwd PSH Flags", "Flow IAT Min"],
    "SSH-Bruteforce": ["Dst Port", "Protocol", "Pkt Len Std", "Flow IAT Min"],
    "Infilteration": ["Dst Port", "Protocol", "Flow IAT Min", "Flow IAT Mean", "Init Bwd Win Byts", "Flow Duration"],
    "SQL Injection": ["Dst Port", "Fwd Pkt Len Max", "Pkt Len Max", "Flow Duration", "Fwd Header Len"],
    "Benign": ["Dst Port", "Pkt Len Std", "Flow IAT Mean", "Flow Duration"],
}

VALID_FEATURES = {
    "Dst Port", "Protocol", "Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts", "TotLen Fwd Pkts",
    "TotLen Bwd Pkts", "Fwd Pkt Len Max", "Fwd Pkt Len Min", "Fwd Pkt Len Mean", "Fwd Pkt Len Std",
    "Bwd Pkt Len Max", "Bwd Pkt Len Min", "Bwd Pkt Len Mean", "Bwd Pkt Len Std", "Flow Byts/s",
    "Flow Pkts/s", "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min", "Fwd IAT Tot",
    "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min", "Bwd IAT Tot", "Bwd IAT Mean",
    "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min", "Fwd PSH Flags", "Bwd PSH Flags", "Fwd URG Flags",
    "Bwd URG Flags", "Fwd Header Len", "Bwd Header Len", "Fwd Pkts/s", "Bwd Pkts/s", "Pkt Len Min",
    "Pkt Len Max", "Pkt Len Mean", "Pkt Len Std", "Pkt Len Var", "FIN Flag Cnt", "SYN Flag Cnt",
    "RST Flag Cnt", "PSH Flag Cnt", "ACK Flag Cnt", "URG Flag Cnt", "CWE Flag Count", "ECE Flag Cnt",
    "Down/Up Ratio", "Pkt Size Avg", "Fwd Seg Size Avg", "Bwd Seg Size Avg", "Fwd Byts/b Avg",
    "Fwd Pkts/b Avg", "Fwd Blk Rate Avg", "Bwd Byts/b Avg", "Bwd Pkts/b Avg", "Bwd Blk Rate Avg",
    "Subflow Fwd Pkts", "Subflow Fwd Byts", "Subflow Bwd Pkts", "Subflow Bwd Byts",
    "Init Fwd Win Byts", "Init Bwd Win Byts", "Fwd Act Data Pkts", "Fwd Seg Size Min",
    "Active Mean", "Active Std", "Active Max", "Active Min", "Idle Mean", "Idle Std", "Idle Max", "Idle Min",
}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def latest_subdir(root):
    candidates = sorted([p for p in root.iterdir() if p.is_dir()])
    if not candidates:
        raise FileNotFoundError(f"Khong tim thay thu muc con trong {root}")
    return candidates[-1]


def top5(group, value_col):
    return list(group.sort_values(value_col, ascending=False)["feature"].iloc[:5])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--shap-dir", type=Path, default=None)
    parser.add_argument("--lime-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.project.resolve()
    shap_dir = (args.shap_dir or latest_subdir(root / "RQ2_SHAP" / "rq2_paired_cohort")).resolve()
    lime_dir = (args.lime_dir or latest_subdir(root / "RQ2_LIME" / "rq2_lime_paired")).resolve()
    shap_long_path = shap_dir / "shap_per_flow_long.csv"
    lime_long_path = lime_dir / "lime_per_flow_long.csv"
    manifest_path = shap_dir / "manifest_main.csv"
    for p in (shap_long_path, lime_long_path, manifest_path):
        if not p.is_file():
            raise FileNotFoundError(f"Khong thay {p}")

    unknown = {f for sig in DOMAIN_SIGNALS.values() for f in sig if f not in VALID_FEATURES}
    if unknown:
        raise ValueError(f"DOMAIN_SIGNALS co ten feature khong ton tai trong danh sach 78 feature: {unknown}")

    out = (args.output or Path(__file__).resolve().parent / "rq2_domain" /
           datetime.now().strftime("%Y%m%d_%H%M%S_%f")).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Thu muc da co du lieu: {out}. Dung --output khac.")
    out.mkdir(parents=True, exist_ok=True)

    print("[1/3] Nap manifest, SHAP long, LIME long...", flush=True)
    manifest = pd.read_csv(manifest_path)
    shap_long = pd.read_csv(shap_long_path)
    lime_long = pd.read_csv(lime_long_path)

    missing_classes = set(manifest["true_label"].unique()) - set(DOMAIN_SIGNALS)
    if missing_classes:
        raise ValueError(f"Thieu expected-signals cho lop: {missing_classes}")

    print("[2/3] Tinh Top-5 SHAP va Top-5 LIME cho tung flow, doi chieu voi expected-signals cua LOP THAT...", flush=True)
    shap_top5 = shap_long.groupby("sample_id").apply(lambda g: top5(g, "abs_shap_value"), include_groups=False)
    lime_top5 = lime_long.groupby("sample_id").apply(lambda g: top5(g, "abs_weight"), include_groups=False)

    rows = []
    for _, m in manifest.iterrows():
        sid, true_label = m["sample_id"], m["true_label"]
        expected = set(DOMAIN_SIGNALS[true_label])
        s_top5 = shap_top5.loc[sid]
        l_top5 = lime_top5.loc[sid]
        s_matched = [f for f in s_top5 if f in expected]
        l_matched = [f for f in l_top5 if f in expected]
        rows.append(dict(
            sample_id=sid, true_label=true_label, predicted_label=m["predicted_label"],
            n_expected_signals=len(expected),
            shap_top5="|".join(s_top5), shap_matched="|".join(s_matched),
            shap_precision_at_5=len(s_matched) / 5.0,
            lime_top5="|".join(l_top5), lime_matched="|".join(l_matched),
            lime_precision_at_5=len(l_matched) / 5.0,
        ))
    per_flow = pd.DataFrame(rows)
    per_flow.to_csv(out / "per_flow_domain_precision.csv", index=False, encoding="utf-8-sig")

    print("[3/3] Gop theo lop (mean/median/N) va macro-average tren 15 lop...", flush=True)
    class_rows = []
    for label, group in per_flow.groupby("true_label"):
        class_rows.append(dict(
            true_label=label, N=len(group),
            shap_precision_at_5_mean=group["shap_precision_at_5"].mean(),
            shap_precision_at_5_median=group["shap_precision_at_5"].median(),
            lime_precision_at_5_mean=group["lime_precision_at_5"].mean(),
            lime_precision_at_5_median=group["lime_precision_at_5"].median(),
        ))
    summary_by_class = pd.DataFrame(class_rows).sort_values("true_label").reset_index(drop=True)
    summary_by_class.to_csv(out / "summary_by_class.csv", index=False, encoding="utf-8-sig")

    macro = dict(
        n_classes=len(summary_by_class),
        shap_precision_at_5_macro_mean_of_class_means=summary_by_class["shap_precision_at_5_mean"].mean(),
        shap_precision_at_5_macro_mean_of_class_medians=summary_by_class["shap_precision_at_5_median"].mean(),
        lime_precision_at_5_macro_mean_of_class_means=summary_by_class["lime_precision_at_5_mean"].mean(),
        lime_precision_at_5_macro_mean_of_class_medians=summary_by_class["lime_precision_at_5_median"].mean(),
    )
    pd.DataFrame([macro]).to_csv(out / "summary_macro.csv", index=False, encoding="utf-8-sig")
    save_json(out / "domain_signals_used.json", DOMAIN_SIGNALS)

    print(f"\nMacro Domain Precision@5 (khong trong so, 15 lop): "
          f"SHAP={macro['shap_precision_at_5_macro_mean_of_class_means']:.4f} | "
          f"LIME={macro['lime_precision_at_5_macro_mean_of_class_means']:.4f}")
    print(summary_by_class[["true_label", "N", "shap_precision_at_5_mean", "lime_precision_at_5_mean"]].to_string(index=False))

    info = dict(
        status="complete",
        protocol="sub_rq_2_2_domain_precision_at_5_v1",
        shap_dir=str(shap_dir), lime_dir=str(lime_dir),
        n_flow=len(manifest),
        input_sha256={str(p): sha256(p) for p in (shap_long_path, lime_long_path, manifest_path)},
        script_sha256=sha256(Path(__file__)),
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
        limitation="Expected-signals suy tu co che tan cong trong Bang 8 ke hoach, khong phai diem so chuyen gia SOC doc lap.",
    )
    save_json(out / "run_info.json", info)
    print(f"\nHOAN TAT. Ket qua: {out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
