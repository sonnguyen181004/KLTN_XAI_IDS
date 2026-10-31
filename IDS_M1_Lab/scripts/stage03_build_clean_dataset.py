"""Bước 3 — Tạo Tập B: một tập flow "sạch" để demo/test hệ thống, đảm bảo
KHÔNG CÓ dòng nào trùng với train_set (nên model chắc chắn chưa từng thấy dưới
bất kỳ hình thức nào — khác với Tập A/cohort RQ2, vốn chỉ đảm bảo nằm trong
test_set nhưng không loại trừ việc một số dòng bị trùng với train do lỗi lấy
mẫu gốc của CSE-CIC-IDS2018, ~27,7% dòng — đã ghi nhận ở RQ2 GĐ1).

Cách làm:
  1. Băm (hash) 78 cột đặc trưng của train_set và test_set.
  2. Loại khỏi test_set mọi dòng có hash trùng với bất kỳ dòng nào trong train_set.
  3. Trên phần còn lại ("sạch"), lấy mẫu phân tầng theo lớp (seed cố định),
     tối đa `max_per_class` dòng/lớp, tới khi đủ khoảng `target_size` dòng.
  4. Lưu ra CSV kèm cột `label_true` (chỉ để TỰ so sánh sau — hệ thống sẽ KHÔNG
     gửi cột này vào model lúc dự đoán, xem lưu ý ở đầu plan.md mục 1.1).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config() -> dict:
    with open(Path(__file__).resolve().parents[1] / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    cfg = load_config()
    seed = cfg["seed"]
    cds = cfg["clean_dataset"]
    target_size = cds["target_size"]
    max_per_class = cds["max_per_class"]

    print("=" * 70)
    print("BƯỚC 3: TẠO TẬP B — DỮ LIỆU SẠCH (LOẠI TRÙNG TRAIN/TEST)")
    print("=" * 70)

    train_path = REPO_ROOT / cfg["paths"]["train_set"]
    test_path = REPO_ROOT / cfg["paths"]["test_set"]
    out_path = REPO_ROOT / cfg["paths"]["clean_set_out"]

    print(f"Nạp train_set: {train_path}")
    train_df = pd.read_parquet(train_path)
    print(f"Nạp test_set:  {test_path}")
    test_df = pd.read_parquet(test_path)
    print(f"  -> train: {len(train_df)} dòng, test: {len(test_df)} dòng")

    feature_cols = [c for c in test_df.columns if c != "Label"]
    assert len(feature_cols) == cfg["n_features_expected"], (
        f"Số đặc trưng ({len(feature_cols)}) khác kỳ vọng ({cfg['n_features_expected']})"
    )

    # ---- Bước băm để tìm dòng trùng (cùng cách RQ2 GĐ1 đã làm) ----------------
    print("\nĐang băm 78 cột đặc trưng để tìm dòng test trùng với train...")
    train_hashes = pd.util.hash_pandas_object(train_df[feature_cols], index=False)
    test_hashes = pd.util.hash_pandas_object(test_df[feature_cols], index=False)
    train_hash_set = set(train_hashes.to_numpy().tolist())
    is_duplicate = test_hashes.isin(train_hash_set).to_numpy()
    n_dup = int(is_duplicate.sum())
    print(f"  -> {n_dup} / {len(test_df)} dòng test ({n_dup/len(test_df)*100:.2f}%) trùng với train "
          "-> sẽ LOẠI BỎ khỏi Tập B.")

    clean_df = test_df.loc[~is_duplicate].reset_index(drop=True)
    print(f"  -> Còn lại {len(clean_df)} dòng test 'sạch' (chưa từng xuất hiện ở train).")

    # ---- Lấy mẫu phân tầng theo lớp -------------------------------------------
    rng = np.random.default_rng(seed)
    classes = sorted(clean_df["Label"].unique())
    n_classes = len(classes)
    # Chia đều mục tiêu cho các lớp, nhưng không vượt quá max_per_class và
    # không vượt quá số dòng sạch thật sự có của lớp đó.
    per_class_target = max(1, target_size // n_classes)

    rows = []
    print(f"\nLấy mẫu phân tầng (mục tiêu ~{target_size} dòng, tối đa {max_per_class}/lớp, "
          f"seed={seed}):")
    for cls in classes:
        pool = clean_df.index[clean_df["Label"] == cls].to_numpy()
        n_take = min(len(pool), max_per_class, max(per_class_target, 1))
        if len(pool) <= n_take:
            chosen = pool
        else:
            chosen = rng.choice(pool, size=n_take, replace=False)
        rows.append(clean_df.loc[chosen])
        print(f"  {cls:30s}: lấy {len(chosen):4d} / {len(pool):6d} dòng sạch có sẵn")

    sample_df = pd.concat(rows, ignore_index=True)
    sample_df = sample_df.rename(columns={"Label": "label_true"})
    sample_df.insert(0, "flow_id", [f"CLEAN-{i:05d}" for i in range(len(sample_df))])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sample_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\nTổng cộng Tập B: {len(sample_df)} dòng, {sample_df['label_true'].nunique()} lớp.")
    print(f"Đã lưu: {out_path}")

    # ---- Tự kiểm tra: không dòng nào trong Tập B trùng train -------------------
    print("\nTự kiểm tra lại: băm 78 cột của Tập B, đối chiếu với train_set...")
    sample_hashes = pd.util.hash_pandas_object(sample_df[feature_cols], index=False)
    still_dup = sample_hashes.isin(train_hash_set).sum()
    if still_dup > 0:
        print(f"  [FAIL] Vẫn còn {still_dup} dòng trùng train trong Tập B!")
        return 1
    print(f"  [PASS] 0/{len(sample_df)} dòng của Tập B trùng với train_set — "
          "model CHẮC CHẮN chưa từng thấy các dòng này.")

    print("\n" + "=" * 70)
    print("BƯỚC 3 HOÀN TẤT.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
