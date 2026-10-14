"""Bước 9 (chuẩn bị) — lấy sẵn 2.000 dòng nền cho LIME từ train_set.parquet, đúng
`background_sample_size`/`background_seed` đã khóa ở RQ2 (`config.yaml: lime.*`), lưu ra
file nhỏ để server không phải đọc lại 2,8 triệu dòng mỗi lần khởi động.

Chạy: python scripts/stage09_compute_lime_background.py  (từ thư mục RQ3_IDS_System/)
"""
from __future__ import annotations

import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import yaml

RQ3_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = RQ3_ROOT.parent


def main():
    with open(RQ3_ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    import joblib
    model = joblib.load(REPO_ROOT / cfg["paths"]["model"])
    feature_names = list(model.feature_names_in_)

    train_path = REPO_ROOT / cfg["paths"]["train_set"]
    print(f"Đọc {train_path} ...")
    df = pd.read_parquet(train_path, columns=feature_names)
    print(f"  {len(df)} dòng.")

    lime_cfg = cfg["lime"]
    background = df.sample(n=lime_cfg["background_sample_size"], random_state=lime_cfg["background_seed"])
    arr = background.to_numpy(dtype=np.float64)

    out_path = RQ3_ROOT / "data" / "lime_background.npy"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_path, arr)
    print(f"Đã ghi {out_path}: shape={arr.shape} "
          f"(kỳ vọng ({lime_cfg['background_sample_size']}, {len(feature_names)}))")


if __name__ == "__main__":
    main()
