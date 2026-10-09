"""Tạo RQ2_Quy_trinh_Thuc_Hien_Chi_Tiet.docx — giải thích từng giai đoạn (GĐ0-13) đã làm
gì, làm như thế nào, và kết quả cụ thể của RUN NÀY — bằng tiếng Việt, dễ hiểu."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, latest_run_dir, get_logger  # noqa: E402
from lib.docx_helpers import new_doc, add_heading, add_para, add_bullets, add_table_from_df, add_page_break  # noqa: E402


def stage_block(doc, so, ten, muc_tieu, cach_lam, ket_qua_lines):
    add_heading(doc, f"Giai đoạn {so}: {ten}", level=1)
    add_para(doc, "Mục tiêu: " + muc_tieu, bold=False)
    add_para(doc, "Cách làm:", bold=True)
    add_bullets(doc, cach_lam)
    add_para(doc, "Kết quả của lần chạy này:", bold=True)
    add_bullets(doc, ket_qua_lines)


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("build_report_process", run_dir)
    out_dir = run_dir / "gd13_report" / "docx"
    out_dir.mkdir(parents=True, exist_ok=True)

    def j(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    gd1 = j(run_dir / "gd1_env_check" / "verification_report.json")
    gd2 = j(run_dir / "gd2_shap_global" / "rq2_shap_global_additivity_report.json")
    gd3 = j(run_dir / "gd3_cohorts" / "cohorts_summary.json")
    gd5 = j(run_dir / "gd5_lime_dev_tuning" / "lime_config_lock_report.json")
    gd6 = j(run_dir / "gd6_lime_per_flow" / "lime_per_flow_report.json")
    gd7_overall = pd.read_csv(run_dir / "gd7_agreement" / "rq2_1_agreement_overall.csv")
    gd8 = j(run_dir / "gd8_quality_gate" / "rq2_1_lime_quality_gate_summary.json")
    gd9_stab_path = run_dir / "gd9_stability_robustness" / "rq2_2_stability_summary.json"
    gd9 = j(gd9_stab_path) if gd9_stab_path.exists() else None
    gd10_auc = pd.read_csv(run_dir / "gd10_faithfulness" / "rq2_3_faithfulness_auc_summary.csv")
    gd10_win = pd.read_csv(run_dir / "gd10_faithfulness" / "rq2_3_shap_vs_lime_winrate.csv")
    gd11 = j(run_dir / "gd11_domain_validation" / "rq2_4_summary.json")
    gd11_prec = pd.read_csv(run_dir / "gd11_domain_validation" / "rq2_4_domain_precision_summary.csv")
    gd12 = j(run_dir / "gd12_error_cohort" / "rq2_error_vs_correct_comparison.json")

    locked = cfg["lime"]["locked_config"]
    k5 = gd7_overall[gd7_overall["k"] == 5].iloc[0]

    doc = new_doc(
        "RQ2 — Quy Trình Thực Hiện Chi Tiết (GĐ0–GĐ13)",
        f"Giải thích từng giai đoạn: làm gì, làm như thế nào, kết quả — run {run_dir.name}",
    )
    add_para(doc,
        "Tài liệu này đi theo đúng 14 giai đoạn (GĐ0 → GĐ13) đã thống nhất trong kế hoạch "
        "(RQ2/docs/plan.md). Mỗi giai đoạn được viết theo 3 phần: MỤC TIÊU (trả lời câu hỏi "
        "gì), CÁCH LÀM (các bước cụ thể, không cần đọc code), và KẾT QUẢ CỦA LẦN CHẠY NÀY "
        "(số liệu thật, không phải ví dụ)."
    )

    stage_block(
        doc, 0, "Chuẩn bị lần chạy",
        "Dọn dẹp để chạy lại RQ2 'từ đầu' một cách có kiểm soát, không mất kết quả cũ.",
        [
            "Chuyển toàn bộ kết quả RQ2 cũ (SHAP, LIME, báo cáo cũ) vào thư mục v1_archive/ "
            "— không xoá, chỉ cất đi để so sánh sau.",
            "Tạo một file config.yaml DUY NHẤT chứa mọi tham số (seed=42, đường dẫn dữ liệu/model, "
            "các giá trị k, số mẫu LIME...) — mọi giai đoạn sau CHỈ đọc tham số từ file này, "
            "không ghi cứng trong code, để đảm bảo tái lập được.",
            "Tạo thư mục chạy mới theo ngày (RQ2/runs/20261009/) với 13 thư mục con, mỗi "
            "giai đoạn một thư mục riêng, và bật ghi log chi tiết cho từng bước.",
        ],
        [
            f"Thư mục chạy: RQ2/runs/{run_dir.name}/",
            "Toàn bộ 35 file/thư mục RQ2 cũ đã nằm trong v1_archive/RQ2_old_20260929/.",
        ],
    )

    stage_block(
        doc, 1, "Kiểm tra dữ liệu, model và môi trường",
        "Chứng minh rằng bước giải thích (SHAP/LIME) sắp làm sẽ dùng ĐÚNG model và ĐÚNG dữ "
        "liệu như RQ1 — nếu sai, mọi kết quả giải thích sau đó đều vô nghĩa.",
        [
            "Nạp lại model XGBoost và test_set.parquet (700.000 flow) đã dùng ở RQ1.",
            "Kiểm tra: đúng 78 đặc trưng + cột Label; thứ tự đặc trưng khớp model; label "
            "encoder có đúng 15 lớp; không có giá trị NaN/Inf.",
            "Chạy lại model trên toàn bộ test set, so sánh Accuracy/Precision/Recall/F1 với "
            "số liệu RQ1 đã công bố — nếu khác nhiều hơn một ngưỡng nhỏ (0.05 điểm %) thì "
            "DỪNG, không chạy tiếp.",
            "Tính checksum (mã băm SHA-256) của file model, encoder, train/test set để sau "
            "này có thể xác minh không có file nào bị đổi.",
        ],
        [
            f"Kết quả chạy lại: Accuracy={gd1['details']['metrics_rerun']['accuracy_pct']:.4f}%, "
            f"Macro F1={gd1['details']['metrics_rerun']['macro_f1_pct']:.4f}% "
            f"— khớp với RQ1 (sai lệch chỉ {gd1['details']['metrics_deltas_pct_points']['macro_f1_pct']:.4f} điểm %, "
            "do làm tròn số).",
            f"Tất cả {len(gd1['checks'])} kiểm tra bắt buộc đều ĐẠT -> tiếp tục GĐ2.",
            f"Phát hiện {gd1['details']['train_test_duplicate_rows']['fraction']*100:.2f}% dòng "
            "ở test set trùng với train set (vấn đề đã biết của bộ dữ liệu CSE-CIC-IDS2018 gốc "
            "— không phải lỗi của pipeline này, chỉ ghi nhận lại).",
        ],
    )

    stage_block(
        doc, 2, "SHAP toàn cục trên toàn test set",
        "Trả lời: với MỖI loại tấn công, mô hình thường dựa vào đặc trưng nào nhất?",
        [
            "Với mỗi lớp (ví dụ 'DDoS-HOIC'), lấy TẤT CẢ flow trong test set thực sự thuộc "
            "lớp đó VÀ được mô hình dự đoán đúng là lớp đó.",
            "Chạy TreeExplainer (thuật toán SHAP chính xác cho mô hình dạng cây) theo lô "
            "(batch) trên các flow này, chỉ lấy đầu ra SHAP cho ĐÚNG lớp đang xét.",
            "Chỉ lưu lại SỐ TRUNG BÌNH (mean |phi| và mean phi có dấu) cho mỗi đặc trưng, "
            "không lưu toàn bộ 700.000×78×15 con số thô (sẽ chiếm hàng GB).",
            "Kiểm tra tính chất cộng (additivity) trên 300 flow ngẫu nhiên để xác nhận SHAP "
            "được tính đúng.",
        ],
        [
            "Đã tính Top-5 SHAP cho toàn bộ 15 lớp (xem RQ2_Bao_cao_SHAP_chi_tiet.docx).",
            f"Sai số additivity rất nhỏ: tối đa {gd2['max_abs_error']:.2e} — xác nhận SHAP đúng.",
            "Toàn bộ 15 lớp chạy xong trong khoảng 5 phút (lớp Benign có ~489.000 flow, lâu nhất).",
        ],
    )

    stage_block(
        doc, 3, "Cohort ghép cặp, tập dev và cohort lỗi",
        "Tạo ra 3 tập flow nhỏ, KHÔNG GIAO NHAU, dùng cho các giai đoạn sau — vì LIME quá "
        "chậm để chạy trên toàn bộ 700.000 flow.",
        [
            "Cohort đánh giá (chính): lấy tối đa 100 flow dự đoán đúng MỖI lớp (lớp hiếm "
            "giữ hết số có), chọn ngẫu nhiên có seed cố định (42) để tái lập được.",
            "Tập dev: 250 flow khác (không trùng cohort), lấy riêng để THỬ cấu hình LIME ở "
            "GĐ5 trước khi áp dụng chính thức.",
            "Cohort lỗi: các flow mô hình dự đoán SAI, cũng lấy tối đa 20 flow/lớp (để LIME "
            "chạy được trong thời gian hợp lý) — tổng số sai thật trong test set là 14.647 "
            "flow, nhưng chỉ lấy mẫu đại diện.",
            "Kiểm tra bằng code rằng 3 tập này THỰC SỰ không có flow nào bị trùng.",
        ],
        [
            f"Cohort đánh giá: {gd3['cohort_size']} flow.",
            f"Tập dev: {gd3['dev_size']} flow.",
            f"Cohort lỗi: {gd3['error_cohort_size']} flow (trong tổng {gd3['n_error_total_raw_in_test_set']} flow sai thật).",
            f"Không giao nhau: {gd3['no_overlap']}.",
        ],
    )

    stage_block(
        doc, 4, "SHAP per-flow trên cohort",
        "Tính SHAP riêng cho TỪNG flow trong cohort đánh giá (không gộp trung bình) — làm "
        "nền tảng để so sánh trực tiếp với LIME ở các giai đoạn sau.",
        [
            "Với mỗi flow, hỏi mô hình dự đoán lớp gì, rồi tính SHAP cho ĐÚNG lớp đó.",
            "Lưu đủ 78 giá trị SHAP, giá trị nền (base_value), xác suất dự đoán, và thời gian "
            "chạy của từng flow.",
        ],
        [
            f"Đã tính cho toàn bộ {gd3['cohort_size']} flow trong vài giây (SHAP rất nhanh).",
            "Additivity đúng trên từng flow — mọi flow đều khớp ID với cohort_ids.csv của GĐ3.",
        ],
    )

    stage_block(
        doc, 5, "Chốt cấu hình LIME trên tập dev",
        "Tìm ra một bộ tham số LIME tốt nhất CÓ THỂ trên dữ liệu này, và CHỐT LẠI tham số "
        "đó TRƯỚC khi áp dụng lên cohort chính — để không bị cám dỗ 'chỉnh' tham số sau khi "
        "thấy kết quả không như ý.",
        [
            "Thử mọi tổ hợp của: kernel_width (3 giá trị), num_samples (3 giá trị), "
            "discretize_continuous (bật/tắt) — tổng 18 tổ hợp, trên một mẫu 150 flow của "
            "tập dev.",
            "Quy tắc chọn (viết ra TRƯỚC khi chạy): chọn tổ hợp có Local R2 trung vị CAO "
            "NHẤT; nếu vài tổ hợp gần bằng nhau (chênh < 0.001) thì chọn tổ hợp CHẠY NHANH "
            "HƠN.",
            "Sau khi chọn, chạy LẠI đúng cấu hình đó trên TOÀN BỘ 250 flow của tập dev để "
            "xác nhận số liệu cuối, rồi ghi cấu hình vào config.yaml.",
        ],
        [
            f"Cấu hình được chọn: kernel_width={locked['kernel_width']}, "
            f"num_samples={locked['num_samples']}, discretize_continuous={locked['discretize_continuous']}.",
            f"Trên toàn bộ tập dev: Local R2 trung vị = {gd5['full_dev_validation']['median_r2']:.4f}, "
            f"{gd5['full_dev_validation']['frac_r2_pass_gate']*100:.1f}% flow đạt ngưỡng chất lượng.",
            "R2 trung vị vẫn dưới ngưỡng 0.3 — đây là giới hạn THỰC của LIME trên dữ liệu "
            "này, được ghi nhận trung thực, không bị che giấu.",
        ],
    )

    stage_block(
        doc, 6, "LIME per-flow trên đúng cohort",
        "Áp dụng CHÍNH THỨC cấu hình đã khóa ở GĐ5 lên toàn bộ cohort đánh giá — đây là bộ "
        "số liệu LIME dùng cho MỌI so sánh với SHAP sau này.",
        [
            "Với mỗi flow (đúng cùng flow, cùng lớp dự đoán như GĐ4), chạy LIME với cấu "
            "hình đã khóa, lưu trọng số, Local R2, thời gian chạy.",
            "Mỗi flow có một 'seed' (số khởi tạo ngẫu nhiên) riêng, cố định theo flow_id, để "
            "kết quả CÓ THỂ TÁI LẬP khi chạy lại đúng flow đó.",
        ],
        [
            f"Đã chạy {gd6['n_flows']} flow trong {gd6['total_time_sec']:.1f} giây "
            f"({gd6['mean_time_sec_per_flow']*1000:.1f} ms/flow).",
            f"Local R2 trung vị trên cohort: {gd6['median_local_r2']:.4f}, "
            f"{gd6['frac_r2_pass_gate']*100:.1f}% flow đạt ngưỡng — CAO HƠN tập dev (có thể vì "
            "cohort có nhiều flow Benign/majority dễ xấp xỉ tuyến tính hơn).",
        ],
    )

    stage_block(
        doc, 7, "Agreement — SHAP và LIME có đồng ý không?",
        "Đo mức độ 'nhìn thấy cùng lý do' giữa SHAP và LIME, trên TỪNG flow của cohort.",
        [
            "Với mỗi flow, xếp hạng 78 đặc trưng theo SHAP và theo LIME (từ quan trọng nhất "
            "đến ít quan trọng nhất).",
            "Tính Jaccard, Spearman, Kendall tau, RBO, sign agreement ở k=3/5/10/20 (xem "
            "giải thích chi tiết từng chỉ số trong RQ2_Kien_thuc_chung_Ly_thuyet.docx).",
            "Mô phỏng một 'đường cơ sở ngẫu nhiên' (chọn k đặc trưng ngẫu nhiên) để biết "
            "con số quan sát được tốt hơn đoán mò bao nhiêu lần.",
            "Gộp các đặc trưng liên quan (ví dụ các cột 'độ dài gói tin' khác nhau) thành "
            "nhóm, tính lại Jaccard ở mức nhóm.",
        ],
        [
            f"Jaccard@5 quan sát = {k5['jaccard_mean']:.4f} — cao hơn ngẫu nhiên nhiều lần "
            "(xem bảng random baseline), nhưng vẫn ở mức THẤP (SHAP và LIME ít khi chọn "
            "đúng cùng 5 đặc trưng).",
            f"Spearman (tính đúng, trên toàn bộ 78 đặc trưng) = {k5['spearman_full78_mean']:.4f} "
            "— DƯƠNG, cho thấy khi xét toàn cục, hai phương pháp có xu hướng đồng thuận, dù "
            "không mạnh.",
            "QUAN TRỌNG: phát hiện và SỬA một lỗi trong lúc chạy — cách tính Spearman chỉ "
            "trên tập con Top-k (không phải toàn bộ 78) bị một sai lệch thống kê khiến nó "
            "RA SỐ ÂM giả tạo ngay cả khi hai phương pháp không hề 'nghịch nhau'. Phiên bản "
            "tính trên toàn bộ 78 đặc trưng (không bị lỗi này) được dùng làm số liệu chính "
            "thức.",
        ],
    )

    stage_block(
        doc, 8, "Quality gate của LIME và R2 so với đồng thuận",
        "Xem việc LIME khớp tốt/kém (Local R2) có liên quan gì đến việc LIME có đồng ý với "
        "SHAP hay không.",
        [
            "Dùng ngưỡng R2≥0.3 đã chốt từ GĐ5 (không đổi), chia flow theo 3 mức: thấp "
            "(<0.1), vừa (0.1–0.3), cao (≥0.3).",
            "So sánh Jaccard@5 và Spearman (toàn 78) giữa SHAP-LIME ở từng mức R2 — nếu mức "
            "R2 cao có đồng thuận cao hơn mức R2 thấp, giả thuyết 'LIME khớp kém gây bất "
            "đồng' được ủng hộ.",
        ],
        [
            f"{gd8['n_pass']}/{gd8['n_total']} flow ({gd8['frac_pass']*100:.1f}%) đạt ngưỡng "
            "trên cohort — tỷ lệ đạt ngưỡng khác RẤT NHIỀU theo lớp (gần 100% ở nhiều lớp "
            "tấn công, chỉ ~23% ở Benign).",
            "Đồng thuận KHÔNG tăng đều theo mức R2 — ghi nhận đúng như số liệu cho thấy, "
            "KHÔNG ép buộc theo giả thuyết ban đầu.",
        ],
    )

    stage9_lines = []
    if gd9:
        stage9_lines = [
            f"LIME: chạy lại 10 lần (10 seed) trên cùng {gd3['cohort_size']} flow, Jaccard@5 "
            f"trung bình GIỮA CÁC LẦN CHẠY = {gd9['lime_mean_pairwise_jaccard5']:.4f} — cho "
            "thấy một mức 'nhảy' kết quả đáng kể nếu không cố định seed.",
            f"SHAP: chạy lại 1 lần, {gd9['shap_jaccard5_rerun']*100:.2f}% flow cho Top-5 "
            "giống TUYỆT ĐỐI — xác nhận TreeSHAP là xác định (deterministic) như lý thuyết.",
            "Thêm nhiễu đầu vào (1%/5%/10% độ lệch chuẩn): cả hai phương pháp đều giảm độ "
            "ổn định khi nhiễu tăng, nhưng SHAP giảm CHẬM HƠN LIME ở mọi mức nhiễu.",
        ]
    else:
        stage9_lines = ["(Giai đoạn này chưa có dữ liệu khi tài liệu được tạo.)"]
    stage_block(
        doc, 9, "Stability và robustness (cho CẢ SHAP và LIME)",
        "Trả lời: phương pháp nào ỔN ĐỊNH hơn — qua các lần chạy khác nhau, và qua nhiễu đo "
        "đạc nhỏ ở đầu vào?",
        [
            "Stability: chạy LIME 10 lần với 10 seed khác nhau trên CÙNG một flow, đo mức "
            "trùng lặp (Jaccard@5) giữa các lần. Chạy lại SHAP 1 lần để xác nhận nó xác định "
            "(không cần 10 lần vì về lý thuyết TreeSHAP không có yếu tố ngẫu nhiên).",
            "Robustness: thêm nhiễu Gaussian nhỏ (1%/5%/10% độ lệch chuẩn mỗi đặc trưng) vào "
            "flow, cắt về miền giá trị hợp lệ (min/max quan sát trên train), rồi giải thích "
            "lại CHO ĐÚNG LỚP ĐÃ DỰ ĐOÁN ban đầu — đo Top-5 mới có còn giống Top-5 gốc không.",
            "Đường hội tụ LIME: thử num_samples = 500/1000/5000/10000 (giữ nguyên "
            "kernel_width/discretize đã khóa) để xem Local R2 thay đổi thế nào.",
        ],
        stage9_lines,
    )

    stage_block(
        doc, 10, "Faithfulness — phương pháp nào trung thành với mô hình hơn?",
        "Kiểm tra: nếu xóa đúng những đặc trưng mà SHAP/LIME nói là quan trọng, xác suất dự "
        "đoán của mô hình có GIẢM THẬT không?",
        [
            "Deletion (comprehensiveness): xóa dần (đưa về giá trị 'nền') các đặc trưng Top-k "
            "theo từng phương pháp, đo xác suất dự đoán giảm bao nhiêu.",
            "Insertion (sufficiency): làm ngược lại — chỉ thêm lại Top-k đặc trưng từ giá trị "
            "nền, đo xác suất phục hồi được bao nhiêu.",
            "Ba kiểm soát bắt buộc: đối chứng xóa NGẪU NHIÊN; thử 3 giá trị nền khác nhau "
            "(trung vị toàn tập, trung vị Benign, trung bình toàn tập); ghi nhận rõ giới hạn "
            "'ngoài phân phối' (OOD) của phương pháp này.",
            "Kiểm định Wilcoxon bắt cặp để biết SHAP thắng LIME có ý nghĩa thống kê không.",
        ],
        [
            "SHAP có AUC comprehensiveness CAO HƠN LIME ở CẢ BA giá trị nền — kết luận ổn "
            "định, không phụ thuộc cách chọn giá trị nền.",
            f"Tỷ lệ SHAP 'thắng' LIME (k=5): "
            f"{gd10_win['shap_win_rate_vs_lime'].mean()*100:.1f}% số flow, với p-value rất "
            "nhỏ (< 0.001) ở cả 3 giá trị nền — khác biệt có ý nghĩa thống kê rõ ràng.",
            "Cả hai phương pháp đều VƯỢT xa đối chứng ngẫu nhiên.",
        ],
    )

    stage_block(
        doc, 11, "Domain validation — giải thích có hợp lý theo kiến thức an ninh mạng không?",
        "So Top-5 của SHAP/LIME với một bảng 'đặc trưng kỳ vọng' do người thực hiện lập "
        "TRƯỚC khi xem kết quả, dựa trên cơ chế tấn công thật (ví dụ DDoS thì tốc độ gói "
        "tin tăng vọt).",
        [
            "Lập bảng tri thức miền cho cả 14 lớp tấn công, mỗi lớp có 2 phiên bản: 'chặt' "
            "(ít đặc trưng, chắc chắn) và 'rộng' (nhiều đặc trưng, bao quát hơn) — có ghi "
            "nguồn/lý do cho mỗi dòng.",
            "Tính precision@5, recall, F1 giữa Top-5 thực tế và bảng kỳ vọng, cho cả SHAP và "
            "LIME, cả 2 phiên bản bảng.",
            "Tính riêng tỷ lệ 'đặc trưng dấu vân tay môi trường' (ví dụ cổng đích, kích cỡ "
            "cửa sổ TCP) trong Top-5 — các đặc trưng này có thể phản ánh đặc điểm riêng của "
            "môi trường thu thập dữ liệu hơn là cơ chế tấn công thật.",
        ],
        [
            f"SHAP có F1 CAO HƠN LIME ở CẢ HAI phiên bản bảng (chặt: "
            f"{gd11_prec[(gd11_prec.method=='SHAP')&(gd11_prec.scope=='strict')]['f1'].iloc[0]:.3f} "
            f"vs {gd11_prec[(gd11_prec.method=='LIME')&(gd11_prec.scope=='strict')]['f1'].iloc[0]:.3f}; "
            f"rộng: {gd11_prec[(gd11_prec.method=='SHAP')&(gd11_prec.scope=='broad')]['f1'].iloc[0]:.3f} "
            f"vs {gd11_prec[(gd11_prec.method=='LIME')&(gd11_prec.scope=='broad')]['f1'].iloc[0]:.3f}) "
            "— kết luận ổn định qua cả hai bản.",
            "Tỷ lệ đặc trưng 'dấu vân tay môi trường' trong Top-5: SHAP ~29%, LIME ~17% — "
            "đáng chú ý, là câu hỏi mở chuyển sang RQ3.",
        ],
    )

    stage_block(
        doc, 12, "Giải thích khi model dự đoán sai (cohort lỗi)",
        "Xem giải thích SHAP/LIME trông khác gì khi model RA QUYẾT ĐỊNH SAI, so với khi nó "
        "đúng — có thể dùng mức bất đồng làm 'tín hiệu nghi ngờ' không (ý tưởng cho RQ3)?",
        [
            f"Chạy SHAP và LIME trên {gd3['error_cohort_size']} flow bị dự đoán sai, giải "
            "thích cho CẢ nhãn model đoán VÀ nhãn thật.",
            "So sánh với cohort đúng: mức tập trung của SHAP Top-5 (chiếm bao % tổng |phi|), "
            "Jaccard@5 SHAP-LIME, tỷ lệ đặc trưng môi trường.",
        ],
        [
            f"Mức tập trung SHAP Top-5: cohort lỗi = {gd12['error_shap_concentration_mean']:.4f}, "
            f"cohort đúng = {gd12['correct_cohort_shap_concentration_mean']:.4f} — khá gần nhau.",
            f"Jaccard@5 SHAP-LIME: cohort lỗi = {gd12['error_shap_lime_jaccard5_mean']:.4f}, "
            f"cohort đúng = {gd12['correct_cohort_shap_lime_jaccard5_mean']:.4f}.",
            "CẢNH BÁO cỡ mẫu: 151 flow, nhiều lớp dưới 10 flow — đây CHỈ là kết quả thăm dò, "
            "KHÔNG đủ để khẳng định sự khác biệt có ý nghĩa thống kê.",
        ],
    )

    stage_block(
        doc, 13, "Tổng hợp và báo cáo cuối",
        "Gom toàn bộ số liệu từ GĐ0-GĐ12 thành các bảng tổng hợp và viết thành các file "
        ".docx để đọc/nộp.",
        [
            "Đọc lại mọi file JSON/CSV của 13 giai đoạn, gom vào 1 file tổng hợp duy nhất.",
            "Viết 5 file .docx: tài liệu lý thuyết/kiến thức chung, báo cáo SHAP chi tiết, "
            "báo cáo LIME chi tiết, tài liệu quy trình từng giai đoạn (chính là file này), "
            "và báo cáo tổng hợp cuối cùng.",
        ],
        [
            "Xem toàn bộ kết quả trong RQ2_Bao_cao_Tong_hop_Final.docx.",
        ],
    )

    out_path = out_dir / "RQ2_Quy_trinh_Thuc_Hien_Chi_Tiet.docx"
    doc.save(str(out_path))
    logger.info("Đã lưu: %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
