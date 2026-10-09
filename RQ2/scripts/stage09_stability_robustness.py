"""GĐ 9 — Stability và robustness (Sub-RQ 2.2), cho CẢ SHAP và LIME (lần trước thiếu SHAP).

1. Stability theo lần chạy (seed): LIME chạy lại với 10 seed, đo Jaccard@5 giữa các lần
   (trung bình theo từng cặp seed, mỗi flow). TreeSHAP là xác định — chạy lại 1 lần để xác
   nhận Jaccard@5 = 1.0 (không có nguồn ngẫu nhiên nào trong TreeExplainer cho mô hình cố
   định).
2. Robustness với nhiễu đầu vào: thêm nhiễu Gaussian ở các mức sigma (phần trăm độ lệch
   chuẩn đặc trưng trên train), cắt về [min, max] quan sát trên train để tránh giá trị phi
   thực tế; đo Jaccard@5 giữa explanation trên flow nhiễu và flow gốc (cùng lớp dự đoán gốc).
3. Đường hội tụ của LIME theo num_samples (500/1000/5000/10000), giữ kernel_width và
   discretize_continuous ở giá trị ĐÃ KHÓA — đo trên mẫu dev-grid giống GĐ5 để tái sử dụng
   quy mô tính toán đã kiểm chứng.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
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


def jaccard(a: set, b: set) -> float:
    u = a | b
    return len(a & b) / len(u) if u else float("nan")


def top5_shap(exp_values_row: np.ndarray, feature_names: list[str]) -> set:
    order = np.argsort(-np.abs(exp_values_row))[:5]
    return {feature_names[i] for i in order}


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage09_stability_robustness", run_dir)
    out_dir = run_dir / "gd9_stability_robustness"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 9: STABILITY VÀ ROBUSTNESS (SHAP VÀ LIME)")
    logger.info("=" * 80)

    seed = cfg["seed"]
    locked = cfg["lime"]["locked_config"]
    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    train_df = pd.read_parquet(resolve_path(cfg["paths"]["train_set"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"])).reset_index(drop=True)
    X_test = test_df.drop(columns=["Label"])
    feature_names = list(X_test.columns)

    cohort_csv = run_dir / "gd3_cohorts" / "cohort_ids.csv"
    flow_ids = pd.read_csv(cohort_csv)["flow_id"].to_numpy()
    X_cohort = X_test.iloc[flow_ids]
    proba_cohort = model.predict_proba(X_cohort)
    pred_idx_cohort = proba_cohort.argmax(axis=1)

    X_train_feat = train_df.drop(columns=["Label"])
    feat_std = X_train_feat.std().to_numpy()
    feat_min = X_train_feat.min().to_numpy()
    feat_max = X_train_feat.max().to_numpy()

    background = X_train_feat.sample(n=locked["background_sample_size"], random_state=locked["background_seed"]).to_numpy()

    def predict_proba_fn(x):
        return model.predict_proba(pd.DataFrame(x, columns=feature_names))

    lime_explainer = LimeTabularExplainer(
        training_data=background,
        feature_names=feature_names,
        class_names=list(le.classes_),
        discretize_continuous=locked["discretize_continuous"],
        kernel_width=locked["kernel_width"],
        random_state=seed,
    )
    shap_explainer = shap.TreeExplainer(model)

    # Reference top-5 from GĐ4/GĐ6 (already computed, no need to recompute originals).
    shap_topk = pd.read_csv(run_dir / "gd4_shap_per_flow" / "shap_per_flow_topk.csv")
    lime_topk = pd.read_csv(run_dir / "gd6_lime_per_flow" / "lime_per_flow_topk.csv")
    ref_shap_top5 = {
        row.flow_id: set(row.top_features.split(";"))
        for row in shap_topk[shap_topk["k"] == 5].itertuples()
    }
    ref_lime_top5 = {
        row.flow_id: set(row.top_features.split(";"))
        for row in lime_topk[lime_topk["k"] == 5].itertuples()
    }

    # =====================================================================================
    # 1. STABILITY ACROSS SEEDS
    # =====================================================================================
    logger.info("-- 1. Stability theo seed --")
    stability_seeds = cfg["lime"]["stability_seeds"]
    n = len(flow_ids)

    lime_top5_by_seed = {s: [None] * n for s in stability_seeds}
    t0 = time.time()
    for s_i, s in enumerate(stability_seeds):
        for i in range(n):
            fid = int(flow_ids[i])
            pidx = int(pred_idx_cohort[i])
            row = X_cohort.iloc[i].to_numpy()
            flow_seed = (seed * 1_000_003 + fid + s * 7_919) % (2 ** 31 - 1)
            set_lime_explainer_seed(lime_explainer, flow_seed)
            # num_features=locked (78), NOT 5: requesting few features here makes LIME's
            # feature_selection='auto' switch to 'forward_selection' (num_features<=6),
            # which fits ~num_features*78 Ridge models instead of one — ~390x slower per
            # call. Always explain the full 78, then take top-5 from the result ourselves.
            exp = lime_explainer.explain_instance(
                row, predict_proba_fn, num_features=locked["num_features"], num_samples=locked["num_samples"], labels=[pidx],
            )
            full_weights = exp.as_list(label=pidx)
            top5 = sorted(full_weights, key=lambda t: -abs(t[1]))[:5]
            lime_top5_by_seed[s][i] = {t[0] for t in top5}
        logger.info("  seed %d/%d hoàn tất (%.1fs đã trôi qua)", s_i + 1, len(stability_seeds), time.time() - t0)

    pairwise_rows = []
    for i in range(n):
        fid = int(flow_ids[i])
        sets_i = [lime_top5_by_seed[s][i] for s in stability_seeds]
        pair_jacs = [jaccard(sets_i[a], sets_i[b]) for a in range(len(sets_i)) for b in range(a + 1, len(sets_i))]
        pairwise_rows.append({"flow_id": fid, "mean_pairwise_jaccard5": float(np.mean(pair_jacs))})
    df_lime_stability = pd.DataFrame(pairwise_rows)
    df_lime_stability.to_csv(out_dir / "rq2_2_stability_lime_per_flow.csv", index=False, encoding="utf-8-sig")
    logger.info(
        "LIME stability (Jaccard@5 trung bình giữa %d seed, %d flow): mean=%.4f median=%.4f",
        len(stability_seeds), n, df_lime_stability["mean_pairwise_jaccard5"].mean(), df_lime_stability["mean_pairwise_jaccard5"].median(),
    )

    # SHAP determinism check: recompute once, compare to GĐ4 top-5.
    shap_stable_matches = 0
    CHUNK = 200
    for start in range(0, n, CHUNK):
        end = min(start + CHUNK, n)
        chunk = X_cohort.iloc[start:end]
        exp = shap_explainer(chunk, check_additivity=False)
        for j in range(len(chunk)):
            fid = int(flow_ids[start + j])
            pidx = int(pred_idx_cohort[start + j])
            top5 = top5_shap(exp.values[j, :, pidx], feature_names)
            if top5 == ref_shap_top5[fid]:
                shap_stable_matches += 1
    shap_stability_jaccard = shap_stable_matches / n
    logger.info("SHAP stability (rerun vs GĐ4, cùng model): %d/%d flow khớp tuyệt đối Top-5 -> Jaccard trung bình=%.6f", shap_stable_matches, n, shap_stability_jaccard)

    write_json(out_dir / "rq2_2_stability_summary.json", {
        "lime_mean_pairwise_jaccard5": float(df_lime_stability["mean_pairwise_jaccard5"].mean()),
        "lime_median_pairwise_jaccard5": float(df_lime_stability["mean_pairwise_jaccard5"].median()),
        "n_stability_seeds": len(stability_seeds),
        "shap_jaccard5_rerun": shap_stability_jaccard,
        "shap_note": "TreeExplainer là xác định cho model cố định — Jaccard=1.0 (hoặc rất gần 1.0 do làm tròn số) là kỳ vọng, không phải augment ngẫu nhiên.",
    })

    # =====================================================================================
    # 2. ROBUSTNESS TO INPUT NOISE
    # =====================================================================================
    logger.info("-- 2. Robustness với nhiễu đầu vào --")
    rng = np.random.default_rng(seed)
    sigma_fractions = cfg["noise"]["sigma_fractions"]
    noise_rows = []
    for sigma_frac in sigma_fractions:
        noise = rng.normal(0, 1, size=X_cohort.shape) * (feat_std * sigma_frac)
        X_noisy = X_cohort.to_numpy() + noise
        X_noisy = np.clip(X_noisy, feat_min, feat_max)
        X_noisy_df = pd.DataFrame(X_noisy, columns=feature_names, index=X_cohort.index)

        # SHAP on noisy inputs, explained for the ORIGINAL predicted class (fairness: same
        # target as the clean explanation, so we measure explanation drift, not a new decision).
        shap_jacs = []
        for start in range(0, n, CHUNK):
            end = min(start + CHUNK, n)
            chunk = X_noisy_df.iloc[start:end]
            exp = shap_explainer(chunk, check_additivity=False)
            for j in range(len(chunk)):
                fid = int(flow_ids[start + j])
                pidx = int(pred_idx_cohort[start + j])
                top5 = top5_shap(exp.values[j, :, pidx], feature_names)
                shap_jacs.append(jaccard(top5, ref_shap_top5[fid]))

        # LIME on noisy inputs, same flow-fixed seed as GĐ6 (isolate the effect of input
        # noise, not of a different sampling seed).
        lime_jacs = []
        for i in range(n):
            fid = int(flow_ids[i])
            pidx = int(pred_idx_cohort[i])
            row = X_noisy_df.iloc[i].to_numpy()
            flow_seed = (seed * 1_000_003 + fid) % (2 ** 31 - 1)
            set_lime_explainer_seed(lime_explainer, flow_seed)
            exp = lime_explainer.explain_instance(
                row, predict_proba_fn, num_features=locked["num_features"], num_samples=locked["num_samples"], labels=[pidx],
            )
            full_weights = exp.as_list(label=pidx)
            top5 = {t[0] for t in sorted(full_weights, key=lambda t: -abs(t[1]))[:5]}
            lime_jacs.append(jaccard(top5, ref_lime_top5[fid]))

        noise_rows.append({
            "sigma_fraction": sigma_frac,
            "shap_mean_jaccard5": float(np.mean(shap_jacs)),
            "shap_median_jaccard5": float(np.median(shap_jacs)),
            "lime_mean_jaccard5": float(np.mean(lime_jacs)),
            "lime_median_jaccard5": float(np.median(lime_jacs)),
            "n_flows": n,
        })
        logger.info(
            "  sigma=%.0f%%: SHAP Jaccard@5=%.4f | LIME Jaccard@5=%.4f",
            sigma_frac * 100, noise_rows[-1]["shap_mean_jaccard5"], noise_rows[-1]["lime_mean_jaccard5"],
        )

    df_noise = pd.DataFrame(noise_rows)
    df_noise.to_csv(out_dir / "rq2_2_noise_robustness.csv", index=False, encoding="utf-8-sig")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([0] + [s * 100 for s in sigma_fractions], [1.0] + df_noise["shap_mean_jaccard5"].tolist(), marker="o", label="SHAP")
    ax.plot([0] + [s * 100 for s in sigma_fractions], [1.0] + df_noise["lime_mean_jaccard5"].tolist(), marker="s", label="LIME")
    ax.set_xlabel("Mức nhiễu (% độ lệch chuẩn đặc trưng)")
    ax.set_ylabel("Jaccard@5 so với giải thích gốc")
    ax.set_title("Robustness với nhiễu đầu vào")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "noise_robustness.png", dpi=150)
    plt.close(fig)

    # =====================================================================================
    # 3. LIME CONVERGENCE BY num_samples (kernel_width & discretize = giá trị đã khóa)
    # =====================================================================================
    logger.info("-- 3. Đường hội tụ LIME theo num_samples (kw/disc đã khóa) --")
    dev_csv = run_dir / "gd3_cohorts" / "dev_ids.csv"
    dev_flow_ids = pd.read_csv(dev_csv)["flow_id"].to_numpy()
    grid_n = min(cfg["lime"]["dev_grid_sample_size"], len(dev_flow_ids))
    rng2 = np.random.default_rng(seed)
    grid_sel = rng2.choice(len(dev_flow_ids), size=grid_n, replace=False)
    X_dev = X_test.iloc[dev_flow_ids].iloc[grid_sel]
    proba_dev = model.predict_proba(X_dev)
    pred_idx_dev = proba_dev.argmax(axis=1)

    convergence_rows = []
    for ns in [500, 1000, 5000, 10000]:
        r2s = []
        t0 = time.time()
        for i in range(len(X_dev)):
            row = X_dev.iloc[i].to_numpy()
            pidx = int(pred_idx_dev[i])
            set_lime_explainer_seed(lime_explainer, seed)
            exp = lime_explainer.explain_instance(
                row, predict_proba_fn, num_features=locked["num_features"], num_samples=ns, labels=[pidx],
            )
            r2 = exp.score[pidx] if isinstance(exp.score, dict) else exp.score
            r2s.append(r2)
        dt = time.time() - t0
        convergence_rows.append({
            "num_samples": ns,
            "median_r2": float(np.median(r2s)),
            "mean_r2": float(np.mean(r2s)),
            "total_time_sec": dt,
            "n_flows": len(X_dev),
        })
        logger.info("  num_samples=%d: median_R2=%.4f (%.1fs)", ns, convergence_rows[-1]["median_r2"], dt)

    df_conv = pd.DataFrame(convergence_rows)
    df_conv.to_csv(out_dir / "rq2_2_lime_convergence.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(df_conv["num_samples"], df_conv["median_r2"], marker="o")
    ax.set_xscale("log")
    ax.set_xlabel("num_samples (log scale)")
    ax.set_ylabel("Local R2 trung vị")
    ax.set_title(f"Hội tụ LIME theo num_samples (kw={locked['kernel_width']}, disc={locked['discretize_continuous']})")
    fig.tight_layout()
    fig.savefig(figures_dir / "lime_convergence.png", dpi=150)
    plt.close(fig)

    logger.info("GĐ 9 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
