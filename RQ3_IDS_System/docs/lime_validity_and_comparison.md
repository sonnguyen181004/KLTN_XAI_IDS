# LIME suy biến và đối chứng đặc trưng — 16/10/2026

## Bằng chứng từ PCAP người dùng

Flow `4546093c-b3b1-400f-ba43-498f704b537b`, nguồn `tesst2.pcapng`, dự đoán Hulk khoảng 72,97%.
Chạy chẩn đoán trong bộ nhớ, không ghi lại kết quả vào DB demo:

- 1.000 mẫu LIME; chỉ 1 mẫu có kernel weight khác 0 (mẫu gốc).
- Cỡ mẫu hiệu dụng ESS = 1; trọng số lớn nhất trong các mẫu còn lại = 0.
- Khoảng cách nhỏ nhất tới mẫu sinh khoảng 1,264 tỷ; mọi hệ số hồi quy bằng 0 nhưng Local R² trả 1.
- `Bwd Blk Rate Avg`: flow ≈ 1.264.390.243,9; cả 2.000 giá trị background đều bằng 0.
- `Bwd Byts/b Avg`: flow = 5.184; background cũng toàn 0.
- Một số đặc trưng cờ khác cũng lệch (ACK = 18 trong flow, background quan sát từ 0 đến 1).

Kết luận giới hạn: các mẫu sinh có trọng số số học bằng 0 nên LIME không học được biến thiên quanh flow này. Chưa đủ bằng chứng kết luận flow là tấn công, lỗi model, hay khẳng định toàn bộ lệch là do đổi đơn vị. Định nghĩa bulk/cờ giữa extractor và dữ liệu train cần đánh giá riêng.

## Cách sửa

1. Giữ nguyên model, 78 đầu vào, seed, kernel width 3.312, 1.000 mẫu, background và cấu hình RQ2. Không clipping đặc trưng, không tự tăng kernel, không thay background hoặc chuyển chế độ lấy mẫu để làm đẹp hình.
2. Quan sát chính neighborhood/kernel mà LIME thực sự dùng. Lưu số mẫu, số weight khác 0, ESS, khoảng cách gần nhất, raw R² và raw Top-5.
3. Nếu ESS < 2: `insufficient_neighborhood`. Đây là kiểm tra tối thiểu chống suy biến, không phải ngưỡng khoa học xác nhận giải thích tốt.
4. Nếu toàn bộ hệ số đúng bằng 0: `zero_coefficients`. R² không hữu hạn: `undefined_fit`. Các trường hợp này trả `local_r2=null`, `top_k=[]`, `agreement_jaccard5=null`. Raw vẫn trong diagnostics để kiểm tra.
5. `ok` chỉ nghĩa không vướng các kiểm tra trên, **không có nghĩa giải thích đúng hay chất lượng cao**.
6. Kết quả cũ có Top-5 toàn 0 được nhận diện khi đọc, không ghi đè lịch sử. Kết quả cũ khác được ghi `legacy_unchecked`; analyst có thể yêu cầu lại để bổ sung chẩn đoán.
7. Khóa các lượt gọi trên cùng LIME explainer để RNG mutable và diagnostic capture không trộn giữa request. Semaphore API vẫn giữ giới hạn số request được nhận; các lượt LIME được tính tuần tự trong cùng instance.

LIME suy biến không thay nhãn dự đoán, không xóa cảnh báo, không tự chuyển nhánh A/B. SHAP vẫn giữ nguyên. Jaccard chỉ tính khi có SHAP và LIME vượt kiểm tra tối thiểu; không so thứ hạng giả do hệ số đồng loạt bằng 0.

## Dữ liệu/API

- Migration cộng thêm `Reliability.lime_diagnostics_json`, giữ dữ liệu cũ.
- `/explain`: thêm `status`, `diagnostics`; R² và agreement có thể null.
- `/flows/{id}`: thêm `lime_status` và `lime_diagnostics`.
- `/flows/{id}/comparison`: 78 đặc trưng, giá trị flow, thông tin nền và nhóm tham chiếu, SHAP/LIME Top-5.
- Đối chứng đọc `lime_background.npy` (2.000 mẫu train đã dùng cho LIME) và `clean_holdout_set.csv` (tập B nhỏ có `label_true`). Không dùng nhãn dự đoán của các flow live để giả làm nhãn thật.
- Nếu thiếu mẫu một lớp: hiển thị n=0 và số liệu thiếu, không tự điền số 0 làm median.
- Tập B chỉ là tham chiếu mô tả; P05–P95 không phải ranh giới tấn công/Benign. Độ lệch chuẩn hóa nền là chỉ báo khoảng cách, không phải điểm nguy hiểm; với cột hằng dùng mẫu số 1 và ghi cờ hằng khác giá trị.
- LIME chỉ đưa vào bảng đối chứng khi `lime_status=ok`. Thiếu tên trong Top-5 là chưa được hiển thị, không đồng nghĩa đóng góp bằng 0.

## Kiểm thử

```powershell
python -B RQ3_IDS_System/scripts/stage15_test_lime_validity.py
python -B RQ3_IDS_System/scripts/stage14_test_dashboard_redesign.py
```

PASS kiểm thử số học normal/degenerate/flat, seed và gọi đồng thời; bộ regression dùng DB/server tạm đã PASS real prediction, SHAP, LIME, tab đối chứng, cảnh báo suy biến, CSV/PCAP và feeder. Không xóa/sửa DB demo trong lúc kiểm thử. Chưa nghiệm thu trực tiếp bằng trình duyệt người dùng sau bản sửa; cần restart API/Streamlit.

## Việc chưa làm

- Chưa sửa định nghĩa extractor/dataset hoặc đánh giá lại độ chính xác live.
- Chưa áp dụng LIME thay thế (sample-around-instance, kernel thích nghi hoặc background live): đây là thay đổi phương pháp cần tách cấu hình và thí nghiệm, không gộp vào bản RQ2 đã khóa.
- Không tự sửa tài liệu kiến trúc DOCX gốc hoặc kết quả nghiên cứu RQ2 đã xuất; bản cập nhật này là ghi chú triển khai RQ3.
