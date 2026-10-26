"""GĐ 11 — Domain validation (Sub-RQ 2.4).

Đối chiếu Top-5 SHAP/LIME theo lớp với bảng tri thức miền đã chốt TRƯỚC (lib/domain_knowledge.py,
viết trước khi xem kết quả này). Chạy cả hai phiên bản bảng (chặt/rộng) để kiểm tra độ
nhạy của kết luận. Có phần riêng về tỷ lệ đặc trưng "dấu vân tay môi trường" trong Top-5.

SHAP top5-by-class: từ GĐ2 (tính trên TOÀN BỘ test set, mọi flow dự đoán đúng của lớp đó).
LIME top5-by-class: tổng hợp lại từ GĐ6 (chỉ trên cohort — tối đa 100 flow/lớp) vì LIME
chỉ được chạy per-flow trên cohort, không có bản toàn cục như SHAP ở GĐ2. Đây là một khác
biệt về QUY MÔ dữ liệu giữa hai cột so sánh — ghi rõ, không che giấu.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import latest_run_dir, get_logger, write_json  # noqa: E402
from lib.domain_knowledge import DOMAIN_KNOWLEDGE, ENVIRONMENT_FINGERPRINT_FEATURES  # noqa: E402


def precision_recall_f1(predicted_top5: set, domain_set: set) -> tuple[float, float, float]:
    inter = predicted_top5 & domain_set
    precision = len(inter) / len(predicted_top5) if predicted_top5 else float("nan")
    recall = len(inter) / len(domain_set) if domain_set else float("nan")
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def main() -> int:
    run_dir = latest_run_dir()
    logger = get_logger("stage11_domain_validation", run_dir)
    out_dir = run_dir / "gd11_domain_validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 11: DOMAIN VALIDATION")
    logger.info("=" * 80)

    # ---- SHAP top5 by class (global, GĐ2) ------------------------------------------------
    df_shap_top5 = pd.read_csv(run_dir / "gd2_shap_global" / "rq2_shap_global_top5_by_class.csv")
    shap_top5_by_class = {
        cls: set(g.sort_values("rank")["feature"].tolist())
        for cls, g in df_shap_top5.groupby("class")
    }

    # ---- LIME top5 by class (aggregated from cohort per-flow weights, GĐ6) --------------
    df_lime_long = pd.read_csv(run_dir / "gd6_lime_per_flow" / "lime_per_flow_long.csv")
    lime_top5_by_class = {}
    lime_class_n_flows = {}
    for cls, g in df_lime_long.groupby("pred_class"):
        agg = g.groupby("feature_desc")["lime_weight"].apply(lambda s: s.abs().mean()).sort_values(ascending=False)
        lime_top5_by_class[cls] = set(agg.head(5).index.tolist())
        lime_class_n_flows[cls] = g["flow_id"].nunique()

    # ---- Domain knowledge table (export for traceability) -------------------------------
    dk_rows = []
    for cls, info in DOMAIN_KNOWLEDGE.items():
        for scope in ("strict", "broad"):
            for feat in info[scope]:
                dk_rows.append({"class": cls, "scope": scope, "feature": feat, "source": info["source"], "rationale": info["rationale"]})
    pd.DataFrame(dk_rows).to_csv(out_dir / "domain_knowledge_table.csv", index=False, encoding="utf-8-sig")

    # ---- Precision/Recall/F1 vs domain knowledge, both scopes ----------------------------
    rows = []
    for cls, info in DOMAIN_KNOWLEDGE.items():
        if cls not in shap_top5_by_class or cls not in lime_top5_by_class:
            logger.warning("Lớp %s thiếu Top-5 ở SHAP hoặc LIME — bỏ qua.", cls)
            continue
        for scope in ("strict", "broad"):
            domain_set = set(info[scope])
            for method, top5 in [("SHAP", shap_top5_by_class[cls]), ("LIME", lime_top5_by_class[cls])]:
                p, r, f1 = precision_recall_f1(top5, domain_set)
                rows.append({
                    "class": cls, "scope": scope, "method": method,
                    "top5": ";".join(sorted(top5)),
                    "domain_set": ";".join(sorted(domain_set)),
                    "precision_at_5": p, "recall": r, "f1": f1,
                })
    df_precision = pd.DataFrame(rows)
    df_precision.to_csv(out_dir / "rq2_4_domain_precision_detail.csv", index=False, encoding="utf-8-sig")

    summary = (
        df_precision.groupby(["scope", "method"])[["precision_at_5", "recall", "f1"]]
        .mean()
        .reset_index()
    )
    summary.to_csv(out_dir / "rq2_4_domain_precision_summary.csv", index=False, encoding="utf-8-sig")
    logger.info("Tóm tắt precision/recall/F1 so với tri thức miền:\n%s", summary.to_string(index=False))

    # ---- Environment-fingerprint ratio in Top-5 ------------------------------------------
    env_rows = []
    for cls in DOMAIN_KNOWLEDGE:
        if cls not in shap_top5_by_class or cls not in lime_top5_by_class:
            continue
        for method, top5 in [("SHAP", shap_top5_by_class[cls]), ("LIME", lime_top5_by_class[cls])]:
            n_env = len(top5 & set(ENVIRONMENT_FINGERPRINT_FEATURES))
            env_rows.append({"class": cls, "method": method, "n_env_features_in_top5": n_env, "frac_env_in_top5": n_env / 5})
    df_env = pd.DataFrame(env_rows)
    df_env.to_csv(out_dir / "rq2_4_environment_fingerprint_by_class.csv", index=False, encoding="utf-8-sig")
    logger.info(
        "Tỷ lệ đặc trưng 'dấu vân tay môi trường' trong Top-5 trung bình: SHAP=%.2f LIME=%.2f",
        df_env[df_env["method"] == "SHAP"]["frac_env_in_top5"].mean(),
        df_env[df_env["method"] == "LIME"]["frac_env_in_top5"].mean(),
    )

    # ---- Sensitivity of conclusion to strict vs broad -------------------------------------
    pivot_f1 = summary.pivot(index="method", columns="scope", values="f1")
    logger.info("F1 trung bình theo scope:\n%s", pivot_f1.to_string())

    # ---- Charts -----------------------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    width = 0.35
    x = np.arange(len(summary["scope"].unique()))
    for i, method in enumerate(["SHAP", "LIME"]):
        vals = summary[summary["method"] == method].set_index("scope").loc[summary["scope"].unique(), "f1"]
        ax.bar(x + (i - 0.5) * width, vals.values, width=width, label=method)
    ax.set_xticks(x)
    ax.set_xticklabels(summary["scope"].unique())
    ax.set_ylabel("F1 so với tri thức miền")
    ax.set_title("Domain precision F1 — chặt vs rộng")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "domain_f1_strict_vs_broad.png", dpi=150)
    plt.close(fig)

    write_json(out_dir / "rq2_4_summary.json", {
        "lime_scope_note": "LIME top5-by-class tính trên cohort (<=100 flow/lớp), SHAP top5-by-class tính trên toàn test set — khác quy mô dữ liệu.",
        "lime_n_flows_per_class": lime_class_n_flows,
        "f1_by_scope_method": pivot_f1.to_dict(),
        "environment_fingerprint_features": ENVIRONMENT_FINGERPRINT_FEATURES,
    })

    logger.info("GĐ 11 HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
