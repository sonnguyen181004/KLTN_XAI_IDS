# Dùng dashboard với mô hình M1

Giao diện giống bản RQ3 (xem [dashboard_usage.md](../../RQ3_IDS_System/docs/dashboard_usage.md) cho từng màn hình). Tài liệu này chỉ ghi phần khác khi chạy M1.

## 1. Bật hệ thống

1. Mở terminal tại `IDS_M1_Lab`.
2. Chạy `.\run_ids.ps1`. API ở cổng 8000, dashboard ở `http://127.0.0.1:8501`.
3. Đợi dashboard hiện trạng thái API là sẵn sàng. Nếu cổng 8000 đang bị bản RQ3 dùng thì tắt bản đó trước, vì hai API không dùng chung một DB.

## 2. Ba cách nạp dữ liệu

| Cách | Thao tác | Ghi chú |
|---|---|---|
| CSV có sẵn 78 đặc trưng | Tab Nạp CSV / PCAP, chọn file CSV | Thử nhanh bằng `data/clean_holdout_set.csv` (236 dòng) hoặc `scripts/m1_full_test_csv.py` |
| PCAP đã ghi | Tab Nạp CSV / PCAP, chọn file PCAP hoặc PCAPNG | Cần môi trường capture |
| Realtime | Tab Realtime, chọn card mạng, bấm bắt đầu | Cần Npcap và token điều khiển do `run_ids.ps1` đặt |

Nếu `IDS_M1_Lab/.venv_capture` chưa có, hệ thống dùng `RQ3_IDS_System/.venv_capture`. Câu lệnh capture tay mà màn hình Realtime hiển thị đã trỏ sẵn tới venv này.

## 3. Đọc kết quả khác với bản M0

- Nhãn dự đoán thuộc 13 lớp (Benign và 12 loại tấn công), không còn các lớp riêng của dữ liệu gốc. Hulk và nhãn tương ứng không còn dựa vào vùng FIN như M0.
- SHAP luôn có. Với flow bình thường, M1 cho đóng góp của đặc trưng FIN gần 0 (trung bình −0,079 trên 148 flow trong vùng FIN), khác M0 (+5,865).
- LIME chạy với kernel 3000 thay vì 3,312. Trạng thái `ok` và R² cao ở kernel này chủ yếu phản ánh trọng số gần đều, nên đọc LIME như xu hướng toàn cục quanh flow, không phải giải thích cục bộ chặt. Xem [README](../README.md) mục "Vì sao kernel LIME là 3000".
- Tab so sánh đang so M1 với M1, nên không dùng nó để so M0 và M1.
- Nhãn dự đoán không phải xác nhận tấn công. Hai ca SSH đã thử (A07, B03) cho SSH-Bruteforce với độ tin cậy 0,82 và 0,78; số mẫu quá ít để kết luận tỷ lệ phát hiện.

## 4. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Nút điều khiển capture bị khóa | Chạy bằng `run_ids.ps1`, hoặc đặt `IDS_CAPTURE_CONTROL_TOKEN` trước khi bật API |
| Không tìm thấy Python của capture | Kiểm tra `RQ3_IDS_System/.venv_capture/Scripts/python.exe` có tồn tại |
| LIME báo `insufficient_neighborhood` | Dùng kernel lớn hơn trong `config.yaml` (xem bảng quét kernel trong README) |
| Thiếu `data/train_stats.json` hoặc `lime_background.npy` | Dựng lại bằng `scripts/stage08_compute_train_stats.py` và `scripts/stage09_compute_lime_background.py` |
