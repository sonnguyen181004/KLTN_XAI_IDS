# Đối chiếu song song M0 và M1

Trang `app/compare_dashboard.py` chạy hai mô hình trên cùng các flow đã lưu trong DB và đặt kết quả cạnh nhau:

- M0: mô hình RQ1, học từ dữ liệu cũ, 15 lớp.
- M1: mô hình RQ4, học từ dữ liệu improved, 13 lớp (`RQ4_Retrain_Compare/models/m1_*.pkl`).

Cả hai dùng 78 đặc trưng và cùng siêu tham số, nên cùng một flow đưa được vào cả hai mô hình.

## Tab trong dashboard chính

Dashboard chính (`app/dashboard.py`) có tab thứ tư **Đối chiếu M0 / M1**. Tab theo lượt dữ liệu và nguồn đang chọn ở thanh bên (mặc định là lượt gần nhất) và tự làm mới mỗi 5 giây như tab Giám sát, nên khi bắt realtime thấy kết quả của cả hai mô hình trên flow mới. M0 vẫn là mô hình chạy chính của API; tab này chỉ đọc DB và tự dự đoán lại bằng M1.

## Chạy trang riêng

Từ thư mục `RQ3_IDS_System/`:

    streamlit run app/compare_dashboard.py --server.port 8502

Dashboard chính vẫn chạy như cũ. Trang này không đổi API, DB hay pipeline: nó mở DB ở chế độ chỉ đọc và tự dự đoán lại.

## Trang cho thấy gì

- Tỷ lệ flow mỗi mô hình báo là tấn công, số flow hai mô hình khác nhãn, số flow trong vùng ba điều kiện của Hulk.
- Bảng số flow theo nhãn và bảng M0 so với M1.
- Chọn một flow để xem nhãn, xác suất và SHAP Top-k của cả hai mô hình, kèm giá trị các đặc trưng chính.

File mô hình M1 không được commit (`.gitignore` bỏ `*.pkl`). Nếu thiếu, huấn luyện lại bằng `python RQ4_Retrain_Compare/scripts/05_train_models.py m1`.

## Kết quả khi thử trên DB hiện tại

| Nguồn | Số flow | M0 báo tấn công | M1 báo tấn công | Trong vùng FIN |
|---|---|---|---|---|
| feeder_live | 1.036 | 149 | 0 | 148 |
| pcap_replay | 448 | 381 | 0 | 381 |
| csv_upload | 105 | 89 | 29 | 0 |

Không flow nào trong DB có nhãn thật (`label_true` trống). Với feeder_live, nhãn Benign do người dùng xác nhận bằng lời cho 784 flow ngày 26/10/2026, các flow mới hơn chưa được xác nhận. Nhãn của pcap_replay và csv_upload chưa được ghi lại trong DB nên không đánh giá đúng sai ở đó.

## Kết quả test ngày 28/10/2026

- Realtime (Wi-Fi, lưu lượng web bình thường tạo bằng curl): 159 flow. M0 báo Hulk 46 flow, tất cả nằm trong vùng FIN của Hulk. M1 báo Benign cả 159. Dự đoán M0 tính lại khớp 100% với dự đoán M0 hệ thống đã lưu.
- CSV mẫu có nhãn thật (`results/system_test_csv.csv`): trên mẫu CSE-CIC-2018 cũ 15 lớp, tấn công bị báo Benign là 9 trên 98 ở M0 và 69 trên 98 ở M1. Trên mẫu 13 lớp chung là 10 trên 96 (M0) và 61 trên 96 (M1).
- PCAP `test.pcapng` (38 flow, chạy qua giao diện): M0 báo 5 flow là Hulk (cả 5 nằm trong vùng FIN), M1 báo Benign cả 38. Chưa có nhãn từng flow nên không tính đúng sai. Ảnh chụp từng bước nằm ở `RQ4_Retrain_Compare/report/demo_screenshots/`.

## Cách đọc

M1 báo Benign trên flow Benign thật không chứng minh M1 tốt. M1 chưa được thử trên tấn công độc lập, vẫn dựa nhiều vào đặc trưng cửa sổ nhận ban đầu, và chỉ nhận 3,7% đến 11,8% Hulk của bộ test cũ. Trang này minh họa vì sao hai mô hình khác nhau, không dùng để xếp hạng chúng.
