"""GĐ 6 — LIME per-flow trên đúng cohort (dùng cấu hình đã khóa ở GĐ5).

- Dùng cấu hình `lime.locked_config` trong config.yaml (KHÔNG đổi ở đây).
- Cùng predict_proba, cùng nhãn dự đoán như GĐ4 (SHAP), num_features=78.
- random_state cố định THEO TỪNG FLOW (seed + flow_id) để có thể tái lập độc lập mỗi flow,
  khác với stability test ở GĐ9 (seed thay đổi có chủ đích).

Đạt khi: ID flow khớp tuyệt đối với GĐ4; không flow nào thiếu; thời gian được ghi lại.
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
    resolve_path,
    latest_run_dir,
    get_logger,
    write_json,
    set_lime_explainer_seed,
)


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage06_lime_per_flow", run_dir)
    out_dir = run_dir / "gd6_lime_per_flow"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 6: LIME PER-FLOW TRÊN COHORT (CẤU HÌNH ĐÃ KHÓA)")
    logger.info("=" * 80)

    locked = cfg["lime"]["locked_config"]
    if not locked:
        logger.error("lime.locked_config chưa được ghi — phải chạy GĐ5 trước. DỪNG.")
        return 1
    logger.info("Cấu hình đã khóa: %s", locked)

    seed = cfg["seed"]
    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    train_df = pd.read_parquet(resolve_path(cfg["paths"]["train_set"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"])).reset_index(drop=True)
    X_test = test_df.drop(columns=["Label"])
    feature_names = list(X_test.columns)
    class_names = list(le.classes_)

    cohort_csv = run_dir / "gd3_cohorts" / "cohort_ids.csv"
    df_cohort = pd.read_csv(cohort_csv)
    flow_ids = df_cohort["flow_id"].to_numpy()

    shap_topk_csv = run_dir / "gd4_shap_per_flow" / "shap_per_flow_topk.csv"
    shap_flow_ids = set(pd.read_csv(shap_topk_csv)["flow_id"].unique().tolist())
    if set(flow_ids.tolist()) != shap_flow_ids:
        logger.error("ID flow KHÔNG khớp giữa cohort_ids.csv và GĐ4 (SHAP). DỪNG.")
        return 1
    logger.info("Xác nhận %d flow_id khớp tuyệt đối với GĐ4.", len(flow_ids))

    X_cohort = X_test.iloc[flow_ids]
    proba_cohort = model.predict_proba(X_cohort)
    pred_idx_cohort = proba_cohort.argmax(axis=1)

    bg_size = locked["background_sample_size"]
    background = train_df.drop(columns=["Label"]).sample(n=bg_size, random_state=locked["background_seed"]).to_numpy()

    def predict_proba_fn(x):
        df_x = pd.DataFrame(x, columns=feature_names)
        return model.predict_proba(df_x)

    explainer = LimeTabularExplainer(
        training_data=background,
        feature_names=feature_names,
        class_names=class_names,
        discretize_continuous=locked["discretize_continuous"],
        kernel_width=locked["kernel_width"],
        random_state=seed,
    )

    long_rows = []
    topk_rows = []
    n = len(flow_ids)
    t_start = time.time()
    for i in range(n):
        fid = int(flow_ids[i])
        pidx = int(pred_idx_cohort[i])
        row = X_cohort.iloc[i].to_numpy()

        flow_seed = (seed * 1_000_003 + fid) % (2 ** 31 - 1)
        set_lime_explainer_seed(explainer, flow_seed)

        t0 = time.time()
        exp = explainer.explain_instance(
            row, predict_proba_fn, num_features=locked["num_features"], num_samples=locked["num_samples"],
            labels=[pidx],
        )
        dt = time.time() - t0

        local_r2 = exp.score[pidx] if isinstance(exp.score, dict) else exp.score
        intercept = exp.intercept[pidx] if isinstance(exp.intercept, dict) else exp.intercept
        local_pred = exp.local_pred[0] if hasattr(exp, "local_pred") else None

        weights = dict(exp.as_list(label=pidx))
        for feat_desc, w in weights.items():
            long_rows.append({
                "flow_id": fid,
                "pred_class": le.classes_[pidx],
                "feature_desc": feat_desc,
                "lime_weight": w,
            })

        order = sorted(weights.items(), key=lambda kv: -abs(kv[1]))
        for k in (1, 3, 5, 10):
            top = order[:k]
            topk_rows.append({
                "flow_id": fid,
                "pred_class": le.classes_[pidx],
                "k": k,
                "top_features": ";".join(t[0] for t in top),
                "top_weights": ";".join(f"{t[1]:.6g}" for t in top),
                "local_r2": local_r2,
                "intercept": intercept,
                "local_pred": local_pred,
                "time_sec": dt,
            })

        if i % 200 == 0:
            logger.info("  ... %d / %d flow (%.1fs đã trôi qua)", i, n, time.time() - t_start)

    total_dt = time.time() - t_start
    df_long = pd.DataFrame(long_rows)
    df_topk = pd.DataFrame(topk_rows)

    long_csv = out_dir / "lime_per_flow_long.csv"
    topk_csv = out_dir / "lime_per_flow_topk.csv"
    scores_csv = out_dir / "lime_sample_scores.csv"
    df_long.to_csv(long_csv, index=False, encoding="utf-8-sig")
    df_topk.to_csv(topk_csv, index=False, encoding="utf-8-sig")
    df_topk[df_topk["k"] == 5][["flow_id", "pred_class", "local_r2", "intercept", "local_pred", "time_sec"]].to_csv(
        scores_csv, index=False, encoding="utf-8-sig"
    )

    r2_values = df_topk[df_topk["k"] == 5]["local_r2"].to_numpy()
    report = {
        "n_flows": n,
        "flow_ids_match_gd4": True,
        "total_time_sec": total_dt,
        "mean_time_sec_per_flow": total_dt / n,
        "median_local_r2": float(np.median(r2_values)),
        "mean_local_r2": float(np.mean(r2_values)),
        "frac_r2_pass_gate": float((r2_values >= cfg["lime"]["local_r2_quality_gate"]).mean()),
        "locked_config_used": locked,
    }
    write_json(out_dir / "lime_per_flow_report.json", report)

    logger.info(
        "Hoàn tất %d flow trong %.1fs (%.3fs/flow). median_R2=%.4f, frac>=gate=%.2f%%",
        n, total_dt, total_dt / n, report["median_local_r2"], report["frac_r2_pass_gate"] * 100,
    )
    logger.info("GĐ 6 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
