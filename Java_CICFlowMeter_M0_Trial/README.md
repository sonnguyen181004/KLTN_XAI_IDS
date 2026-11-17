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

## Thử CSV mẫu và CSV realtime đã lưu (17/11/2026)

Chạy `python Java_CICFlowMeter_M0_Trial/audit_csv_m0.py` từ gốc repo. Script đọc CSV trực tiếp, chuẩn hóa như feeder, dự đoán M0 trong bộ nhớ và chỉ ghi số tổng hợp vào `csv_and_saved_live_m0_20261117.json`. Không gọi API, không ghi DB. CSV mẫu đã ở đơn vị train; CSV live được đổi các cột thời gian từ giây sang micro giây theo feeder hiện tại.

| CSV | Dòng hợp lệ | Benign dự đoán | Hulk dự đoán | Khác |
|---|---:|---:|---:|---:|
| Mẫu 15 lớp có nhãn | 105/105 | 16 | 7 | 86/105 khớp nhãn tham chiếu; 7 Benign thật đều được dự đoán Benign |
| `live_review_01.csv` | 669/669 | 551 | 117 | 1 Bot |
| `live_manual_01.csv` | 267/267 | 221 | 46 | 0 |
| `live_phone_01.csv` | 22/22 | 21 | 1 | 0 |

CSV mẫu có 7 dòng mỗi lớp, được chọn để demo; 86/105 không phải chất lượng chung của model. Ba CSV live không có nhãn thật từng flow, nên các cảnh báo không được gọi là FPR. `live_review` và `live_manual` ghi extractor `rq3-cfm-0.5.0-fixes-v2`; `live_phone` không lưu phiên bản. Các file này là traffic đã thu và lưu trước đây, không phải phiên bắt realtime mới trong ngày 17/11.

Chỉ có CSV thì không thể chạy lại **CICFlowMeter Java** để so trích xuất: Java cần gói tin PCAP gốc của cùng phiên. Phép thử CSV kiểm tra đường chuẩn hóa và M0; phép thử PCAP phía trên mới so Java với Python.

## Việc còn cần xác minh

1. Xác minh từng flow Hulk bằng log hoạt động/PCAP và thời điểm bắt gói; chưa gán nhãn toàn bộ traffic live chỉ từ tên file.
2. Đối chiếu quy ước tính gói và độ dài của Java/Python với bộ tạo dữ liệu train M0; không ghép flow theo số dòng.
3. Đối chiếu các flow có nhãn thực được xác minh trước khi so Benign/Hulk. Kiểm tra đơn vị thời gian theo từng cột; Java README ghi micro giây nên script hiện không nhân 1e6.
4. Nếu thử realtime Java: kiểm tra riêng việc bắt trên card, xuất CSV khi flow đóng, timeout, flush khi dừng và feeder đọc dòng mới. Chưa kết nối vào nút capture của RQ3.

Model hiện có: M0 (`RQ1_Model_Training_xboost/saved_models/`, 15 lớp), M0b (`RQ4_Retrain_Compare/models/`, 13 lớp), M1 (`RQ4_Retrain_Compare/models/` và bản trong `IDS_M1_Lab/models/`, 13 lớp). M2 chỉ là kế hoạch hoãn, chưa có file model đã huấn luyện.

## Java bắt Wi-Fi realtime → flow → M0 (17/11/2026)

Đã thêm `LiveTrial.java` cho CLI Java thử riêng. Mã này bắt trên card Npcap theo tên chính xác, giới hạn 1–120 giây, ghi một dòng CSV khi Java đóng flow và ghi nốt flow còn mở khi hết thời gian. `run_java_live_m0.py` theo dõi CSV, dự đoán M0 từng dòng hoàn chỉnh ngay trong lúc capture chạy. Không gọi API, không dùng DB, không dùng M1; file CSV có IP được giữ trong `output/` và không commit.

Lượt 20 giây trên `Realtek RTL8852BE WiFi 6 802.11ax PCIe Adapter` đã kết thúc với mã 0; 57 dòng flow hợp lệ, M0 dự đoán 51 Benign và 6 DoS attacks-Hulk. Trong lúc Java còn bắt, đã thấy ít nhất 8 dự đoán được in ra trước khi tiến trình kết thúc. Đây là bằng chứng đường live hoạt động, **không** là bằng chứng 6 cảnh báo đúng hay sai vì không ghi nhãn từng flow/nhật ký hoạt động. Cũng chưa đo số packet nhận và packet mất ở NIC/Npcap; lượt 20 giây chưa kiểm chứng độ ổn định lâu dài.

Chạy lại từ thư mục gốc dự án sau khi clone Java, áp `trial-build.patch` và chép `LiveTrial.java` vào `upstream/src/main/java/cic/cs/unb/ca/ifm/`:

```powershell
cd Java_CICFlowMeter_M0_Trial/upstream
$env:JAVA_HOME = 'C:\Program Files\Java\jdk1.8.0_431'
$env:GRADLE_USER_HOME = (Join-Path (Get-Location) '.gradle-home')
.\gradlew.bat liveTrial -PtrialArgs=--list --offline --no-daemon
cd ..\..
python Java_CICFlowMeter_M0_Trial/run_java_live_m0.py --interface 'Realtek RTL8852BE WiFi 6 802.11ax PCIe Adapter' --seconds 20
```

Chạy PowerShell có quyền bắt gói trên card đã chọn. Để có các phép đo về traffic thật, cần chạy phiên có ghi ground truth/hoạt động rõ ràng, lưu PCAP cùng phiên để đối chiếu packet, và đánh giá tương thích đặc trưng Java với train M0. Không gọi 6 Hulk là báo nhầm chỉ vì người dùng không chủ động tạo tấn công trong 20 giây.

### Lệnh chạy gọn và chọn interface

Tại thư mục `SELF_KLTN`, dùng **một lệnh**:

```powershell
python Java_CICFlowMeter_M0_Trial/run_java_live_m0.py
```

Chương trình liệt kê các card Java/Npcap thấy được, cho nhập **số thứ tự** card (Wi-Fi thường có tên `Realtek RTL8852BE WiFi 6 802.11ax PCIe Adapter`; số thứ tự có thể thay đổi). Mặc định bắt 20 giây, flow nào Java đóng sẽ được M0 dự đoán ngay; khi hết thời gian Java ghi nốt flow còn mở. Chỉ định thời lượng khác: thêm `--seconds 30` (giới hạn 1–120 giây cho khu thử). Muốn xem card mà chưa bắt: `python Java_CICFlowMeter_M0_Trial/run_java_live_m0.py --list`. Bỏ qua menu nếu biết chính xác tên card: `--interface 'Realtek RTL8852BE WiFi 6 802.11ax PCIe Adapter'`.

Đây là menu **trong terminal của khu thử riêng**, chưa phải nút/chọn card trên dashboard chính. CSV và log Java từng lượt nằm trong `Java_CICFlowMeter_M0_Trial/output/` (không commit). Đã kiểm tra `--list` thấy card Wi-Fi thật; lệnh bắt trực tiếp 20 giây đã được kiểm tra ở lượt trên. Menu không dùng API/DB và không thay cách chạy M1.

## Đọc hai CSV phiên lab 04/11/2026 bằng M0

Theo yêu cầu, đã đọc trực tiếp `IDS_M1_Lab/data/capture_sessions/ff8f0fa5051b45389a9393023effc083/flows.csv` và `.../a10c3bc274594a00be959997bf552236/flows.csv`, áp ánh xạ/đơn vị như feeder rồi chạy M0 trong khu thử riêng. Cả 101 flow của phiên mang tên Hulk được M0 dự đoán Hulk. Trong phiên SSH, M0 dự đoán 173 Benign, 135 Hulk, 60 SSH-Bruteforce, 5 Infilteration. Riêng 323 flow đích cổng 22: 135 Hulk, 128 Benign, 60 SSH-Bruteforce. Đây là **nhãn do M0 trả về**, chưa phải phép đo đúng/sai từng flow vì cần nhãn thực và mốc thời gian của kịch bản. Không có PCAP trong hai thư mục phiên, nên không thể dùng Java CICFlowMeter trích xuất lại chính traffic đó từ các CSV.
