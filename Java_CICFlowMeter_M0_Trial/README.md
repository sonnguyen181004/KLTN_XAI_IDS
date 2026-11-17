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

## Đối chiếu PCAP thật ngày 17/11/2026

Đã chuyển `test.pcapng` và `tesst2.pcapng` sang PCAP bằng Wireshark `editcap -F pcap`. Số frame trước/sau của `test` là 515/515; Java/Python đều đọc chính file PCAP sau chuyển. Dùng Python extractor `project` (lifecycle v3) của RQ3. Kết quả chi tiết không chứa IP nằm trong `real_pcap_comparison_20261117.json`.

| File | Java / Python flow CSV | Gói tính vào CSV Java / Python | Cặp flow ghép duy nhất | M0 Hulk Java / Python | Nhãn khác nhau trên cặp ghép |
|---|---:|---:|---:|---:|---:|
| test | 38 / 38 | 510 / 511 | 33 | 1 / 5 | 4 |
| tesst2 | 60 / 61 | 635 / 637 | 58 | 1 / 3 | 2 |

Ghép bằng IP nguồn/đích, cổng, giao thức và giây bắt đầu; flow trùng khóa hoặc không có phía đối ứng được loại khỏi so sánh theo cặp. Trên 33 và 58 cặp, lần lượt 63 và 62 trong 78 đặc trưng có ít nhất một giá trị khác. Các cột độ dài gói lệch có hệ thống, thường khoảng 54 byte; đây là dấu hiệu khác quy ước tính header/payload, cần xác minh bằng gói gốc trước khi kết luận nguyên nhân. `test` có 1 dòng Java với `Flow Bytes/s` và `Flow Packets/s` không hữu hạn, nên chỉ 37/38 dòng được M0 dự đoán. Script từ chối dòng đó, không điền 0.

Hai PCAP này chưa có nhãn từng flow được kiểm chứng. Số Hulk thay đổi **không phải** độ chính xác hay FPR; cũng chưa thể kết luận bản Java đúng hơn. Java README ghi thời gian micro giây và script không nhân lại 1e6. Môi trường chạy model hiện tại có cảnh báo phiên bản XGBoost/scikit-learn khác lúc lưu pickle; cần kiểm tra trước khi dùng số liệu làm kết quả luận văn.

Lệnh tái lập sau khi có hai file `.pcap` trong `input/`:

```powershell
cd Java_CICFlowMeter_M0_Trial/upstream
$env:JAVA_HOME = 'C:\Program Files\Java\jdk1.8.0_431'
$env:GRADLE_USER_HOME = (Join-Path (Get-Location) '.gradle-home')
.\gradlew.bat exeCMD -PtrialInput='..\input' -PtrialOutput='..\output' --offline --no-daemon
cd ..\..
foreach ($name in @('test','tesst2')) {
  .\RQ3_IDS_System\.venv_capture\Scripts\python.exe RQ3_IDS_System\scripts\run_live_capture.py --pcap-input "Java_CICFlowMeter_M0_Trial\input\$name.pcap" --output "Java_CICFlowMeter_M0_Trial\output\${name}_python.csv" --extractor project
  python Java_CICFlowMeter_M0_Trial\predict_m0.py "Java_CICFlowMeter_M0_Trial\output\${name}.pcap_Flow.csv" --format java --output "Java_CICFlowMeter_M0_Trial\output\${name}_java_m0.csv"
  python Java_CICFlowMeter_M0_Trial\predict_m0.py "Java_CICFlowMeter_M0_Trial\output\${name}_python.csv" --format python --output "Java_CICFlowMeter_M0_Trial\output\${name}_python_m0.csv"
}
python Java_CICFlowMeter_M0_Trial\compare_extractors.py
```

## Bước kiểm chứng tiếp

### Thử thêm hai PCAP ngày 17/11/2026

Thử `ddos/restore.pcapng` (33 frame) và `ddos/HTTP-CPU025-02.pcapng` (3.440 frame). `editcap -F pcap` giữ nguyên số frame ở cả hai file. Kết quả đầy đủ không chứa IP trong `extra_pcap_comparison_20261117.json`.

| File | Flow Java / Python | Gói cộng từ CSV Java / Python | Cặp ghép duy nhất | M0 Hulk Java / Python | Cặp đổi nhãn |
|---|---:|---:|---:|---:|---:|
| restore | 3 / 3 | 31 / 33 | 3 | 0 / 2 | 2 |
| HTTP-CPU025-02 | 378 / 387 | 3.063 / 3.440 | 378 | 0 / 378 | 377 |

Trong file HTTP, ở 368/378 cặp ghép được, Python có nhiều hơn Java đúng một gói trong tổng số gói của flow. Các cột độ dài gói cũng khác ở cả 378 cặp; độ lệch trung vị `Fwd Pkt Len Max` là 66 byte. Đây là **bất tương thích trích xuất đáng kể**. Chưa xác minh nguyên nhân chính xác từ mã nguồn và từng packet; không xem Java là bản sửa lỗi cho M0. Tên file chứa `ddos` không phải nhãn chuẩn của từng flow. Không có log tấn công và nhãn từng flow để đo recall, FPR hay chọn bộ trích xuất tốt hơn.

Để tái lập, chuyển hai PCAPNG bằng `editcap -F pcap`, chạy Java `exeCMD` với từng PCAP, chạy Python `run_live_capture.py --extractor project` trên **cùng PCAP sau chuyển**, chạy `predict_m0.py` với `--format java` hoặc `--format python`, sau đó `python Java_CICFlowMeter_M0_Trial/compare_extractors.py restore HTTP-CPU025-02 --report extra_pcap_comparison.json`.

### Việc còn cần xác minh

1. Chuyển `test.pcapng` và `tesst2.pcapng` sang PCAP bằng công cụ đọc PCAPNG đáng tin cậy; ghi số packet trước/sau chuyển.
2. Chạy cùng PCAP qua Java và Python hiện tại, đối chiếu flow bằng IP/cổng/giao thức/thời gian, rồi so từng đặc trưng. Không ghép theo số dòng.
3. Đối chiếu những flow có nhãn thực được xác minh trước khi so số Benign/Hulk. Kiểm tra đơn vị thời gian theo từng cột; Java README ghi micro giây nên script hiện không nhân 1e6.
4. Nếu thử realtime Java: kiểm tra riêng việc bắt trên card, xuất CSV khi flow đóng, timeout, flush khi dừng và feeder đọc dòng mới. Chưa kết nối vào nút capture của RQ3.

Model hiện có: M0 (`RQ1_Model_Training_xboost/saved_models/`, 15 lớp), M0b (`RQ4_Retrain_Compare/models/`, 13 lớp), M1 (`RQ4_Retrain_Compare/models/` và bản trong `IDS_M1_Lab/models/`, 13 lớp). M2 chỉ là kế hoạch hoãn, chưa có file model đã huấn luyện.
