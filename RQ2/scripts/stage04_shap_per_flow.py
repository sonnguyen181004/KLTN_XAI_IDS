"""GĐ 4 — SHAP per-flow trên cohort.

Với mỗi flow trong cohort_ids.csv (GĐ3), XGBoost dự đoán lớp nào thì SHAP giải thích đúng
lớp đó (margin space, cùng cách tính như GĐ2). Lưu đủ 78 giá trị SHAP, base value, xác suất
dự đoán, thời gian chạy từng flow; rút Top-1/3/5/10.

Đạt khi: additivity đúng trên từng flow; ID flow khớp cohort_ids.csv.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb

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
    logger = get_logger("stage04_shap_per_flow", run_dir)
    out_dir = run_dir / "gd4_shap_per_flow"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 4: SHAP PER-FLOW TRÊN COHORT")
    logger.info("=" * 80)

    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"])).reset_index(drop=True)
    X_test = test_df.drop(columns=["Label"])
    feature_names = list(X_test.columns)

    cohort_csv = run_dir / "gd3_cohorts" / "cohort_ids.csv"
    df_cohort = pd.read_csv(cohort_csv)
    flow_ids = df_cohort["flow_id"].to_numpy()
    logger.info("Nạp %d flow_id từ %s", len(flow_ids), cohort_csv)

    X_cohort = X_test.iloc[flow_ids]
    proba_cohort = model.predict_proba(X_cohort)
    pred_idx_cohort = proba_cohort.argmax(axis=1)
    pred_label_cohort = le.inverse_transform(pred_idx_cohort)

    # Sanity: predicted label from model must match cohort's recorded pred_label (GĐ3 used
    # the same model/test_set, so this should be an exact match — if not, cohort is stale).
    mismatch = (pred_label_cohort != df_cohort["pred_label"].to_numpy()).sum()
    if mismatch > 0:
        logger.error("LỆCH %d/%d flow giữa dự đoán hiện tại và cohort_ids.csv — DỪNG.", mismatch, len(df_cohort))
        return 1

    explainer = shap.TreeExplainer(model)
    booster = model.get_booster()

    long_rows = []
    topk_rows = []
    additivity_errors = []
    flow_times = []

    CHUNK = 200
    n = len(X_cohort)
    for start in range(0, n, CHUNK):
        end = min(start + CHUNK, n)
        chunk_X = X_cohort.iloc[start:end]
        chunk_ids = flow_ids[start:end]
        chunk_pred_idx = pred_idx_cohort[start:end]
        chunk_proba = proba_cohort[start:end]

        t0 = time.time()
        exp = explainer(chunk_X, check_additivity=False)
        dt = time.time() - t0
        per_row_time = dt / len(chunk_X)

        dm = xgb.DMatrix(chunk_X, feature_names=feature_names)
        margin = booster.predict(dm, output_margin=True)

        for i in range(len(chunk_X)):
            fid = int(chunk_ids[i])
            c = int(chunk_pred_idx[i])
            class_name = le.classes_[c]
            phi = exp.values[i, :, c]
            base = float(np.array(exp.base_values)[i, c])
            recon = base + phi.sum()
            add_err = abs(recon - margin[i, c])
            additivity_errors.append(add_err)
            flow_times.append(per_row_time)

            for feat, val, shap_val in zip(feature_names, chunk_X.iloc[i].to_numpy(), phi):
                long_rows.append({
                    "flow_id": fid,
                    "pred_class": class_name,
                    "feature": feat,
                    "feature_value": val,
                    "shap_value": shap_val,
                })

            order = np.argsort(-np.abs(phi))
            for k in (1, 3, 5, 10):
                top_feats = [feature_names[j] for j in order[:k]]
                top_vals = [float(phi[j]) for j in order[:k]]
                topk_rows.append({
                    "flow_id": fid,
                    "pred_class": class_name,
                    "k": k,
                    "top_features": ";".join(top_feats),
                    "top_shap_values": ";".join(f"{v:.6g}" for v in top_vals),
                    "base_value": base,
                    "pred_proba": float(chunk_proba[i, c]),
                    "additivity_error": add_err,
                    "time_sec": per_row_time,
                })

        if (start // CHUNK) % 3 == 0:
            logger.info("  ... %d / %d flow xử lý", end, n)

    df_long = pd.DataFrame(long_rows)
    df_topk = pd.DataFrame(topk_rows)

    long_csv = out_dir / "shap_per_flow_long.csv"
    topk_csv = out_dir / "shap_per_flow_topk.csv"
    df_long.to_csv(long_csv, index=False, encoding="utf-8-sig")
    df_topk.to_csv(topk_csv, index=False, encoding="utf-8-sig")

    additivity_errors = np.array(additivity_errors)
    flow_times = np.array(flow_times)
    report = {
        "n_flows": int(n),
        "additivity_max_error": float(additivity_errors.max()),
        "additivity_mean_error": float(additivity_errors.mean()),
        "time_mean_sec_per_flow": float(flow_times.mean()),
        "time_total_sec": float(flow_times.sum()),
        "flow_ids_match_cohort": bool(set(flow_ids.tolist()) == set(df_cohort["flow_id"].tolist())),
    }
    write_json(out_dir / "shap_per_flow_report.json", report)

    logger.info("Đã lưu: %s (%d dòng), %s (%d dòng)", long_csv, len(df_long), topk_csv, len(df_topk))
    logger.info("Additivity: max=%.3e mean=%.3e | thời gian TB/flow=%.4fs", report["additivity_max_error"], report["additivity_mean_error"], report["time_mean_sec_per_flow"])
    logger.info("GĐ 4 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
