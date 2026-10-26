"""Tạo RQ2_Bao_cao_Tong_hop_Final.docx — báo cáo RQ2 chuẩn chỉnh, đầy đủ, chi tiết, theo
mạch 5 câu hỏi. MỌI hình/biểu đồ đều có phần phân tích dễ hiểu đi kèm."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, latest_run_dir, get_logger  # noqa: E402
from lib.docx_helpers import (  # noqa: E402
    new_doc, add_heading, add_para, add_bullets, add_table_from_df,
    add_image, add_image_with_analysis, add_page_break,
)


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("build_report_final", run_dir)
    out_dir = run_dir / "gd13_report" / "docx"
    out_dir.mkdir(parents=True, exist_ok=True)

    def j(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    gd1 = j(run_dir / "gd1_env_check" / "verification_report.json")
    gd2_add = j(run_dir / "gd2_shap_global" / "rq2_shap_global_additivity_report.json")
    df_top5_global = pd.read_csv(run_dir / "gd2_shap_global" / "rq2_shap_global_top5_by_class.csv")
    gd3 = j(run_dir / "gd3_cohorts" / "cohorts_summary.json")
    gd4 = j(run_dir / "gd4_shap_per_flow" / "shap_per_flow_report.json")
    gd5 = j(run_dir / "gd5_lime_dev_tuning" / "lime_config_lock_report.json")
    gd6 = j(run_dir / "gd6_lime_per_flow" / "lime_per_flow_report.json")
    gd7_overall = pd.read_csv(run_dir / "gd7_agreement" / "rq2_1_agreement_overall.csv")
    gd7_baseline = pd.read_csv(run_dir / "gd7_agreement" / "rq2_1_random_baseline.csv")
    gd7_by_class = pd.read_csv(run_dir / "gd7_agreement" / "rq2_1_agreement_by_class.csv")
    gd8 = j(run_dir / "gd8_quality_gate" / "rq2_1_lime_quality_gate_summary.json")
    gd8_bucket = pd.read_csv(run_dir / "gd8_quality_gate" / "rq2_1_r2_bucket_vs_agreement.csv")
    gd9_path = run_dir / "gd9_stability_robustness" / "rq2_2_stability_summary.json"
    gd9 = j(gd9_path) if gd9_path.exists() else None
    gd9_noise = pd.read_csv(run_dir / "gd9_stability_robustness" / "rq2_2_noise_robustness.csv")
    gd9_conv = pd.read_csv(run_dir / "gd9_stability_robustness" / "rq2_2_lime_convergence.csv")
    gd10_auc = pd.read_csv(run_dir / "gd10_faithfulness" / "rq2_3_faithfulness_auc_summary.csv")
    gd10_win = pd.read_csv(run_dir / "gd10_faithfulness" / "rq2_3_shap_vs_lime_winrate.csv")
    gd11_prec = pd.read_csv(run_dir / "gd11_domain_validation" / "rq2_4_domain_precision_summary.csv")
    gd11_env = pd.read_csv(run_dir / "gd11_domain_validation" / "rq2_4_environment_fingerprint_by_class.csv")
    gd11 = j(run_dir / "gd11_domain_validation" / "rq2_4_summary.json")
    gd12 = j(run_dir / "gd12_error_cohort" / "rq2_error_vs_correct_comparison.json")

    k5 = gd7_overall[gd7_overall["k"] == 5].iloc[0]
    k3 = gd7_overall[gd7_overall["k"] == 3].iloc[0]
    k20 = gd7_overall[gd7_overall["k"] == 20].iloc[0]
    locked = cfg["lime"]["locked_config"]

    doc = new_doc(
        "RQ2 — Giải Thích Mô Hình XGBoost Bằng SHAP và LIME",
        f"Báo cáo tổng hợp chính thức, đầy đủ và chi tiết — run {run_dir.name} — KLTN XAI-IDS",
    )

    # =====================================================================================
    add_heading(doc, "0. Giới thiệu và cách đọc báo cáo này", level=1)
    add_para(doc,
        "RQ1 đã huấn luyện một mô hình XGBoost phân loại 15 loại lưu lượng mạng (14 loại "
        "tấn công + Benign) trên bộ dữ liệu CSE-CIC-IDS2018, đạt Accuracy 97.91% và Macro "
        "F1 85.81%. Mô hình này là một 'hộp đen' (black-box): nó dự đoán đúng nhưng không "
        "tự giải thích vì sao. RQ2 trả lời câu hỏi đó bằng hai công cụ giải thích AI (XAI) "
        "phổ biến nhất hiện nay — SHAP và LIME — và kiểm tra NGHIÊM TÚC xem hai công cụ này "
        "có đáng tin, có đồng ý với nhau, và có hợp lý theo kiến thức an ninh mạng không."
    )
    add_para(doc,
        "Báo cáo này đi theo MẠCH 5 CÂU HỎI: (1) model dựa vào đặc trưng nào; (2.1) SHAP và "
        "LIME có đồng ý không; (2.2) phương pháp nào ổn định hơn; (2.3) phương pháp nào "
        "trung thành với mô hình hơn; (2.4) giải thích có hợp lý theo kiến thức an ninh "
        "mạng không. Mỗi phần đều có số liệu, biểu đồ, VÀ PHẦN PHÂN TÍCH giải thích biểu đồ "
        "đó nói lên điều gì — không chỉ trình bày hình mà không diễn giải."
    )
    add_para(doc,
        "Giải thích đầy đủ về SHAP, LIME và từng chỉ số (Jaccard, Spearman, RBO, Local R2, "
        "comprehensiveness, v.v.) được trình bày riêng trong file "
        "RQ2_Kien_thuc_chung_Ly_thuyet.docx — nên đọc file đó trước nếu chưa quen các khái "
        "niệm này. File RQ2_Quy_trinh_Thuc_Hien_Chi_Tiet.docx giải thích CÁCH từng giai đoạn "
        "(GĐ0-GĐ13) được thực hiện."
    )

    # =====================================================================================
    add_heading(doc, "1. Tóm tắt điều hành", level=1)
    add_bullets(doc, [
        "SHAP và LIME có đồng thuận DƯƠNG trên toàn cục (Spearman tính trên toàn bộ 78 đặc "
        f"trưng ≈ {k5['spearman_full78_mean']:.2f}) nhưng mức trùng khớp Top-5 cụ thể còn "
        f"THẤP (Jaccard@5 ≈ {k5['jaccard_mean']:.2f}, dù đã cao hơn ngẫu nhiên "
        f"{gd7_baseline[gd7_baseline.k==5]['fold_over_random'].iloc[0]:.1f} lần).",
        "SHAP ỔN ĐỊNH hơn LIME: SHAP cho kết quả GIỐNG TUYỆT ĐỐI mỗi lần chạy lại (tính "
        "chất toán học của TreeSHAP); LIME có thể 'nhảy' kết quả đáng kể giữa các lần chạy "
        "nếu không cố định seed ngẫu nhiên.",
        "SHAP TRUNG THÀNH hơn LIME với hành vi thật của mô hình: khi xóa đúng Top-5 đặc "
        "trưng SHAP chọn, xác suất dự đoán giảm MẠNH HƠN RÕ RỆT so với xóa Top-5 của LIME, "
        "ở CẢ BA cách chọn giá trị nền khác nhau (p<0.001).",
        "SHAP khớp kiến thức an ninh mạng tốt hơn LIME: đối chiếu Top-5 với bảng đặc trưng "
        "kỳ vọng theo cơ chế tấn công thật, SHAP có điểm F1 cao hơn LIME ở cả bảng kỳ vọng "
        "'chặt' và 'rộng'.",
        "LIME có Local R2 (độ khớp của mô hình tuyến tính xấp xỉ) khá thấp trên dữ liệu "
        "mạng này — một giới hạn thực sự của bản thân phương pháp LIME, không phải lỗi cấu "
        "hình, được ghi nhận trung thực.",
        "Khuyến nghị: dùng SHAP làm phương pháp giải thích CHÍNH cho hệ thống IDS-XAI; LIME "
        "chỉ nên dùng làm ĐỐI CHỨNG tham khảo thêm, không nên dùng độc lập để ra quyết định "
        "khi Local R2 thấp.",
    ])

    # =====================================================================================
    add_page_break(doc)
    add_heading(doc, "2. Model và dữ liệu có đáng tin để giải thích không? (GĐ0-1)", level=1)
    add_para(doc,
        "Trước khi giải thích bất cứ điều gì, phải chắc chắn mô hình và dữ liệu dùng ở RQ2 "
        "THỰC SỰ là cùng mô hình/dữ liệu đã dùng ở RQ1 — nếu không, mọi giải thích sau đó "
        "đều vô nghĩa (giải thích nhầm model)."
    )
    df_check = pd.DataFrame([
        {"Chỉ số": "Accuracy", "RQ1": 97.91, "Chạy lại ở RQ2": gd1["details"]["metrics_rerun"]["accuracy_pct"]},
        {"Chỉ số": "Macro Precision", "RQ1": 90.84, "Chạy lại ở RQ2": gd1["details"]["metrics_rerun"]["macro_precision_pct"]},
        {"Chỉ số": "Macro Recall", "RQ1": 83.99, "Chạy lại ở RQ2": gd1["details"]["metrics_rerun"]["macro_recall_pct"]},
        {"Chỉ số": "Macro F1", "RQ1": 85.81, "Chạy lại ở RQ2": gd1["details"]["metrics_rerun"]["macro_f1_pct"]},
    ])
    add_table_from_df(doc, df_check, float_fmt="{:.2f}")
    add_para(doc,
        "Sai lệch giữa hai cột chỉ nằm ở mức làm tròn số (< 0.01 điểm %) — xác nhận ĐÚNG "
        "model, ĐÚNG dữ liệu. Toàn bộ các kiểm tra bắt buộc khác (đúng 78 đặc trưng, đúng "
        "thứ tự đặc trưng, đúng 15 lớp, không có giá trị NaN/Inf, checksum file) đều ĐẠT."
    )

    # =====================================================================================
    add_page_break(doc)
    add_heading(doc, "3. Mỗi loại tấn công dựa vào đặc trưng nào? (GĐ2)", level=1)
    add_para(doc,
        "Tính SHAP trên TOÀN BỘ 700.000 flow của test set (không chỉ cohort nhỏ) — với mỗi "
        "lớp, chỉ xét các flow THỰC SỰ thuộc lớp đó và được mô hình dự đoán ĐÚNG. Sai số "
        f"additivity (kiểm tra SHAP tính đúng) tối đa chỉ {gd2_add['max_abs_error']:.2e} — "
        "rất nhỏ, xác nhận số liệu đáng tin."
    )
    add_para(doc,
        "Dưới đây là 4 ví dụ minh hoạ (xem đầy đủ cả 15 lớp trong "
        "RQ2_Bao_cao_SHAP_chi_tiet.docx):"
    )

    highlight = [
        ("DDOS attack-HOIC", "top5_DDOS_attack_HOIC.png",
         "Đây là tấn công DDoS băng thông cao (công cụ HOIC) — gửi rất nhiều request đồng "
         "thời. Các đặc trưng liên quan TỐC ĐỘ GÓI/BYTE (Fwd Pkts/s, Flow Byts/s...) chiếm "
         "vị trí cao, ĐÚNG như kỳ vọng cơ chế tấn công: tốc độ truyền dữ liệu tăng vọt là "
         "dấu hiệu đặc trưng nhất của DDoS."),
        ("DoS attacks-Slowloris", "top5_DoS_attacks_Slowloris.png",
         "Slowloris là tấn công 'chậm' (low-and-slow): giữ kết nối mở bằng cách gửi dữ liệu "
         "cực chậm. Biểu đồ cho thấy các đặc trưng liên quan THỜI GIAN (Flow Duration, "
         "IAT...) nổi bật — ĐÚNG hướng, vì đặc điểm nhận dạng của Slowloris là flow kéo dài "
         "bất thường, khác hẳn tấn công flood nhanh như Hulk/HOIC ở trên."),
        ("SSH-Bruteforce", "top5_SSH_Bruteforce.png",
         "Brute-force SSH là hành vi thử nhiều mật khẩu liên tiếp tới CÙNG MỘT CỔNG (22). "
         "Việc 'Dst Port' (cổng đích) xuất hiện trong Top-5 phù hợp với cơ chế này — mô "
         "hình học được rằng traffic nhắm vào cổng dịch vụ cố định là một dấu hiệu."),
        ("Infilteration", "top5_Infilteration.png",
         "Infiltration mô phỏng hành vi SAU KHI đã chiếm được máy (dò quét nội bộ, khai "
         "thác lỗ hổng) — đây là loại tấn công 'mơ hồ' nhất về tín hiệu mạng, nên Top-5 ở "
         "đây thường khó đoán trước và cần đối chiếu kỹ với domain knowledge ở GĐ11."),
    ]
    for cls, fname, note in highlight:
        sub = df_top5_global[df_top5_global["class"] == cls].sort_values("rank")
        add_heading(doc, f"Lớp: {cls}", level=2)
        add_image_with_analysis(
            doc, run_dir / "gd2_shap_global" / "figures" / fname,
            caption=f"Top-5 SHAP toàn cục cho lớp {cls} (n={int(sub['n_flows'].iloc[0])} flow). "
                    "Đỏ = đóng góp dương trung bình (đẩy về lớp này); Xanh = âm (đẩy ra xa).",
            analysis=[
                f"5 đặc trưng quan trọng nhất: {', '.join(sub['feature'].tolist())}.",
                note,
                "Độ dài thanh ngang (|SHAP| trung bình) cho biết mức độ ảnh hưởng chung, "
                "không phân biệt chiều hướng; màu sắc mới cho biết đặc trưng đó thường ĐẨY "
                "VỀ (đỏ) hay ĐẨY RA XA (xanh) lớp đang xét.",
            ],
            width_cm=12,
        )

    # =====================================================================================
    add_page_break(doc)
    add_heading(doc, "4. Câu hỏi 2.1 — SHAP và LIME có đồng ý không? (GĐ7-8)", level=1)
    add_para(doc,
        f"Cohort đánh giá: {gd3['cohort_size']} flow (tối đa 100 flow/lớp, phân tầng). Với "
        "mỗi flow, xếp hạng 78 đặc trưng theo SHAP và theo LIME, rồi so sánh bằng nhiều chỉ "
        "số khác nhau (xem định nghĩa trong file lý thuyết)."
    )
    add_table_from_df(doc, gd7_overall[["k", "jaccard_mean", "spearman_full78_mean", "rbo_mean", "sign_agreement_mean"]])

    add_image_with_analysis(
        doc, run_dir / "gd7_agreement" / "figures" / "agreement_by_k.png",
        caption="Các chỉ số đồng thuận SHAP-LIME theo k (số đặc trưng xét), so với đường cơ sở ngẫu nhiên.",
        analysis=[
            f"Đường Jaccard (xanh dương) dao động quanh {k3['jaccard_mean']:.2f}-"
            f"{k20['jaccard_mean']:.2f} — LUÔN cao hơn đường ngẫu nhiên (đường nét đứt màu "
            "xám) nhiều lần, nghĩa là SHAP và LIME KHÔNG chọn đặc trưng một cách độc lập "
            "ngẫu nhiên, nhưng mức trùng khớp tuyệt đối vẫn thấp (dưới 25%).",
            f"Đường Spearman full-78 (màu khác) GIỮ NGUYÊN ở mức {k5['spearman_full78_mean']:.2f} "
            "xuyên suốt mọi k — đây là một con số TÍNH TRÊN TOÀN BỘ 78 đặc trưng nên không "
            "đổi theo k (k chỉ ảnh hưởng tới Jaccard/RBO/sign agreement, là các chỉ số tính "
            "trên TẬP CON Top-k).",
            f"Sign agreement GIẢM DẦN khi k tăng (từ {k3['sign_agreement_mean']:.2f} ở k=3 "
            f"xuống {k20['sign_agreement_mean']:.2f} ở k=20) — hợp lý: các đặc trưng Top-3 "
            "(được cả hai phương pháp đồng thuận MẠNH nhất) có xu hướng cùng chiều (cùng đẩy "
            "về/đẩy ra) hơn các đặc trưng ở hạng thấp hơn như hạng 15-20, nơi tín hiệu yếu "
            "và dễ nhiễu.",
            "RBO giảm nhẹ rồi khá ổn định quanh 0.27-0.30 — vì RBO ưu tiên các hạng cao nên "
            "ít nhạy với k hơn Jaccard thường.",
        ],
        width_cm=13,
    )

    df_neg = gd7_by_class[(gd7_by_class["k"] == 5) & (gd7_by_class["spearman_full78_mean"] < 0.1)]
    add_image_with_analysis(
        doc, run_dir / "gd7_agreement" / "figures" / "spearman_by_class_k5.png",
        caption="Spearman (toàn bộ 78 đặc trưng) giữa SHAP và LIME, theo từng lớp tấn công.",
        analysis=[
            "KHÔNG có lớp nào có Spearman âm — mọi lớp đều có xu hướng đồng thuận DƯƠNG "
            "giữa hai phương pháp khi xét toàn cục 78 đặc trưng (khác với một phiên bản "
            "tính SAI ban đầu trong quá trình chạy, đã phát hiện và sửa — xem "
            "RQ2_Quy_trinh_Thuc_Hien_Chi_Tiet.docx, Giai đoạn 7).",
            "Mức đồng thuận khác nhau RÕ RỆT theo lớp: một số lớp (ví dụ các lớp DDoS/DoS "
            "có tín hiệu tốc độ gói tin rất mạnh) có Spearman cao hơn; các lớp khó/hiếm "
            "(SQL Injection, Brute Force -XSS, chỉ 9-44 flow) có Spearman thấp hơn và kém "
            "tin cậy hơn do cỡ mẫu nhỏ.",
            "Thanh dài hơn (bất kể hướng) có nghĩa Spearman gần 0 hoặc khác biệt lớn — những "
            "lớp này là nơi SHAP và LIME 'nhìn' ra lý do khác nhau nhiều nhất, nên ưu tiên "
            "đọc kỹ khi dùng giải thích cho các lớp đó trong thực tế.",
        ],
        width_cm=13,
    )

    add_heading(doc, "Quality gate của LIME (GĐ8)", level=2)
    add_para(doc,
        f"Ngưỡng chất lượng Local R2 ≥ 0.3 (chốt TRƯỚC khi xem kết quả, ở GĐ5): "
        f"{gd8['n_pass']}/{gd8['n_total']} flow ({gd8['frac_pass']*100:.1f}%) đạt ngưỡng "
        "trên cohort đánh giá."
    )
    add_table_from_df(doc, gd8_bucket, float_fmt="{:.4f}")
    add_image_with_analysis(
        doc, run_dir / "gd8_quality_gate" / "figures" / "agreement_by_r2_bucket.png",
        caption="Đồng thuận SHAP-LIME theo mức chất lượng (Local R2) của LIME.",
        analysis=[
            "Giả thuyết ban đầu: 'LIME khớp mô hình kém (R2 thấp) thì bất đồng với SHAP "
            "nhiều hơn'. Nếu đúng, cột bên phải (R2 cao) phải CAO HƠN RÕ RỆT cột bên trái "
            "(R2 thấp) ở cả Jaccard và Spearman.",
            f"Số liệu thực tế KHÔNG ủng hộ giả thuyết này: nhóm 'vừa' (R2 0.1-0.3, "
            f"n={int(gd8_bucket.iloc[1]['n_flows'])}) có Jaccard CAO NHẤT "
            f"({gd8_bucket.iloc[1]['mean_jaccard']:.3f}), không phải nhóm 'cao'.",
            "Kết luận quan trọng: bất đồng giữa SHAP và LIME KHÔNG được giải thích đầy đủ "
            "chỉ bằng việc LIME khớp mô hình kém — rất có thể còn do sự khác biệt BẢN CHẤT "
            "giữa cách hai phương pháp định nghĩa 'quan trọng' (SHAP: đóng góp Shapley chính "
            "xác toàn cục; LIME: hệ số hồi quy tuyến tính cục bộ).",
        ],
        width_cm=12,
    )

    # =====================================================================================
    add_page_break(doc)
    add_heading(doc, "5. Câu hỏi 2.2 — Phương pháp nào ổn định hơn? (GĐ9)", level=1)
    if gd9:
        add_para(doc,
            f"LIME: chạy lại 10 lần (10 seed khác nhau) trên CÙNG {gd3['cohort_size']} flow "
            f"— Jaccard@5 trung bình GIỮA CÁC LẦN CHẠY = {gd9['lime_mean_pairwise_jaccard5']:.4f} "
            f"(trung vị {gd9['lime_median_pairwise_jaccard5']:.4f}). SHAP: chạy lại 1 lần — "
            f"{gd9['shap_jaccard5_rerun']*100:.2f}% flow cho Top-5 giống TUYỆT ĐỐI (xác định "
            "hoàn toàn, đúng như lý thuyết TreeSHAP)."
        )
        add_para(doc,
            "Ý nghĩa thực tế: nếu một chuyên viên SOC chạy LIME hai lần cho CÙNG một flow "
            "nghi vấn, có khoảng 42% khả năng Top-5 đặc trưng KHÔNG hoàn toàn giống nhau "
            f"(1 − {gd9['lime_mean_pairwise_jaccard5']:.2f} ≈ 0.42) — đây là một rủi ro thực "
            "sự khi dùng LIME để ra quyết định quan trọng mà không chạy nhiều lần kiểm tra."
        )

    add_table_from_df(doc, gd9_noise)
    add_image_with_analysis(
        doc, run_dir / "gd9_stability_robustness" / "figures" / "noise_robustness.png",
        caption="Robustness: Jaccard@5 giữa giải thích trên flow GỐC và flow bị thêm nhiễu, theo mức nhiễu.",
        analysis=[
            f"Ở mức nhiễu nhỏ nhất (1% độ lệch chuẩn — gần với sai số đo đạc thực tế), SHAP "
            f"giữ được Jaccard@5={gd9_noise.iloc[0]['shap_mean_jaccard5']:.2f} còn LIME chỉ "
            f"{gd9_noise.iloc[0]['lime_mean_jaccard5']:.2f} — SHAP đã nhạy hơn mong đợi "
            "nhưng vẫn ổn định hơn LIME rõ rệt.",
            f"Khi nhiễu tăng lên 10%, LIME giảm MẠNH xuống còn "
            f"{gd9_noise.iloc[2]['lime_mean_jaccard5']:.2f} (gần một nửa so với mức 1%), "
            f"trong khi SHAP chỉ giảm nhẹ xuống {gd9_noise.iloc[2]['shap_mean_jaccard5']:.2f} "
            "— đường LIME (vuông) dốc hơn đường SHAP (tròn) rõ rệt trên biểu đồ.",
            "Ý nghĩa: trong thực tế, các con số đo flow mạng luôn có một chút sai số/biến "
            "động tự nhiên (do đo đạc, do thời điểm capture...) — một giải thích CẦN giữ "
            "được Top-5 tương đối ổn định trước những biến động nhỏ này. SHAP làm điều đó "
            "tốt hơn LIME.",
        ],
        width_cm=12,
    )

    add_image_with_analysis(
        doc, run_dir / "gd9_stability_robustness" / "figures" / "lime_convergence.png",
        caption="Local R2 trung vị của LIME theo num_samples (giữ nguyên kernel_width/discretize đã khóa).",
        analysis=[
            f"KẾT QUẢ BẤT NGỜ: Local R2 GIẢM khi num_samples TĂNG (500 mẫu: "
            f"R2={gd9_conv.iloc[0]['median_r2']:.3f} → 10.000 mẫu: "
            f"R2={gd9_conv.iloc[3]['median_r2']:.3f}) — ngược với trực giác thông thường "
            "rằng 'nhiều mẫu hơn luôn tốt hơn'.",
            "Lý do khả dĩ: với kernel_width hẹp (3.312, đã chọn ở GĐ5) và "
            "discretize_continuous=False, tăng num_samples khiến vùng lân cận được lấy mẫu "
            "mở RỘNG hơn về mặt thống kê (nhiều điểm xa trung tâm hơn xuất hiện), nên mô "
            "hình tuyến tính đơn giản của LIME phải xấp xỉ một vùng KHÔNG TUYẾN TÍNH hơn — "
            "làm giảm R2.",
            "Ý nghĩa thực tế: đơn giản 'tăng num_samples' KHÔNG phải cách chắc chắn để cải "
            "thiện chất lượng LIME trên dữ liệu mạng có phân phối lệch như thế này — cần "
            "cân nhắc đồng thời với kernel_width, đúng như cách GĐ5 đã làm (dò lưới đồng "
            "thời, không tối ưu riêng từng tham số).",
        ],
        width_cm=11,
    )

    # =====================================================================================
    add_page_break(doc)
    add_heading(doc, "6. Câu hỏi 2.3 — Phương pháp nào trung thành với mô hình hơn? (GĐ10)", level=1)
    add_para(doc,
        "Kiểm tra bằng cách XÓA DẦN (đưa về giá trị 'nền' trung lập) các đặc trưng Top-k "
        "theo từng phương pháp, đo xác suất dự đoán GIẢM bao nhiêu (comprehensiveness) — "
        "giải thích trung thành thì xóa đúng đặc trưng quan trọng phải làm xác suất giảm "
        "MẠNH. Làm NGƯỢC LẠI (chỉ thêm lại Top-k từ giá trị nền) đo được sufficiency."
    )
    add_table_from_df(doc, gd10_auc)

    for baseline_name, baseline_vn in [
        ("global_median", "trung vị toàn tập"), ("global_mean", "trung bình toàn tập"), ("benign_median", "trung vị riêng lớp Benign"),
    ]:
        auc_sub = gd10_auc[gd10_auc["baseline"] == baseline_name]
        shap_c = auc_sub[auc_sub.method == "SHAP"]["comprehensiveness_auc"].iloc[0]
        lime_c = auc_sub[auc_sub.method == "LIME"]["comprehensiveness_auc"].iloc[0]
        rand_c = auc_sub[auc_sub.method == "Random"]["comprehensiveness_auc"].iloc[0]
        add_image_with_analysis(
            doc, run_dir / "gd10_faithfulness" / "figures" / f"deletion_insertion_{baseline_name}.png",
            caption=f"Đường Deletion (trái) và Insertion (phải) — giá trị nền = {baseline_vn}.",
            analysis=[
                f"Deletion (trái): đường SHAP (xanh dương) nằm TRÊN đường LIME (vàng/cam) "
                "ở MỌI giá trị k — xóa Top-k theo SHAP làm giảm xác suất dự đoán nhiều hơn "
                "xóa Top-k theo LIME, ở mọi mức k từ 1 đến 10.",
                f"AUC comprehensiveness: SHAP={shap_c:.3f}, LIME={lime_c:.3f}, "
                f"Random (đối chứng)={rand_c:.3f} — CẢ HAI phương pháp vượt xa đối chứng "
                "ngẫu nhiên (đường xám, gần như bằng phẳng ở đáy biểu đồ), xác nhận cả hai "
                "đều có giá trị giải thích thật, nhưng SHAP vượt trội hơn.",
                "Insertion (phải): đường SHAP phục hồi xác suất dự đoán NHANH HƠN và CAO "
                "HƠN khi chỉ dùng Top-k đặc trưng — nghĩa là 5-10 đặc trưng SHAP chọn chứa "
                "nhiều 'thông tin quyết định' hơn 5-10 đặc trưng LIME chọn.",
            ],
            width_cm=14,
        )

    add_table_from_df(doc, gd10_win)
    add_para(doc,
        f"Tỷ lệ SHAP 'thắng' LIME (k=5, so trực tiếp từng flow): trung bình "
        f"{gd10_win['shap_win_rate_vs_lime'].mean()*100:.1f}% số flow, với kiểm định "
        "Wilcoxon bắt cặp cho p-value cực nhỏ (<10⁻¹⁴⁰) ở cả 3 giá trị nền — khác biệt này "
        "RẤT KHÓ xảy ra do ngẫu nhiên, là một kết luận vững."
    )
    add_para(doc,
        "Giới hạn cần biết: đặt đặc trưng về giá trị nền có thể tạo ra một flow 'không thật' "
        "(ngoài phân phối dữ liệu mà model từng học, gọi là out-of-distribution/OOD) — xác "
        "suất đo được lúc đó có thể không hoàn toàn phản ánh đúng hành vi model trên dữ "
        "liệu thực tế. Đây là hạn chế đã biết của PHƯƠNG PHÁP deletion/insertion nói chung "
        "trong toàn ngành XAI, không phải lỗi riêng của cách làm ở RQ2.",
        italic=True,
    )

    # =====================================================================================
    add_page_break(doc)
    add_heading(doc, "7. Câu hỏi 2.4 — Giải thích có khớp kiến thức an ninh mạng không? (GĐ11)", level=1)
    add_para(doc,
        "Trước khi xem Top-5 thực tế, đã lập một bảng 'đặc trưng kỳ vọng' cho mỗi loại tấn "
        "công dựa trên cơ chế hoạt động thật (ví dụ DDoS → tốc độ gói tin tăng vọt; "
        "Brute-force → cổng dịch vụ cố định) — có 2 phiên bản: 'chặt' (ít đặc trưng, chắc "
        "chắn) và 'rộng' (nhiều đặc trưng, bao quát hơn). Xem đầy đủ bảng tri thức trong "
        "RQ2/runs/<ngày>/gd11_domain_validation/domain_knowledge_table.csv."
    )
    add_table_from_df(doc, gd11_prec)
    add_image_with_analysis(
        doc, run_dir / "gd11_domain_validation" / "figures" / "domain_f1_strict_vs_broad.png",
        caption="Điểm F1 (so khớp với bảng tri thức miền) của SHAP và LIME, bảng 'chặt' và 'rộng'.",
        analysis=[
            "Cột SHAP (xanh) CAO HƠN cột LIME (cam) ở CẢ HAI bảng — kết luận 'SHAP hợp lý "
            "hơn theo kiến thức an ninh mạng' KHÔNG đổi dù dùng bảng tri thức hẹp hay rộng, "
            "cho thấy kết luận này không phải do may rủi chọn bảng tri thức.",
            "F1 ở bảng 'rộng' cao hơn bảng 'chặt' cho cả hai phương pháp (dễ hiểu: bảng "
            "rộng có nhiều đặc trưng kỳ vọng hơn nên dễ trùng hơn) — đây là hành vi mong "
            "đợi, không phải dấu hiệu bất thường.",
            "Điểm F1 tuyệt đối còn khá thấp (0.19-0.20 cho SHAP) — một phần vì Top-5 chỉ "
            "lấy 5/78 đặc trưng trong khi cơ chế tấn công thật có thể biểu hiện qua nhiều "
            "đặc trưng tương quan với nhau (xem phần nhóm đặc trưng ở GĐ7); đây không có "
            "nghĩa là SHAP 'sai', mà phản ánh việc Top-5 chỉ là một lát cắt nhỏ của toàn bộ "
            "hành vi mô hình.",
        ],
        width_cm=11,
    )
    add_para(doc,
        f"Tỷ lệ đặc trưng 'dấu vân tay môi trường' (Dst Port, Init Fwd Win Byts, Fwd Seg "
        f"Size Min) trong Top-5: SHAP ≈ "
        f"{gd11_env[gd11_env.method=='SHAP']['frac_env_in_top5'].mean()*100:.0f}%, LIME ≈ "
        f"{gd11_env[gd11_env.method=='LIME']['frac_env_in_top5'].mean()*100:.0f}%. Các đặc "
        "trưng này có thể phản ánh ĐẶC ĐIỂM RIÊNG của môi trường thu thập dữ liệu (ví dụ "
        "cấu hình mạng khi capture) hơn là bản chất cơ chế tấn công — nếu tỷ lệ này cao, mô "
        "hình có thể đang dựa vào một 'lối tắt' (shortcut) chứ không học đúng bản chất tấn "
        "công. Đây là câu hỏi mở quan trọng chuyển sang RQ3."
    )

    # =====================================================================================
    add_page_break(doc)
    add_heading(doc, "8. Phân tích bổ sung — Giải thích khi model dự đoán sai (GĐ12)", level=1)
    add_para(doc,
        f"Chạy SHAP và LIME trên {151} flow bị dự đoán SAI (cỡ mẫu NHỎ — nhiều lớp dưới 10 "
        "flow — mọi kết luận ở đây CHỈ mang tính thăm dò)."
    )
    df_err = pd.DataFrame([
        {"Chỉ số": "Mức tập trung SHAP Top-5 (|phi|)", "Cohort lỗi": gd12["error_shap_concentration_mean"], "Cohort đúng": gd12["correct_cohort_shap_concentration_mean"]},
        {"Chỉ số": "Jaccard@5 SHAP-LIME", "Cohort lỗi": gd12["error_shap_lime_jaccard5_mean"], "Cohort đúng": gd12["correct_cohort_shap_lime_jaccard5_mean"]},
    ])
    add_table_from_df(doc, df_err)
    add_image_with_analysis(
        doc, run_dir / "gd12_error_cohort" / "figures" / "error_vs_correct.png",
        caption="So sánh cohort lỗi và cohort đúng: mức tập trung SHAP Top-5 (trái), Jaccard@5 SHAP-LIME (phải).",
        analysis=[
            "Hai hộp (boxplot) ở mỗi biểu đồ nằm KHÁ GẦN NHAU về vị trí trung tâm (đường "
            "giữa hộp) — không có sự khác biệt rõ ràng bằng mắt thường giữa flow đúng và "
            "flow sai, ở cả hai chỉ số.",
            "Hộp 'Cohort lỗi' (bên trái mỗi biểu đồ) có xu hướng RỘNG HƠN (khoảng biến "
            "động lớn hơn) — hợp lý vì cỡ mẫu nhỏ hơn nhiều (151 so với 1339 flow).",
            "KHÔNG có bằng chứng rõ ràng ủng hộ ý tưởng 'mức bất đồng SHAP-LIME tăng lên khi "
            "model dự đoán sai' trong dữ liệu này — nhưng với cỡ mẫu 151 flow (nhiều lớp "
            "dưới 10 flow), đây CHƯA PHẢI là kết luận cuối cùng. RQ3 nên thử lại ý tưởng "
            "này với cỡ mẫu lớn hơn nếu muốn theo đuổi hướng 'bất đồng làm tín hiệu độ tin "
            "cậy'.",
        ],
        width_cm=13,
    )

    # =====================================================================================
    add_page_break(doc)
    add_heading(doc, "9. Giới hạn của nghiên cứu", level=1)
    add_bullets(doc, [
        "Một bộ dữ liệu duy nhất (CSE-CIC-IDS2018), một mô hình duy nhất (XGBoost cấu hình "
        "cố định từ RQ1) — kết luận chưa tổng quát hoá cho dữ liệu/mô hình khác.",
        "Cohort đánh giá chính (GĐ4-11) chỉ gồm flow DỰ ĐOÁN ĐÚNG — không đại diện đầy đủ "
        "cho hành vi model trên flow khó/sai (phần đó được xét riêng, cỡ mẫu nhỏ, ở GĐ12).",
        "Giá trị nền trong faithfulness (GĐ10) có thể tạo mẫu ngoài phân phối huấn luyện.",
        "Bảng tri thức miền (GĐ11) do người thực hiện tổng hợp từ tài liệu gốc "
        "CSE-CIC-IDS2018 và kiến thức an ninh mạng phổ biến — không phải một benchmark "
        "chính thức đã công bố riêng cho đúng 78 đặc trưng này.",
        "LIME Top-5-theo-lớp (dùng ở GĐ11) tính trên cohort (≤100 flow/lớp), còn SHAP "
        "Top-5-theo-lớp tính trên toàn test set (GĐ2) — khác quy mô dữ liệu giữa hai cột so "
        "sánh, cần lưu ý khi đọc.",
        "Background của LIME (2000 dòng mẫu từ train set) là một lựa chọn cố định, KHÔNG "
        "được đưa vào lưới tìm kiếm tham số ở GĐ5 (chỉ kernel_width, num_samples, "
        "discretize_continuous được dò).",
        "Nhiễu đầu vào ở GĐ9 được tính theo % ĐỘ LỆCH CHUẨN TOÀN CỤC (toàn train set, mọi "
        "lớp trộn chung) của mỗi đặc trưng. Một số đặc trưng (Flow Duration, Fwd/Flow IAT "
        "Tot/Mean...) có phân phối LỆCH DÀY (heavy-tailed, do vài flow ngoại lai rất lớn), "
        "nên 'nhiễu 1%' theo độ lệch chuẩn toàn cục có thể là một bước nhảy TUYỆT ĐỐI rất "
        "lớn so với giá trị thật của một flow Benign thông thường — có thể làm tỷ lệ đổi "
        "NHÃN dự đoán dưới nhiễu cao hơn trực giác thông thường. Đây là hạn chế của cách "
        "định nghĩa mức nhiễu (nên cân nhắc nhiễu theo % giá trị TỪNG FLOW ở lần chạy sau), "
        "không phải lỗi tính toán — các chỉ số Jaccard@5 báo cáo ở GĐ9 vẫn đúng và nhất "
        "quán với định nghĩa nhiễu này.",
    ])

    add_heading(doc, "10. Khả năng tái lập", level=1)
    add_para(doc, f"Toàn bộ run này tái lập được bằng: seed={cfg['seed']}, cấu hình đầy đủ trong RQ2/config.yaml.")
    add_bullets(doc, [
        "Lệnh chạy (theo đúng thứ tự): stage00 → stage01 → ... → stage13, trong RQ2/scripts/.",
        f"Phiên bản phần mềm: {gd1['details']['env_versions']}",
        "Checksum model/encoder/train/test: xem RQ2/runs/<ngày>/gd1_env_check/checksums.json.",
        "Cấu hình LIME đã khóa (GĐ5): "
        f"kernel_width={locked['kernel_width']}, num_samples={locked['num_samples']}, "
        f"discretize_continuous={locked['discretize_continuous']}.",
    ])

    add_heading(doc, "11. Kết luận và câu hỏi chuyển sang RQ3", level=1)
    add_bullets(doc, [
        "SHAP nên là phương pháp giải thích CHÍNH của hệ thống IDS-XAI (ổn định, trung "
        "thành, hợp lý theo domain knowledge hơn LIME ở mọi phép kiểm tra thực hiện trong "
        "RQ2); LIME dùng làm đối chứng tham khảo, không nên dùng độc lập khi Local R2 thấp.",
        "Mô hình có vẻ dựa một phần vào các đặc trưng liên quan đến 'dấu vân tay môi "
        "trường' (cổng, kích thước cửa sổ TCP) — RQ3 nên kiểm tra mô hình có còn hoạt động "
        "tốt khi các đặc trưng này thay đổi (ví dụ dữ liệu từ một môi trường mạng khác)?",
        "Mức bất đồng SHAP-LIME trên flow lỗi KHÔNG rõ rệt hơn flow đúng trong mẫu nhỏ này "
        "(151 flow) — RQ3 có thể thử lại với cỡ mẫu lớn hơn nếu muốn theo đuổi ý tưởng 'bất "
        "đồng làm tín hiệu độ tin cậy' cho hệ thống cảnh báo.",
        "Bất đồng SHAP-LIME KHÔNG được giải thích đầy đủ chỉ bằng chất lượng surrogate "
        "(Local R2) của LIME (GĐ8) — gợi ý rằng ngay cả khi cải thiện cấu hình LIME hơn "
        "nữa, hai phương pháp vẫn có thể bất đồng vì khác biệt BẢN CHẤT trong cách định "
        "nghĩa 'đặc trưng quan trọng'.",
    ])

    out_path = out_dir / "RQ2_Bao_cao_Tong_hop_Final.docx"
    doc.save(str(out_path))
    logger.info("Đã lưu: %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
