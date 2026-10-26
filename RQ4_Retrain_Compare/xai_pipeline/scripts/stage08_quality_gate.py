"""GĐ 8 — Quality gate của LIME và "R2 so với đồng thuận".

Ngưỡng Local R2 (0.3) đã được chốt TRƯỚC khi chạy (trong config.yaml, GĐ5). Ở đây:
  1. Báo cáo cả toàn bộ flow và nhóm vượt ngưỡng + phân bố lớp của nhóm vượt ngưỡng.
  2. Chia flow theo mức Local R2 (thấp/vừa/cao) và xem đồng thuận (Jaccard/Spearman full-78)
     với SHAP có tăng theo mức R2 không — nếu có, phần lớn bất đồng ở GĐ7 được giải thích
     bằng chất lượng surrogate của LIME; nếu không, ghi nhận đúng như thấy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, latest_run_dir, get_logger, write_json  # noqa: E402


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage08_quality_gate", run_dir)
    out_dir = run_dir / "gd8_quality_gate"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 8: QUALITY GATE CỦA LIME VÀ R2 SO VỚI ĐỒNG THUẬN")
    logger.info("=" * 80)

    gate = cfg["lime"]["local_r2_quality_gate"]
    logger.info("Ngưỡng quality gate (đã chốt ở GĐ5 trước khi xem kết quả cohort): R2 >= %.2f", gate)

    df_scores = pd.read_csv(run_dir / "gd6_lime_per_flow" / "lime_sample_scores.csv")
    n_total = len(df_scores)
    df_pass = df_scores[df_scores["local_r2"] >= gate]
    n_pass = len(df_pass)

    logger.info("Toàn bộ cohort: %d flow. Vượt ngưỡng: %d (%.2f%%).", n_total, n_pass, 100 * n_pass / n_total)

    class_dist_all = df_scores["pred_class"].value_counts().to_dict()
    class_dist_pass = df_pass["pred_class"].value_counts().to_dict()
    class_pass_rate = (
        df_scores.groupby("pred_class")["local_r2"]
        .apply(lambda s: (s >= gate).mean())
        .sort_values(ascending=False)
    )
    logger.info("Tỷ lệ vượt ngưỡng theo lớp:\n%s", class_pass_rate.to_string())

    write_json(out_dir / "rq2_1_lime_quality_gate_summary.json", {
        "gate": gate,
        "n_total": n_total,
        "n_pass": n_pass,
        "frac_pass": n_pass / n_total,
        "class_distribution_all": class_dist_all,
        "class_distribution_pass": class_dist_pass,
        "class_pass_rate": class_pass_rate.to_dict(),
    })
    df_scores.to_csv(out_dir / "rq2_1_lime_quality_gate.csv", index=False, encoding="utf-8-sig")

    # ---- R2 bucket vs agreement with SHAP ------------------------------------------------
    df_agree = pd.read_csv(run_dir / "gd7_agreement" / "rq2_1_agreement_per_flow.csv")
    df_agree_k5 = df_agree[df_agree["k"] == 5][["flow_id", "jaccard", "spearman_full78", "sign_agreement"]]
    merged = df_scores.merge(df_agree_k5, on="flow_id", how="inner")

    bins = [-np.inf, 0.1, gate, np.inf]
    labels = ["thấp (<0.1)", f"vừa (0.1–{gate})", f"cao (>={gate})"]
    merged["r2_bucket"] = pd.cut(merged["local_r2"], bins=bins, labels=labels)

    bucket_stats = merged.groupby("r2_bucket", observed=True).agg(
        n_flows=("flow_id", "count"),
        mean_jaccard=("jaccard", "mean"),
        mean_spearman_full78=("spearman_full78", "mean"),
        mean_sign_agreement=("sign_agreement", "mean"),
    ).reset_index()
    bucket_csv = out_dir / "rq2_1_r2_bucket_vs_agreement.csv"
    bucket_stats.to_csv(bucket_csv, index=False, encoding="utf-8-sig")
    logger.info("Đồng thuận theo mức Local R2 (k=5):\n%s", bucket_stats.to_string(index=False))

    monotonic = bucket_stats["mean_jaccard"].is_monotonic_increasing and bucket_stats["mean_spearman_full78"].is_monotonic_increasing
    if monotonic:
        logger.info("Đồng thuận TĂNG theo mức Local R2 — bất đồng ở GĐ7 một phần được giải thích bởi chất lượng surrogate LIME.")
    else:
        logger.warning("Đồng thuận KHÔNG tăng đều theo mức Local R2 — ghi nhận đúng như thấy, không có bằng chứng rõ cho giả thuyết 'R2 thấp gây bất đồng'.")

    # ---- Chart ------------------------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(bucket_stats))
    ax.bar(x - 0.2, bucket_stats["mean_jaccard"], width=0.4, label="Jaccard@5")
    ax.bar(x + 0.2, bucket_stats["mean_spearman_full78"], width=0.4, label="Spearman full-78")
    ax.set_xticks(x)
    ax.set_xticklabels(bucket_stats["r2_bucket"], rotation=15)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend()
    ax.set_title("Đồng thuận SHAP–LIME theo mức Local R2 của LIME")
    fig.tight_layout()
    fig.savefig(figures_dir / "agreement_by_r2_bucket.png", dpi=150)
    plt.close(fig)

    write_json(out_dir / "rq2_1_r2_bucket_summary.json", {
        "gate": gate,
        "monotonic_increase": bool(monotonic),
        "buckets": bucket_stats.to_dict("records"),
    })

    logger.info("GĐ 8 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
