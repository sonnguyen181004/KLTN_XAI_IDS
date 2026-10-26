"""GĐ 12 — Giải thích khi model dự đoán sai (cohort lỗi, 151 flow — GĐ3).

Chạy SHAP và LIME trên cohort lỗi (giải thích CẢ nhãn dự đoán và nhãn thật). So với flow
dự đoán đúng (cohort chính, GĐ4/GĐ6): mức tập trung SHAP (Top-5 chiếm bao nhiêu % tổng
|phi|), đồng thuận SHAP–LIME, và tỷ lệ đặc trưng môi trường.

Cỡ mẫu nhỏ (151 flow, nhiều lớp chỉ có vài flow) — mọi kết luận ở đây là THĂM DÒ, không
khẳng định, nêu rõ trong report.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
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
from lib.domain_knowledge import ENVIRONMENT_FINGERPRINT_FEATURES  # noqa: E402


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage12_error_cohort", run_dir)
    out_dir = run_dir / "gd12_error_cohort"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 12: GIẢI THÍCH KHI MODEL DỰ ĐOÁN SAI (COHORT LỖI)")
    logger.info("=" * 80)

    seed = cfg["seed"]
    locked = cfg["lime"]["locked_config"]
    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    train_df = pd.read_parquet(resolve_path(cfg["paths"]["train_set"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"])).reset_index(drop=True)
    X_test = test_df.drop(columns=["Label"])
    feature_names = list(X_test.columns)

    df_error = pd.read_csv(run_dir / "gd3_cohorts" / "error_ids.csv")
    flow_ids = df_error["flow_id"].to_numpy()
    X_err = X_test.iloc[flow_ids]
    proba_err = model.predict_proba(X_err)
    pred_idx_err = proba_err.argmax(axis=1)
    true_idx_err = le.transform(df_error["true_label"])
    n = len(flow_ids)
    logger.info("Cohort lỗi: %d flow", n)

    background = train_df.drop(columns=["Label"]).sample(n=locked["background_sample_size"], random_state=locked["background_seed"]).to_numpy()
    lime_explainer = LimeTabularExplainer(
        training_data=background, feature_names=feature_names, class_names=list(le.classes_),
        discretize_continuous=locked["discretize_continuous"], kernel_width=locked["kernel_width"], random_state=seed,
    )
    shap_explainer = shap.TreeExplainer(model)
    booster = model.get_booster()

    def predict_proba_fn(x):
        return model.predict_proba(pd.DataFrame(x, columns=feature_names))

    rows = []
    for i in range(n):
        fid = int(flow_ids[i])
        row = X_err.iloc[[i]]
        row_vec = row.to_numpy()[0]
        pidx, tidx = int(pred_idx_err[i]), int(true_idx_err[i])

        exp = shap_explainer(row, check_additivity=False)
        dm = xgb.DMatrix(row, feature_names=feature_names)
        margin = booster.predict(dm, output_margin=True)[0]

        for label_kind, cidx in [("predicted", pidx), ("true", tidx)]:
            phi = exp.values[0, :, cidx]
            base = float(np.array(exp.base_values)[0, cidx])
            order = np.argsort(-np.abs(phi))
            top5_idx = order[:5]
            top5_feats = {feature_names[j] for j in top5_idx}
            concentration = float(np.abs(phi[top5_idx]).sum() / np.abs(phi).sum()) if np.abs(phi).sum() > 0 else float("nan")
            n_env = len(top5_feats & set(ENVIRONMENT_FINGERPRINT_FEATURES))

            flow_seed = (seed * 1_000_003 + fid + (0 if label_kind == "predicted" else 999_983)) % (2 ** 31 - 1)
            set_lime_explainer_seed(lime_explainer, flow_seed)
            lime_exp = lime_explainer.explain_instance(
                row_vec, predict_proba_fn, num_features=locked["num_features"], num_samples=locked["num_samples"], labels=[cidx],
            )
            lime_weights = dict(lime_exp.as_list(label=cidx))
            lime_top5 = set(sorted(lime_weights.items(), key=lambda kv: -abs(kv[1]))[:5])
            lime_top5_feats = {t[0] for t in lime_top5}
            lime_r2 = lime_exp.score[cidx] if isinstance(lime_exp.score, dict) else lime_exp.score

            jacc = len(top5_feats & lime_top5_feats) / len(top5_feats | lime_top5_feats) if (top5_feats | lime_top5_feats) else float("nan")

            rows.append({
                "flow_id": fid,
                "true_label": le.classes_[tidx],
                "pred_label": le.classes_[pidx],
                "explained_for": label_kind,
                "class_explained": le.classes_[cidx],
                "shap_top5": ";".join(sorted(top5_feats)),
                "shap_top5_concentration": concentration,
                "lime_top5": ";".join(sorted(lime_top5_feats)),
                "lime_local_r2": lime_r2,
                "shap_lime_jaccard5": jacc,
                "n_env_features_in_shap_top5": n_env,
            })

        if i % 30 == 0:
            logger.info("  ... %d / %d flow lỗi", i, n)

    df_out = pd.DataFrame(rows)
    df_out.to_csv(out_dir / "rq2_error_cohort_explanations.csv", index=False, encoding="utf-8-sig")

    # ---- Compare to the correctly-predicted cohort (GĐ4/GĐ7) ----------------------------
    df_shap_correct = pd.read_csv(run_dir / "gd4_shap_per_flow" / "shap_per_flow_long.csv")
    correct_concentration = []
    for fid, g in df_shap_correct.groupby("flow_id"):
        phi = g["shap_value"].to_numpy()
        order = np.argsort(-np.abs(phi))[:5]
        c = np.abs(phi[order]).sum() / np.abs(phi).sum() if np.abs(phi).sum() > 0 else np.nan
        correct_concentration.append(c)
    df_agree_correct = pd.read_csv(run_dir / "gd7_agreement" / "rq2_1_agreement_per_flow.csv")
    correct_jaccard5 = df_agree_correct[df_agree_correct["k"] == 5]["jaccard"].to_numpy()

    pred_rows = df_out[df_out["explained_for"] == "predicted"]
    comparison = {
        "error_cohort_n_flows": n,
        "error_shap_concentration_mean": float(pred_rows["shap_top5_concentration"].mean()),
        "correct_cohort_shap_concentration_mean": float(np.nanmean(correct_concentration)),
        "error_shap_lime_jaccard5_mean": float(pred_rows["shap_lime_jaccard5"].mean()),
        "correct_cohort_shap_lime_jaccard5_mean": float(np.nanmean(correct_jaccard5)),
        "error_env_fraction_in_top5_mean": float((pred_rows["n_env_features_in_shap_top5"] / 5).mean()),
        "caveat": "Cỡ mẫu nhỏ (151 flow, nhiều lớp <10 flow) — chỉ mang tính thăm dò, KHÔNG khẳng định khác biệt có ý nghĩa thống kê.",
    }
    write_json(out_dir / "rq2_error_vs_correct_comparison.json", comparison)
    logger.info("So sánh cohort lỗi vs cohort đúng:\n%s", comparison)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].boxplot(
        [pred_rows["shap_top5_concentration"].dropna(), pd.Series(correct_concentration).dropna()],
        tick_labels=["Cohort lỗi", "Cohort đúng"],
    )
    axes[0].set_title("Mức tập trung SHAP Top-5 (|phi|)")
    axes[1].boxplot(
        [pred_rows["shap_lime_jaccard5"].dropna(), pd.Series(correct_jaccard5).dropna()],
        tick_labels=["Cohort lỗi", "Cohort đúng"],
    )
    axes[1].set_title("Jaccard@5 SHAP-LIME")
    fig.tight_layout()
    fig.savefig(figures_dir / "error_vs_correct.png", dpi=150)
    plt.close(fig)

    logger.info("GĐ 12 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
