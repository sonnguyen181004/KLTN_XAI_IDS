"""GĐ 3 — Cohort ghép cặp, tập dev và cohort lỗi.

- Cohort đánh giá: tối đa `cohort.max_per_class` flow dự đoán đúng mỗi lớp (lớp hiếm giữ hết),
  phân tầng theo lớp, seed cố định.
- Tập dev: `cohort.dev_set_size` flow lấy từ phần còn lại (đúng dự đoán, không trùng cohort),
  dùng để chốt cấu hình LIME ở GĐ5.
- Cohort lỗi: toàn bộ flow model dự đoán sai.

flow_id = chỉ số dòng gốc (0-based) trong test_set.parquet — ổn định vì GĐ1 đã xác nhận
test_set.parquet không bị sắp xếp lại giữa các giai đoạn (cùng checksum).

Đạt khi: ba tập không giao nhau; ID được lưu lại.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import (  # noqa: E402
    load_config,
    resolve_path,
    latest_run_dir,
    get_logger,
    write_json,
)


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage03_cohorts", run_dir)
    out_dir = run_dir / "gd3_cohorts"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 3: COHORT GHÉP CẶP, TẬP DEV VÀ COHORT LỖI")
    logger.info("=" * 80)

    seed = cfg["seed"]
    rng = np.random.default_rng(seed)

    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"])).reset_index(drop=True)

    X_test = test_df.drop(columns=["Label"])
    y_true = le.transform(test_df["Label"])
    y_pred = model.predict(X_test)
    flow_id = np.arange(len(test_df))

    true_label = le.inverse_transform(y_true)
    pred_label = le.inverse_transform(y_pred)
    correct_mask = (y_true == y_pred)

    max_per_class = cfg["cohort"]["max_per_class"]
    dev_set_size = cfg["cohort"]["dev_set_size"]
    max_per_class_error = cfg["cohort"]["max_per_class_error"]

    # ---- Cohort đánh giá: stratified, max N per class, seed cố định --------------------
    cohort_ids: list[int] = []
    cohort_rows = []
    for c in range(len(le.classes_)):
        class_name = le.classes_[c]
        pool = flow_id[(y_true == c) & correct_mask]
        if len(pool) <= max_per_class:
            chosen = pool
        else:
            chosen = rng.choice(pool, size=max_per_class, replace=False)
        cohort_ids.extend(chosen.tolist())
        for fid in chosen:
            cohort_rows.append({"flow_id": int(fid), "true_label": class_name, "pred_label": class_name})
        logger.info("Cohort — lớp %-25s: chọn %d / %d flow đúng dự đoán", class_name, len(chosen), len(pool))

    cohort_ids_set = set(cohort_ids)
    df_cohort = pd.DataFrame(cohort_rows).sort_values("flow_id").reset_index(drop=True)

    # ---- Cohort lỗi: stratified theo lớp thật, cap max_per_class_error -----------------
    # (toàn bộ flow sai trong test set là 14,647 — quá lớn để chạy LIME per-flow ở GĐ12;
    # cap theo lớp giữ tính đại diện, cùng quy ước với v1 (CAP_ERROR=20/lớp)).
    error_mask = ~correct_mask
    n_error_total_raw = int(error_mask.sum())
    error_rows = []
    for c in range(len(le.classes_)):
        class_name = le.classes_[c]
        pool = flow_id[(y_true == c) & error_mask]
        if len(pool) == 0:
            continue
        if len(pool) <= max_per_class_error:
            chosen = pool
        else:
            chosen = rng.choice(pool, size=max_per_class_error, replace=False)
        for fid in chosen:
            error_rows.append({
                "flow_id": int(fid),
                "true_label": class_name,
                "pred_label": pred_label[fid],
            })
    df_error = pd.DataFrame(error_rows).sort_values("flow_id").reset_index(drop=True)
    error_ids_set = set(df_error["flow_id"].tolist())
    logger.info(
        "Cohort lỗi: chọn %d / %d flow dự đoán sai (cap %d/lớp theo nhãn thật)",
        len(df_error), n_error_total_raw, max_per_class_error,
    )

    # ---- Tập dev: lấy từ phần còn lại (đúng dự đoán, không trong cohort/lỗi) -------------
    remaining_pool = flow_id[correct_mask & ~np.isin(flow_id, list(cohort_ids_set))]
    # remaining_pool đã loại correct nên tự động không giao với error_ids_set
    if len(remaining_pool) < dev_set_size:
        logger.warning(
            "Pool còn lại (%d) nhỏ hơn dev_set_size (%d) — lấy toàn bộ pool còn lại.",
            len(remaining_pool), dev_set_size,
        )
        dev_chosen = remaining_pool
    else:
        dev_chosen = rng.choice(remaining_pool, size=dev_set_size, replace=False)
    df_dev = pd.DataFrame({
        "flow_id": dev_chosen,
        "true_label": true_label[dev_chosen],
        "pred_label": pred_label[dev_chosen],
    }).sort_values("flow_id").reset_index(drop=True)
    dev_ids_set = set(dev_chosen.tolist())

    dev_class_dist = df_dev["true_label"].value_counts().to_dict()
    logger.info("Tập dev: %d flow. Phân bố lớp: %s", len(df_dev), dev_class_dist)

    # ---- Kiểm tra không giao nhau --------------------------------------------------------
    overlap_cohort_dev = cohort_ids_set & dev_ids_set
    overlap_cohort_error = cohort_ids_set & error_ids_set
    overlap_dev_error = dev_ids_set & error_ids_set
    no_overlap = not overlap_cohort_dev and not overlap_cohort_error and not overlap_dev_error

    logger.info(
        "Kiểm tra không giao nhau — cohort&dev=%d, cohort&error=%d, dev&error=%d -> %s",
        len(overlap_cohort_dev), len(overlap_cohort_error), len(overlap_dev_error), no_overlap,
    )
    if not no_overlap:
        logger.error("GĐ 3 KHÔNG ĐẠT: các tập bị giao nhau.")
        return 1

    cohort_csv = out_dir / "cohort_ids.csv"
    dev_csv = out_dir / "dev_ids.csv"
    error_csv = out_dir / "error_ids.csv"
    df_cohort.to_csv(cohort_csv, index=False, encoding="utf-8-sig")
    df_dev.to_csv(dev_csv, index=False, encoding="utf-8-sig")
    df_error.to_csv(error_csv, index=False, encoding="utf-8-sig")
    logger.info("Đã lưu: %s (%d), %s (%d), %s (%d)", cohort_csv, len(df_cohort), dev_csv, len(df_dev), error_csv, len(df_error))

    summary = {
        "cohort_size": len(df_cohort),
        "cohort_class_distribution": df_cohort["true_label"].value_counts().to_dict(),
        "dev_size": len(df_dev),
        "dev_class_distribution": dev_class_dist,
        "error_cohort_size": len(df_error),
        "error_cohort_class_distribution": df_error["true_label"].value_counts().to_dict(),
        "n_error_total_raw_in_test_set": n_error_total_raw,
        "no_overlap": no_overlap,
        "max_per_class": max_per_class,
        "max_per_class_error": max_per_class_error,
        "dev_set_size_requested": dev_set_size,
        "seed": seed,
    }
    write_json(out_dir / "cohorts_summary.json", summary)

    logger.info("GĐ 3 HOÀN TẤT — cohort=%d, dev=%d, error=%d, không giao nhau=%s",
                len(df_cohort), len(df_dev), len(df_error), no_overlap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
