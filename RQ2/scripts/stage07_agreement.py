"""GĐ 7 — Agreement SHAP và LIME (Sub-RQ 2.1).

Chỉ số trên mỗi flow, k = 3/5/10/20: Jaccard, Spearman (trên hợp của hai top-k, theo rank
gốc 78 đặc trưng), Kendall tau (tương tự), RBO, sign agreement (trên phần giao của top-k).
Có đường cơ sở ngẫu nhiên (mô phỏng), bản theo nhóm đặc trưng (gộp cột tương quan), và theo
từng lớp. Mọi chỉ số tổng hợp có khoảng tin cậy bootstrap.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, latest_run_dir, get_logger, write_json  # noqa: E402
from lib.feature_groups import build_group_map  # noqa: E402
from lib.agreement_metrics import (  # noqa: E402
    jaccard_at_k,
    spearman_at_k,
    kendall_at_k,
    rbo_at_k,
    sign_agreement_at_k,
    full_rank_correlation,
    random_baseline_jaccard,
    bootstrap_ci,
)


def build_rankings(df_shap: pd.DataFrame, df_lime: pd.DataFrame):
    """Return {flow_id: (shap_rank, shap_sign, lime_rank, lime_sign, pred_class)}."""
    out = {}
    shap_groups = df_shap.groupby("flow_id")
    lime_groups = df_lime.groupby("flow_id")
    for flow_id, g in shap_groups:
        g = g.reindex(g["shap_value"].abs().sort_values(ascending=False).index)
        shap_rank = g["feature"].tolist()
        shap_sign = dict(zip(g["feature"], np.sign(g["shap_value"])))
        pred_class = g["pred_class"].iloc[0]
        gl = lime_groups.get_group(flow_id)
        gl = gl.reindex(gl["lime_weight"].abs().sort_values(ascending=False).index)
        lime_rank = gl["feature_desc"].tolist()
        lime_sign = dict(zip(gl["feature_desc"], np.sign(gl["lime_weight"])))
        out[flow_id] = (shap_rank, shap_sign, lime_rank, lime_sign, pred_class)
    return out


def group_rank(rank: list[str], group_map: dict[str, str]) -> list[str]:
    """Map a feature rank list to groups, deduplicating while preserving first occurrence
    (so a top-k cut on the group-level list still makes sense as 'k distinct groups
    represented among the top-k original features')."""
    seen = []
    for f in rank:
        g = group_map.get(f, "Other")
        if g not in seen:
            seen.append(g)
    return seen


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage07_agreement", run_dir)
    out_dir = run_dir / "gd7_agreement"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 7: AGREEMENT SHAP VÀ LIME")
    logger.info("=" * 80)

    seed = cfg["seed"]
    rng = np.random.default_rng(seed)
    ks = cfg["topk"]["values"]
    n_boot = cfg["bootstrap"]["n_resamples"]
    ci = cfg["bootstrap"]["ci"]

    df_shap = pd.read_csv(run_dir / "gd4_shap_per_flow" / "shap_per_flow_long.csv")
    df_lime = pd.read_csv(run_dir / "gd6_lime_per_flow" / "lime_per_flow_long.csv")

    feature_names = sorted(df_shap["feature"].unique().tolist())
    n_features = len(feature_names)
    group_map = build_group_map(feature_names)

    rankings = build_rankings(df_shap, df_lime)
    logger.info("Xây dựng rank cho %d flow (mỗi flow %d đặc trưng)", len(rankings), n_features)

    per_flow_rows = []
    for flow_id, (shap_rank, shap_sign, lime_rank, lime_sign, pred_class) in rankings.items():
        group_shap_rank = group_rank(shap_rank, group_map)
        group_lime_rank = group_rank(lime_rank, group_map)
        spearman_full78, kendall_full78 = full_rank_correlation(shap_rank, lime_rank)
        for k in ks:
            row = {
                "flow_id": flow_id,
                "pred_class": pred_class,
                "k": k,
                "jaccard": jaccard_at_k(shap_rank, lime_rank, k),
                "spearman_topk_union": spearman_at_k(shap_rank, lime_rank, k),
                "kendall_tau_topk_union": kendall_at_k(shap_rank, lime_rank, k),
                "spearman_full78": spearman_full78,
                "kendall_full78": kendall_full78,
                "rbo": rbo_at_k(shap_rank, lime_rank, k),
                "sign_agreement": sign_agreement_at_k(shap_rank, shap_sign, lime_rank, lime_sign, k),
                "jaccard_group": jaccard_at_k(group_shap_rank, group_lime_rank, min(k, len(group_shap_rank))),
            }
            per_flow_rows.append(row)

    df_per_flow = pd.DataFrame(per_flow_rows)
    per_flow_csv = out_dir / "rq2_1_agreement_per_flow.csv"
    df_per_flow.to_csv(per_flow_csv, index=False, encoding="utf-8-sig")
    logger.info("Đã lưu agreement theo từng flow: %s (%d dòng)", per_flow_csv, len(df_per_flow))

    # ---- Overall summary with bootstrap CI --------------------------------------------
    metrics = [
        "jaccard", "spearman_topk_union", "kendall_tau_topk_union",
        "spearman_full78", "kendall_full78", "rbo", "sign_agreement", "jaccard_group",
    ]
    overall_rows = []
    for k in ks:
        sub = df_per_flow[df_per_flow["k"] == k]
        row = {"k": k, "n_flows": len(sub)}
        for m in metrics:
            mean, lo, hi = bootstrap_ci(sub[m].to_numpy(), n_boot, ci, rng)
            row[f"{m}_mean"] = mean
            row[f"{m}_ci_lo"] = lo
            row[f"{m}_ci_hi"] = hi
        overall_rows.append(row)
    df_overall = pd.DataFrame(overall_rows)
    overall_csv = out_dir / "rq2_1_agreement_overall.csv"
    df_overall.to_csv(overall_csv, index=False, encoding="utf-8-sig")
    logger.info("Agreement tổng thể:\n%s", df_overall.to_string(index=False))

    # ---- By class with bootstrap CI -----------------------------------------------------
    by_class_rows = []
    for (k, cls), sub in df_per_flow.groupby(["k", "pred_class"]):
        row = {"k": k, "class": cls, "n_flows": len(sub)}
        for m in metrics:
            mean, lo, hi = bootstrap_ci(sub[m].to_numpy(), n_boot, ci, rng)
            row[f"{m}_mean"] = mean
            row[f"{m}_ci_lo"] = lo
            row[f"{m}_ci_hi"] = hi
        by_class_rows.append(row)
    df_by_class = pd.DataFrame(by_class_rows).sort_values(["k", "class"])
    by_class_csv = out_dir / "rq2_1_agreement_by_class.csv"
    df_by_class.to_csv(by_class_csv, index=False, encoding="utf-8-sig")
    logger.info("Đã lưu agreement theo lớp: %s", by_class_csv)

    negative_spearman = df_by_class[(df_by_class["spearman_full78_mean"] < 0)]
    if len(negative_spearman):
        logger.warning(
            "Các lớp có Spearman (full-78, không chịu selection-bias) trung bình ÂM:\n%s",
            negative_spearman[["k", "class", "spearman_full78_mean"]].to_string(index=False),
        )
    else:
        logger.info("Không có lớp nào có Spearman (full-78) trung bình âm.")

    # ---- Random baseline -----------------------------------------------------------------
    baseline_rows = []
    for k in ks:
        sim = random_baseline_jaccard(n_features, k, n_trials=5000, rng=rng)
        baseline_rows.append({
            "k": k,
            "random_jaccard_mean": float(sim.mean()),
            "random_jaccard_ci_lo": float(np.quantile(sim, (1 - cfg["bootstrap"]["ci"]) / 2)),
            "random_jaccard_ci_hi": float(np.quantile(sim, 1 - (1 - cfg["bootstrap"]["ci"]) / 2)),
            "observed_jaccard_mean": float(df_overall[df_overall["k"] == k]["jaccard_mean"].iloc[0]),
        })
    df_baseline = pd.DataFrame(baseline_rows)
    df_baseline["fold_over_random"] = df_baseline["observed_jaccard_mean"] / df_baseline["random_jaccard_mean"]
    baseline_csv = out_dir / "rq2_1_random_baseline.csv"
    df_baseline.to_csv(baseline_csv, index=False, encoding="utf-8-sig")
    logger.info("Đường cơ sở ngẫu nhiên:\n%s", df_baseline.to_string(index=False))

    # ---- Charts ---------------------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 4))
    for m in ["jaccard", "spearman_full78", "rbo", "sign_agreement"]:
        ax.plot(df_overall["k"], df_overall[f"{m}_mean"], marker="o", label=m)
    ax.plot(df_baseline["k"], df_baseline["random_jaccard_mean"], marker="x", linestyle="--", color="gray", label="jaccard (random baseline)")
    ax.set_xlabel("k")
    ax.set_ylabel("giá trị trung bình")
    ax.set_title("Agreement SHAP vs LIME theo k")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figures_dir / "agreement_by_k.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    k5 = df_by_class[df_by_class["k"] == 5].sort_values("spearman_full78_mean")
    colors = ["#d62728" if v < 0 else "#1f77b4" for v in k5["spearman_full78_mean"]]
    ax.barh(k5["class"], k5["spearman_full78_mean"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Spearman (full-78 feature, không phụ thuộc k)")
    ax.set_title("Spearman SHAP vs LIME theo lớp")
    fig.tight_layout()
    fig.savefig(figures_dir / "spearman_by_class_k5.png", dpi=150)
    plt.close(fig)

    logger.info("Đã lưu biểu đồ vào %s", figures_dir)
    write_json(out_dir / "rq2_1_summary.json", {
        "n_flows": len(rankings),
        "ks": ks,
        "n_features": n_features,
        "negative_spearman_full78_classes": negative_spearman[["k", "class", "spearman_full78_mean"]].to_dict("records"),
    })

    logger.info("GĐ 7 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
