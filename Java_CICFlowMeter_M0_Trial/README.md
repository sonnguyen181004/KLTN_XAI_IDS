# Thử CICFlowMeter Java với M0 và M1 (độc lập)

Mục đích: kiểm tra bản Java V4 trích xuất traffic/PCAP thành flow, rồi cho M0 (15 lớp) và M1 (13 lớp) dự đoán, giải thích riêng trên cùng flow. Tên thư mục giữ từ giai đoạn chỉ thử M0. Khu này có API/UI riêng, không ghi DB hoặc sửa model của RQ3/IDS_M1_Lab. Kết quả Java không tự chứng minh tương thích với bộ train của hai model.

**Kết luận kiểm tra mới nhất 17/11/2026:** đúng là Java trích xuất, nhưng chưa tương thích đầy đủ với bộ train M0 hoặc bộ improved tham chiếu M1. M1 đang dùng trong IDS_M1_Lab đã khác checksum bản M1 nghiên cứu lưu ở RQ4. Trên hai CSV lab cũ do Python xuất, M1 hiện tại trả toàn bộ Benign; không dùng việc ít cảnh báo khi duyệt web để kết luận M1 tốt hơn. Xem mục kiểm tra CSV và ngữ nghĩa đặc trưng cuối tài liệu.

**Dọn phần thử ngày 17/11/2026:** bỏ `smoke_dashboard.py` chỉ kiểm tra M0; chuyển kiểm tra SHAP tự động và LIME cảnh báo vào `smoke_dual_models.py` để giữ phạm vi kiểm thử. Giữ các JSON kết quả có ngày vì chúng lưu phiên bản/model và bằng chứng khác nhau. `input/`, `output/`, `upstream/` và cache Python không đưa lên Git; không xóa PCAP, CSV hay model cục bộ. README gốc có liên kết vào hướng dẫn này.

## Chạy dashboard và tự bấm Bắt/Dừng

Mở một terminal **PowerShell trong VS Code**, dán cả khối sau:

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN
python Java_CICFlowMeter_M0_Trial/launch_dashboard.py
```

Giữ terminal này chạy và mở **http://127.0.0.1:8502**. Launcher tự chạy API và dashboard; không cần mở thêm terminal feeder hoặc chép token.

1. Chọn **M0** hoặc **M1** ở đầu trang.
2. Mở tab **Realtime**, chọn **Realtek RTL8852BE WiFi 6 802.11ax PCIe Adapter** để bắt traffic Wi-Fi của Windows. Kiểm tra ngày 17/11/2026: card đang Up, IP `192.168.3.6`; IP có thể thay đổi khi đổi mạng. Nếu test lab mạng `192.168.11.x`, chọn **VMware Virtual Ethernet Adapter for VMnet1**.
3. Giữ ô thời gian là **0**: chạy đến khi bạn bấm Dừng, không tự dừng sau một số giây. Chỉ nhập số lớn hơn 0 khi muốn tự dừng theo thời lượng.
4. Bấm **Bắt đầu Java**. Đợi `starting` chuyển sang `capturing`, rồi lướt web hoặc tạo traffic hợp lệ trên mạng lab đang chọn.
5. Khi muốn kết thúc, bấm **Dừng và ghi nốt flow**, đợi `finished`. Flow còn mở sẽ được ghi nốt để model xử lý.
6. Vào **Giám sát flow**, **bấm trực tiếp một dòng trong bảng** để hiện chi tiết ngay bên dưới, gồm xác suất, SHAP, LIME và đặc trưng. Không cần chọn thêm trong danh sách. Flow đang xem được giữ khi có flow mới. Chọn M0/M1 ở thanh bên trái để xem kết quả riêng trên cùng lượt dữ liệu.

Nếu chưa có flow trong lúc bắt, thử tạo traffic rồi bấm Dừng để ghi nốt. Nếu kết thúc vẫn báo 0 gói, kiểm tra card được chọn và đường gói; chưa có dữ liệu để đánh giá model.

**Đóng hoặc chạy lại sau cập nhật:** bấm Dừng, đợi `finished`, sau đó nhấn **Ctrl+C** trong terminal. Muốn mở bản mới, chạy lại khối lệnh trên và tải lại trang. Lịch sử trên giao diện hiện ở RAM, đóng launcher sẽ mất; CSV và log capture nằm trong `Java_CICFlowMeter_M0_Trial/output/`.

## Đã kiểm tra ngày 17/11/2026

### Sửa lỗi 500 khi mở chi tiết và đồng bộ bố cục IDS_M1

Lượt Java `dashboard_86b5e6f743c5.csv`, dòng flow 108 có `Flow Duration=0`, `Flow Bytes/s=Infinity`, `Flow Packets/s=Infinity`. Bộ dự đoán đã từ chối dòng này nhưng API cũ vẫn đưa số vô hạn vào JSON chi tiết nên trả HTTP 500. Đã sửa phản hồi JSON: các số không hữu hạn hiển thị `null`, kèm `invalid_features` ghi giá trị gốc. Vector nội bộ vẫn được kiểm tra và không dự đoán; không điền 0, không đổi nhãn. Cơ chế này cũng áp dụng cho phản hồi SHAP/LIME và các chỉ số chưa hữu hạn.

Giao diện dùng bố cục trình bày của IDS_M1: bộ lọc bên trái, thanh trạng thái, sáu ô chỉ số, biểu đồ thời gian và nhãn, bảng tô màu với chọn dòng trực tiếp, nút Trang trước/Trang sau, sáu tab chi tiết (Xác suất, SHAP tự động, LIME, Đối chứng đặc trưng, Đánh giá giải thích, Đặc trưng và thời gian). Flow lỗi có nhóm riêng, không tính vào cảnh báo. Lỗi lấy chi tiết được hiển thị gọn và không giữ chi tiết của flow trước. Model và lượt dữ liệu có khóa lựa chọn riêng; nạp lại cùng tên CSV vẫn tạo mã lượt mới.

Kiểm thử riêng trên cổng 18765/18766 để không can thiệp phiên người dùng: `test_invalid_flow.py` tái hiện dòng 108 và thêm NaN, -Infinity, giá trị thiếu cho cả M0/M1; chi tiết trả 200 với JSON hợp lệ, SHAP/LIME cho flow lỗi trả 422, không có token trả 403, flow không tồn tại trả 404. `smoke_ui.py` gửi sự kiện chọn dòng bảng thật qua Streamlit AppTest, kiểm tra chi tiết flow lỗi/hợp lệ, SHAP/LIME từng model, giữ lựa chọn khi có dòng mới và bộ lọc Không hợp lệ. Đây là kiểm thử giao diện bằng AppTest, không phải kiểm tra ảnh từng pixel trong trình duyệt.

Sau cập nhật cần dừng capture rồi khởi động lại launcher để API nạp bản sửa. CSV phiên cũ vẫn ở `output/`; có thể nạp lại qua tab CSV để xem sau khi restart. Bố cục theo IDS_M1 nhưng các phần vận hành chưa triển khai (DB lịch sử, hàng đợi SHAP, đo độ trễ đầy đủ) vẫn giữ giới hạn đã ghi bên dưới; không hiển thị số liệu giả cho những phần đó.

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

## Dashboard riêng Java + M0/M1 + SHAP/LIME

Lệnh chạy **một terminal** tại gốc `SELF_KLTN`:

```powershell
python Java_CICFlowMeter_M0_Trial/launch_dashboard.py
```

Mở `http://127.0.0.1:8502`. Chọn **M0** hoặc **M1** ở đầu trang. Mỗi chế độ có ba tab: **Giám sát flow**, **Realtime**, **Nạp CSV / PCAP**. Mỗi model có nhãn, xác suất, SHAP, LIME, nền trung vị train và nhánh giải thích riêng; không có bảng so sánh M0/M1. Chọn interface trong Realtime, chọn thời gian `0` để chạy tới khi bấm **Dừng và ghi nốt flow**, hoặc nhập 1–3600 giây để tự dừng. Một phiên Java cung cấp cùng các flow cho hai model; đổi chế độ xem không bắt lại traffic. Java xuất flow khi đóng hoặc khi dừng, sau đó cả hai model dự đoán. SHAP tự tính cho cảnh báo; Benign có nút SHAP theo yêu cầu. LIME chỉ tính khi bấm nút và sẽ báo không đủ vùng mẫu nếu cỡ mẫu hiệu dụng quá thấp. Giám sát làm mới 3 giây, có biểu đồ theo phút/nhãn, lọc IP/nhãn/thời gian/cảnh báo, phân trang 50 flow và nhóm cảnh báo theo 5 phút. Đóng bằng Ctrl+C ở terminal đã chạy lệnh.

Tab Nạp dữ liệu nhận CSV có đủ 78 cột theo tên Java hoặc tên model, tối đa 20 MB/10.000 flow. Chỉ bật đổi giây sang micro giây khi CSV do Python CICFlowMeter xuất thời gian theo giây; CSV Java/dataset đã có micro giây thì để tắt. PCAP tối đa 100 MB được Java trích xuất; PCAPNG cần `editcap` của Wireshark để đổi sang PCAP trước. File tạm và CSV trích xuất ở `output/imports/`. Một lượt import thay danh sách flow trong bộ nhớ của khu thử; không lưu DB. Khi cần giữ kết quả, giữ CSV/PCAP riêng trước khi chạy lượt mới.

Thiết kế thử: `launch_dashboard.py` sở hữu API ở `127.0.0.1:8765` và Streamlit ở `127.0.0.1:8502`. API giữ trạng thái capture qua lần vẽ lại, chặn bắt trùng và dùng token cục bộ. `service.py` quản lý Java và hai bộ model/XAI độc lập; `dashboard.py` chỉ hiển thị/gửi lệnh. Java trích xuất, Python điều phối và dự đoán. Tập lớp và cấu hình/nền LIME của M0/M1 lấy từ thư mục tương ứng ở chế độ chỉ đọc. Lượt đang xem ở RAM, đóng launcher sẽ mất lịch sử trên giao diện. Hai dashboard RQ3 và IDS_M1_Lab không bị ghi vào.

Đã kiểm tra: API mở/dừng Java thật trên Wi-Fi, từ chối bắt trùng, đọc dòng CSV mới và ghi nốt flow lúc dừng (lượt kiểm tra sau cùng: 647 gói Java nhận, 27 flow, M0: 25 Benign và 2 Hulk). Kiểm tra offline từ CSV Java: SHAP giải thích đúng lớp Hulk với sai số cộng tính `2,86×10⁻⁶`; LIME trả `insufficient_neighborhood`, ESS=1. Kiểm tra giao diện bằng Streamlit AppTest: danh sách card, bảng flow, chọn flow và nút LIME đều hoạt động. Lượt ngắn này **chưa** kiểm chứng độ ổn định lâu dài, độ đúng nhãn hay tương thích đặc trưng Java–train M0. Tiến trình capture trong bản thử vẫn cần launcher còn sống; nếu hệ điều hành kết thúc launcher đột ngột, cần kiểm tra tiến trình Java còn lại trước khi mở lượt mới.

**Mở rộng M0/M1 (17/11/2026).** Mục đích là để thử hai model trên cùng flow do Java trích, với giao diện và thao tác theo dashboard RQ3/M1 nhưng hai chế độ hiển thị riêng. Kiểm tra offline trên `test.pcap_Flow.csv`: 38 dòng Java, M0 có 36 Benign/1 Hulk/1 dòng không hợp lệ; M1 có 37 Benign/1 dòng không hợp lệ. SHAP theo yêu cầu kiểm tra sai số cộng tính dưới 10⁻³ ở cả hai model; LIME M0 báo `insufficient_neighborhood`, M1 trả `ok` trên flow đã chọn. Trên CSV Java của lượt khác, M1 tự tạo SHAP cho một flow Infilteration (sai số cộng tính 1,67×10⁻⁶) và gắn nhánh B; nhãn này chưa có ground truth. CSV tên cột model được nạp đúng 78 giá trị; PCAP thử được Java xuất 38 flow và hai model xử lý. Streamlit AppTest đã chọn flow, bấm LIME rồi chuyển M1 mà không lỗi. Một lượt Wi-Fi 8 giây tự kết thúc với 0 gói trong lúc máy không tạo traffic; lượt đó chỉ kiểm tra vòng đời, không dùng để khẳng định đường live hai model đã nhận flow mới. Cần thử lại khi có traffic thực trước khi dùng kết quả live trong báo cáo.

Các chức năng giống cách dùng dashboard RQ3/M1: phạm vi M0/M1 riêng, trạng thái capture, biểu đồ nhãn và thời gian, bảng lọc và phân trang, nhóm cảnh báo 5 phút, chi tiết flow, xác suất các lớp, SHAP, LIME có kiểm tra hiệu lực, đối chứng 78 đặc trưng với trung vị train, nạp CSV/PCAP. **Giới hạn của khu thử:** chưa có DB/lịch sử qua lần khởi động, hàng đợi SHAP nền, chỉ số thời gian API, hay giao diện so sánh M0/M1 (người dùng không yêu cầu so sánh). SHAP cảnh báo được tính ngay trong tiến trình đọc CSV, nên PCAP nhiều flow hoặc traffic dày có thể khiến UI/API chậm; chưa kiểm thử tải cao. Bản Java và model M1 vẫn cần đánh giá tương thích đặc trưng và nhãn thật; khác biệt số cảnh báo không phải bằng chứng model nào tốt hơn.

## Kiểm tra card lab và trạng thái capture (17/11/2026)

Mục đích: xác minh người dùng chọn được card lab và tránh hiển thị đang bắt khi Gradle chưa mở card. Java/Npcap liệt kê được VMnet1, VMnet8, Wi-Fi, hai card VirtualBox. Windows hiện có VMnet1 = 192.168.11.1, VMnet8 = 192.168.52.1, Wi-Fi = 192.168.3.6; IP có thể thay đổi. Lab dùng mạng 192.168.11.x thì chọn **VMware Virtual Ethernet Adapter for VMnet1** trong tab Realtime. Không dùng số thứ tự card làm định danh cố định.

Đã tách trạng thái `starting` (Java/Gradle khởi động) và `capturing` (Java xác nhận mở card bằng `capture_started`). Có thể Dừng khi đang khởi động. Import/bắt trùng bị chặn ở giai đoạn đó. UI cảnh báo khi phiên kết thúc với 0 gói hợp lệ. Lỗi liệt kê card được trả về dưới dạng lỗi xử lý được và có timeout 90 giây.

Kiểm thử `python Java_CICFlowMeter_M0_Trial/smoke_live_api.py --interface VMnet1`: mở đúng GUID VMnet1, chạy thời hạn capture 8 giây, từ chối bắt trùng, kết thúc thành công nhưng 0 packet/0 flow. Chỉ xác minh mở/đóng card; chưa xác minh khả năng nhìn thấy traffic giữa hai VM. Streamlit AppTest chọn flow, LIME và chuyển M1 cũng PASS sau sửa.

Kiểm tra tiếp trong lab: bật capture trên VMnet1, tạo một phiên HTTP/SSH hợp lệ giữa Kali và Ubuntu trong cùng mạng lab, bấm Dừng và kiểm tra bảng có đúng cặp IP/cổng. Nếu không có flow, kiểm tra mạng ảo và đường gói bằng Wireshark trên cùng card; chưa dùng nhãn model để đánh giá. Việc thấy card VMnet1 không tự chứng minh Windows nhìn thấy toàn bộ traffic giữa hai VM.

Ưu tiên cải thiện sau kiểm tra đường gói: hàng đợi SHAP nền để dự đoán không phải chờ giải thích, DB riêng giữ lịch sử, thông số packet/drop và tài nguyên trong lúc chạy, kiểm thử tải lâu với traffic có nhãn. Chưa coi 0 packet là test dự đoán thành công, chưa kết luận ổn định dài hạn.

## Đọc hai CSV phiên lab 04/11/2026 bằng M0 (kết quả cũ)

Theo yêu cầu, đã đọc trực tiếp `IDS_M1_Lab/data/capture_sessions/ff8f0fa5051b45389a9393023effc083/flows.csv` và `.../a10c3bc274594a00be959997bf552236/flows.csv`, áp ánh xạ/đơn vị như feeder rồi chạy M0 trong khu thử riêng. Cả 101 flow của phiên mang tên Hulk được M0 dự đoán Hulk. Trong phiên SSH, M0 dự đoán 173 Benign, 135 Hulk, 60 SSH-Bruteforce, 5 Infilteration. Riêng 323 flow đích cổng 22: 135 Hulk, 128 Benign, 60 SSH-Bruteforce. Đây là **nhãn do M0 trả về**, chưa phải phép đo đúng/sai từng flow vì cần nhãn thực và mốc thời gian của kịch bản. Không có PCAP trong hai thư mục phiên, nên không thể dùng Java CICFlowMeter trích xuất lại chính traffic đó từ các CSV.

## Kiểm thử realtime qua điều khiển dashboard sau sửa lỗi 500 (17/11/2026)

Mục đích: kiểm tra luồng Wi-Fi thật → Java → CSV → hai model → chọn dòng xem chi tiết, sau thay đổi xử lý NaN/Infinity và giao diện. Đã chạy `test_realtime_ui.py` lúc khoảng 19:56–19:57, dùng API riêng cổng 18767 và Streamlit AppTest thực thi nút Bắt đầu/Dừng của dashboard. Không giả lập card hoặc CSV, không đổi model, không reset DB. Đây là kiểm thử chức năng UI bằng AppTest; chưa phải kiểm tra hình ảnh trên trình duyệt thật.

Phiên `5e1b1eae9e28` dùng card Realtek RTL8852BE WiFi 6. Script tạo sáu yêu cầu HTTPS tới example.com, đều HTTP 200; capture đồng thời chứa traffic nền trên card, không chỉ sáu yêu cầu này. Dùng chế độ thời lượng 0 rồi bấm Dừng: 31,32 giây từ lúc phát hiện Java đã mở card tới khi gửi Dừng; 33,19 giây tới khi đọc hết dữ liệu. Thời gian này không bao gồm khởi động Gradle.

| Kiểm tra | Kết quả |
| --- | --- |
| Gói TCP/UDP Java nhận | 16.163 |
| Flow xuất khi đang bắt / ghi nốt khi dừng | 20 / 36 |
| Đối soát CSV / API M0 / API M1 | 56 / 56 / 56; không có dòng không hợp lệ |
| M0 | 50 Benign, 6 DoS attacks-Hulk |
| M1 hiện tại | 56 Benign |
| GET chi tiết từng flow | 112/112 HTTP 200, JSON hợp lệ |
| Bấm dòng trên bảng | Flow 56 hiện đúng chi tiết ở cả M0 và M1 |
| SHAP theo yêu cầu trên flow 56 | Đúng lớp được dự đoán; sai số cộng tính M0 1,91×10⁻⁶, M1 3,81×10⁻⁶ |
| LIME trên flow 56 | M0: insufficient_neighborhood, ESS=1; M1: ok, ESS≈1000, R²≈0,646 |
| Dừng và giải phóng tiến trình | Java exit 0, luồng đọc CSV kết thúc, API kiểm thử tắt |

Kết quả chi tiết và SHA-256 của hai model nằm trong `realtime_ui_20261117.json`. CSV/log gốc ở `output/dashboard_5e1b1eae9e28.*`, chỉ giữ cục bộ. Kết quả này xác minh chức năng realtime và chọn flow sau sửa; không chứng minh không mất gói ở NIC/Npcap, không đo FPR, không chứng minh ổn định tải cao hoặc dài hạn. LIME M0 vẫn không có giải thích hữu ích cho flow đã thử; trạng thái `ok` của M1 không chứng nhận nhãn đúng hay lời giải thích có tính nhân quả. Phiên này không phát sinh Infinity, nên lỗi Infinity được kiểm tra riêng bằng `test_invalid_flow.py`, không quy cho phiên realtime này.

Chạy lại test khi không có phiên Java capture khác đang chạy:

```powershell
python Java_CICFlowMeter_M0_Trial/test_realtime_ui.py
```

Lệnh này thực sự mở card Wi-Fi, tạo traffic HTTPS nhẹ, dừng sau khoảng 30 giây rồi kiểm tra XAI và UI. Kết quả mới ghi `output/realtime_ui_latest.json`; không ghi đè kết quả đã lưu trong Git. Khi muốn tự sử dụng dashboard, vẫn chạy `python Java_CICFlowMeter_M0_Trial/launch_dashboard.py`, mở cổng 8502 và chọn model/interface như phần hướng dẫn trên.

## Kiểm tra CSV lab và ngữ nghĩa đặc trưng Java–train (17/11/2026)

Mục đích: xác minh bộ trích xuất thật, chạy lại hai CSV lab được chỉ định bằng hai model hiện có, và kiểm tra tương thích bằng dữ liệu train cùng packet biết trước. Script `audit_lab_and_semantics.py`; kết quả `lab_semantics_audit_20261117.json`. Không sửa model, extractor, nhãn hay DB. Toàn bộ bước này chạy offline, không phát gói tấn công.

### Bằng chứng đang dùng Java

Upstream là `https://github.com/ahlashkari/CICFlowMeter.git`, commit `98a5ebad0df579cc8b43eedd3421b3ae87699901`. Thư mục lõi `src/main/java/cic/cs/unb/ca/jnetpcap` không có thay đổi so với commit này. `LiveTrial.java` của khu thử trùng checksum với source trong thư mục build. Task Gradle `liveTrial` chạy lớp `cic.cs.unb.ca.ifm.LiveTrial`, gọi `Pcap.openLive` và `FlowGenerator`; log lượt `5e1b1eae9e28` có `capture_started`, `accepted_packets=16163 closed_flows=20 flushed_flows=36`. Python đảm nhiệm điều phối, đọc CSV, dự đoán và giao diện; không phải bộ trích xuất của lượt live đó. Đây không phải bằng chứng bản Java hiện tại chính là commit lịch sử đã tạo dataset 2018.

### Hai CSV lab cũ

Cả CSV và capture.log của hai phiên ghi `rq3-cfm-0.5.0-lifecycle-v3`: đây là CSV Python. Không có PCAP/PCAPNG trong hai thư mục phiên, nên chưa thể trích lại chính hai phiên đó bằng Java. Audit đổi tên cột theo feeder, đổi các cột thời gian giây → micro giây đúng một lần, giữ nguyên các rate; sau đó nhập CSV tên cột model vào service Java trial. Cả 474 vector đều đủ 78 cột hữu hạn. Dự đoán qua service khớp chạy trực tiếp model cho mọi dòng. Đây là kiểm tra suy luận từ CSV, không phải Java chuyển CSV thành packet.

| Phiên | Số flow | M0 hiện tại | M1 hiện tại |
| --- | ---: | --- | --- |
| Hulk, `ff8f0fa5051b45389a9393023effc083/flows.csv` | 101 | 101 Hulk | 101 Benign |
| SSH, `a10c3bc274594a00be959997bf552236/flows.csv` | 373 | 173 Benign, 135 Hulk, 60 SSH-Bruteforce, 5 Infilteration | 373 Benign |
| Riêng flow đích cổng 22 trong phiên SSH | 323 | 128 Benign, 135 Hulk, 60 SSH-Bruteforce | 323 Benign |

Các cảnh báo M0 có SHAP tự động, không lỗi; sai số cộng tính lớn nhất 2,86×10⁻⁶. Nhãn do model trả về không thay thế ground truth của từng flow. Nếu nhật ký kịch bản xác nhận các flow là tấn công, kết quả M1 toàn Benign cần được tính là bỏ sót tương ứng, không coi là cải thiện báo nhầm. CSV Python không thể chứng minh Java sẽ có cùng nhãn khi bắt lại.

M0 checksum `52eb5a671ee82109…` khớp model RQ1. M1 đang chạy checksum `3b858ed12c374f28…`, khác M1 nghiên cứu RQ4 `6ed405c11b53e412…` trong `models_manifest.csv`. Audit ghi đủ checksum, đường dẫn và tập lớp. `d2_train.parquet` được dùng làm bộ train improved tham chiếu; chưa có manifest tái tạo liên kết chắc chắn bộ này với M1 đã thay ngày 17/11. Không gán các kết quả nghiên cứu của M1 cũ sang artifact mới.

### Phần khớp và phần lệch đã đo lại

Đã quét toàn bộ 2.800.000 dòng train M0 và 2.728.397 dòng `d2_train.parquet`; thứ tự 78 cột đều khớp danh sách model. Tạo PCAP tổng hợp 21 packet với timestamp, chiều, payload, cờ và window biết trước, rồi chạy Java và Python lifecycle-v3 trên cùng PCAP. Đây là kiểm thử ngữ nghĩa, không phải traffic tấn công hay phép đo độ chính xác.

| Đặc trưng/quy tắc | Java đang dùng | Bằng chứng đối chiếu |
| --- | --- | --- |
| Đơn vị thời gian | Micro giây | 5 packet kéo dài 0,4 giây → Flow Duration 400.000. CSV Java không nhân thêm 10⁶. |
| Độ dài packet | Payload TCP/UDP | Ba packet forward payload 10/30/50 byte → tổng 90; Python đo frame → tổng 252. Không thể đổi tên cột để xóa sai khác này. |
| Std độ dài packet | Sample SD | Fixture forward trả 20; Python trả 16,33 (population SD). Trong train M0, 35.079/35.079 ca forward và 59.954/59.954 ca backward đủ điều kiện hai gói khớp sample SD. Train improved tham chiếu cũng khớp sample SD ở các ca đủ điều kiện. |
| Down/Up Ratio | Chia nguyên, fixture 2/3 → 0 | Train M0: 1.057.559/1.057.559 ca tỷ lệ không nguyên khớp floor. Train improved: 1.104.362/1.104.362 ca khớp tỷ lệ thực, tức Java hiện tại lệch bộ improved. |
| FIN/SYN/ACK/PSH và các cờ tổng | Đếm số gói có cờ | Fixture PSH=5, ACK=5; toàn bộ train M0 chỉ có giá trị 0/1 ở các cờ tổng. Train improved có giá trị lớn hơn 1. Không tự ép cờ về 0/1 khi chưa có quy ước lịch sử đầy đủ. |
| Fwd/Bwd PSH Flags | Chỉ cập nhật khi khởi tạo flow | Fixture có 3 PSH forward, 2 backward nhưng Java trả 1/0, Python trả 3/2. Java gần phạm vi train M0 (Fwd 0/1, Bwd toàn 0) nhưng lệch đếm cờ trong improved. |
| Pkt Len Mean và Pkt Size Avg | Packet đầu tham gia thống kê độ dài toàn flow hai lần | Fixture payload tổng 150 của 5 gói: Java Mean=160/6, Size Avg=160/5. Train M0 thỏa `SizeAvg*n=Mean*(n+1)` trên 2,8M dòng; improved thỏa hai mean bằng nhau trên toàn bộ 2.728.397 dòng. Khớp dấu vết số học không chứng minh bản lịch sử giống hoàn toàn. |
| Init Bwd Win Byts | Bị ghi lại bằng window packet backward sau | Window đầu 2000, sau 3000 → Java trả 3000; Python trả 2000. Chưa chứng nhận đây là quy ước bộ train. |
| Subflow, bulk, active | Có sai khác trong fixture | Ví dụ numeric flow Java Subflow Fwd Pkts=0, Python=3. Không khẳng định tương thích toàn bộ nhóm chỉ vì có cùng tên cột. |
| Đóng flow và ghi flow một gói | Có quy tắc FIN và bỏ flow một gói tại bước flush | PCAP 21 packet → Java 6 dòng chứa tổng 20 packet; Python 5 dòng chứa đủ 21. ACK cuối của ca FIN-forward thành flow một gói bị loại khỏi CSV Java. Source flush có điều kiện `packetCount()>1`; không gọi đây là mất gói ở NIC. |

Có 34/78 giá trị khác nhau giữa hai extractor trên riêng flow numeric gồm đúng 5 packet. Mười sáu kiểm tra Java khớp quy ước quan sát trong source, bao gồm các hành vi bất thường; PASS ở đây không có nghĩa 78 đặc trưng đã đúng về ngữ nghĩa mạng hoặc khớp hoàn toàn train. Fixture FIN cũng tái hiện khác biệt khi FIN backward đến trước; code cộng `getBwdFINFlags()` hai lần ở điều kiện đóng flow. Lõi chưa sửa trong bước audit để không âm thầm đổi đường dữ liệu trước khi có baseline.

**Kết luận:** Java dùng được để thử nghiệm có kiểm soát, nhưng chưa phải bộ trích xuất tương thích hoàn toàn cho cả M0/M1. Cần tách hồ sơ tương thích từng model, truy manifest của M1 hiện tại và lưu PCAP của phiên lab mới để so cùng packet. Không tự sửa cờ/window/tỷ lệ theo mục tiêu làm nhãn đẹp hơn. Thiếu source preprocessing/commit extractor lịch sử và cặp PCAP–CSV gốc nên chưa thể chứng nhận toàn bộ 78 đặc trưng của dataset.

### Bắt lại từ hai máy ảo

Card Windows kiểm tra ngày 17/11: VMnet1 đang Up, IP 192.168.11.1; VMnet8 đang Up, IP 192.168.52.1. Nếu Kali/Ubuntu dùng lab 192.168.11.x, chọn VMnet1 trong Realtime. Trước kịch bản tấn công, tạo HTTP/SSH hợp lệ và kiểm tra flow có đúng IP hai VM. Cùng VMnet1 không tự bảo đảm Windows thấy mọi unicast VM↔VM: nếu thiếu gói, cần xác minh bằng Wireshark và bố trí mirror/TAP hoặc cho traffic đi qua máy IDS. Không coi việc Java mở được card là đã nhìn thấy traffic lab.

Đợt tiếp theo: lưu PCAP gốc và nhật ký kịch bản cho từng phiên Hulk/SSH; trích Java và Python từ cùng PCAP; chạy đúng artifact M0/M1, đánh giá phát hiện/bỏ sót và đặc trưng. Không so hai lượt traffic khác nhau rồi quy khác biệt cho extractor.

## Chẩn đoán phiên Wi-Fi người dùng xác nhận là traffic bình thường

Phiên `ff127eeb80c7` ngày 17/11/2026: log xác nhận task Java `liveTrial`, cùng GUID Wi-Fi, 37.215 packet được nhận, 138 flow đóng trong phiên và 146 flow ghi lúc dừng. CSV có 284 dòng, đều hữu hạn và đủ 78 cột. Chạy lại đúng M0 checksum `52eb5a671ee82109…` thu được 176 Benign, 68 DoS attacks-Hulk, 40 DDOS attack-HOIC. Người dùng mô tả toàn bộ traffic là bình thường; theo mô tả đó, 108 cảnh báo là báo nhầm. Chưa có xác minh nhãn độc lập từng flow để dùng như benchmark FPR.

Tính lại SHAP cho cả 108 cảnh báo: trong 68 Hulk, FIN Flag Cnt là đóng góp dương mạnh nhất ở mọi flow; 60 flow có FIN=2, 8 flow FIN=1. Ví dụ flow 3: FIN=2 đóng góp +5,865 vào raw margin Hulk; Fwd Pkt Len Max=1400 góp +2,491; xác suất Hulk≈84,64%. FIN đóng kết nối hợp lệ và payload lớn đều có thể gặp trong traffic thường. Việc đã có 8 Hulk với FIN=1 cho thấy không thể quy tất cả sai nhãn chỉ cho giá trị cờ vượt 1 hoặc coi nhị phân hóa cờ là chắc chắn sửa được.

Trong 40 HOIC, Init Fwd Win Byts là đóng góp dương mạnh nhất ở mọi flow; ví dụ flow 20 có window=65535, đóng góp +5,240 vào raw margin HOIC, xác suất≈88,81%. Cả 40 flow có cổng đích 53; riêng cổng không xác minh ứng dụng hay nhãn thật. Window là thông số TCP, không phải bằng chứng HOIC. Sai số cộng tính SHAP lớn nhất khoảng 3,34×10⁻⁶: lời giải thích khớp phép tính model, không làm nhãn thành đúng.

Kết luận chẩn đoán: bộ trích xuất đúng là Java đang được thử, ánh xạ/đơn vị đã qua kiểm tra, nhưng tương thích ngữ nghĩa Java–train chưa đạt đầy đủ như bảng audit trên. M0 phản ứng mạnh với FIN/window trong các ca này; SHAP chỉ chỉ ra cách model tính, không chứng minh mọi nguyên nhân của báo nhầm. Không đổi model, không sửa đặc trưng đầu vào hoặc ép nhãn Benign trong bước này. Bằng chứng tổng hợp không chứa IP: `live_m0_diagnosis_ff127eeb80c7.json`. Tái lập:

```powershell
python Java_CICFlowMeter_M0_Trial/audit_live_m0.py Java_CICFlowMeter_M0_Trial/output/dashboard_ff127eeb80c7.csv --output Java_CICFlowMeter_M0_Trial/output/live_m0_diagnosis.json
```

## Đối chiếu PCAP SSH ngày 18/11/2026

Mục đích: xác minh vì sao phiên Hydra thử 20 mật khẩu sai được M0/M1 trả Benign; không sửa model hay đầu vào để ép nhãn. Script `audit_ssh_pcap.py` chạy Java và Python trên cùng `ssbrute.pcapng`, lưu checksum model/PCAP, dự đoán và SHAP trong `ssh_pcap_audit_20261118.json`. PCAP và thư mục output giữ cục bộ, không đưa vào Git.

Wireshark ghi 201 packet TCP/SSH thuộc 5 kết nối. Số lần thử mật khẩu không bằng số flow. Nhật ký Ubuntu do người dùng cung cấp xác nhận nhiều lần xác thực thất bại; chưa gán nhãn riêng cho mọi packet hoặc coi các flow nền trong PCAP là tấn công.

| Phạm vi 5 flow TCP tới cổng 22 | Java | Python project |
| --- | --- | --- |
| Tổng packet trong flow xuất ra | 195 | 201 |
| M0 | 5 Benign | 5 DoS attacks-Hulk |
| M1 hiện tại | 5 Benign | 5 Benign |

Toàn CSV Java có 8 dòng (gồm nền), Python có 7; tất cả đủ 78 giá trị hữu hạn. Không dùng tổng packet toàn CSV Java là 201 để tuyên bố bảo toàn 201 packet SSH: riêng SSH chỉ có 195. Cần tiếp tục đối soát 6 packet còn lại theo quy tắc đóng/flush flow; đây chưa phải bằng chứng NIC mất gói. Năm flow Java replay ghép được với CSV live `dashboard_d75fec2af76d.csv`, tái hiện nhãn Benign. Không khẳng định 78 giá trị bằng tuyệt đối: 8 đặc trưng IAT lệch nhỏ, các min/max lệch tối đa 1 micro giây, độ lệch chuẩn chênh dưới 1 micro giây.

Ví dụ flow SSH thứ hai, M0 cho Benign 99,746%. SHAP cho lớp SSH-Bruteforce: Dst Port=22 góp +2,469, Init Bwd Win Byts=127 góp -1,834, Flow IAT Mean khoảng 573.936 micro giây góp -0,584 và Fwd Pkts/s khoảng 0,891 góp -0,555. Với M1, Fwd PSH Flags=0 góp -1,877, PSH Flag Cnt=23 góp -1,271, trong khi cổng 22 chỉ góp +0,907. Các số là đóng góp raw margin theo từng model, không phải phần trăm hay chứng cứ xác nhận hành vi tấn công.

Kết quả cho thấy model ưu tiên các mẫu thống kê khác với kịch bản SSH này. Bản Java đã kiểm tra có bất thường ở directional PSH và Init Bwd Win Byts như audit ngữ nghĩa phía trên; do đó chưa thể quy toàn bộ lỗi cho domain shift, cũng chưa thể chứng nhận tương thích dataset chỉ vì đủ 78 tên cột. Python đổi M0 sang Hulk cũng không phải nhận đúng SSH. Model dùng thống kê flow, không nhận số lần Failed password trong nhật ký Ubuntu. Cần hoàn thiện hồ sơ tương thích theo từng artifact, đối soát packet/cờ/window, rồi đánh giá lại trên nhiều lượt có nhật ký chuẩn. Chưa đổi runtime hay train lại trong bước này.

Tái lập (cần PCAP gốc và CSV live còn ở máy):

```powershell
python Java_CICFlowMeter_M0_Trial/audit_ssh_pcap.py
```

## Đối chiếu Patator ss2 ngày 18/11/2026

Mục đích: kiểm tra cùng công cụ Patator có giải quyết bỏ sót SSH của Hydra không. Đã chạy offline Java và Python trên cùng `ss2.pcapng`, giữ nguyên artifact M0/M1; bằng chứng `ssh_patator_audit_20261118.json`. Script audit nhận `--pcap`, `--output` và `--live-csv` tùy chọn; không còn tự ghép CSV live của lượt Hydra khi kiểm tra PCAP khác. Lượt này không đối chiếu trực tiếp trạng thái dashboard live.

PCAP có 160 packet SSH thuộc 3 TCP stream. Java xuất 4 flow tới cổng 22 chứa 158 packet: 3 flow chính dài 18,25 / 19,82 / 18,18 giây và một flow phụ 2 packet dài 749 micro giây. M0 trả Benign cho 3 flow chính (99,31–99,45%), SSH-Bruteforce cho flow phụ (49,72%); M1 trả Benign cho 3 flow chính và Infilteration cho flow phụ. Không coi một flow phụ được gọi SSH là bằng chứng nhận diện tốt cả kịch bản. Python xuất 3 flow SSH chứa 160 packet; M0 trả Hulk cả 3, M1 trả Benign cả 3. Hai flow nền Java không tính là SSH. Chênh packet xuất ra cần đối soát lifecycle, không suy ra NIC mất gói.

Ảnh Patator 1.1.0 do người dùng cung cấp: 20 ứng viên, 18 kết quả và 2 lỗi No existing session; không diễn giải Hits=18 là tìm được 18 mật khẩu. Ubuntu ghi Failed password và đóng phiên vì quá số lần xác thực. Lượt này có traffic thử mật khẩu thật, nhưng không tái tạo chính xác cấu hình dataset.

Đọc lại toàn bộ 41.828 dòng SSH trong train M0: Flow Duration trung vị 367.033,5 micro giây (max 565.508); Fwd Pkts/s trung vị 62,470; Init Bwd Win Byts trung vị 230; Fwd Pkt Len Max trung vị 640. Trong train improved tham chiếu M1, PSH Flag Cnt toàn bộ mẫu SSH bằng 31; ss2 Java cũng có 31 ở ba flow chính, góp +3,300 SHAP vào lớp SSH của M1. Tuy nhiên Fwd PSH Flags=0 góp -1,877; các đóng góp còn lại và điểm các lớp khiến Benign vẫn thắng. SHAP là raw margin, không chứng minh nguyên nhân duy nhất. Cùng công cụ không xóa khác biệt cấu hình SSH, tốc độ và extractor. Dataset gốc công bố dùng Patator: https://www.unb.ca/cic/datasets/ids-2018.html . Chưa xác minh phiên bản/tham số lịch sử; chưa chứng nhận provenance bản M1 rebuilt với train tham chiếu.

Tái lập:

```powershell
python Java_CICFlowMeter_M0_Trial/audit_ssh_pcap.py --pcap Java_CICFlowMeter_M0_Trial/ss2.pcapng --output Java_CICFlowMeter_M0_Trial/ssh_patator_audit_20261118.json
```

Bước tiếp: đối soát directional PSH/window/flow với PCAP và extractor improved, xác minh provenance M1; chưa tăng tải hoặc sửa nhãn để buộc kết quả đúng. Không thay đổi model/runtime trong bước audit.

## Sửa thử nghiệm PSH theo chiều — 18/11/2026

Mục đích: sửa lỗi đếm cờ có bằng chứng từ PCAP, đo riêng ảnh hưởng lên M0/M1, không chỉnh đặc trưng để ép nhãn. `test_psh_fix.py` sao chép Java vào thư mục output riêng, thêm cập nhật fPSH_cnt/bPSH_cnt cho các packet sau packet đầu trong BasicFlow.addPacket. firstPacket giữ nguyên để không đếm hai lần. Quy tắc chiều theo đúng nhánh thống kê packet hiện có; không sửa window, FIN, timeout hoặc tổng PSH. Patch lưu trong `directional_psh_fix.patch`; kết quả và checksum trong `directional_psh_fix_20261118.json`. Dashboard vẫn dùng upstream gốc; bản thử nghiệm không thay runtime đang chạy.

Kiểm chứng đã PASS:
- PCAP tổng hợp có PSH ngay gói đầu: kết quả forward=3, backward=2, tổng=5, không đếm trùng gói đầu.
- ss2: ba flow chính đều forward=16, backward=15, tổng=31, khớp kiểm đếm TShark trước đó. Flow phụ 2 gói không có PSH vẫn 0/0/0.
- Giữ nguyên số dòng và định danh/thứ tự flow. Đối chiếu 78 cột giữa bản gốc và sửa: chỉ Fwd PSH Flags và Bwd PSH Flags khác; 76 cột còn lại khớp trong sai số số học kiểm thử. Checksum source upstream gốc không thay đổi.

| Model / xác suất SSH từng flow chính | Trước sửa | Sau sửa |
| --- | --- | --- |
| M0, cổng 44578 | 0,197880% | 0,197818% |
| M0, cổng 33750 | 0,162781% | 0,162738% |
| M0, cổng 40548 | 0,162782% | 0,162738% |
| M1, cổng 44578 | 0,038578% | 1,031234% |
| M1, cổng 33750 | 0,022605% | 0,733990% |
| M1, cổng 40548 | 0,019387% | 0,630154% |

Ba flow chính vẫn Benign ở cả hai model. Flow phụ giữ nguyên: M0 SSH-Bruteforce 49,72%, M1 Infilteration 99,68%. Sửa PSH cải thiện phép đếm, chưa giải quyết bỏ sót. Kết quả này bác bỏ giả thiết chỉ sửa PSH là đủ để nhận đúng kịch bản. M0 train có quy ước cờ khác nên không mặc định đưa patch đếm thật vào M0 runtime. Model pickle vẫn phát cảnh báo chênh phiên bản thư viện lúc nạp; hai nhánh dùng cùng môi trường và cùng artifact, chưa chứng nhận tương thích toàn bộ môi trường train.

Tái lập (không capture mới):

```powershell
python Java_CICFlowMeter_M0_Trial/test_psh_fix.py
```

Bước tiếp chưa thực hiện: xác minh provenance M1 rebuilt và tương thích các đặc trưng còn lại, đặc biệt window và lifecycle; đánh giá nhiều lượt SSH hợp lệ/không hợp lệ trước khi chọn profile extractor cho runtime. Không đổi model hoặc train lại trong thử nghiệm PSH.

## Tích hợp profile Java theo model — 18/11/2026

Mục đích: dùng cùng quy ước trích xuất cho PCAP và realtime của từng model, không sửa số cờ để ép nhãn. Mục này thay thế mô tả cũ “một lượt cho cả hai model”; các mục audit trước đó là lịch sử thử nghiệm.

- M1 dùng mã nguồn Java cải tiến của GintsEngelen, ghim commit `13a061520b862d605eea746c79ca4033b30d98fc` (2022). `runtime_profile.py` tạo bản build riêng, kiểm checksum mã Java; chỉ bổ sung wrapper capture và cấu hình build Windows. Không thay mã nguồn tính đặc trưng đã kiểm chứng.
- M0 giữ upstream hiện có, profile `m0-current-unverified`. Chưa có bằng chứng đủ để xác nhận trùng extractor tạo dataset M0 gốc. Không ép cờ count thành 0/1 và không tự áp profile M1 cho M0.
- Chọn M0/M1 trước khi bắt hoặc nạp PCAP. Chỉ model được chọn dự đoán; chuyển model không tự suy luận trên đặc trưng của lượt khác. Một instance API chặn chạy capture/import trùng. UI hiển thị profile và model của lượt.
- CSV dùng nguyên 78 đặc trưng có sẵn, không được gọi là “trích lại bằng Java”. Nguồn CSV hiện ghi `csv-unknown`; người dùng phải chọn đúng dữ liệu theo model. Java đã dùng microsecond nên không bật đổi giây lần nữa. NaN/Infinity giữ trạng thái không hợp lệ, không tự điền số; xem chi tiết vẫn được, yêu cầu XAI trả 422 thay vì lỗi 500.
- PCAP mỗi lượt có thư mục output riêng, tránh đọc nhầm CSV cũ. Mỗi model giữ riêng nền LIME và SHAP; LIME suy biến được báo đúng trạng thái.

### Chạy để tự kiểm tra

Dừng API/dashboard Java cũ bằng Ctrl+C tại terminal đã mở, sau đó:

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN
python Java_CICFlowMeter_M0_Trial/launch_dashboard.py
```

1. Chọn M0 hoặc M1 ở thanh bên.
2. CSV: tab Nạp CSV / PCAP, chọn CSV đủ 78 cột, chỉ bật chuyển giây nếu file thật sự dùng giây.
3. PCAP: chọn file PCAP/PCAPNG, bấm Java trích flow và dự đoán. M1 tự chọn profile cải tiến.
4. Realtime: chọn Realtek WiFi 6 cho mạng Wi-Fi của Windows, hoặc VMware VMnet1 cho lab nếu card này thấy traffic hai VM. Không chọn Microsoft Wi-Fi Direct Virtual Adapter. Giữ thời gian 0 để chạy đến khi bấm Dừng.
5. Bấm Dừng và ghi nốt flow; chờ finished. Chọn một dòng trong bảng để xem chi tiết; SHAP chạy tự động với cảnh báo, LIME theo yêu cầu.
6. Muốn thử model còn lại, đổi model và nạp/bắt một lượt riêng. Giữ PCAP để so hai model trên cùng gói tin nếu cần.

Profile M1 lần đầu cần git clone nguồn nếu cache chưa tồn tại, JDK8/Gradle và Npcap như hướng dẫn cài đặt hiện có. Không sửa model hoặc reset DB của hệ thống chính.

### Bằng chứng và giới hạn

- `java_78_feature_contract_20261118.csv`, `java_contract_verification_20261118.json`: kiểm đủ 78 đầu ra trên fixture tính trước; bản hiện tại lệch 12 cột so với quy ước published-2022 trên fixture, bản ghim không lệch. Không suy rộng một fixture thành chứng nhận mọi gói tin.
- `java_profile_positive_tests_20261118.json`: 26 kiểm tra bổ sung có giá trị khác 0 cho bulk, cờ, active/idle và UDP.
- `java_contract_audit_20261118.json`: đối chiếu train/test, 6 PCAP và CSV lab. Bản M1 giữ đủ 160 gói SSH trong ss2; ba flow SSH chính vẫn Benign. Đây vẫn là bỏ sót kịch bản, không phải sửa xong độ chính xác model.
- M0 raw ngày 14/02 có cờ 0/1; chưa xác minh được pipeline/binary gốc tạo quy ước đó. M1 hiện tại đã rebuild, chưa có provenance đầy đủ để chứng minh test độc lập; không dùng accuracy trên tập có sẵn như bằng chứng tổng quát hóa lab.
- Các quy ước legacy về subflow/window được giữ khi phù hợp dữ liệu improved; không tự lấy bản upstream mới nhất vì có thể đổi nghĩa đặc trưng.
- Chưa có cặp PCAP/CSV gốc của dataset để chứng nhận tương đương tuyệt đối. Còn cảnh báo phiên bản thư viện khi load pickle. Không coi nhãn trên traffic không có ground truth là FPR, không coi capture ngắn là PASS dài hạn.

Tái lập kiểm thử:

```powershell
python Java_CICFlowMeter_M0_Trial/test_runtime_profiles.py
python Java_CICFlowMeter_M0_Trial/smoke_ui.py
python Java_CICFlowMeter_M0_Trial/test_invalid_flow.py
# Tùy chọn, có bắt Wi-Fi thật:
$env:JAVA_TEST_MODEL='M1'
python Java_CICFlowMeter_M0_Trial/test_realtime_ui.py
```

### Kết quả tích hợp đã chạy lại

PCAP ss2 + CSV roundtrip, SHAP/LIME cả hai model: PASS (`java_runtime_integration_20261118.json`). AppTest chọn dòng, chi tiết, SHAP/LIME và hồi quy NaN/Inf: PASS. Hai lượt Wi-Fi riêng chạy nút Bắt đầu/Dừng qua AppTest, không phải kiểm tra trình duyệt bằng mắt:

- M0: 31.06 giây trước yêu cầu Dừng; accepted_packets=1138 closed_flows=21 flushed_flows=40; nhãn {'Benign': 47, 'DoS attacks-Hulk': 14}; 0 dòng không hợp lệ; LIME ca được chọn: insufficient_neighborhood. Process exit=0, cleanup đã xác nhận. Bằng chứng: `java_realtime_m0_20261118.json`.
- M1: 30.7 giây trước yêu cầu Dừng; accepted_packets=1354 closed_flows=0 flushed_flows=54; nhãn {'Benign': 41, 'DDOS attack-LOIC-UDP': 1}; 12 dòng không hợp lệ; LIME ca được chọn: ok. Process exit=0, cleanup đã xác nhận. Bằng chứng: `java_realtime_m1_20261118.json`.

M1 có 12 dòng một gói, thời lượng 0: Flow Bytes/s, Flow Pkts/s và bốn thống kê Flow IAT không hữu hạn. Lưu nguyên CSV để kiểm tra; không điền 0. M0 lượt riêng không có dòng lỗi. Đây là hai lượt khác nhau, không dùng số lượng nhãn để kết luận M1 tốt hơn M0. Không tạo tấn công trong thử nghiệm này; M0 vẫn gán Hulk và M1 có LOIC-UDP, cần đối soát ground truth. Chưa có soak test dài hạn cho profile mới.

Xem `java_live_invalid_audit_20261118.json` để biết đường dẫn CSV thô, `features_78.csv` theo thứ tự model và `rejected.csv` có source_row/invalid_columns. Số dòng source_row bắt đầu từ 1, không tính header. Capture này không lưu PCAP: CSV không khôi phục được gói tin. Muốn kiểm đếm từ từng gói, cần lưu PCAP bằng Wireshark trên cùng interface rồi nạp lại; không coi CSV là bằng chứng packet thô.

### GoldenEye lab và sửa nhãn UI — 18/11/2026

Lượt dashboard_2049dd9c9059: 14.255 dòng CSV, 12.803 dòng hữu hạn. UI cũ coi prediction=None là không hợp lệ kể cả khi lượt thuộc model khác. Đã chặn hiển thị thống kê trong trường hợp này và giải thích chưa chạy model đang chọn; kiểm thử nhánh này PASS.

Chạy lại cùng CSV, lọc Kali 192.168.11.133 → Ubuntu 192.168.11.134:80 có 12.540 dòng hữu hạn. M0: 9.022 GoldenEye, 1.635 Benign, 1.623 Hulk, 148 HOIC, 111 Slowloris, 1 Infilteration. M1: 9 GoldenEye, 9.592 Benign, 1.519 Hulk, 1.288 Infilteration, 85 Slowloris, 47 LOIC-HTTP. Bằng chứng `goldeneye_live_audit_20261118.json`. Đây là inference trên cùng CSV, không phải đối chiếu profile Java riêng; chưa có nhãn theo thời gian/log cho toàn bộ lượt nên không gọi tỷ lệ trên là recall. Chưa xác định nguyên nhân cụ thể của M1; cần PCAP và phân tích đặc trưng/SHAP, không tăng tải để ép nhãn.

## Runbook GoldenEye: Kali → Ubuntu Apache, M0 realtime (30 giây)

Mục đích: kiểm thử IDS trong lab do người dùng quản lý; lưu gói và log để đối chiếu. Kali dự kiến 192.168.11.133, Ubuntu 192.168.11.134 trên VMnet1. Xác minh IP thực tế trước khi chạy. Hai VM cùng mạng host-only VMnet1; có thể dùng card NAT riêng để cài gói. Windows phải nhìn thấy traffic giữa hai VM trên VMnet1, không suy ra từ ping thành công.

### Ubuntu: chuẩn bị web server

```bash
ip -br addr
sudo apt update
sudo apt install -y apache2
# Chỉ dừng nginx nếu đang dùng nó trên máy nạn nhân lab này.
# Lệnh này tạm ngừng website đang phục vụ qua nginx.
sudo systemctl stop nginx
sudo apache2ctl configtest
sudo systemctl start apache2
systemctl is-active apache2
curl -I http://192.168.11.134/
```

Nếu nginx không được cài, bỏ qua thông báo không tìm thấy dịch vụ. Cần Syntax OK, active và HTTP 200 từ Apache. AH00558 về ServerName không chặn thử nghiệm. Nếu Apache failed, kiểm tra trước khi chạy tải:

```bash
sudo ss -ltnp 'sport = :80'
sudo journalctl -u apache2 -n 30 --no-pager
```

Mở terminal Ubuntu khác để xem request:

```bash
sudo tail -f /var/log/apache2/access.log
```

### Kali: chuẩn bị công cụ

```bash
ip -br addr
ping -c 3 192.168.11.134
curl -I --max-time 5 http://192.168.11.134/
sudo apt update
sudo apt install -y git python3 curl
mkdir -p ~/ids-demo
cd ~/ids-demo
# Chỉ clone khi chưa có thư mục GoldenEye.
git clone https://github.com/jseidl/GoldenEye.git
cd GoldenEye
git rev-parse HEAD
python3 goldeneye.py -h
```

Nếu đã cài: chỉ chạy `cd ~/ids-demo/GoldenEye`, không clone lại. Nguồn và tham số: https://github.com/jseidl/GoldenEye . Lưu commit công cụ cùng log; không giả định bản hiện tại giống binary của dataset.

### Windows: bắt trước khi tạo tải

1. Wireshark chọn VMware Network Adapter VMnet1 và Start. Display filter: `ip.addr == 192.168.11.133 && ip.addr == 192.168.11.134 && tcp.port == 80`.
2. Chạy curl trên Kali và xác nhận Windows thấy gói hai chiều. Nếu không thấy thì kiểm tra đường capture, chưa chạy tải.
3. Dashboard Java: dừng lượt cũ, chờ finished; chọn M0 → Realtime → VMnet1, thời gian 0 → Bắt đầu Java. Chờ capturing. Chuyển radio M0/M1 không đổi model của capture đang chạy.

### Kali: lượt GoldenEye 30 giây

```bash
cd ~/ids-demo/GoldenEye
set -o pipefail
{
  date -Is
  timeout --signal=INT --kill-after=5s 30s \
    python3 -u goldeneye.py http://192.168.11.134/ \
    -w 1 -s 2 -m get
  echo "exit_code=$?"
  date -Is
} 2>&1 | tee ~/ids-demo/goldeneye-m0-30s.log
```

Chỉ nhắm Ubuntu lab. Một worker, hai socket; timeout yêu cầu dừng sau 30 giây, kill-after thêm tối đa 5 giây nếu chưa thoát. Ctrl+C để dừng sớm. Exit 124 thường biểu thị timeout đã hết. Mỗi lượt đổi tên log để không ghi đè. Không tăng tải chỉ để ép nhãn GoldenEye.

### Kết thúc và lưu

1. Dashboard Dừng và ghi nốt flow → chờ finished.
2. Wireshark Stop → Save As `goldeneye-m0-30s.pcapng` trong Downloads. CSV dashboard không thay thế PCAP.
3. Ubuntu lưu snapshot log (có thể gồm request trước lượt, phải lọc theo giờ/IP):

```bash
sudo tail -n 5000 /var/log/apache2/access.log > ~/goldeneye-m0-30s-apache.log
curl -I --max-time 5 http://192.168.11.134/
```

4. Giữ giờ bắt đầu/kết thúc có múi giờ từ Kali, log Apache, PCAP và mã lượt dashboard. Hai máy có thể hiển thị múi giờ khác nhau; quy về cùng UTC khi gán nhãn.
5. Nạp cùng PCAP riêng cho M0 và M1 để mỗi nhánh trích đúng profile; so số flow hữu hạn, không hợp lệ, nhãn và SHAP/LIME. Không gọi tỷ lệ nhãn là accuracy khi chưa gán ground truth.

### Việc tiếp theo

Chốt lượt GoldenEye 30 giây trước: kiểm tra PCAP, đối chiếu log và các flow đúng/sai. Ghi thêm baseline HTTP bình thường riêng. Sau đó mới thử Hulk trong lab với một runbook riêng; tiếp theo Slowloris, HOIC để sau khi có thiết kế nguồn traffic phân tán. Không tuyên bố M0/M1 ổn từ một lượt.
