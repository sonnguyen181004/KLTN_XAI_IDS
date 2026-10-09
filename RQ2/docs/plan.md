# Kế hoạch chạy lại RQ2 từ đầu (SHAP và LIME)

> Nguồn: do người dùng cung cấp ngày 2026-10-09. Lưu lại nguyên văn để mọi script trong `RQ2/scripts` đối chiếu, tránh lệch mạch chuyện khi triển khai.

## Mục tiêu và nguyên tắc

Lần chạy lại này tạo bộ bằng chứng RQ2 có thể tái lập, đi theo một mạch năm câu hỏi: hai phương pháp có đồng ý không, vì sao bất đồng, phương pháp nào ổn định, phương pháp nào trung thành với mô hình, và giải thích có hợp lý theo kiến thức miền không. Kế hoạch gồm 14 giai đoạn (Gđ0 đến Gđ13), chạy theo thứ tự.

### Mạch câu hỏi

| Giai đoạn | Sub-RQ (theo mạch) |
|---|---|
| Gđ2 | Nền cho RQ2 — Với mỗi loại tấn công, XGBoost dựa vào đặc trưng nào? |
| Gđ7, Gđ8 | 2.1 Agreement — SHAP và LIME có đồng ý không, và bất đồng do đâu? |
| Gđ9 | 2.2 Stability, robustness — Phương pháp nào ổn định, chịu nhiễu tốt hơn? |
| Gđ10 | 2.3 Faithfulness — Phương pháp nào trung thành với mô hình hơn? |
| Gđ11 | 2.4 Domain validation — Giải thích có khớp cơ chế tấn công thực tế không? |
| Gđ12 | Phân tích bổ sung — Giải thích khi mô hình dự đoán sai khác gì? |

Lưu ý: proposal hiện đánh số domain là 2.2, ổn định là 2.3, faithfulness là 2.4. Thứ tự trong bảng là thứ tự trình bày theo mạch; cần hỏi thầy trước khi đổi số trong tài liệu chính thức.

### Nguyên tắc chung

- Chốt trước, xem sau. Cấu hình LIME (tập dev), bảng tri thức miền và ngưỡng quality gate được quyết định trước khi nhìn kết quả trên cohort đánh giá.
- Công bằng giữa hai phương pháp. Cùng model, cùng cohort, cùng nhãn dự đoán, cùng hàm predict_proba.
- Thống kê đi kèm. Mọi chỉ số báo cáo kèm khoảng tin cậy bootstrap; so SHAP với LIME bằng kiểm định cặp (Wilcoxon) trên cùng flow.
- Kiểm tra nhất quán tự động. Sau mỗi giai đoạn, kiểm tra ID flow, số dòng và checksum khớp với giai đoạn trước.
- Giữ kết quả cũ. Chuyển kết quả hiện có vào thư mục v1_archive trước khi chạy lại, để so được hai lần chạy.
- Báo cáo cả kết quả không như mong đợi và ghi rõ giới hạn.

### Yêu cầu đầu ra bổ sung (chốt ngày 2026-10-09)

Ngoài các file CSV/JSON/biểu đồ của từng giai đoạn, **bắt buộc có các báo cáo .docx chi tiết, đầy đủ** ở Gđ13:

- Báo cáo riêng cho SHAP: trọng số/đóng góp của từng đặc trưng theo từng lớp tấn công (Top-5/Top-10, giá trị φ có dấu, additivity).
- Báo cáo riêng cho LIME: trọng số cục bộ theo từng lớp tấn công tương tự (kèm Local R², cấu hình đã khóa ở Gđ5).
- Báo cáo tổng hợp RQ2 "chuẩn chỉnh nhất": trình bày theo mạch 5 câu hỏi, đủ số liệu + CI + case study, dùng để nộp/báo cáo thầy.

## GĐ 0 và GĐ 1: Chuẩn bị và kiểm tra

Hai giai đoạn này chứng minh rằng SHAP và LIME thật sự dùng đúng model và đúng dữ liệu; nếu không đạt thì dừng, không chạy tiếp.

### GĐ 0. Chuẩn bị lần chạy
- Làm: chuyển kết quả RQ2 hiện có vào v1_archive; tạo thư mục chạy mới theo ngày; tạo config.yaml chứa mọi tham số (seed 42, đường dẫn, k, số mẫu LIME, kernel width); bật ghi log cho từng bước.
- Đầu ra: config.yaml, thư mục v1_archive, file log.
- Đạt khi: các giai đoạn sau chỉ đọc tham số từ config.yaml, không ghi cứng trong code.

### GĐ 1. Kiểm tra dữ liệu, model và môi trường
- Kiểm tra bắt buộc:
  - test_set.parquet có đúng 78 đặc trưng cộng cột Label.
  - Thứ tự đặc trưng khớp với model XGBoost; label encoder khớp 15 lớp.
  - XGBoost nạp được; không còn NaN hoặc Inf (nếu dữ liệu gốc có, ghi lại cách xử lý).
  - Chạy model trên test set và đối chiếu F1, Precision với kết quả RQ1. Khớp thì mới chứng minh đúng model.
  - Kiểm tra dòng trùng giữa train và test (CSE-CIC-IDS2018 có nhiều dòng trùng).
  - Lưu checksum của model, encoder, train và test.
- Đầu ra: run_info.json (seed, git commit, máy chạy, thời gian), feature_schema.json (tên, thứ tự, đơn vị, kiểu), checksums.json, phiên bản Python, SHAP, LIME, XGBoost.
- Đạt khi: F1/Precision trên test khớp RQ1 (sai lệch chỉ do làm tròn); mọi kiểm tra bắt buộc qua; checksum được ghi.

## GĐ 2 và GĐ 3: SHAP toàn cục và cohort ghép cặp

### GĐ 2. SHAP toàn cục trên toàn test set
- Định nghĩa: với mỗi lớp c, lấy các flow thật sự thuộc lớp c và được dự đoán đúng là c, rồi lấy SHAP của đầu ra lớp c.
- Làm: TreeExplainer trên ~700.000 flow theo lô; chỉ lưu giá trị tổng hợp theo lớp (mean |φ| và mean φ có dấu); additivity check trên mẫu con.
- Đầu ra: Top-5 SHAP của 14 lớp tấn công; CSV feature importance theo lớp; biểu đồ Top-5 positive/negative; báo cáo additivity.
- Đạt khi: sai số additivity nhỏ; mỗi lớp có số flow ghi rõ.

### GĐ 3. Cohort ghép cặp, tập dev và cohort lỗi
- Cohort đánh giá: tối đa 100 flow dự đoán đúng mỗi lớp, lớp hiếm giữ tất cả, phân tầng theo lớp, seed 42.
- Tập dev: ~200-300 flow từ phần test còn lại, không trùng cohort đánh giá, dùng chốt cấu hình LIME ở Gđ5.
- Cohort lỗi: các flow model dự đoán sai, giữ riêng.
- Đầu ra: cohort_ids.csv, dev_ids.csv, error_ids.csv.
- Đạt khi: ba tập không giao nhau; ID lưu lại cho SHAP/LIME dùng đúng cùng tập.

## GĐ 4 đến GĐ 6: Giải thích từng flow

### GĐ 4. SHAP per-flow trên cohort
- Lưu đủ 78 giá trị SHAP, base value, xác suất dự đoán, thời gian/flow; rút Top-1/3/5/10.
- Đạt khi: additivity đúng từng flow; ID khớp cohort_ids.csv.

### GĐ 5. Chốt cấu hình LIME trên tập dev
- Vấn đề: Local R² của LIME lần trước rất thấp (trung vị 0,068; 12,3% flow đạt R² ≥ 0,3).
- Làm: thử kernel_width (0.5x/1x/2x của 6.624), num_samples (1000/5000/10000), discretize_continuous bật/tắt, chọn background.
- Quy tắc: chỉ chọn theo R² và chi phí, không theo mức đồng thuận với SHAP.
- Đạt khi: một cấu hình duy nhất + lý do ghi lại; nếu R² vẫn thấp thì ghi nhận giới hạn, không ép đẹp.

### GĐ 6. LIME per-flow trên đúng cohort
- Chạy LIME mới (không dùng lại kết quả cũ), cấu hình đã khóa, cùng predict_proba, cùng nhãn dự đoán như Gđ4, num_features=78, random_state cố định theo flow.
- Đạt khi: ID khớp tuyệt đối Gđ4; không flow thiếu; thời gian ghi lại.

## GĐ 7 và GĐ 8: Agreement (Sub-RQ 2.1)

### GĐ 7. Agreement SHAP và LIME
- Chỉ số: Jaccard, Spearman, RBO, Kendall tau trên Top-k (k=3,5,10,20); sign agreement.
- Đường cơ sở ngẫu nhiên; so ở mức nhóm đặc trưng; theo lớp; CI bootstrap.
- Đạt khi: mọi chỉ số có CI; có baseline ngẫu nhiên; có bảng theo lớp.

### GĐ 8. Quality gate LIME và R² so với đồng thuận
- Ngưỡng Local R² chốt trước (0.3). Báo cáo cả toàn bộ và nhóm vượt ngưỡng (ghi phân bố lớp).
- Phân tích chính: chia theo mức R² (thấp/vừa/cao), xem đồng thuận với SHAP.
- Đạt khi: ngưỡng ghi trong config.yaml trước khi chạy; có phân bố lớp nhóm vượt ngưỡng.

## GĐ 9 đến GĐ 11: Ổn định, trung thành, hợp lý theo miền

### GĐ 9. Stability và robustness (2.2)
- Stability theo seed (LIME ~10 seed, Jaccard@5; TreeSHAP xác định, dự kiến =1).
- Robustness với nhiễu (σ = 1%, 5%, 10%), đường hội tụ LIME theo num_samples.
- Đạt khi: có số liệu cho cả hai phương pháp, kèm CI.

### GĐ 10. Faithfulness (2.3)
- Xóa dần k đặc trưng quan trọng nhất (đưa về giá trị nền), đo giảm xác suất lớp dự đoán; đường deletion/insertion, AUC; comprehensiveness/sufficiency k=1..10.
- Ba kiểm soát bắt buộc: đối chứng xóa ngẫu nhiên; nhiều giá trị nền; ghi giới hạn OOD.
- Đạt khi: so với đối chứng ngẫu nhiên; kết luận ổn định qua các giá trị nền (hoặc nêu rõ khi khác).

### GĐ 11. Domain validation (2.4)
- Bảng tri thức miền trước khi xem Top-5 (có nguồn trích dẫn); đối chiếu Top-5 SHAP/LIME theo lớp.
- Chỉ số: precision@5, recall, F1 so với bảng tri thức; bản chặt và bản rộng.
- Phần riêng: tỷ lệ đặc trưng "dấu vân tay môi trường" trong Top-5 (cầu nối RQ3).
- Đạt khi: mỗi dòng bảng tri thức có nguồn; kết luận nêu trên cả hai bản.

## GĐ 12 và GĐ 13: Cohort lỗi và báo cáo cuối

### GĐ 12. Giải thích khi model dự đoán sai
- SHAP/LIME trên cohort lỗi; so với flow đúng: mức tập trung SHAP, đồng thuận, tỷ lệ đặc trưng môi trường.
- Đạt khi: nêu rõ cỡ mẫu (kết luận thăm dò, không khẳng định).

### GĐ 13. Báo cáo và biểu đồ cuối RQ2
- Trình bày theo mạch 5 câu hỏi; 3-4 case study; bảng/hình đầy đủ; phần giới hạn, tái lập, "khác v1".
- **Báo cáo .docx riêng cho SHAP (trọng số theo lớp), riêng cho LIME (trọng số theo lớp), và báo cáo tổng hợp RQ2 chuẩn chỉnh.**
- Đạt khi: mọi số liệu truy ngược được về CSV trong thư mục chạy.

## Rủi ro chính

| Rủi ro | Cách xử lý |
|---|---|
| Chỉnh LIME để giống SHAP | Chỉnh trên tập dev, chỉ theo R² và chi phí (Gđ5) |
| Cohort nhỏ ở lớp hiếm | Ghi số flow/lớp; không khẳng định dưới ngưỡng mẫu |
| Bảng tri thức miền thiên vị | Bản chặt + bản rộng, có nguồn (Gđ11) |
| Xóa đặc trưng tạo mẫu OOD | Nhiều giá trị nền, đối chứng ngẫu nhiên (Gđ10) |
| Kết quả khác v1 | Giữ v1_archive, nêu nguyên nhân khi khác |
| Chạy quá lâu | Ước lượng thời gian/flow ở Gđ5 trước khi chạy toàn bộ; chạy theo lô có checkpoint |

## Thứ tự chạy
1. Gđ0, Gđ1 (dừng nếu không đạt)
2. Gđ2, Gđ3
3. Gđ4, Gđ5, Gđ6
4. Gđ7, Gđ8
5. Gđ9, Gđ10, Gđ11 (có thể song song)
6. Gđ12, rồi Gđ13
