"""Tạo RQ2_Kien_thuc_chung_Ly_thuyet.docx — giải thích SHAP, LIME và mọi chỉ số dùng trong
RQ2, bằng tiếng Việt, dễ hiểu, đầy đủ. File này KHÔNG phụ thuộc vào số liệu của run cụ thể
— có thể tạo trước hoặc sau các giai đoạn khác.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import RQ2_DIR, latest_run_dir, get_logger  # noqa: E402
from lib.docx_helpers import new_doc, add_heading, add_para, add_bullets, add_page_break  # noqa: E402


def main() -> int:
    run_dir = latest_run_dir()
    logger = get_logger("build_report_theory", run_dir)
    out_dir = run_dir / "gd13_report" / "docx"
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = new_doc(
        "RQ2 — Kiến Thức Chung và Lý Thuyết",
        "Giải thích SHAP, LIME và toàn bộ chỉ số sử dụng trong phân tích RQ2 — viết lại ngắn gọn, dễ hiểu",
    )

    add_heading(doc, "1. Bài toán RQ2 là gì?", level=1)
    add_para(doc,
        "RQ1 đã huấn luyện một mô hình XGBoost để phân loại 15 loại lưu lượng mạng "
        "(14 loại tấn công + Benign) với độ chính xác cao. Nhưng mô hình XGBoost là một "
        "mô hình 'hộp đen' (black-box): nó cho ra kết quả đúng, nhưng không tự giải thích "
        "VÌ SAO nó đưa ra kết quả đó. RQ2 trả lời câu hỏi: 'Mô hình dựa vào đặc trưng nào để "
        "ra quyết định, và hai công cụ giải thích phổ biến nhất (SHAP và LIME) có cho ra cùng "
        "một câu trả lời không?'"
    )
    add_para(doc,
        "Một flow mạng (network flow) là một phiên kết nối giữa hai máy (ví dụ một lần tải "
        "trang web), được mô tả bằng 78 con số (đặc trưng) như: thời gian phiên kéo dài bao "
        "lâu, có bao nhiêu gói tin, tốc độ gửi gói tin, kích thước gói tin trung bình, các cờ "
        "TCP (SYN/ACK/FIN...), v.v. Mô hình nhìn vào 78 con số này để đoán flow đó là Benign "
        "(bình thường) hay một trong 14 loại tấn công."
    )

    add_heading(doc, "2. SHAP là gì?", level=1)
    add_para(doc,
        "SHAP (SHapley Additive exPlanations) dựa trên lý thuyết trò chơi (Shapley value, "
        "giải Nobel Kinh tế 2012 trao cho Lloyd Shapley cho công trình gốc). Ý tưởng: coi mỗi "
        "đặc trưng như một 'người chơi' đóng góp vào kết quả dự đoán cuối cùng. SHAP tính "
        "công bằng phần đóng góp của từng đặc trưng bằng cách xét MỌI cách kết hợp có thể của "
        "các đặc trưng (có đặc trưng này / không có đặc trưng này) và đo mức thay đổi kết quả."
    )
    add_bullets(doc, [
        "Giá trị SHAP (ký hiệu φ, đọc là 'phi') của một đặc trưng cho một flow: là một con số "
        "có dấu. Dương (+) nghĩa là đặc trưng đó ĐẨY dự đoán VỀ PHÍA lớp đang xét; Âm (−) "
        "nghĩa là đặc trưng đó ĐẨY dự đoán RA XA lớp đang xét.",
        "Tính CHẤT CỘNG (additivity): base_value + tổng tất cả φ = đầu ra thô (margin) của "
        "mô hình cho lớp đó. Đây là tính chất toán học chặt — nếu sai lệch lớn, nghĩa là có "
        "lỗi tính toán. RQ2 luôn kiểm tra tính chất này (xem GĐ2, GĐ4).",
        "TreeExplainer: với mô hình dạng cây (XGBoost, Random Forest...), có thuật toán "
        "TreeSHAP tính CHÍNH XÁC giá trị SHAP (không cần lấy mẫu ngẫu nhiên, không có nhiễu) "
        "— đây là lý do SHAP được coi là 'chuẩn vàng' để so sánh, và vì sao SHAP cho kết quả "
        "GIỐNG NHAU mỗi lần chạy lại (deterministic).",
        "Vì SHAP xét mọi flow một cách chính xác và nhất quán, RQ2 dùng SHAP làm phương pháp "
        "giải thích CHÍNH; LIME dùng để ĐỐI CHỨNG.",
    ])

    add_heading(doc, "3. LIME là gì?", level=1)
    add_para(doc,
        "LIME (Local Interpretable Model-agnostic Explanations) đi theo hướng khác hẳn: thay "
        "vì tính chính xác, LIME xây dựng một MÔ HÌNH ĐƠN GIẢN (hồi quy tuyến tính / Ridge) "
        "để BẮT CHƯỚC hành vi của mô hình phức tạp (XGBoost) CHỈ TRONG MỘT VÙNG NHỎ quanh "
        "flow đang xét."
    )
    add_bullets(doc, [
        "Cách làm: LIME tạo ra hàng ngàn phiên bản 'nhiễu' (perturbation) của flow đang xét "
        "(num_samples), hỏi mô hình XGBoost dự đoán xác suất cho từng phiên bản nhiễu đó, rồi "
        "DÙNG CHÍNH các cặp (phiên bản nhiễu, xác suất) này để huấn luyện một mô hình hồi quy "
        "tuyến tính đơn giản — trọng số của mô hình tuyến tính này chính là 'giải thích LIME'.",
        "kernel_width: quyết định một phiên bản nhiễu 'gần' flow gốc bao nhiêu thì được tính "
        "trọng số cao khi huấn luyện mô hình tuyến tính (vùng lân cận rộng hay hẹp).",
        "num_samples: số phiên bản nhiễu được tạo ra. Nhiều hơn thường ổn định hơn nhưng chạy "
        "chậm hơn.",
        "discretize_continuous: có chia nhỏ các đặc trưng liên tục thành các khoảng (bin) "
        "trước khi nhiễu hay không. RQ2 (GĐ5) tìm thấy KHÔNG chia (False) cho Local R2 cao "
        "hơn trên dữ liệu mạng này.",
        "Local R2 (hệ số xác định cục bộ): đo mô hình tuyến tính đơn giản của LIME khớp với "
        "hành vi THẬT của XGBoost quanh flow đó TỐT ĐẾN ĐÂU. R2 = 1 là khớp hoàn hảo; R2 gần "
        "0 nghĩa là lời giải thích của LIME không đáng tin — mô hình tuyến tính gần như không "
        "giải thích được gì về hành vi thật của XGBoost ở vùng đó.",
        "Vì LIME có bước LẤY MẪU NGẪU NHIÊN, kết quả CÓ THỂ KHÁC NHAU giữa các lần chạy nếu "
        "không cố định seed (random_state) — đây là lý do RQ2 phải kiểm tra 'stability' "
        "(GĐ9) cho LIME.",
    ])

    add_heading(doc, "4. Vì sao SHAP và LIME có thể cho kết quả khác nhau?", level=1)
    add_para(doc,
        "SHAP trả lời câu hỏi 'đóng góp CHÍNH XÁC của từng đặc trưng vào quyết định CUỐI "
        "CÙNG của mô hình thật là gì'. LIME trả lời câu hỏi khác: 'nếu tôi thay mô hình thật "
        "bằng một đường thẳng đơn giản chỉ trong vùng lân cận nhỏ quanh flow này, đường thẳng "
        "đó sẽ dựa vào đặc trưng nào'. Hai câu hỏi gần nhau nhưng không giống nhau — đặc biệt "
        "khi mô hình thật (XGBoost, gồm 100 cây quyết định sâu 8 tầng) có ranh giới quyết "
        "định rất phức tạp, 'không tuyến tính', một đường thẳng đơn giản có thể xấp xỉ rất "
        "kém (Local R2 thấp) → hai phương pháp 'nhìn' ra hai câu trả lời khác nhau. Đây gọi "
        "là 'Disagreement Problem' (vấn đề bất đồng), đã được ghi nhận trong nhiều nghiên cứu "
        "XAI (ví dụ Krishna et al., 2022)."
    )

    add_heading(doc, "5. Giải thích từng chỉ số dùng trong RQ2", level=1)

    add_heading(doc, "5.1. Chỉ số đồng thuận (Agreement) — GĐ7", level=2)
    add_bullets(doc, [
        "Top-k: lấy k đặc trưng có |giá trị tuyệt đối| lớn nhất theo mỗi phương pháp (k = "
        "3, 5, 10, 20 trong RQ2).",
        "Jaccard@k: tỷ lệ TRÙNG NHAU giữa 2 danh sách Top-k (bỏ qua thứ tự và dấu). "
        "Jaccard = |giao| / |hợp|. Jaccard = 1 là trùng hoàn toàn; 0 là không trùng gì.",
        "Spearman (full-78): đo mức độ 'xếp hạng theo cùng một thứ tự' giữa SHAP và LIME "
        "trên TOÀN BỘ 78 đặc trưng (không chỉ Top-k). Giá trị từ −1 (xếp hạng ngược hoàn "
        "toàn) đến +1 (xếp hạng giống hoàn toàn), 0 là không liên quan. RQ2 dùng bản 'full-78' "
        "này làm số chính vì bản tính trên tập con Top-k dễ bị lệch (xem khung giải thích "
        "bên dưới).",
        "Kendall tau: tương tự Spearman nhưng đo theo một cách khác (đếm số cặp bị đảo thứ "
        "tự) — cùng mục đích, dùng để kiểm tra chéo với Spearman.",
        "RBO (Rank-Biased Overlap): giống Jaccard nhưng ƯU TIÊN các đặc trưng xếp hạng cao "
        "hơn (gần vị trí số 1) — hai phương pháp trùng ở hạng 1-2 được tính 'nặng' hơn trùng "
        "ở hạng 9-10.",
        "Sign agreement: trong số các đặc trưng CẢ HAI phương pháp đều chọn vào Top-k, bao "
        "nhiêu phần trăm có CÙNG DẤU (cùng đẩy về lớp đang xét, hoặc cùng đẩy ra xa).",
        "Đường cơ sở ngẫu nhiên (random baseline): nếu chọn k đặc trưng NGẪU NHIÊN (không "
        "nhìn dữ liệu) hai lần độc lập, Jaccard mong đợi là bao nhiêu? Dùng để biết con số "
        "Jaccard quan sát được 'tốt' hơn việc đoán mò bao nhiêu lần.",
    ])
    p = add_para(doc, "")
    r = p.add_run(
        "Lưu ý kỹ thuật quan trọng: bản Spearman/Kendall tính TRÊN RIÊNG tập hợp của Top-k "
        "(gọi là 'union-restricted') có một SAI LỆCH THỐNG KÊ (selection bias) khiến nó có "
        "xu hướng lệch về giá trị ÂM ngay cả khi hai phương pháp thực ra không hề 'nghịch "
        "nhau' — vì cách chọn mẫu (lấy đúng các đặc trưng mà MỘT TRONG HAI phương pháp xếp "
        "hạng rất cao) tự nó đã tạo ra tương quan âm giả. RQ2 phát hiện ra hiện tượng này khi "
        "chạy lại (xem log GĐ7) và SỬA bằng cách báo cáo thêm bản tính trên toàn bộ 78 đặc "
        "trưng (không bị lệch) làm số liệu chính thức."
    )
    r.italic = True

    add_heading(doc, "5.2. Quality gate của LIME — GĐ8", level=2)
    add_para(doc,
        "Vì Local R2 của LIME có thể rất thấp trên dữ liệu mạng (các đặc trưng có phân phối "
        "lệch, nhiều ngoại lai), RQ2 đặt một 'ngưỡng chất lượng' (R2 ≥ 0.3) ĐƯỢC CHỐT TRƯỚC "
        "khi nhìn kết quả, để tránh tình trạng 'chọn ngưỡng sao cho đẹp'. Flow có R2 dưới "
        "ngưỡng vẫn được báo cáo đầy đủ — không bị loại bỏ, chỉ được đánh dấu riêng."
    )

    add_heading(doc, "5.3. Stability và Robustness — GĐ9", level=2)
    add_bullets(doc, [
        "Stability (ổn định giữa các lần chạy): chạy LIME NHIỀU LẦN (10 seed khác nhau) "
        "trên CÙNG một flow, đo Jaccard@5 giữa các lần — nếu LIME 'nhảy' kết quả nhiều giữa "
        "các lần chạy, giải thích đó khó tin cậy để báo cáo cho một người dùng thật (ví dụ "
        "chuyên viên SOC).",
        "Robustness (chịu nhiễu đầu vào): thêm một chút nhiễu ngẫu nhiên vào các con số đặc "
        "trưng (ví dụ ±1%, ±5%, ±10% độ lệch chuẩn), xem giải thích Top-5 có còn giữ nguyên "
        "không. Flow mạng thực tế luôn có một chút biến động đo đạc — một giải thích tốt "
        "không nên 'vỡ' chỉ vì nhiễu đo đạc nhỏ.",
    ])

    add_heading(doc, "5.4. Faithfulness (tính trung thành với mô hình) — GĐ10", level=2)
    add_bullets(doc, [
        "Comprehensiveness (deletion): XÓA DẦN các đặc trưng được giải thích là quan trọng "
        "nhất (đưa về một giá trị 'nền' trung lập), xem xác suất dự đoán của mô hình GIẢM "
        "bao nhiêu. Giải thích TRUNG THÀNH thì xóa đúng đặc trưng quan trọng sẽ làm xác suất "
        "giảm MẠNH.",
        "Sufficiency (insertion): làm ngược lại — bắt đầu từ giá trị nền (mô hình gần như "
        "không biết gì), rồi CHỈ thêm lại các đặc trưng Top-k, xem mô hình PHỤC HỒI được bao "
        "nhiêu phần xác suất dự đoán ban đầu.",
        "AUC (area under curve) của hai đường trên: một con số tổng hợp duy nhất để so sánh "
        "phương pháp nào 'trung thành' hơn, tính trên nhiều giá trị k cùng lúc.",
        "Đối chứng ngẫu nhiên (Random): xóa/thêm k đặc trưng CHỌN NGẪU NHIÊN (không theo giải "
        "thích nào) — nếu SHAP/LIME không tốt hơn ngẫu nhiên thì giải thích đó vô giá trị.",
        "Giá trị nền (baseline): giá trị 'trung lập' được gán khi xóa một đặc trưng. RQ2 thử "
        "3 giá trị nền khác nhau (trung vị toàn tập, trung vị riêng lớp Benign, trung bình "
        "toàn tập) để chắc chắn kết luận không phụ thuộc vào một lựa chọn nền cụ thể.",
        "Hạn chế đã biết: khi xóa nhiều đặc trưng cùng lúc, mẫu kết quả có thể rơi ra ngoài "
        "vùng dữ liệu mà mô hình từng được huấn luyện (out-of-distribution, OOD) — xác suất "
        "đo được lúc đó có thể không phản ánh đúng hành vi thật của mô hình trên dữ liệu "
        "thực tế. Đây là hạn chế chung của phương pháp deletion/insertion trong toàn ngành "
        "XAI, không phải lỗi riêng của RQ2.",
    ])

    add_heading(doc, "5.5. Domain validation (đối chiếu kiến thức an ninh mạng) — GĐ11", level=2)
    add_para(doc,
        "Với mỗi loại tấn công, có những đặc trưng mạng MÀ CHUYÊN GIA AN NINH MẠNG kỳ vọng sẽ "
        "quan trọng, dựa trên cách tấn công đó hoạt động (ví dụ: DDoS làm tốc độ gói tin tăng "
        "vọt; Brute-force luôn nhắm vào một cổng dịch vụ cố định). RQ2 lập một bảng các đặc "
        "trưng kỳ vọng này TRƯỚC khi xem Top-5 thực tế của SHAP/LIME, rồi tính:"
    )
    add_bullets(doc, [
        "Precision@5: trong Top-5 mà SHAP/LIME chọn, bao nhiêu phần trăm KHỚP với bảng kỳ "
        "vọng.",
        "Recall: trong bảng kỳ vọng, bao nhiêu phần trăm XUẤT HIỆN trong Top-5.",
        "F1: trung bình điều hoà của Precision và Recall — một con số duy nhất cân bằng cả "
        "hai.",
        "Bản 'chặt' (strict) và 'rộng' (broad): bảng kỳ vọng hẹp hay rộng để kiểm tra kết "
        "luận có nhạy với cách chọn bảng kỳ vọng hay không.",
        "Đặc trưng 'dấu vân tay môi trường' (environment fingerprint): một số đặc trưng (ví "
        "dụ cổng đích Dst Port, kích thước cửa sổ TCP ban đầu) có thể phản ánh ĐẶC ĐIỂM RIÊNG "
        "của môi trường thu thập dữ liệu hơn là bản chất tấn công thật — nếu các đặc trưng "
        "này chiếm tỷ lệ cao trong Top-5, mô hình có thể đang học một 'lối tắt' (shortcut) "
        "chứ không học đúng cơ chế tấn công. Đây là cầu nối sang RQ3.",
    ])

    add_heading(doc, "5.6. Thống kê đi kèm (CI, bootstrap, Wilcoxon)", level=2)
    add_bullets(doc, [
        "Khoảng tin cậy bootstrap (bootstrap CI): lấy mẫu LẠI NHIỀU LẦN (ví dụ 2000 lần, có "
        "lặp) từ dữ liệu đang có, tính lại trung bình mỗi lần, rồi lấy khoảng chứa 95% các "
        "giá trị trung bình đó. Cho biết số liệu trung bình báo cáo ổn định đến đâu, không "
        "chỉ là một con số 'may rủi' từ đúng 1339 flow này.",
        "Kiểm định Wilcoxon (paired): kiểm định thống kê so sánh HAI PHƯƠNG PHÁP trên ĐÚNG "
        "CÙNG một flow (bắt cặp) — trả lời câu hỏi 'SHAP có thực sự tốt hơn LIME một cách có "
        "ý nghĩa thống kê, hay chỉ là khác biệt ngẫu nhiên'. Giá trị p rất nhỏ (ví dụ < 0.001) "
        "nghĩa là khác biệt quan sát được RẤT KHÓ xảy ra do ngẫu nhiên.",
    ])

    add_heading(doc, "6. Tóm tắt một trang", level=1)
    add_bullets(doc, [
        "SHAP = chính xác về mặt toán học, xác định (không đổi mỗi lần chạy), dùng làm chuẩn.",
        "LIME = xấp xỉ cục bộ bằng mô hình tuyến tính, có yếu tố ngẫu nhiên, Local R2 cho "
        "biết xấp xỉ đó tin được đến đâu.",
        "Agreement (GĐ7/8) = hai phương pháp có nhìn ra cùng lý do không.",
        "Stability/Robustness (GĐ9) = giải thích có ổn định qua các lần chạy / qua nhiễu nhỏ "
        "không.",
        "Faithfulness (GĐ10) = giải thích có phản ánh ĐÚNG hành vi thật của mô hình không.",
        "Domain validation (GĐ11) = giải thích có hợp lý theo kiến thức an ninh mạng không.",
        "Mọi số liệu đều kèm khoảng tin cậy hoặc kiểm định thống kê để biết mức độ tin cậy, "
        "không chỉ là một con số đơn lẻ.",
    ])

    out_path = out_dir / "RQ2_Kien_thuc_chung_Ly_thuyet.docx"
    doc.save(str(out_path))
    logger.info("Đã lưu: %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
