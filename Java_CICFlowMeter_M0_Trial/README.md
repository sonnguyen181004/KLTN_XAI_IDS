# Thử CICFlowMeter Java với M0 (độc lập)

Mục đích: kiểm tra bản Java V4 trích xuất PCAP thành flow và chạy model RQ1 M0 (15 lớp). Thư mục này không dùng API, DB, UI hay M1. Kết quả Java không tự chứng minh tương thích với bộ train M0.

## Đã kiểm tra ngày 17/11/2026

- Clone `ahlashkari/CICFlowMeter` vào `upstream/` (bản V4, Gradle 4.2, Java 8).
- Thay dependency jNetPcap bằng JAR có sẵn trong kho, chỉ trong bản clone thử nghiệm.
- Build `classes` thành công bằng JDK 8 trên Windows.
- Chạy `RQ3_IDS_System/data/stage13_synthetic.pcap`: 6 packet hợp lệ, Java xuất 1 dòng flow vào `output/stage13_synthetic.pcap_Flow.csv`. Chương trình cũng in `total 2 flows`; cần kiểm tra khác biệt giữa flow nội bộ và dòng CSV khi thử PCAP lớn.
- Script `predict_m0.py` đọc CSV Java, ánh xạ tên cột bằng bảng sẵn có của RQ4, kiểm tra đủ 78 đặc trưng và giá trị hữu hạn, rồi chạy M0 độc lập: 1 dòng synthetic ra Benign. Đây chỉ là smoke test, không phải đo accuracy/FPR.
- Môi trường Python hiện tại cảnh báo khác phiên bản XGBoost/scikit-learn khi đọc pickle; cần đối chiếu phiên bản huấn luyện trước khi dùng kết quả để báo cáo.

## Chạy lại với một PCAP

Nếu chuyển thư mục thử sang máy khác, clone [kho Java](https://github.com/ahlashkari/CICFlowMeter) vào `upstream/` rồi áp dụng hai thay đổi nhỏ được mô tả trong `trial-build.patch` trước khi chạy.

Trong PowerShell tại gốc `SELF_KLTN`:

```powershell
cd Java_CICFlowMeter_M0_Trial/upstream
$env:JAVA_HOME = 'C:\Program Files\Java\jdk1.8.0_431'
$env:GRADLE_USER_HOME = (Join-Path (Get-Location) '.gradle-home')
.\gradlew.bat exeCMD -PtrialInput='..\..\RQ3_IDS_System\data\stage13_synthetic.pcap' -PtrialOutput='..\output' --offline --no-daemon
cd ..\..
python Java_CICFlowMeter_M0_Trial/predict_m0.py Java_CICFlowMeter_M0_Trial/output/stage13_synthetic.pcap_Flow.csv
```

Đổi `trialInput` sang PCAP cần thử; đầu ra là `<tên PCAP>_Flow.csv`. `Cmd` của bản Java này chỉ nhận `.pcap`; các file `.pcapng` phải chuyển sang PCAP trước khi thử, giữ bản gốc để đối chiếu. Không dùng CSV từ phiên khác để kết luận về PCAP này.

## Bước kiểm chứng tiếp

1. Chuyển `test.pcapng` và `tesst2.pcapng` sang PCAP bằng công cụ đọc PCAPNG đáng tin cậy; ghi số packet trước/sau chuyển.
2. Chạy cùng PCAP qua Java và Python hiện tại, đối chiếu flow bằng IP/cổng/giao thức/thời gian, rồi so từng đặc trưng. Không ghép theo số dòng.
3. Đối chiếu những flow có nhãn thực được xác minh trước khi so số Benign/Hulk. Kiểm tra đơn vị thời gian theo từng cột; Java README ghi micro giây nên script hiện không nhân 1e6.
4. Nếu thử realtime Java: kiểm tra riêng việc bắt trên card, xuất CSV khi flow đóng, timeout, flush khi dừng và feeder đọc dòng mới. Chưa kết nối vào nút capture của RQ3.

Model hiện có: M0 (`RQ1_Model_Training_xboost/saved_models/`, 15 lớp), M0b (`RQ4_Retrain_Compare/models/`, 13 lớp), M1 (`RQ4_Retrain_Compare/models/` và bản trong `IDS_M1_Lab/models/`, 13 lớp). M2 chỉ là kế hoạch hoãn, chưa có file model đã huấn luyện.
