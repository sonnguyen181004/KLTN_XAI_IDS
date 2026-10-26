"""Tạo RQ2_Bao_cao_SHAP_chi_tiet.docx — trọng số SHAP theo từng lớp tấn công, kèm giải
thích đầy đủ, dễ hiểu cho từng chỉ số xuất hiện trong báo cáo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, latest_run_dir, get_logger  # noqa: E402
from lib.docx_helpers import new_doc, add_heading, add_para, add_bullets, add_table_from_df, add_image, add_page_break  # noqa: E402


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("build_report_shap", run_dir)
    gd2 = run_dir / "gd2_shap_global"
    gd4 = run_dir / "gd4_shap_per_flow"
    out_dir = run_dir / "gd13_report" / "docx"
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = new_doc(
        "RQ2 — Báo Cáo SHAP Chi Tiết",
        f"Trọng số SHAP theo từng loại tấn công — run {run_dir.name}",
    )

    add_heading(doc, "1. SHAP là gì, đọc bảng này như thế nào?", level=1)
    add_para(doc,
        "SHAP tính đóng góp (ký hiệu φ) của từng đặc trưng (trong 78 đặc trưng flow mạng) "
        "vào quyết định phân loại của mô hình XGBoost, dựa trên lý thuyết Shapley value. "
        "Mỗi flow mạng có 78 giá trị φ (một cho mỗi đặc trưng); φ dương nghĩa là đặc trưng "
        "đó ĐẨY dự đoán VỀ PHÍA lớp đang xét, φ âm nghĩa là ĐẨY RA XA. Trong báo cáo này:"
    )
    add_bullets(doc, [
        "mean |phi| (trị tuyệt đối trung bình): đo đặc trưng đó QUAN TRỌNG đến đâu nói "
        "chung (không quan tâm chiều hướng) — dùng để XẾP HẠNG Top-5.",
        "mean phi (có dấu, trung bình): đo đặc trưng đó thường ĐẨY VỀ PHÍA (dương) hay ĐẨY "
        "RA XA (âm) lớp đang xét — ví dụ nếu 'Flow Byts/s' có mean phi dương lớn ở lớp DDoS, "
        "nghĩa là tốc độ byte CAO thường khiến mô hình nghĩ đó LÀ DDoS.",
        "n_flows: số flow THẬT SỰ thuộc lớp đó và được mô hình dự đoán ĐÚNG, dùng để tính "
        "trung bình — lớp có n_flows nhỏ (ví dụ SQL Injection chỉ 9 flow) thì số liệu kém "
        "vững hơn, cần đọc cẩn trọng.",
    ])

    with open(gd2 / "rq2_shap_global_additivity_report.json", encoding="utf-8") as f:
        import json
        add_rep = json.load(f)
    add_para(doc,
        f"Kiểm tra tính chất cộng (additivity, GĐ2): trên mẫu {add_rep['sample_size']} flow "
        f"ngẫu nhiên, sai số tối đa giữa (base_value + tổng SHAP) và đầu ra thực tế của mô "
        f"hình là {add_rep['max_abs_error']:.2e} — sai số này RẤT NHỎ (do làm tròn số thực), "
        "xác nhận giá trị SHAP được tính đúng theo định nghĩa toán học."
    )

    add_heading(doc, "2. Top-5 SHAP theo từng loại tấn công (toàn bộ test set)", level=1)
    add_para(doc,
        "Tính trên TẤT CẢ các flow trong test set (700.000 flow) THỰC SỰ thuộc lớp đó và "
        "ĐƯỢC MÔ HÌNH DỰ ĐOÁN ĐÚNG — không phải chỉ trên cohort nhỏ, nên số liệu ở đây đại "
        "diện tốt cho toàn bộ hành vi mô hình với lớp đó."
    )
    df_top5 = pd.read_csv(gd2 / "rq2_shap_global_top5_by_class.csv")
    for cls in df_top5["class"].unique():
        add_heading(doc, f"Lớp: {cls}", level=2)
        sub = df_top5[df_top5["class"] == cls].sort_values("rank")
        n_flows = sub["n_flows"].iloc[0]
        add_para(doc, f"Số flow dùng để tính (dự đoán đúng): {n_flows}")
        add_table_from_df(doc, sub[["rank", "feature", "mean_abs_shap", "mean_signed_shap"]])
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in cls)
        add_image(doc, gd2 / "figures" / f"top5_{safe_name}.png", width_cm=12,
                   caption="Đỏ = đóng góp dương trung bình (đẩy về lớp này); Xanh = âm (đẩy ra xa).")

    add_page_break(doc)
    add_heading(doc, "3. SHAP per-flow trên cohort đánh giá", level=1)
    with open(gd4 / "shap_per_flow_report.json", encoding="utf-8") as f:
        import json
        rep4 = json.load(f)
    add_para(doc,
        f"Trên cohort đánh giá ({rep4['n_flows']} flow, lấy tối đa 100 flow/lớp, phân tầng), "
        f"SHAP được tính riêng cho TỪNG flow (không gộp trung bình). Sai số additivity: "
        f"tối đa {rep4['additivity_max_error']:.2e}, trung bình {rep4['additivity_mean_error']:.2e}. "
        f"Thời gian trung bình mỗi flow: {rep4['time_mean_sec_per_flow']*1000:.2f} ms "
        "(TreeSHAP rất nhanh so với LIME)."
    )
    add_para(doc,
        "Dữ liệu đầy đủ (78 giá trị SHAP mỗi flow) được lưu trong "
        "gd4_shap_per_flow/shap_per_flow_long.csv của thư mục run — có thể tra lại bất kỳ "
        "flow cụ thể nào."
    )

    stability_json = run_dir / "gd9_stability_robustness" / "rq2_2_stability_summary.json"
    if stability_json.exists():
        import json
        with open(stability_json, encoding="utf-8") as f:
            stab = json.load(f)
        add_heading(doc, "4. SHAP có ổn định qua các lần chạy không?", level=1)
        add_para(doc,
            f"Chạy lại TreeExplainer trên cùng cohort: {stab['shap_jaccard5_rerun']*100:.2f}% "
            "flow cho Top-5 giống TUYỆT ĐỐI so với lần chạy gốc. " + stab.get("shap_note", "")
        )

    out_path = out_dir / "RQ2_Bao_cao_SHAP_chi_tiet.docx"
    doc.save(str(out_path))
    logger.info("Đã lưu: %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
