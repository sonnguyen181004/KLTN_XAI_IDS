"""GĐ 13a — Tổng hợp số liệu từ GĐ0–GĐ12 thành các bảng tổng hợp dùng để viết báo cáo.

Không tạo file .docx ở đây (xem build_docx_reports.py) — chỉ gom các CSV/JSON rải rác
thành một bộ bảng tổng hợp + so sánh với v1_archive, để các báo cáo .docx đọc lại cho
nhất quán và mọi số liệu trong báo cáo truy ngược được về đúng 1 file CSV của run này.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, latest_run_dir, get_logger, write_json, REPO_ROOT  # noqa: E402


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage13_build_report_data", run_dir)
    out_dir = run_dir / "gd13_report"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("GĐ 13a: TỔNG HỢP SỐ LIỆU CHO BÁO CÁO")
    logger.info("=" * 80)

    master = {}

    # GĐ1
    import json
    with open(run_dir / "gd1_env_check" / "verification_report.json", encoding="utf-8") as f:
        master["gd1_verification"] = json.load(f)

    # GĐ2
    master["gd2_shap_global_top5"] = pd.read_csv(run_dir / "gd2_shap_global" / "rq2_shap_global_top5_by_class.csv").to_dict("records")
    with open(run_dir / "gd2_shap_global" / "rq2_shap_global_additivity_report.json", encoding="utf-8") as f:
        master["gd2_additivity"] = json.load(f)

    # GĐ3
    with open(run_dir / "gd3_cohorts" / "cohorts_summary.json", encoding="utf-8") as f:
        master["gd3_cohorts"] = json.load(f)

    # GĐ5
    with open(run_dir / "gd5_lime_dev_tuning" / "lime_config_lock_report.json", encoding="utf-8") as f:
        master["gd5_lime_lock"] = json.load(f)

    # GĐ6
    with open(run_dir / "gd6_lime_per_flow" / "lime_per_flow_report.json", encoding="utf-8") as f:
        master["gd6_lime_per_flow"] = json.load(f)

    # GĐ7
    master["gd7_agreement_overall"] = pd.read_csv(run_dir / "gd7_agreement" / "rq2_1_agreement_overall.csv").to_dict("records")
    master["gd7_random_baseline"] = pd.read_csv(run_dir / "gd7_agreement" / "rq2_1_random_baseline.csv").to_dict("records")

    # GĐ8
    with open(run_dir / "gd8_quality_gate" / "rq2_1_lime_quality_gate_summary.json", encoding="utf-8") as f:
        master["gd8_quality_gate"] = json.load(f)
    with open(run_dir / "gd8_quality_gate" / "rq2_1_r2_bucket_summary.json", encoding="utf-8") as f:
        master["gd8_r2_bucket"] = json.load(f)

    # GĐ9
    gd9_dir = run_dir / "gd9_stability_robustness"
    if (gd9_dir / "rq2_2_stability_summary.json").exists():
        with open(gd9_dir / "rq2_2_stability_summary.json", encoding="utf-8") as f:
            master["gd9_stability"] = json.load(f)
        master["gd9_noise"] = pd.read_csv(gd9_dir / "rq2_2_noise_robustness.csv").to_dict("records")
        master["gd9_convergence"] = pd.read_csv(gd9_dir / "rq2_2_lime_convergence.csv").to_dict("records")
    else:
        logger.warning("GĐ9 chưa có đủ output — bỏ qua phần này trong tổng hợp.")

    # GĐ10
    master["gd10_auc_summary"] = pd.read_csv(run_dir / "gd10_faithfulness" / "rq2_3_faithfulness_auc_summary.csv").to_dict("records")
    master["gd10_winrate"] = pd.read_csv(run_dir / "gd10_faithfulness" / "rq2_3_shap_vs_lime_winrate.csv").to_dict("records")
    with open(run_dir / "gd10_faithfulness" / "rq2_3_summary.json", encoding="utf-8") as f:
        master["gd10_summary"] = json.load(f)

    # GĐ11
    master["gd11_domain_summary"] = pd.read_csv(run_dir / "gd11_domain_validation" / "rq2_4_domain_precision_summary.csv").to_dict("records")
    with open(run_dir / "gd11_domain_validation" / "rq2_4_summary.json", encoding="utf-8") as f:
        master["gd11_summary"] = json.load(f)

    # GĐ12
    with open(run_dir / "gd12_error_cohort" / "rq2_error_vs_correct_comparison.json", encoding="utf-8") as f:
        master["gd12_error_comparison"] = json.load(f)

    write_json(out_dir / "rq2_master_summary.json", master)
    logger.info("Đã ghi bảng tổng hợp: %s", out_dir / "rq2_master_summary.json")

    # ---- Comparison with v1 ------------------------------------------------------------
    v1_dir = REPO_ROOT / cfg["paths"]["v1_archive"]
    comparison_rows = [
        {"chỉ số": "Cohort chính (flow)", "v1": 1339, "v2": master["gd3_cohorts"]["cohort_size"]},
        {"chỉ số": "Cohort lỗi (flow)", "v1": 151, "v2": master["gd3_cohorts"]["error_cohort_size"]},
        {"chỉ số": "LIME median Local R2 (toàn cohort)", "v1": 0.068, "v2": master["gd6_lime_per_flow"]["median_local_r2"]},
        {"chỉ số": "LIME % flow vượt gate R2>=0.3", "v1": 12.3, "v2": master["gd8_quality_gate"]["frac_pass"] * 100},
        {"chỉ số": "Jaccard@5 SHAP-LIME quan sát", "v1": 0.213, "v2": next(r["jaccard_mean"] for r in master["gd7_agreement_overall"] if r["k"] == 5)},
    ]
    df_cmp = pd.DataFrame(comparison_rows)
    df_cmp.to_csv(out_dir / "rq2_v1_vs_v2_comparison.csv", index=False, encoding="utf-8-sig")
    logger.info("So sánh v1 vs v2:\n%s", df_cmp.to_string(index=False))

    logger.info("GĐ 13a HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
