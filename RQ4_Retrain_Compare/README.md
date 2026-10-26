# RQ4 — Huấn luyện lại XGBoost trên dữ liệu đã sửa lỗi và so sánh với dữ liệu cũ

Mục đích: kiểm tra giả thuyết rằng báo nhầm Hulk trên lưu lượng thật đến từ khoảng trống của
CSE-CIC-IDS2018 bản CSV gốc (thiếu Benign "đóng bằng FIN có dữ liệu"), bằng cách huấn luyện lại
**đúng quy trình RQ1 và RQ2** trên bản improved rồi so sánh.

## Nguyên tắc: làm y như mô hình cũ

| Hạng mục | Mô hình cũ (RQ1, RQ2) | Mô hình mới (RQ4) |
|---|---|---|
| Thuật toán | XGBClassifier, tree_method hist, n_estimators 100, random_state 42 | Giống hệt |
| Siêu tham số | Chọn bằng quét 7 cấu hình ở RQ1: độ sâu 8, learning rate 0,08 | Dùng đúng cấu hình đó, không quét lại |
| Đặc trưng | 78 đặc trưng, float32, không Timestamp, không IP | Giống hệt (đổi tên theo bảng ánh xạ) |
| Cách lấy mẫu | 3,5 triệu dòng, 70 % Benign và 30 % tấn công, giữ 100 % lớp hiếm | Cùng công thức, trần theo số mẫu sẵn có |
| Chia dữ liệu | Stratified 80/20 | Giống hệt: stratified 80/20, seed 42, lấy ngẫu nhiên từ toàn bộ dữ liệu, không bộ giữ riêng nào |
| Chỉ số | Accuracy, Macro P/R/F1, FPR Benign, FNR tấn công (`ids_metrics.py`) | Giống hệt |
| Giải thích | SHAP toàn cục và từng flow, LIME khóa cấu hình, độ đồng thuận, cổng chất lượng, độ ổn định, faithfulness, miền tri thức, nhóm lỗi (RQ2 GĐ0 đến 13) | Chạy lại cùng các giai đoạn trên mô hình mới |

Những chỗ **không** thể giống hệt, và cách xử lý:
- Bản improved không có SlowHTTPTest, và FTP-BruteForce chỉ có dạng "Attempted". Cả hai lớp bị bỏ, nên
  không gian nhãn của mô hình mới là 13 lớp. Để công bằng, mô hình cũ cũng được huấn luyện lại trên 13 lớp
  này (M0b) bên cạnh M0 gốc 15 lớp.
- Các nhãn "Attempted" được bỏ, bốn loại Infiltration gộp thành một lớp.
- Chưa tìm thấy mã tạo `train_set.parquet` nên cách lấy mẫu của RQ1 được dựng lại từ báo cáo dataset 3,5 triệu dòng.

## Các mô hình

| Mã | Dữ liệu huấn luyện | Vai trò |
|---|---|---|
| M0 | Train cũ 15 lớp (đã có, RQ1) | Mô hình gốc để tham chiếu |
| M0b | Train cũ giới hạn 13 lớp chung | Điểm so sánh công bằng về không gian nhãn |
| M1 | Train lấy từ bản improved | Dữ liệu đã sửa lỗi có giúp không |
| M2 (hoãn) | Train cũ cộng Benign "FIN có dữ liệu" lấy từ improved | Tách "thiếu mẫu" khỏi "khác định nghĩa đặc trưng". Theo yêu cầu của người dùng, tạm không chạy. Mã đã có (`04_build_datasets.py`, `05_train_models.py m2_10000`) để chạy sau |

## Bộ đánh giá

| Mã | Nội dung | Ghi chú |
|---|---|---|
| T1 | Test cũ (`test_set.parquet`) | Trong phân phối của M0, M0b, M2 |
| T2 | Test stratified 20 % của bản improved | Trong phân phối của M1 |
| T3 | Flow realtime của máy người dùng (`feeder_live`), có nhật ký hoạt động | Đo báo nhầm trên lưu lượng thật. Không dùng PCAP đã nạp |

Siêu tham số XGBoost và cấu hình SHAP, LIME giữ nguyên của RQ1 và RQ2, không quét hay chọn lại.

## Thứ tự thực hiện (mỗi bước một commit)

1. Kế hoạch và quy ước (tệp này).
2. Gom mã kiểm toán dataset và bảng ánh xạ đặc trưng, nhãn.
3. Dựng bộ dữ liệu từ bản improved.
4. Quét tham số và huấn luyện M0b, M1, M2.
5. Đánh giá chéo trên T1, T2, T3.
6. SHAP và LIME cho các mô hình mới.
7. Báo cáo đầy đủ.

Dữ liệu trung gian (`data/`) và mô hình (`models/`) không được commit. Kết quả CSV, mã và tài liệu được commit.

## Trạng thái (26/10/2026)

| Hạng mục | Trạng thái |
|---|---|
| Bảng ánh xạ, so sánh hai bộ train (cũ và improved) | Xong |
| Dựng train và test M1 theo công thức lấy mẫu của RQ1 | Xong |
| Huấn luyện M0b và M1 (tham số RQ1, không quét lại) | Xong |
| Đánh giá chéo T1, T2a, T3, có bản bỏ dòng trùng | Xong |
| SHAP và LIME cho M1 (cấu hình RQ2 đã khóa, bỏ GĐ5 và GĐ9) | Xong |
| M2 (thêm Benign vào train cũ) | Hoãn theo yêu cầu người dùng |
| Kiểm tra riêng M1 (nhãn xáo trộn, đường cong học, gần trùng, Src IP theo lớp) | Xong |
| Báo cáo đầy đủ | `report/Bao_cao_RQ4_so_sanh_dataset_cu_va_moi.docx`, dựng bằng `report/build_report.js` |

Dựng lại báo cáo: `python scripts/11_report_data.py` rồi `node report/build_report.js <đầu ra.docx> <văn bản.txt>`.
