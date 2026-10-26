"""GĐ 5 — Chốt cấu hình LIME trên tập dev.

Thử lưới kernel_width x num_samples x discretize_continuous trên một mẫu con của tập dev
(dev_grid_sample_size flow, lấy ngẫu nhiên có seed cố định từ dev_ids.csv). Quy tắc chọn
CHỈ dựa trên Local R2 (trung vị) và chi phí thời gian — không bao giờ theo mức đồng thuận
với SHAP, để giữ phép so sánh công bằng ở các giai đoạn sau.

Quy tắc chọn (viết ra TRƯỚC khi chạy lưới, không đổi theo kết quả):
  1. Chọn cấu hình có Local R2 trung vị cao nhất.
  2. Nếu hoà (chênh lệch < 1e-3), chọn cấu hình có tổng thời gian thấp hơn.

Nền (background) cho LimeTabularExplainer cố định = mẫu background_sample_size dòng từ
train_set, seed cố định — xem ghi chú trong config.yaml (không đưa vào lưới tìm kiếm).

Sau khi chốt, chạy lại đúng cấu hình đó trên TOÀN BỘ tập dev (250 flow) để có số liệu
chất lượng cuối cùng, rồi ghi `lime.locked_config` vào RQ2/config.yaml.

Đạt khi: có một cấu hình duy nhất + lý do được ghi lại trong report; nếu R2 vẫn thấp thì
ghi nhận đây là giới hạn của LIME trên dữ liệu này, không ép đẹp.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import (  # noqa: E402
    load_config,
    save_config,
    resolve_path,
    latest_run_dir,
    get_logger,
    write_json,
)


def run_lime_batch(explainer_kwargs, num_samples, X_rows, pred_idx, predict_proba_fn, num_features):
    explainer = LimeTabularExplainer(**explainer_kwargs)
    r2s = []
    times = []
    for row, pidx in zip(X_rows, pred_idx):
        t0 = time.time()
        exp = explainer.explain_instance(
            row, predict_proba_fn, num_features=num_features, num_samples=num_samples, labels=[int(pidx)]
        )
        dt = time.time() - t0
        r2 = exp.score[int(pidx)] if isinstance(exp.score, dict) else exp.score
        r2s.append(r2)
        times.append(dt)
    return np.array(r2s), np.array(times)


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage05_lock_lime_config", run_dir)
    out_dir = run_dir / "gd5_lime_dev_tuning"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 5: CHỐT CẤU HÌNH LIME TRÊN TẬP DEV")
    logger.info("=" * 80)

    seed = cfg["seed"]
    rng = np.random.default_rng(seed)

    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    train_df = pd.read_parquet(resolve_path(cfg["paths"]["train_set"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"])).reset_index(drop=True)
    X_test = test_df.drop(columns=["Label"])
    feature_names = list(X_test.columns)
    class_names = list(le.classes_)

    dev_csv = run_dir / "gd3_cohorts" / "dev_ids.csv"
    df_dev = pd.read_csv(dev_csv)
    dev_flow_ids = df_dev["flow_id"].to_numpy()
    logger.info("Nạp %d flow_id từ tập dev: %s", len(dev_flow_ids), dev_csv)

    X_dev_all = X_test.iloc[dev_flow_ids]
    proba_dev_all = model.predict_proba(X_dev_all)
    pred_idx_dev_all = proba_dev_all.argmax(axis=1)

    bg_size = cfg["lime"]["background_sample_size"]
    background = train_df.drop(columns=["Label"]).sample(n=bg_size, random_state=seed).to_numpy()
    logger.info("Background cho LimeTabularExplainer: mẫu %d dòng từ train_set (seed=%d)", bg_size, seed)

    def predict_proba_fn(x):
        df_x = pd.DataFrame(x, columns=feature_names)
        return model.predict_proba(df_x)

    # ---- Grid search on a subsample of the dev set -------------------------------------
    grid_n = min(cfg["lime"]["dev_grid_sample_size"], len(dev_flow_ids))
    grid_sel = rng.choice(len(dev_flow_ids), size=grid_n, replace=False)
    X_grid = X_dev_all.iloc[grid_sel].to_numpy()
    pred_idx_grid = pred_idx_dev_all[grid_sel]
    logger.info("Lưới tìm kiếm trên mẫu con %d / %d flow của tập dev", grid_n, len(dev_flow_ids))

    kw_candidates = cfg["lime"]["kernel_width_candidates"]
    ns_candidates = cfg["lime"]["num_samples_candidates"]
    disc_candidates = cfg["lime"]["discretize_continuous_candidates"]

    grid_results = []
    for kw in kw_candidates:
        for disc in disc_candidates:
            explainer_kwargs = dict(
                training_data=background,
                feature_names=feature_names,
                class_names=class_names,
                discretize_continuous=disc,
                kernel_width=kw,
                random_state=seed,
            )
            for ns in ns_candidates:
                t0 = time.time()
                r2s, times = run_lime_batch(explainer_kwargs, ns, X_grid, pred_idx_grid, predict_proba_fn, cfg["lime"]["num_features"])
                total_dt = time.time() - t0
                median_r2 = float(np.median(r2s))
                mean_r2 = float(np.mean(r2s))
                frac_pass = float((r2s >= cfg["lime"]["local_r2_quality_gate"]).mean())
                grid_results.append({
                    "kernel_width": kw,
                    "discretize_continuous": disc,
                    "num_samples": ns,
                    "median_r2": median_r2,
                    "mean_r2": mean_r2,
                    "frac_r2_pass_gate": frac_pass,
                    "mean_time_sec": float(times.mean()),
                    "total_time_sec": total_dt,
                    "n_flows": grid_n,
                })
                logger.info(
                    "  kw=%-8.3f disc=%-5s ns=%-6d -> median_R2=%.4f mean_R2=%.4f frac>=gate=%.2f%% thời gian=%.1fs",
                    kw, disc, ns, median_r2, mean_r2, frac_pass * 100, total_dt,
                )

    df_grid = pd.DataFrame(grid_results)
    grid_csv = out_dir / "lime_dev_grid_results.csv"
    df_grid.to_csv(grid_csv, index=False, encoding="utf-8-sig")
    logger.info("Đã lưu lưới kết quả: %s", grid_csv)

    # ---- Selection rule (fixed BEFORE looking at results) -------------------------------
    best_r2 = df_grid["median_r2"].max()
    near_best = df_grid[df_grid["median_r2"] >= best_r2 - 1e-3].copy()
    chosen = near_best.sort_values("total_time_sec").iloc[0]
    logger.info(
        "QUY TẮC CHỌN: median_R2 cao nhất (=%.4f), hoà (<1e-3) thì chọn thời gian thấp nhất.", best_r2
    )
    logger.info("Cấu hình được chọn: %s", chosen.to_dict())

    locked = {
        "kernel_width": float(chosen["kernel_width"]),
        "num_samples": int(chosen["num_samples"]),
        "discretize_continuous": bool(chosen["discretize_continuous"]),
        "num_features": cfg["lime"]["num_features"],
        "background_sample_size": bg_size,
        "background_seed": seed,
        "selection_rule": "highest median_r2 on dev-grid-subsample; ties within 1e-3 broken by lowest total_time_sec",
        "dev_grid_sample_size": grid_n,
    }

    # ---- Validate the locked config on the FULL dev set ---------------------------------
    explainer_kwargs_final = dict(
        training_data=background,
        feature_names=feature_names,
        class_names=class_names,
        discretize_continuous=locked["discretize_continuous"],
        kernel_width=locked["kernel_width"],
        random_state=seed,
    )
    t0 = time.time()
    r2s_full, times_full = run_lime_batch(
        explainer_kwargs_final, locked["num_samples"], X_dev_all.to_numpy(), pred_idx_dev_all,
        predict_proba_fn, cfg["lime"]["num_features"],
    )
    full_dt = time.time() - t0
    median_r2_full = float(np.median(r2s_full))
    frac_pass_full = float((r2s_full >= cfg["lime"]["local_r2_quality_gate"]).mean())
    logger.info(
        "Xác nhận cấu hình chốt trên TOÀN BỘ tập dev (%d flow): median_R2=%.4f, frac>=gate=%.2f%%, thời gian=%.1fs",
        len(X_dev_all), median_r2_full, frac_pass_full * 100, full_dt,
    )

    if median_r2_full < cfg["lime"]["local_r2_quality_gate"]:
        logger.warning(
            "Local R2 trung vị trên tập dev (%.4f) THẤP HƠN ngưỡng quality gate (%.2f). "
            "Đây là GIỚI HẠN THỰC SỰ của LIME trên dữ liệu này — không ép đẹp, ghi nhận và tiếp tục.",
            median_r2_full, cfg["lime"]["local_r2_quality_gate"],
        )

    validation_report = {
        "locked_config": locked,
        "full_dev_validation": {
            "n_flows": int(len(X_dev_all)),
            "median_r2": median_r2_full,
            "mean_r2": float(np.mean(r2s_full)),
            "frac_r2_pass_gate": frac_pass_full,
            "mean_time_sec": float(times_full.mean()),
            "total_time_sec": full_dt,
        },
        "grid_best_row": chosen.to_dict(),
    }
    write_json(out_dir / "lime_config_lock_report.json", validation_report)

    # Per-flow dev R2 (for the locked config) — useful reference for GĐ8's quality-gate discussion.
    pd.DataFrame({
        "flow_id": dev_flow_ids,
        "pred_class": le.inverse_transform(pred_idx_dev_all),
        "local_r2": r2s_full,
        "time_sec": times_full,
    }).to_csv(out_dir / "lime_dev_full_scores.csv", index=False, encoding="utf-8-sig")

    # ---- Lock into config.yaml ----------------------------------------------------------
    cfg["lime"]["locked_config"] = locked
    save_config(cfg)
    logger.info("Đã ghi lime.locked_config vào RQ2/config.yaml: %s", locked)

    # Snapshot config at this point into the run dir, per GĐ0's convention.
    import shutil
    shutil.copyfile(Path(__file__).resolve().parents[1] / "config.yaml", run_dir / "config_snapshot_gd5.yaml")

    logger.info("GĐ 5 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
