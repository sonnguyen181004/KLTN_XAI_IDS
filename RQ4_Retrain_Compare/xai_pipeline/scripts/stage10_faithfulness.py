"""GĐ 10 — Faithfulness (Sub-RQ 2.3).

Xóa dần k đặc trưng quan trọng nhất theo từng phương pháp (đưa về giá trị NỀN), đo mức
giảm xác suất của lớp dự đoán; đường deletion/insertion, AUC; comprehensiveness và
sufficiency cho k = 1..10.

Ba kiểm soát bắt buộc:
  1. Đối chứng "xóa k đặc trưng NGẪU NHIÊN" (cùng k, cùng giá trị nền).
  2. Nhiều giá trị nền: trung vị toàn tập, trung vị lớp Benign, trung bình toàn tập.
  3. Giới hạn: đặt đặc trưng về giá trị nền có thể tạo mẫu ngoài phân phối (OOD) — ghi
     nhận rõ, không che giấu.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, resolve_path, latest_run_dir, get_logger, write_json  # noqa: E402


def deletion_curve(model, X_cohort, pred_idx, ranked_features_per_flow, feature_names, baseline_vec, k_values):
    """ranked_features_per_flow: list of ranked feature-name lists (most important first),
    one per row of X_cohort, in the SAME row order. Returns dict k -> array of prob drop."""
    n = len(X_cohort)
    base_proba = model.predict_proba(X_cohort)[np.arange(n), pred_idx]
    results = {k: np.empty(n) for k in k_values}
    feat_idx = {f: i for i, f in enumerate(feature_names)}

    X_work = X_cohort.to_numpy().copy()
    max_k = max(k_values)
    # Apply deletions incrementally (k=1, then add the 2nd most important feature, etc.)
    # to avoid recomputing from scratch for each k.
    current = X_cohort.to_numpy().copy()
    for k in range(1, max_k + 1):
        for row_i in range(n):
            feats = ranked_features_per_flow[row_i]
            if k - 1 < len(feats):
                fidx = feat_idx[feats[k - 1]]
                current[row_i, fidx] = baseline_vec[fidx]
        if k in k_values:
            df_current = pd.DataFrame(current, columns=feature_names, index=X_cohort.index)
            proba_k = model.predict_proba(df_current)[np.arange(n), pred_idx]
            results[k] = base_proba - proba_k  # comprehensiveness-style drop
    return results, base_proba


def insertion_curve(model, X_cohort, pred_idx, ranked_features_per_flow, feature_names, baseline_vec, k_values):
    """Start fully at baseline, insert back the top-k most important features (sufficiency:
    how much probability is recovered using ONLY the top-k features)."""
    n = len(X_cohort)
    feat_idx = {f: i for i, f in enumerate(feature_names)}
    baseline_matrix = np.tile(baseline_vec, (n, 1))
    results = {}
    max_k = max(k_values)
    current = baseline_matrix.copy()
    orig_vals = X_cohort.to_numpy()
    for k in range(1, max_k + 1):
        for row_i in range(n):
            feats = ranked_features_per_flow[row_i]
            if k - 1 < len(feats):
                fidx = feat_idx[feats[k - 1]]
                current[row_i, fidx] = orig_vals[row_i, fidx]
        if k in k_values:
            df_current = pd.DataFrame(current, columns=feature_names, index=X_cohort.index)
            proba_k = model.predict_proba(df_current)[np.arange(n), pred_idx]
            results[k] = proba_k  # sufficiency-style recovered probability
    return results


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage10_faithfulness", run_dir)
    out_dir = run_dir / "gd10_faithfulness"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 10: FAITHFULNESS (DELETION/INSERTION)")
    logger.info("=" * 80)

    seed = cfg["seed"]
    rng = np.random.default_rng(seed)
    k_values = cfg["faithfulness"]["k_values"]

    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    train_df = pd.read_parquet(resolve_path(cfg["paths"]["train_set"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"])).reset_index(drop=True)
    X_test = test_df.drop(columns=["Label"])
    feature_names = list(X_test.columns)

    cohort_csv = run_dir / "gd3_cohorts" / "cohort_ids.csv"
    df_cohort = pd.read_csv(cohort_csv)
    flow_ids = df_cohort["flow_id"].to_numpy()
    X_cohort = X_test.iloc[flow_ids].reset_index(drop=True)
    pred_idx = model.predict_proba(X_cohort).argmax(axis=1)
    pred_class_names = le.inverse_transform(pred_idx)

    X_train_feat = train_df.drop(columns=["Label"])
    baselines = {
        "global_median": X_train_feat.median().to_numpy(),
        "global_mean": X_train_feat.mean().to_numpy(),
        "benign_median": train_df[train_df["Label"] == "Benign"].drop(columns=["Label"]).median().to_numpy(),
    }

    shap_topk = pd.read_csv(run_dir / "gd4_shap_per_flow" / "shap_per_flow_topk.csv")
    lime_topk = pd.read_csv(run_dir / "gd6_lime_per_flow" / "lime_per_flow_topk.csv")
    shap_rank10 = {
        row.flow_id: row.top_features.split(";")
        for row in shap_topk[shap_topk["k"] == 10].itertuples()
    }
    lime_rank10 = {
        row.flow_id: row.top_features.split(";")
        for row in lime_topk[lime_topk["k"] == 10].itertuples()
    }
    shap_ranked_list = [shap_rank10[int(fid)] for fid in flow_ids]
    lime_ranked_list = [lime_rank10[int(fid)] for fid in flow_ids]

    rng_ranked_list = []
    for _ in flow_ids:
        perm = rng.permutation(feature_names)[:max(k_values)].tolist()
        rng_ranked_list.append(perm)

    all_rows = []
    auc_rows = []
    for baseline_name, baseline_vec in baselines.items():
        logger.info("-- Giá trị nền: %s --", baseline_name)
        for method_name, ranked_list in [("SHAP", shap_ranked_list), ("LIME", lime_ranked_list), ("Random", rng_ranked_list)]:
            del_results, base_proba = deletion_curve(model, X_cohort, pred_idx, ranked_list, feature_names, baseline_vec, k_values)
            ins_results = insertion_curve(model, X_cohort, pred_idx, ranked_list, feature_names, baseline_vec, k_values)

            comprehensiveness_auc = np.mean([del_results[k].mean() for k in k_values])
            sufficiency_auc = np.mean([ins_results[k].mean() for k in k_values])

            for k in k_values:
                for i, fid in enumerate(flow_ids):
                    all_rows.append({
                        "flow_id": int(fid),
                        "pred_class": pred_class_names[i],
                        "baseline": baseline_name,
                        "method": method_name,
                        "k": k,
                        "comprehensiveness_drop": float(del_results[k][i]),
                        "sufficiency_proba": float(ins_results[k][i]),
                        "base_proba": float(base_proba[i]),
                    })

            auc_rows.append({
                "baseline": baseline_name,
                "method": method_name,
                "comprehensiveness_auc": comprehensiveness_auc,
                "sufficiency_auc": sufficiency_auc,
            })
            logger.info(
                "  %-6s: comprehensiveness_AUC=%.4f sufficiency_AUC=%.4f",
                method_name, comprehensiveness_auc, sufficiency_auc,
            )

    df_all = pd.DataFrame(all_rows)
    df_all.to_csv(out_dir / "rq2_3_per_flow_faithfulness.csv", index=False, encoding="utf-8-sig")
    df_auc = pd.DataFrame(auc_rows)
    df_auc.to_csv(out_dir / "rq2_3_faithfulness_auc_summary.csv", index=False, encoding="utf-8-sig")
    logger.info("Bảng AUC:\n%s", df_auc.to_string(index=False))

    # ---- Win-rate SHAP vs LIME (k=5, comprehensiveness) + paired Wilcoxon -----------------
    win_rows = []
    for baseline_name in baselines:
        sub5 = df_all[(df_all["baseline"] == baseline_name) & (df_all["k"] == 5)]
        shap5 = sub5[sub5["method"] == "SHAP"].set_index("flow_id")["comprehensiveness_drop"]
        lime5 = sub5[sub5["method"] == "LIME"].set_index("flow_id")["comprehensiveness_drop"]
        common = shap5.index.intersection(lime5.index)
        shap5, lime5 = shap5.loc[common], lime5.loc[common]
        win_rate = float((shap5 > lime5).mean())
        try:
            stat, p = wilcoxon(shap5, lime5)
        except ValueError:
            stat, p = float("nan"), float("nan")
        win_rows.append({
            "baseline": baseline_name,
            "k": 5,
            "shap_win_rate_vs_lime": win_rate,
            "wilcoxon_stat": float(stat),
            "wilcoxon_p": float(p),
            "n_flows": len(common),
        })
    df_win = pd.DataFrame(win_rows)
    df_win.to_csv(out_dir / "rq2_3_shap_vs_lime_winrate.csv", index=False, encoding="utf-8-sig")
    logger.info("Win-rate SHAP vs LIME (k=5, comprehensiveness):\n%s", df_win.to_string(index=False))

    conclusion_stable = (
        df_auc.pivot(index="method", columns="baseline", values="comprehensiveness_auc").loc["SHAP"] >
        df_auc.pivot(index="method", columns="baseline", values="comprehensiveness_auc").loc["LIME"]
    ).all()
    logger.info("Kết luận SHAP > LIME (comprehensiveness) ổn định qua mọi giá trị nền: %s", conclusion_stable)

    # ---- Charts -----------------------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    for baseline_name in baselines:
        sub = df_all[df_all["baseline"] == baseline_name]
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for method_name, color in [("SHAP", "#1f77b4"), ("LIME", "#ff7f0e"), ("Random", "#888888")]:
            curve = sub[sub["method"] == method_name].groupby("k")["comprehensiveness_drop"].mean()
            axes[0].plot(curve.index, curve.values, marker="o", label=method_name, color=color)
            curve2 = sub[sub["method"] == method_name].groupby("k")["sufficiency_proba"].mean()
            axes[1].plot(curve2.index, curve2.values, marker="s", label=method_name, color=color)
        axes[0].set_title(f"Deletion (comprehensiveness) — nền={baseline_name}")
        axes[0].set_xlabel("k"); axes[0].set_ylabel("giảm xác suất")
        axes[1].set_title(f"Insertion (sufficiency) — nền={baseline_name}")
        axes[1].set_xlabel("k"); axes[1].set_ylabel("xác suất phục hồi")
        axes[0].legend(); axes[1].legend()
        fig.tight_layout()
        fig.savefig(figures_dir / f"deletion_insertion_{baseline_name}.png", dpi=150)
        plt.close(fig)

    write_json(out_dir / "rq2_3_summary.json", {
        "k_values": k_values,
        "baselines": list(baselines.keys()),
        "conclusion_shap_more_faithful_all_baselines": bool(conclusion_stable),
        "note_ood_limitation": (
            "Đặt đặc trưng về giá trị nền có thể tạo ra mẫu ngoài phân phối huấn luyện "
            "(out-of-distribution) — xác suất đo được sau khi xóa đặc trưng có thể không "
            "phản ánh đúng hành vi model trên dữ liệu thực. Đây là giới hạn đã biết của "
            "phương pháp deletion/insertion, không phải lỗi triển khai."
        ),
    })

    logger.info("GĐ 10 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
