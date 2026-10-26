# RQ4 — Huấn luyện lại XGBoost trên dữ liệu đã sửa lỗi và so sánh với dữ liệu cũ

Mục đích: kiểm tra giả thuyết rằng báo nhầm Hulk trên lưu lượng thật đến từ khoảng trống của
CSE-CIC-IDS2018 bản CSV gốc (thiếu Benign "đóng bằng FIN có dữ liệu"), bằng cách huấn luyện lại
**đúng quy trình RQ1 và RQ2** trên bản improved rồi so sánh.

## Nguyên tắc: làm y như mô hình cũ

| Hạng mục | Mô hình cũ (RQ1, RQ2) | Mô hình mới (RQ4) |
|---|---|---|
| Thuật toán | XGBClassifier, tree_method hist, n_estimators 100, random_state 42 | Giống hệt |
| Quét tham số | 7 cấu hình (độ sâu 4 đến 12, learning rate 0,05 đến 0,10), chọn theo Macro F1 | Giống hệt |
| Đặc trưng | 78 đặc trưng, float32, không Timestamp, không IP | Giống hệt (đổi tên theo bảng ánh xạ) |
| Cách lấy mẫu | 3,5 triệu dòng, 70 % Benign và 30 % tấn công, giữ 100 % lớp hiếm | Cùng công thức, trần theo số mẫu sẵn có |
| Chia dữ liệu | Stratified 80/20 | Stratified 80/20 và thêm bộ giữ riêng theo thời gian |
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
| T2 | Test stratified 20 % của bản improved và bộ giữ riêng theo thời gian | Trong phân phối của M1 |
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
