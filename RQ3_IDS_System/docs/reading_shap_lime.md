# Đọc đặc trưng, SHAP và LIME dễ hiểu

Cập nhật 16/10/2026. Chỉ cải thiện trình bày, không thay model, feature vector, cấu hình RQ2, hay luật nhánh A/B.

## 1. Ba điều khác nhau cần đọc

1. **Đặc trưng là gì?** Ví dụ `FIN Flag Cnt` ghi số gói có cờ FIN; FIN dùng cho kết thúc một chiều kết nối TCP.
2. **Giá trị của flow là bao nhiêu?** Giá trị 1 nghĩa là extractor ghi nhận một gói có cờ này; không phải một cuộc tấn công.
3. **Model sử dụng thông tin đó thế nào trong lần dự đoán này?** SHAP dương đẩy điểm về lớp đang giải thích; âm kéo điểm ra khỏi lớp đó. Đây không phải quy tắc “có FIN thì là Hulk”.

Ví dụ từ ảnh người dùng:

| Tên | Cách hiểu giá trị | Cách đọc SHAP của flow trong ảnh |
|---|---|---|
| FIN Flag Cnt = 1 | Một gói được ghi nhận có cờ kết thúc kết nối | φ khoảng +5,865: đẩy điểm model về lớp Hulk |
| Fwd Pkt Len Max = 1454 | Gói lớn nhất chiều forward dài 1454 byte theo extractor | φ khoảng +2,473: đẩy điểm về Hulk |
| Dst Port = 443 | Cổng đích 443, thường dùng cho HTTPS; chưa xác nhận ứng dụng | φ khoảng −0,483: kéo điểm ra khỏi Hulk |
| Fwd IAT Min = 0 | Khoảng cách nhỏ nhất giữa gói forward bằng 0 trong dữ liệu; có thể do timestamp hoặc thiếu khoảng đo | φ khoảng −0,482: kéo điểm ra khỏi Hulk |
| Fwd Seg Size Min = 20 | Với extractor Python hiện tại, header IPv4 forward nhỏ nhất là 20 byte | φ khoảng +0,301: đẩy điểm về Hulk |

Đây là ví dụ cụ thể của flow trong ảnh, không phải quy tắc áp dụng cho mọi flow. SHAP dùng raw margin: +5,865 **không phải** +586,5% hay +5,865 điểm phần trăm xác suất. Chỉ có Top-5 nên không cộng các thanh này thành xác suất lớp.

## 2. Tra cứu ngay trên UI

- Tab SHAP/LIME: dưới biểu đồ có **Đọc từng đặc trưng bằng lời**. Mở tên cần xem; mục đầu mặc định mở. Tên gốc vẫn giữ để đối chiếu code/dataset.
- Tab Đối chứng đặc trưng: chọn tên → xem tên tiếng Việt, ý nghĩa, giá trị kèm đơn vị, lưu ý và hướng giải thích.
- Thống kê mẫu nền/Benign/lớp dự đoán là phần mở rộng, không phải nội dung bắt buộc để hiểu tên.
- Tra cứu toàn bộ 78 tên và bảng chẩn đoán lệch nền được thu gọn riêng.
- Fwd là chiều gói đầu tiên của flow, Bwd là chiều ngược lại; không mặc định Fwd luôn là laptop gửi ra Internet.
- IAT là khoảng thời gian giữa các gói; Mean trung bình, Min/Max nhỏ/lớn nhất, Std độ lệch chuẩn, Var phương sai.
- Dùng khoảng trắng nhóm hàng nghìn, dấu phẩy thập phân: `1 000` là một nghìn; ESS = `1` là một mẫu, không còn ghi `1.000` gây nhầm.

## 3. Vì sao LIME trong ảnh không có thanh?

LIME tạo 1.000 mẫu thay đổi đặc trưng, cho model dự đoán rồi học một mô hình đơn giản ở vùng gần flow. Mẫu càng xa flow gốc càng có trọng số nhỏ.

Trong trường hợp đã kiểm tra, 999 mẫu có trọng số số học bằng 0; chỉ mẫu gốc còn tác dụng. LIME gần như chỉ có một ví dụ nên không học được sự thay đổi giữa các mẫu. Các hệ số bằng 0 không tạo được một thứ hạng giải thích có ý nghĩa.

Một dấu hiệu nổi bật: `Bwd Blk Rate Avg` của flow khoảng 1,264 tỷ byte/giây theo extractor, trong khi 2.000 mẫu nền của cột này đều 0. Đây là tốc độ trong bulk (đợt truyền), không phải tốc độ trung bình của toàn flow hay thông lượng đường truyền đã được kiểm chứng. Các giá trị lệch mẫu nền góp vào khoảng cách rất lớn. Chưa đủ để kết luận đó là lỗi đơn vị hay tấn công.

- Kết quả dự đoán XGBoost vẫn tồn tại; SHAP vẫn có thể xem.
- LIME lần này không đủ cơ sở làm đối chiếu. R²=1 với một mẫu hiệu dụng không chứng minh giải thích tốt.
- Không tự thay trọng số, mở rộng kernel hay đổi background để vẽ thanh cho đẹp.
- Bấm lại cùng flow/config thường cho cùng kết quả; kiểm tra tính hợp lệ mới có ích nếu kết quả cũ chưa lưu chẩn đoán.
- Khi LIME hợp lệ, dấu của weight là dấu hệ số trong mô hình xấp xỉ cục bộ. Không trình bày weight như phần trăm gây ra dự đoán hoặc quan hệ nhân quả.

## 4. Nguồn định nghĩa và giới hạn

Danh mục dùng chung: `app/feature_help.py` (78 tên, kiểm tra khớp mapping trong feeder). Diễn giải UI: `app/xai_reading_ui.py`.
Đối chiếu triển khai cục bộ CICFlowMeter Python 0.5.0: `flow.py`, `features/packet_length.py`, `features/packet_count.py`, `features/flow_bytes.py`; thời gian đầu vào model theo `app/normalize.py`.

Các chi tiết khác biệt extractor được ghi chú, không giả định mọi phiên bản CICFlowMeter giống nhau:

- Header dùng header IPv4 trong extractor hiện tại.
- Seg Size Avg sao chép Pkt Len Mean; Subflow sao chép tổng gói/byte tương ứng.
- `CWE Flag Count` trong dataset liên quan CWR, nhưng extractor Python 0.5.0 hiện sao chép Fwd URG Flags vào cột xuất tương ứng. UI cảnh báo để không diễn giải nhầm thành phép đếm CWR độc lập.
- Cách tính đặc trưng/cờ live có thể khác dataset; bản này không sửa extractor hay đánh giá lại khả năng tổng quát hóa model.

## 5. Kiểm thử và chạy lại

```powershell
python -B RQ3_IDS_System/scripts/stage16_test_feature_help.py
python -B RQ3_IDS_System/scripts/stage15_test_lime_validity.py
python -B RQ3_IDS_System/scripts/stage14_test_dashboard_redesign.py
```

Stage16 kiểm tra đủ 78 tên/đơn vị, định dạng số và hướng diễn giải; Stage15 kiểm tra LIME số học; Stage14 kiểm tra API/UI, chọn FIN để tra cứu, trạng thái LIME lỗi, CSV/PCAP trên DB tạm. Không cần reset DB để dùng UI mới. Khởi động lại API và Streamlit sau cập nhật; tự-refresh không tự chạy lại LIME.
