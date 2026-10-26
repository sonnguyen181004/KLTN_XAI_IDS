"""GĐ 2 — SHAP toàn cục trên toàn test set.

Định nghĩa: với mỗi lớp c, lấy các flow thật sự thuộc lớp c và được dự đoán đúng là c,
rồi lấy SHAP của đầu ra lớp c (margin space, khớp model.get_booster().predict(output_margin=True)).

Chỉ lưu giá trị tổng hợp theo lớp (mean |phi| và mean phi có dấu) — không lưu SHAP thô của
700k x 78 x 15 giá trị (~3GB). Additivity được kiểm tra trên một mẫu con ngẫu nhiên.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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

CHUNK_SIZE = 20000
ADDITIVITY_SAMPLE_SIZE = 300


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage02_shap_global", run_dir)
    out_dir = run_dir / "gd2_shap_global"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 2: SHAP TOÀN CỤC TRÊN TOÀN TEST SET")
    logger.info("=" * 80)

    seed = cfg["seed"]
    rng = np.random.default_rng(seed)

    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"]))

    X_test = test_df.drop(columns=["Label"])
    y_test = le.transform(test_df["Label"])
    y_pred = model.predict(X_test)
    feature_names = list(X_test.columns)
    n_classes = len(le.classes_)

    logger.info("Tổng %d flow, %d lớp, %d đặc trưng", len(X_test), n_classes, len(feature_names))

    explainer = shap.TreeExplainer(model)

    rows = []
    top5_rows = []

    for c in range(n_classes):
        class_name = le.classes_[c]
        mask = (y_test == c) & (y_pred == c)
        n_flows = int(mask.sum())
        if n_flows == 0:
            logger.warning("Lớp %s: không có flow nào dự đoán đúng — bỏ qua.", class_name)
            continue

        X_c = X_test.loc[mask]
        sum_abs = np.zeros(len(feature_names))
        sum_signed = np.zeros(len(feature_names))

        t0 = time.time()
        n_done = 0
        for start in range(0, n_flows, CHUNK_SIZE):
            chunk = X_c.iloc[start:start + CHUNK_SIZE]
            exp = explainer(chunk, check_additivity=False)
            vals_c = exp.values[:, :, c]
            sum_abs += np.abs(vals_c).sum(axis=0)
            sum_signed += vals_c.sum(axis=0)
            n_done += len(chunk)
        dt = time.time() - t0

        mean_abs = sum_abs / n_flows
        mean_signed = sum_signed / n_flows

        for feat, ma, ms in zip(feature_names, mean_abs, mean_signed):
            rows.append({
                "class": class_name,
                "feature": feat,
                "mean_abs_shap": ma,
                "mean_signed_shap": ms,
                "n_flows": n_flows,
            })

        order = np.argsort(-mean_abs)[:5]
        for rank, idx in enumerate(order, start=1):
            top5_rows.append({
                "class": class_name,
                "rank": rank,
                "feature": feature_names[idx],
                "mean_abs_shap": mean_abs[idx],
                "mean_signed_shap": mean_signed[idx],
                "n_flows": n_flows,
            })

        logger.info(
            "Lớp %-25s n_flows=%6d  thời gian=%.1fs (%.0f flow/s)  Top1=%s",
            class_name, n_flows, dt, n_flows / dt if dt > 0 else float("nan"),
            feature_names[order[0]],
        )

    df_all = pd.DataFrame(rows)
    df_top5 = pd.DataFrame(top5_rows)

    all_csv = out_dir / "rq2_shap_global_feature_importance_by_class.csv"
    top5_csv = out_dir / "rq2_shap_global_top5_by_class.csv"
    df_all.to_csv(all_csv, index=False, encoding="utf-8-sig")
    df_top5.to_csv(top5_csv, index=False, encoding="utf-8-sig")
    logger.info("Đã lưu: %s, %s", all_csv, top5_csv)

    # ---- Charts: Top-5 |phi| per class, colored by sign of mean_signed ----------------
    charts_dir = out_dir / "figures"
    charts_dir.mkdir(parents=True, exist_ok=True)
    for class_name in df_top5["class"].unique():
        sub = df_top5[df_top5["class"] == class_name].sort_values("mean_abs_shap")
        colors = ["#d62728" if v >= 0 else "#1f77b4" for v in sub["mean_signed_shap"]]
        fig, ax = plt.subplots(figsize=(6, 3.2))
        ax.barh(sub["feature"], sub["mean_abs_shap"], color=colors)
        ax.set_xlabel("mean |SHAP value| (margin)")
        ax.set_title(f"Top-5 SHAP — {class_name}\n(đỏ = đóng góp dương trung bình, xanh = âm)")
        fig.tight_layout()
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in class_name)
        fig.savefig(charts_dir / f"top5_{safe_name}.png", dpi=150)
        plt.close(fig)
    logger.info("Đã lưu %d biểu đồ Top-5 vào %s", df_top5["class"].nunique(), charts_dir)

    # ---- Additivity check on a random subsample ----------------------------------------
    sample_idx = rng.choice(len(X_test), size=min(ADDITIVITY_SAMPLE_SIZE, len(X_test)), replace=False)
    X_sample = X_test.iloc[sample_idx]
    exp_sample = explainer(X_sample, check_additivity=False)
    booster = model.get_booster()
    dm = xgb.DMatrix(X_sample, feature_names=feature_names)
    margin = booster.predict(dm, output_margin=True)
    recon = np.array(exp_sample.base_values) + exp_sample.values.sum(axis=1)
    err = np.abs(recon - margin)
    additivity_report = {
        "sample_size": int(len(X_sample)),
        "max_abs_error": float(err.max()),
        "mean_abs_error": float(err.mean()),
    }
    write_json(out_dir / "rq2_shap_global_additivity_report.json", additivity_report)
    logger.info("Additivity trên mẫu %d flow: max_err=%.3e, mean_err=%.3e", len(X_sample), err.max(), err.mean())

    logger.info("GĐ 2 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
