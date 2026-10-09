"""Tạo RQ2_Bao_cao_LIME_chi_tiet.docx — trọng số LIME theo từng lớp tấn công, kèm giải
thích đầy đủ, dễ hiểu cho từng chỉ số xuất hiện trong báo cáo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, latest_run_dir, get_logger  # noqa: E402
from lib.docx_helpers import new_doc, add_heading, add_para, add_bullets, add_table_from_df, add_image, add_page_break  # noqa: E402


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("build_report_lime", run_dir)
    gd5 = run_dir / "gd5_lime_dev_tuning"
    gd6 = run_dir / "gd6_lime_per_flow"
    gd8 = run_dir / "gd8_quality_gate"
    out_dir = run_dir / "gd13_report" / "docx"
    out_dir.mkdir(parents=True, exist_ok=True)

    locked = cfg["lime"]["locked_config"]

    doc = new_doc(
        "RQ2 — Báo Cáo LIME Chi Tiết",
        f"Trọng số LIME theo từng loại tấn công — run {run_dir.name}",
    )

    add_heading(doc, "1. LIME là gì, đọc bảng này như thế nào?", level=1)
    add_para(doc,
        "LIME xây dựng một mô hình tuyến tính đơn giản để xấp xỉ hành vi của XGBoost CHỈ "
        "TRONG MỘT VÙNG NHỎ quanh flow đang xét, bằng cách tạo nhiều phiên bản 'nhiễu' của "
        "flow đó và học một đường hồi quy từ các phiên bản này. Trọng số của đường hồi quy "
        "(lime_weight) là 'mức quan trọng' theo LIME — dương/âm có ý nghĩa giống SHAP (đẩy "
        "về/đẩy ra xa lớp đang xét), nhưng được tính bằng cách HOÀN TOÀN KHÁC (xấp xỉ cục "
        "bộ, không phải Shapley value chính xác)."
    )

    add_heading(doc, "2. Cấu hình LIME đã chốt (GĐ5)", level=1)
    add_para(doc,
        "Cấu hình dưới đây được chọn bằng cách thử nhiều tổ hợp trên TẬP DEV (250 flow, "
        "tách riêng khỏi cohort đánh giá) TRƯỚC khi chạy trên cohort chính — quy tắc chọn "
        "CHỈ dựa trên Local R2 và chi phí thời gian, không theo mức đồng thuận với SHAP."
    )
    cfg_rows = pd.DataFrame([
        {"Tham số": "kernel_width", "Giá trị": locked["kernel_width"],
         "Ý nghĩa": "Độ rộng vùng lân cận được coi là 'gần' flow gốc khi tính trọng số mẫu nhiễu"},
        {"Tham số": "num_samples", "Giá trị": locked["num_samples"],
         "Ý nghĩa": "Số phiên bản nhiễu tạo ra để huấn luyện mô hình tuyến tính cục bộ"},
        {"Tham số": "discretize_continuous", "Giá trị": locked["discretize_continuous"],
         "Ý nghĩa": "Có chia nhỏ đặc trưng liên tục thành khoảng trước khi nhiễu hay không"},
        {"Tham số": "num_features", "Giá trị": locked["num_features"],
         "Ý nghĩa": "Số đặc trưng tối đa LIME trả về trọng số (78 = toàn bộ)"},
        {"Tham số": "background_sample_size", "Giá trị": locked["background_sample_size"],
         "Ý nghĩa": "Số dòng mẫu từ train_set dùng làm 'nền' thống kê (trung vị/độ lệch chuẩn mỗi đặc trưng)"},
    ])
    add_table_from_df(doc, cfg_rows, float_fmt="{}")

    with open(gd5 / "lime_config_lock_report.json", encoding="utf-8") as f:
        lock_rep = json.load(f)
    full_dev = lock_rep["full_dev_validation"]
    add_para(doc,
        f"Xác nhận trên TOÀN BỘ tập dev ({full_dev['n_flows']} flow): Local R2 trung vị = "
        f"{full_dev['median_r2']:.4f}, {full_dev['frac_r2_pass_gate']*100:.1f}% flow đạt "
        "ngưỡng chất lượng (R2 ≥ 0.3)."
    )
    if full_dev["median_r2"] < cfg["lime"]["local_r2_quality_gate"]:
        add_para(doc,
            "Lưu ý: Local R2 trung vị trên tập dev THẤP HƠN ngưỡng chất lượng — đây là GIỚI "
            "HẠN THỰC SỰ của LIME trên loại dữ liệu mạng này (các đặc trưng flow có phân "
            "phối lệch mạnh, nhiều ngoại lai, khiến một đường thẳng khó xấp xỉ tốt hành vi "
            "của XGBoost). Kết quả KHÔNG bị điều chỉnh để trông đẹp hơn.", italic=True)

    add_heading(doc, "3. Chất lượng LIME trên cohort đánh giá (GĐ8)", level=1)
    with open(gd8 / "rq2_1_lime_quality_gate_summary.json", encoding="utf-8") as f:
        gate = json.load(f)
    add_para(doc,
        f"Trên cohort đánh giá ({gate['n_total']} flow): {gate['n_pass']} flow "
        f"({gate['frac_pass']*100:.2f}%) đạt ngưỡng Local R2 ≥ 0.3 — CAO HƠN NHIỀU so với "
        "tập dev, cho thấy chất lượng LIME khác nhau đáng kể giữa các flow."
    )
    df_rate = pd.DataFrame(
        [{"Lớp": k, "Tỷ lệ đạt ngưỡng (%)": v * 100} for k, v in gate["class_pass_rate"].items()]
    ).sort_values("Tỷ lệ đạt ngưỡng (%)", ascending=False)
    add_table_from_df(doc, df_rate, max_rows=20)

    add_heading(doc, "4. Top-5 LIME theo từng loại tấn công (trên cohort)", level=1)
    add_para(doc,
        "Khác với SHAP (tính trên toàn test set), LIME chỉ được chạy trên cohort đánh giá "
        "(tối đa 100 flow/lớp) vì chi phí tính toán — Top-5 dưới đây là trọng số |lime_weight| "
        "trung bình trên các flow của cohort thuộc lớp đó."
    )
    df_lime_long = pd.read_csv(gd6 / "lime_per_flow_long.csv")
    for cls, g in df_lime_long.groupby("pred_class"):
        agg = g.groupby("feature_desc")["lime_weight"].agg(
            mean_abs_weight=lambda s: s.abs().mean(),
            mean_signed_weight="mean",
        ).sort_values("mean_abs_weight", ascending=False).head(5).reset_index()
        add_heading(doc, f"Lớp: {cls} (n={g['flow_id'].nunique()} flow trong cohort)", level=2)
        add_table_from_df(doc, agg.rename(columns={"feature_desc": "feature"}))

    add_page_break(doc)
    add_heading(doc, "5. LIME có ổn định qua các lần chạy và chịu nhiễu tốt không?", level=1)
    stability_csv = run_dir / "gd9_stability_robustness" / "rq2_2_stability_lime_per_flow.csv"
    noise_csv = run_dir / "gd9_stability_robustness" / "rq2_2_noise_robustness.csv"
    if stability_csv.exists():
        df_stab = pd.read_csv(stability_csv)
        add_para(doc,
            f"Chạy LIME lại 10 lần (10 seed khác nhau) trên cùng {len(df_stab)} flow của "
            f"cohort: Jaccard@5 trung bình GIỮA CÁC LẦN CHẠY = {df_stab['mean_pairwise_jaccard5'].mean():.4f} "
            f"(trung vị = {df_stab['mean_pairwise_jaccard5'].median():.4f}). Giá trị này càng gần 1 thì LIME "
            "càng ổn định giữa các lần chạy; giá trị quan sát được cho thấy LIME có một mức "
            "độ 'nhảy' kết quả đáng kể nếu không cố định seed."
        )
    if noise_csv.exists():
        df_noise = pd.read_csv(noise_csv)
        add_table_from_df(doc, df_noise)
        add_image(doc, run_dir / "gd9_stability_robustness" / "figures" / "noise_robustness.png", width_cm=12)
    conv_csv = run_dir / "gd9_stability_robustness" / "rq2_2_lime_convergence.csv"
    if conv_csv.exists():
        add_heading(doc, "6. Đường hội tụ theo num_samples", level=1)
        df_conv = pd.read_csv(conv_csv)
        add_table_from_df(doc, df_conv)
        add_image(doc, run_dir / "gd9_stability_robustness" / "figures" / "lime_convergence.png", width_cm=12)

    out_path = out_dir / "RQ2_Bao_cao_LIME_chi_tiet.docx"
    doc.save(str(out_path))
    logger.info("Đã lưu: %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
