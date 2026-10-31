"""Bước 8 (chuẩn bị) — tính 1 lần, lưu sẵn ra file: trung vị toàn cục (global_median)
của 78 đặc trưng + số mẫu huấn luyện từng lớp, từ train_set.parquet.

Vì sao tính trước thay vì tính lúc chạy: train_set.parquet có 2,8 triệu dòng, đọc +
tính median mỗi lần server khởi động mất vài giây nhưng không cần làm lại mỗi request.
Hai số này được dùng ở Bước 8 (app/reliability.py):
  - global_median: giá trị "nền" dùng cho faithfulness proxy (xóa Top-k đặc trưng về
    giá trị này rồi hỏi lại model, xem xác suất tấn công tụt bao nhiêu).
  - train_samples_per_class: dùng cho cờ "lớp hiếm" (< rare_class_min_train_samples).

Chạy: python scripts/stage08_compute_train_stats.py  (từ thư mục RQ3_IDS_System/)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import yaml

RQ3_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = RQ3_ROOT.parent
sys.path.insert(0, str(RQ3_ROOT / "app"))


def main():
    with open(RQ3_ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    import joblib
    model = joblib.load(REPO_ROOT / cfg["paths"]["model"])
    feature_names = list(model.feature_names_in_)

    train_path = REPO_ROOT / cfg["paths"]["train_set"]
    print(f"Đọc {train_path} ...")
    df = pd.read_parquet(train_path)
    print(f"  {len(df)} dòng, {len(df.columns)} cột.")

    missing = set(feature_names) - set(df.columns)
    if missing:
        raise SystemExit(f"train_set.parquet thiếu cột model cần: {sorted(missing)}")

    global_median = df[feature_names].median().to_dict()
    train_samples_per_class = df["Label"].value_counts().to_dict()

    out = {
        "global_median": {k: float(v) for k, v in global_median.items()},
        "train_samples_per_class": {k: int(v) for k, v in train_samples_per_class.items()},
    }

    out_path = RQ3_ROOT / "data" / "train_stats.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Đã ghi {out_path}")
    print(f"  Số lớp hiếm (< {cfg['rare_class_min_train_samples']} mẫu): "
          f"{[c for c, n in train_samples_per_class.items() if n < cfg['rare_class_min_train_samples']]}")


if __name__ == "__main__":
    main()
