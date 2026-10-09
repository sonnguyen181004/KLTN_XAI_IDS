"""GĐ 1 — Kiểm tra dữ liệu, model và môi trường.

Kiểm tra bắt buộc (dừng nếu không đạt):
  - test_set.parquet có đúng 78 đặc trưng + cột Label.
  - Thứ tự đặc trưng khớp model XGBoost; label encoder khớp 15 lớp.
  - Model nạp được; không còn NaN/Inf trong X_test.
  - F1/Precision (macro) trên test khớp RQ1 trong sai số cho phép.
  - Kiểm tra dòng trùng giữa train và test.
  - Lưu checksum model/encoder/train/test.

Đầu ra: run_info.json, feature_schema.json, checksums.json, verification_report.json
Thoát mã != 0 nếu bất kỳ kiểm tra bắt buộc nào không đạt -> các giai đoạn sau không được chạy.
"""
from __future__ import annotations

import importlib.metadata as im
import platform
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import (  # noqa: E402
    RQ2_DIR,
    load_config,
    resolve_path,
    latest_run_dir,
    get_logger,
    sha256_of_file,
    git_commit_hash,
    write_json,
)


def pkg_version(name: str) -> str:
    try:
        return im.version(name)
    except Exception:
        return "unknown"


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage01_verify_env", run_dir)
    out_dir = run_dir / "gd1_env_check"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 1: KIỂM TRA DỮ LIỆU, MODEL VÀ MÔI TRƯỜNG")
    logger.info("=" * 80)

    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    # ---- Environment versions -------------------------------------------------
    env_versions = {
        "python": platform.python_version(),
        "xgboost": pkg_version("xgboost"),
        "shap": pkg_version("shap"),
        "lime": pkg_version("lime"),
        "scikit-learn": pkg_version("scikit-learn"),
        "pandas": pkg_version("pandas"),
        "numpy": pkg_version("numpy"),
        "scipy": pkg_version("scipy"),
        "pyarrow": pkg_version("pyarrow"),
    }
    logger.info("Phiên bản môi trường: %s", env_versions)
    details["env_versions"] = env_versions

    # ---- Load artifacts ---------------------------------------------------------
    model_path = resolve_path(cfg["paths"]["model"])
    encoder_path = resolve_path(cfg["paths"]["label_encoder"])
    train_path = resolve_path(cfg["paths"]["train_set"])
    test_path = resolve_path(cfg["paths"]["test_set"])

    t0 = time.time()
    model = joblib.load(model_path)
    le = joblib.load(encoder_path)
    logger.info("Nạp model + label encoder trong %.2fs", time.time() - t0)

    checks["model_loads"] = True

    t0 = time.time()
    test_df = pd.read_parquet(test_path)
    logger.info("Nạp test_set.parquet (%d dòng) trong %.2fs", len(test_df), time.time() - t0)

    # ---- 78 features + Label ----------------------------------------------------
    n_expected = cfg["n_features_expected"]
    cols = list(test_df.columns)
    has_label = "Label" in cols
    n_features_actual = len(cols) - (1 if has_label else 0)
    checks["test_set_78_features_plus_label"] = has_label and n_features_actual == n_expected
    details["test_set_shape"] = {"rows": len(test_df), "cols": len(cols), "n_features": n_features_actual}
    logger.info(
        "test_set.parquet: %d dòng, %d cột (%d đặc trưng + Label=%s) -> %s",
        len(test_df), len(cols), n_features_actual, has_label, checks["test_set_78_features_plus_label"],
    )

    X_test = test_df.drop(columns=["Label"])
    y_test_raw = test_df["Label"]

    # ---- Feature order matches model ---------------------------------------------
    model_feature_names = list(getattr(model, "feature_names_in_", []))
    data_feature_names = list(X_test.columns)
    order_matches = model_feature_names == data_feature_names
    checks["feature_order_matches_model"] = order_matches
    details["feature_order_mismatch_sample"] = (
        None if order_matches else list(zip(model_feature_names[:5], data_feature_names[:5]))
    )
    logger.info("Thứ tự đặc trưng khớp model: %s", order_matches)

    # ---- Label encoder has 15 classes --------------------------------------------
    n_classes_expected = cfg["n_classes_expected"]
    checks["label_encoder_15_classes"] = len(le.classes_) == n_classes_expected
    details["label_encoder_classes"] = list(le.classes_)
    logger.info("Label encoder: %d lớp (kỳ vọng %d) -> %s", len(le.classes_), n_classes_expected, checks["label_encoder_15_classes"])

    # ---- NaN / Inf check -----------------------------------------------------------
    n_nan = int(X_test.isna().sum().sum())
    n_inf = int(np.isinf(X_test.select_dtypes(include=[np.number]).to_numpy()).sum())
    checks["no_nan_inf_in_test"] = (n_nan == 0 and n_inf == 0)
    details["nan_inf_counts"] = {"n_nan": n_nan, "n_inf": n_inf}
    logger.info("NaN=%d, Inf=%d trong X_test -> %s", n_nan, n_inf, checks["no_nan_inf_in_test"])

    # ---- Run model, compare to RQ1 reference metrics --------------------------------
    y_test = le.transform(y_test_raw)
    t0 = time.time()
    y_pred = model.predict(X_test)
    predict_duration = time.time() - t0
    logger.info("Dự đoán %d dòng trong %.2fs", len(X_test), predict_duration)

    acc = accuracy_score(y_test, y_pred) * 100
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="macro", zero_division=0)
    prec, rec, f1 = prec * 100, rec * 100, f1 * 100

    ref = cfg["rq1_reference_metrics"]
    tol = cfg["tolerance_pct_points"]
    deltas = {
        "accuracy_pct": abs(acc - ref["accuracy_pct"]),
        "macro_precision_pct": abs(prec - ref["macro_precision_pct"]),
        "macro_recall_pct": abs(rec - ref["macro_recall_pct"]),
        "macro_f1_pct": abs(f1 - ref["macro_f1_pct"]),
    }
    metrics_match = all(d <= tol for d in deltas.values())
    checks["metrics_match_rq1"] = metrics_match
    details["metrics_rerun"] = {
        "accuracy_pct": round(acc, 4),
        "macro_precision_pct": round(prec, 4),
        "macro_recall_pct": round(rec, 4),
        "macro_f1_pct": round(f1, 4),
    }
    details["metrics_rq1_reference"] = ref
    details["metrics_deltas_pct_points"] = {k: round(v, 4) for k, v in deltas.items()}
    logger.info("Kết quả chạy lại: %s", details["metrics_rerun"])
    logger.info("RQ1 tham chiếu: %s | sai lệch: %s (ngưỡng %.2f) -> %s", ref, details["metrics_deltas_pct_points"], tol, metrics_match)

    # ---- Duplicate rows between train and test ---------------------------------------
    t0 = time.time()
    train_df = pd.read_parquet(train_path)
    feature_cols = [c for c in test_df.columns if c != "Label"]
    train_hashes = pd.util.hash_pandas_object(train_df[feature_cols], index=False)
    test_hashes = pd.util.hash_pandas_object(test_df[feature_cols], index=False)
    train_hash_set = set(train_hashes.to_numpy().tolist())
    n_dup = int(test_hashes.isin(train_hash_set).sum())
    dup_frac = n_dup / len(test_df)
    logger.info(
        "Dòng trùng (theo hash 78 đặc trưng) giữa train (%d dòng) và test (%d dòng): %d (%.4f%%) — %.2fs",
        len(train_df), len(test_df), n_dup, dup_frac * 100, time.time() - t0,
    )
    details["train_test_duplicate_rows"] = {"n_duplicates": n_dup, "fraction": round(dup_frac, 6)}
    # Không phải quality gate cứng (biết trước CSE-CIC-IDS2018 có trùng) — chỉ ghi nhận, không chặn.
    checks["duplicate_check_recorded"] = True

    # ---- Checksums -----------------------------------------------------------------
    checksums = {
        "model": sha256_of_file(model_path),
        "label_encoder": sha256_of_file(encoder_path),
        "train_set": sha256_of_file(train_path),
        "test_set": sha256_of_file(test_path),
    }
    logger.info("Checksums: %s", checksums)
    write_json(out_dir / "checksums.json", checksums)

    # ---- feature_schema.json ---------------------------------------------------------
    feature_schema = {
        "n_features": len(data_feature_names),
        "order": data_feature_names,
        "dtypes": {c: str(X_test[c].dtype) for c in data_feature_names},
    }
    write_json(out_dir / "feature_schema.json", feature_schema)

    # ---- run_info.json ------------------------------------------------------------
    run_info = {
        "seed": cfg["seed"],
        "git_commit": git_commit_hash(),
        "machine": platform.node(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "timestamp": pd.Timestamp.now().isoformat(),
        "env_versions": env_versions,
    }
    write_json(out_dir / "run_info.json", run_info)

    # ---- Final verification report --------------------------------------------------
    all_required_pass = (
        checks["model_loads"]
        and checks["test_set_78_features_plus_label"]
        and checks["feature_order_matches_model"]
        and checks["label_encoder_15_classes"]
        and checks["no_nan_inf_in_test"]
        and checks["metrics_match_rq1"]
    )
    report = {"checks": checks, "details": details, "GATE_PASS": all_required_pass}
    write_json(out_dir / "verification_report.json", report)

    logger.info("-" * 80)
    for k, v in checks.items():
        logger.info("  [%s] %s", "PASS" if v else "FAIL", k)
    logger.info("-" * 80)
    if all_required_pass:
        logger.info("GĐ 1 ĐẠT — có thể tiếp tục GĐ 2.")
        return 0
    else:
        logger.error("GĐ 1 KHÔNG ĐẠT — DỪNG, không chạy các giai đoạn sau.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
