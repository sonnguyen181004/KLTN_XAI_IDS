# Vận hành, phục hồi và kiểm thử RQ3

## HT3.1 — xác nhận giao nhận (18/10/2026)

Mục đích: không tiến checkpoint khi phản hồi HTTP 200 thiếu/sai cấu trúc, tránh báo gửi thành công rồi lỗi khi đọc trường còn thiếu. Feeder kiểm tra đầy đủ các trường xác nhận, giữ khóa idempotency khi retry, từ chối poll không hữu hạn/không dương; lỗi I/O được báo dừng rõ. Stage27 5/5 PASS (ACK lỗi, HTTP 408/425/429/5xx, lỗi lưu checkpoint sau ACK, sai khóa xác nhận, poll sai). Stage24 kiểm chứng thực bằng server/DB tạm cho mất ACK, restart, giao dịch rollback và phục hồi SHAP. Không thay đổi API/model hoặc bỏ qua dòng lỗi. Commit: `fix(rq3): validate feeder acknowledgements before checkpoint`.

Tài liệu hợp nhất ngày 16/10/2026. Chỉ còn 5 tài liệu RQ3 chính: [kiến trúc và kế hoạch](plan.md), [chạy và đọc UI](dashboard_usage.md), [vận hành](operations.md), [kiểm chứng XAI](xai_validation.md), [tương thích đặc trưng](feature_compatibility.md).

> Trạng thái hiện hành (HT2, 18/10/2026): capture project lifecycle v3; v2 còn chọn được bằng `--extractor project-v2`; feeder checkpoint/chống gửi trùng; SHAP queue 200 và phục hồi sau restart. Giữ XGBoost/78 đặc trưng, cấu hình LIME RQ2 và nhánh A/B. Nhật ký bên dưới giữ số liệu của phiên bản được ghi tại thời điểm kiểm thử. Chưa chứng nhận tương thích đầy đủ train–PCAP hoặc độ ổn định live dài hạn; nhãn live chưa phải ground truth.

- [Capture v2, phục hồi và kiểm thử](#stability-v2)
- [Hợp đồng dữ liệu và trạng thái HT1](#contract-ht1)

## Cập nhật kiểm chứng HT2.1 — 18/10/2026

**Hiện hành HT2.4:** lệnh cũ không cần đổi: `project` mặc định trỏ lifecycle v3 cho cả CLI live và UI PCAP. Dùng CSV tên mới; không ghi đè CSV đang có feeder theo dõi. Bản v2 chọn bằng `--extractor project-v2`; v1 và train-candidate vẫn tách biệt. CSV thêm `flow_end_reason` (metadata, không phải cột model), dòng kết thúc CLI có `late_packets`; lý do chưa được truyền qua API/UI. Phiên đang chạy không tự nâng cấp: dừng capture/flush, đợi feeder gửi hết rồi dừng feeder, khởi động lượt mới. Không reset DB.

V3 dùng tuổi tối đa 90s từ packet đầu (kể cả flow im lặng), kiểm tra cùng biên `>=` trước admission và trong GC. Idle 240s là dự phòng, bị tuổi 90s chi phối ở mặc định. Xuất sớm khi quan sát RST, FIN/ACK đủ hai chiều, SYN mở phiên mới; packet trễ được giữ trong flow một packet có lý do. Clock PCAP dùng timestamp gói; live có GC clock máy. Clock máy lệch/nhảy và mất gói capture chưa được chứng nhận ở HT2, thuộc nghiệm thu vận hành sau này. Không bảo đảm độ trễ end-to-end chỉ từ timeout.

Lệnh kiểm tra HT2 từ thư mục `RQ3_IDS_System`:

```powershell
.\.venv_capture\Scripts\python.exe scripts\stage20_test_capture_adapter.py
.\.venv_capture\Scripts\python.exe scripts\stage26_test_capture_lifecycle.py
python scripts\stage23_audit_feature_semantics.py --self-test
python scripts\stage21_compare_capture_versions.py --baseline project-v2 --candidate project-v3 --output docs\lifecycle_review_NEW.json
python -B scripts\stage14_test_dashboard_redesign.py
```

Stage21 dùng PCAP/model thật nhưng CSV tạm, không gửi API; từ HT2 từ chối ghi đè JSON bằng chứng. Stage14 mở server/DB tạm và đóng khi xong. Không dùng tên bằng chứng đã có. `stage25_audit_flag_sensitivity.py` được ghim explicit `project-v2` để tái lập thí nghiệm cờ lịch sử. Kết quả và commit HT2.4 ghi tại `plan.md`, không suy ra FPR từ số nhãn cảnh báo.

Đoạn HT2.1 dưới đây là trạng thái trước khi thay default:

Không đổi cách chạy hệ thống. Stage20 hiện có **21 test PASS**, gồm sáu characterization mới ghi lại giới hạn vòng đời v2; đây không phải bản sửa capture mới. Stage25 kiểm tra model thật trên hai PCAP: nhị phân hóa cờ trong bộ nhớ không đổi nhãn/xác suất/lá của 92 flow; không áp dụng phép biến đổi này vào runtime. Stage23 self-test 3/3 PASS; chưa chạy full scan mới hoặc benchmark live. Xem [bằng chứng, lệnh tái lập và việc tiếp theo](feature_compatibility.md#ht21). Các số 13/15 test và phiên live ngày 16/10 bên dưới vẫn là lịch sử.

<a id="contract-ht1"></a>

## HT1 — Hợp đồng dữ liệu và trạng thái (18/10/2026)

**Mục đích:** thống nhất ranh giới giữa capture, feeder, API, XAI và UI trước khi hoàn thiện realtime. Đây là đặc tả đối chiếu code hiện hành, không phải thông báo đã triển khai bộ quản lý capture. Tiến độ/commit từng bước nằm trong [kế hoạch](plan.md).

### 1. Bất biến và trách nhiệm

- CSV có đặc trưng và PCAP/live sau trích xuất đều gửi HTTP `/predict`. UI không gọi model hoặc ghi trực tiếp SQLite.
- Model RQ1 và cấu hình LIME RQ2 giữ nguyên làm baseline. Nhãn khác `Benign` tạo alert; A/B chỉ đổi trình bày, không đổi nhãn hoặc che cảnh báo.
- API lưu Flow/Prediction/Alert/Timing cùng giao dịch trước khi dispatch SHAP. SHAP nền; LIME theo yêu cầu. Giữ sáu bảng hiện hành ở HT1; nếu bước sau cần thay schema cho phản hồi analyst phải ghi thiết kế/migration riêng, không nhét dữ liệu giả vào bảng cũ để giữ số bảng.
- Cùng vector chuẩn hóa và cùng model phải cho cùng dự đoán, bất kể nguồn. Điều này không có nghĩa cùng traffic qua hai extractor sẽ cho cùng vector; phần đó cần HT2 kiểm chứng.

### 2. Hợp đồng đầu vào và metadata

| Nhóm | Hiện hành / quy tắc | Phần cần hoàn thiện |
|---|---|---|
| Vector model | Lấy đúng danh sách/thứ tự từ `Detector.feature_names`; kỳ vọng 78 số hữu hạn. `normalize_flow` từ chối thiếu cột, NaN/Inf; cột thừa không đưa vào vector lưu/model | Kiểm tra schema tại mọi cửa vào; log lỗi kiểu dữ liệu bị từ chối trước handler cũng cần được đánh giá |
| Đơn vị | API nhận vector đã chuẩn hóa; feeder/UI đổi riêng `TIME_COLUMNS` giây → micro giây khi được chọn. Rate không nhân theo thời gian; không đổi hai lần | Có khai báo nguồn/quy tắc chuyển đổi rõ hơn; không đoán đơn vị chỉ từ độ lớn |
| Nguồn và lượt | `source`, `capture_run_id`, `run_name` là metadata. UI upload tạo lượt cho mỗi lần gửi; feeder giữ run ID trong checkpoint | Không dùng model prediction để suy ra nguồn hoặc kịch bản |
| Mạng | `src_ip`, `dst_ip`, `src_port` riêng với vector; `Dst Port`, `Protocol` vẫn là đặc trưng model và được UI đọc từ vector | Thiếu IP hiển thị không được cung cấp; không bịa IP từ dataset không chứa IP |
| Phiên bản | `extractor_version` lưu riêng; `model_version` nằm trong Prediction | Chưa có manifest đầy đủ cho preprocessing/background/XAI; bổ sung có version ở bước tương ứng |
| Nhãn thật | DB có `label_true`, nhưng đường `/predict`/UI upload hiện chưa lưu nhãn thật từ CSV | HT5 phải thêm nguồn nhãn/xác minh; không đưa nhãn vào model, không tự gán Benign cho toàn bộ traffic cá nhân |
| Giá trị thô | DB hiện giữ vector chuẩn hóa, không phải toàn bộ vector trước chuyển đổi | Bản adapter ứng viên cần lưu đối chiếu thô/chuyển đổi có kiểm soát; chưa tuyên bố DB hiện có dữ liệu này |

Nguồn đối chiếu: `app/normalize.py`, `app/predict.py`, `app/flow_metadata.py`, `app/feeder.py`, `app/ingestion_ui.py`, `app/main.py`, `app/db.py`. API không bắt buộc IP với CSV không có metadata. Không thêm IP thành đặc trưng thứ 79.

### 3. Hợp đồng thời gian

| Mốc | Hiện hành | Cách đọc / giới hạn |
|---|---|---|
| `flow_timestamp` | Chuỗi thời điểm nguồn cung cấp; capture dùng mốc flow | Không phải thời điểm API nhận; CSV ngoài cần xác minh ý nghĩa timestamp |
| `flow_timestamp_utc` | Chuẩn hóa khi timestamp có múi giờ hoặc có `capture_timezone` | Timestamp không rõ múi giờ giữ UTC là null; không đoán rồi tính latency |
| `received_at` | UTC khi handler API bắt đầu xử lý flow | Chưa phải thời điểm byte đầu HTTP tới máy |
| `predicted_at` | UTC sau inference, trước giao dịch lưu core | Tách với thời gian packet, không sửa thành timestamp PCAP |
| `Timing` | Duration dùng đồng hồ đo khoảng thời gian; `recorded_at` là UTC | `total` hiện dừng trước commit cuối/dispatch, không phải HTTP end-to-end; SHAP/LIME riêng, không cộng các bước lồng nhau |
| Xuất flow / ACK / hoàn tất phiên | Chưa có đầy đủ mốc bền và telemetry thống nhất | HT3/HT4 cần bổ sung để phân biệt capture delay, backlog và thời gian xử lý |

UI đổi thời gian có timezone sang GMT+7 để đọc; lưu UTC và giữ nguồn gốc. Replay PCAP cũ không được lấy ngày nhận trừ ngày packet rồi gọi đó là độ trễ xử lý live. E1 cần đo riêng từ flow sẵn sàng đến ACK, đến XAI hoàn tất và HTTP thực tế. Chú thích UI hiện gọi `total` là thời gian request còn chưa chính xác hoàn toàn; HT6 cần đồng bộ.

### 4. Trạng thái XAI đang có

| Trạng thái | Ý nghĩa / hành vi hiện hành |
|---|---|
| `pending_dispatch` | Alert đã lưu, chưa đưa vào hàng đợi RAM |
| `queued` | Đã nhận tác vụ; hiện không tách riêng trạng thái tác vụ đang chạy |
| `processed` | SHAP đã lưu; không đồng nghĩa nhãn dự đoán đã được xác minh |
| `dropped_queue_full` | Bỏ tác vụ SHAP mới vì queue đầy; prediction/alert vẫn giữ, chưa tự retry |
| `failed` | Dispatch/giải thích/phục hồi lỗi; không tự retry vô hạn |
| `recovery_pending` | Việc bị ngắt được phát hiện khi restart; lấy dần từ DB khi queue RAM rảnh |
| `not_required` | Trạng thái do lớp đọc/UI gán cho Benign, không phải alert được tạo |
| `unknown_legacy` | Lịch sử không đủ trạng thái; không suy đoán thành thành công |

Queue RAM: 200 chờ + một worker đang xử lý; backlog phục hồi trong DB có thể lớn hơn 200. Không giới hạn tổng flow bằng queue XAI. HT3 phải kiểm tra công bằng giữa việc mới và việc phục hồi, và chính sách retry thủ công có giới hạn.

LIME tách riêng: `not_requested`, `ok`, `insufficient_neighborhood`, `zero_coefficients`, `undefined_fit`, `legacy_unchecked`. `ok` chỉ vượt kiểm tra suy biến tối thiểu, không chứng nhận chất lượng cao. Kết quả suy biến không có Top-5/R²/Jaccard dùng để kết luận; chẩn đoán thô vẫn giữ. `/alerts` còn tên tương thích `shap_only`/`shap_and_lime`; không dùng những tên này để kết luận LIME hợp lệ thay cho `lime_status`.

### 5. Vòng đời realtime đề xuất — CHƯA triển khai

| Thành phần | Trạng thái mục tiêu | Điều kiện quan sát |
|---|---|---|
| Capture | `starting → capturing → stopping → stopped`, hoặc `failed`; `unknown` khi mất khả năng xác minh | Bộ quản lý sở hữu tiến trình + heartbeat; log `receiving_started` hiện có chưa đủ để biết tình trạng hiện tại |
| Feeder | `waiting_input`, `sending`, `caught_up`, `retrying`, `draining`, `stopped`, `failed`, `unknown` | Offset/ACK và lỗi thực; `caught_up` chỉ là đã bắt kịp CSV hiện tại, không phải capture kết thúc |
| Phiên | `starting → running → stopping → draining → completed`; hoặc `failed`/`interrupted` | Chỉ `completed` khi capture dừng an toàn, ghi nốt thành công và feeder xác nhận hết record hợp lệ |

Tên trên là đặc tả cho HT4, chưa phải API hiện có. `completed` của phiên ingestion không có nghĩa SHAP đã chạy hết hoặc không bị dropped; hiển thị backlog XAI riêng. Buộc dừng/mất tiến trình không được ghi là hoàn tất; phải báo nguy cơ mất packet/flow chưa ra CSV. UI reload không khởi chạy phiên mới. API khỏe không chứng minh capture khỏe; không có flow mới không chứng minh mất kết nối.

Thứ tự dừng bình thường: ngừng nhận packet → đợi capture thread kết thúc → ghi nốt và đóng CSV → feeder gửi hết/nhận ACK → đóng phiên. Giữ API hoạt động trong giai đoạn drain. Cần ownership đầu ra, chống chạy trùng, quy tắc nhận diện phiên sau restart và giới hạn tài nguyên trước khi nối nút UI. Chưa bật capture hoặc thay chính sách timeout trong HT1.

### 6. Tiêu chí nghiệm thu theo bước

- **HT1 (đặc tả):** đã xác định nguồn sự thật cho vector/metadata/time; trạng thái hiện hành tách khỏi mục tiêu; có danh sách khoảng trống và bước phụ trách; đối chiếu với code, không chỉ với ảnh UI.
- **Các bước triển khai sau:** test cùng vector qua các nguồn; lỗi input; mất ACK/restart; không gửi trùng; dừng/flush/drain; queue đầy; UI reload/giữ lựa chọn. Mỗi bước ghi rõ test mới chạy và kết quả lịch sử được kế thừa.
- **Nghiệm thu realtime cuối:** đo thời gian chạy, RAM/CPU, số packet được adapter nhận, flow xuất/ACK, backlog/lỗi và latency p50/p95; ghi riêng giới hạn không đo được packet mất trước callback. Ngưỡng chấp nhận phải chốt trước lượt benchmark, không chọn sau khi thấy số.
- **Độ đúng phát hiện:** chỉ tính FPR/FNR trên nhãn xác minh có nguồn; thiếu nhãn không đổi thành số 0. Adapter ít dự đoán Hulk hơn không tự chứng minh tương thích train hoặc hoàn thành E4.

**Kiểm tra HT1:** thay đổi chỉ hai tài liệu hiện có; kiểm tra diff/whitespace, link `plan.md` và anchor `contract-ht1`, đối chiếu trường và trạng thái với mã. Không chạy lại capture, không khởi động API và không ghi DB ở bước đặc tả này. Các test PASS của lượt review trước là bằng chứng lịch sử, không tính là test mới HT1.

## Commit đã đối chiếu — 16/10/2026

Đối chiếu `git log`, danh sách file thay đổi và code hiện tại; đây không phải một lần chạy lại toàn bộ benchmark. Không đổi code runtime/model trong đợt cập nhật hướng dẫn này.

| Commit | Nội dung đã lưu | Giới hạn cần giữ rõ |
|---|---|---|
| `8d1a8a7` | SHAP queue 50 → 200 | Không phải giới hạn số flow; chưa kết luận 200 tối ưu |
| `f831347`, `c64e7bb` | Audit feature và quan hệ từng dòng train/test | Chưa chứng nhận tương thích đầy đủ train–PCAP |
| `28f68cf` | Adapter v1 và kiểm thử capture/live | Baseline lịch sử, mặc định hiện tại là v2 |
| `795b7de` | Capture v2, CSV Windows, checkpoint/idempotency, lưu giao dịch và phục hồi SHAP | Candidate chỉ opt-in; LIME không tự hết suy biến |
| `d411a49` | Gộp 11 Markdown thành 5, ba tab UI và hướng dẫn live | Chưa có nút điều khiển capture |
| `b24f93c` | Chờ capture đáp ứng tín hiệu dừng, flush và test | Stage20 PASS 15; phím Ctrl+C trên mọi VS Code/Npcap chưa được chứng nhận |

**Quyết định lịch sử ngày 16/10:** tự chạy API/UI/capture/feeder bằng terminal VS Code, live liên tục không cần `--seconds`; hoãn nút Bắt đầu/Dừng. Lộ trình ngày 18/10 đã đưa quản lý capture và UI vào các bước sau, chưa triển khai. Hướng dẫn terminal vẫn hiệu lực: xem [hướng dẫn hiện hành](dashboard_usage.md#run-ui), không dùng PID hoặc số flow trong nhật ký dưới đây làm trạng thái hiện tại.

## Nhật ký áp dụng trên máy người dùng — 16/10/2026

### Sửa capture không phản hồi Ctrl+C

Phiên live chờ `sniffer.join()` vô hạn trong main thread; đây là điểm có thể trì hoãn xử lý Ctrl+C trong môi trường Windows/Python đang dùng. Đã thay bằng vòng chờ ngắn 0,1 giây, handler SIGINT/SIGBREAK chỉ yêu cầu dừng, `stop(join=False)` rồi đợi thread kết thúc trước khi flush CSV. Handler giữ trong lúc cleanup để Ctrl+C lặp không ngắt giữa chừng. Chờ shutdown tối đa 15 giây; nếu thread vẫn chạy thì báo lỗi, không giả định đã dừng an toàn hoặc flush đồng thời với thread.

Giữ nguyên công thức feature, extractor version v2, timeout flow 90s/240s và model/XAI. Stage20 hiện PASS 15 test, gồm tín hiệu phát bằng `signal.raise_signal`, hẹn giờ, lỗi sniffer, khôi phục handler và CLI PCAP thật; chưa phải kiểm thử end-to-end phím Ctrl+C trong mọi phiên terminal VS Code/Npcap. Bản sửa chỉ có hiệu lực khi khởi chạy capture mới.

Lệnh chạy live thường dùng, không đặt giới hạn thời gian:

```powershell
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --interface "Wi-Fi" --output data\live_manual_02.csv
```

Chạy feeder theo đúng CSV đó. Nếu tên đã dùng, đổi tên ở cả capture và feeder. Đợi capture báo `receiving_stopped` và ghi nốt flow; đợi feeder gửi hết trước khi dừng feeder. Không đóng cưỡng bức terminal trừ khi chấp nhận mất flow chưa xuất. `--seconds N` chỉ là tùy chọn kiểm thử có thời hạn, không bắt buộc và không dùng trong quy trình live mặc định.

### Phiên mở UI trước lần reset DB — thông tin lịch sử

Các số đếm và PID dưới đây là ảnh chụp của lần mở UI trước; DB sau đó đã được reset theo yêu cầu, người dùng tự nạp/test lại. Không suy ra số flow hiện tại hoặc dừng tiến trình theo PID cũ.

- Bật API tại `127.0.0.1:8000` và Streamlit tại `127.0.0.1:8501`; health xác nhận model `52eb5a671ee82109`, 78 đặc trưng, 15 lớp, idempotency và queue 200. Không chạy thêm API cùng DB.
- Không reset DB, không gửi thêm flow và không tự bật capture. DB hiện có 176 flow/88 cảnh báo; worker tự tiếp tục các SHAP bị ngắt theo cơ chế phục hồi v2. Việc cập nhật giải thích không phải tạo thêm traffic.
- Có bản sao SQLite nhất quán `data/ids_system_backup_ui_20261016_112528.db`, không đưa vào Git. Bản sao được tạo sau lúc API khởi động (lần sao lưu trước bị quyền sandbox chặn), vì vậy có thể đã chứa một phần trạng thái SHAP được phục hồi.
- UI được mở và kiểm tra trên trình duyệt: thấy ba tab, dữ liệu lịch sử/biểu đồ và hướng dẫn live. Kiểm thử tự động Stage14 dùng DB tạm, không nạp fixture vào DB này. Đây chưa phải nghiệm thu mọi kích thước màn hình hoặc điều khiển capture trực tiếp.
- Stage14 sau thay UI PASS, gồm assertion ba tab/lệnh capture, regression CSV/PCAP, chọn flow và LIME. Kiểm tra liên kết tới file cục bộ của năm tài liệu PASS. Sau startup, 50 tác vụ SHAP được phục hồi hoàn tất, backlog về 0; không tự thử lại các việc đã dropped.
- Hai dịch vụ từng được bật nền để xem lại rồi chuyển về hướng dẫn tự chạy terminal theo yêu cầu. PID chỉ thuộc phiên lịch sử: API `17032`, UI `45184`; không dùng chúng làm lệnh dừng hiện tại vì PID có thể tái sử dụng.

---

<a id="stability-v2"></a>

# Cập nhật độ ổn định RQ3 — capture v2 và giao nhận có phục hồi

Ngày 16/10/2026. Tiếp nối [audit ngữ nghĩa](feature_compatibility.md#semantics). Model XGBoost/78 đặc trưng, cấu hình LIME khóa RQ2 và luật nhánh A/B được giữ nguyên.

## Thay đổi theo kiến trúc

| Thành phần | Thay đổi | Ranh giới được giữ |
|---|---|---|
| Bắt gói/gom flow | `project` mặc định là `rq3-cfm-0.5.0-fixes-v2`, bảo toàn TCP window đầu bằng 0 | Vẫn xuất flow CSV, metadata version riêng; timeout 90s/240s như v1 |
| Feeder | Đọc tiếp từ byte offset; checkpoint sau ACK, thử lại lỗi tạm, khóa một feeder/checkpoint | Vẫn gửi `/predict` qua HTTP; không gọi model hoặc DB trực tiếp |
| API + lưu trữ | Header tùy chọn `Idempotency-Key`, ghi Flow/Prediction/Alert/Timing/biên nhận cùng giao dịch | Vẫn sáu bảng; thêm ba cột/index vào FlowRecord, không thêm tầng dự đoán |
| SHAP | Khôi phục việc bị ngắt từ Alert/Flow đã lưu khi API khởi động lại | Worker nền riêng, hàng đợi RAM 200; nhãn/cảnh báo có trước giải thích |
| LIME và A/B | Giữ cấu hình/điều kiện hiện hành | LIME theo yêu cầu, trạng thái suy biến được giữ rõ; A/B không sửa nhãn |
| Dashboard | Hiển thị chờ khôi phục SHAP và số việc còn trong DB | Tiếp tục đọc qua API, không đọc SQLite trực tiếp |

## Capture và bản thử nghiệm

Về giá trị đặc trưng, `project` v2 bổ sung sửa lỗi initial window: gói đầu window=0, gói sau=4096 thì kết quả vẫn là 0. Cả hai chiều đều được kiểm thử. `project-v1` giữ class cũ để tái lập audit. `legacy` giữ Python CICFlowMeter trước các sửa lỗi v1.

Về xuất file, v2/candidate dùng CSV writer UTF-8 với `newline=''`, flush sau mỗi flow. Kiểm thử live ban đầu phát hiện writer upstream trên Windows tạo `CRCRLF`, khiến bộ đọc nghiêm ngặt hiểu header thành hai record và feeder dừng dù capture có packet. Đã sửa writer và cho bộ đọc bỏ record trống do kiểu newline này, vẫn kiểm tra record thực/quote/dòng chưa ghi xong. Có regression cho cả CSV mới và CSV kiểu cũ; không sửa số liệu feature để vượt qua lỗi đọc.

`train-candidate` là **thử nghiệm một phần**, có metadata `rq3-train-conventions-experimental-v1`: đổi std độ dài từng chiều sang sample SD, Down/Up sang phần nguyên và window chưa quan sát sang -1. Length vẫn là toàn frame; chưa đổi payload/header, cờ, bulk, IAT std, quan hệ hai mean hoặc segmentation. Không gọi nó là bản tương thích đầy đủ với dataset V3, không chọn công thức theo số nhãn Hulk giảm.

CLI mặc định từ chối ghi đè CSV đã có dữ liệu. Chọn tên file mới cho mỗi phiên; `--overwrite` chỉ dùng khi chủ động muốn ghi đè và không có feeder đang theo dõi file đó.

Đối chiếu hai PCAP bằng script stage21, không đưa thêm vào DB demo:

| So sánh | tesst2.pcapng | test.pcapng | SHAP/LIME |
|---|---|---|---|
| project-v1 → project v2 | 59 flow, 0 vector đổi, 0 nhãn đổi | 33 flow, 0 vector đổi, 0 nhãn đổi | Các PCAP này không làm xuất hiện trường hợp window bị sửa; fixture độc lập đã xác minh lỗi |
| project v2 → train-candidate | 45/59 vector đổi, 0 nhãn đổi | 26/33 vector đổi, 0 nhãn đổi | Cả 8 cảnh báo vẫn LIME `insufficient_neighborhood`; có đo SHAP additivity từng flow trong JSON |

Cả hai so sánh đều ghép đủ 92 flow, không key mơ hồ; mỗi cặp dùng cùng seed chẩn đoán LIME. Kết quả nhãn vẫn 84 Benign/8 Hulk, chưa có ground truth xác minh để tính accuracy/FPR.

Bằng chứng: [v1/v2](capture_v2_comparison_20261016.json), [v2/candidate](capture_candidate_comparison_20261016.json). Không ghi đè JSON audit cũ. Stage23 chọn rõ class `ProjectFlowV1` để fixture lịch sử vẫn mô tả v1.

## Cơ chế feeder/API

- Mặc định lưu `<tên CSV>.feeder-state.json`: run ID, byte offset, số dòng đã xác nhận, cấu hình gửi, định danh file và hash 512 byte ngay trước offset. Không lưu vector/IP/payload trong checkpoint.
- File khóa hệ điều hành ngăn hai feeder cùng dùng checkpoint. Checkpoint được ghi file tạm, flush/fsync rồi replace; nếu chết trước khi lưu checkpoint, lần chạy sau gửi lại cùng khóa dòng.
- Khóa mỗi dòng là run ID + số thứ tự, không phải hash nội dung. Hai dòng giống hệt nhau vẫn là hai flow; thử lại một dòng giữ cùng flow ID.
- API lưu khóa/hash request/biên nhận cùng bản ghi prediction. Gửi lại cùng khóa và đầu vào trả cùng kết quả đã lưu; khác nội dung/metadata trả 409. Các request đồng thời được phân xử bằng transaction SQLite và unique index; chỉ request tạo mới đưa SHAP vào queue.
- Mất kết nối, timeout, HTTP 408/425/429/5xx: giữ con trỏ, thử lại với khoảng chờ tăng dần tới 30 giây. Dữ liệu thiếu cột, NaN/Infinity, 4xx khác: dừng rõ lỗi, giữ checkpoint để xử lý; không âm thầm bỏ dòng.
- Chờ dòng kết thúc bằng newline, kể cả dòng quote nhiều dòng; không gửi dòng đang ghi dở. Dòng trống được bỏ qua có checkpoint, không tạo flow. Giới hạn một record 1 MiB.
- Đọc thêm tối đa 100 record mỗi vòng, không nạp lại toàn bộ CSV mỗi giây. Tốc độ gửi vẫn phụ thuộc API, cấu hình poll và ổ đĩa.
- Phát hiện đổi file, truncate hoặc thay phần cuối đã đọc thì dừng. Hợp đồng là **CSV chỉ append**, không bảo đảm phát hiện mọi sửa đổi tùy ý ở phần xa trước checkpoint. Không sửa CSV đang capture.

`Idempotency-Key` là tùy chọn, client cũ vẫn gửi được. Feeder mới yêu cầu API echo header này trước khi tiến checkpoint: phải restart API bản mới trước feeder. UI upload hiện gửi theo từng lần bấm như trước, chưa dùng checkpoint/retry bền qua restart trình duyệt.

Tính bảo toàn phụ thuộc việc giữ cả checkpoint lẫn DB. Nếu chủ động reset DB, muốn gửi lại CSV cũ thì chọn `--checkpoint` mới; nếu xóa checkpoint thì feeder tạo run mới và có thể gửi lại cả file. Các dòng đã gửi bằng feeder cũ trước khi có checkpoint không tự suy ra được vị trí tiếp tục; nên bắt đầu phiên CSV mới khi nâng cấp.

## Khôi phục SHAP và giới hạn 200

API lưu trạng thái `pending_dispatch` trước khi đưa vào RAM. Khi restart, các trạng thái `queued`/`pending_dispatch` chưa có SHAP chuyển sang `recovery_pending`. Worker lấy từng việc từ DB khi queue hiện tại rảnh; không tải cả backlog vào RAM. Các việc đã có SHAP được đánh dấu hoàn tất. Nếu model version của prediction khác model hiện tại hoặc dữ liệu không chuẩn hóa được, đánh dấu lỗi để tránh giải thích bằng model khác.

Queue RAM vẫn tối đa **200 chờ + một đang chạy**. Tác vụ mới gặp queue đầy vẫn `dropped_queue_full`, giữ prediction/alert; không tự đổi chính sách thành retry những việc vốn đã bị bỏ. `failed` cũng không tự thử lại vô hạn. Backlog phục hồi ở DB có thể lớn hơn 200, dashboard hiển thị riêng; `/explain_queue_status` có `n_recovered` và `recovery_pending`. Khi traffic mới liên tục, việc phục hồi có thể phải chờ queue rảnh.

Mỗi DB chỉ chạy **một tiến trình API/SHAP worker**; file khóa `<db>.worker.lock` được hệ điều hành giải phóng khi tiến trình dừng/kết thúc bất thường. Không chạy `uvicorn --workers 2` với cùng DB. Đây là triển khai single-process đúng phạm vi hiện tại, chưa phải thiết kế phân tán.

Timing `total` mới đo từ lúc xử lý request đến sau các lệnh insert của giao dịch, trước commit cuối và dispatch; không chứa SHAP/LIME. `shap_recovery_wait` đo từ lúc claim phục hồi trong tiến trình mới, không tính thời gian API tắt. Khi làm E1 phải ghi nhận thay đổi này và đo thêm latency HTTP/end-to-end; không so thẳng `total` với các bản cũ khác ranh giới đo.

## Áp dụng trong VS Code

Từ `RQ3_IDS_System`, Ctrl+C đúng terminal API/UI/feeder/capture cũ rồi chạy API và UI lại; dùng CSV mới cho phiên nâng cấp:

```powershell
# Terminal API (một process)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Terminal UI
python -m streamlit run app/dashboard.py
# Terminal capture
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --interface "Wi-Fi" --output data\live_v2_01.csv
# Terminal feeder
python app\feeder.py --watch data\live_v2_01.csv --convert-units --capture-timezone +07:00
```

Nếu chỉ feeder/API bị ngắt, chạy lại cùng lệnh feeder để tiếp tục. Không khởi chạy capture ghi đè file đang tiếp tục. Muốn phát lại từ đầu có chủ đích: dùng `--checkpoint data\replay_02.feeder-state.json` chưa tồn tại; đó là run mới. UI CSV/PCAP cũng tiếp tục tạo run riêng cho mỗi lần gửi.

Chỉ thử candidate khi đối chiếu nghiên cứu:

```powershell
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --pcap-input ..\test.pcapng --output data\candidate_01.csv --extractor train-candidate
```

## Kiểm chứng và việc còn lại

- Stage20: 13 fixture/regression test PASS, gồm zero window cả hai chiều, baseline v1, candidate chỉ đổi nhóm được phép, chống ghi đè và các test packet/flow trước đó.
- Stage24: API/model/SQLite thật trên DB tạm; gửi trùng đồng thời, xung đột khóa, rollback giữa giao dịch, mất kết nối, mất ACK sau commit, restart API/feeder, dòng trống/dở dang, khóa feeder, lỗi input và truncate. Có mô phỏng việc SHAP bị ngắt bằng trạng thái DB sau khi dừng API, xác nhận phục hồi khi restart và giữ các việc dropped.
- Stage14: hồi quy API/UI/CSV/PCAP và LIME qua model thật, Streamlit AppTest; dữ liệu cô lập.
- Stage20 còn kiểm tra file xuất không có `CRCRLF`; Stage24 kiểm tra đọc CSV Windows kiểu cũ, NaN, khóa worker, và timestamp dự đoán riêng với timestamp nhận. Cả ba bộ Stage20/24/14 đã PASS sau các sửa cuối.

### Wi-Fi thật sau sửa CSV Windows

Hai phiên chỉ quan sát traffic có sẵn trên máy, dùng DB/API tạm; không thêm dữ liệu vào DB demo và không phát traffic tấn công:

| Phiên | Packet nhận/xuất/tổng CSV | Flow CSV/API | Nhãn model | SHAP |
|---|---|---|---|---|
| 20 giây | 9.201 / 9.201 / 9.201 | 48 / 48 | 43 Benign, 5 Hulk | 5 hoàn tất, 0 bỏ do queue |
| 100 giây | 44.156 / 44.156 / 44.156 | 150 / 150 | 123 Benign, 27 Hulk | 27 hoàn tất, 0 bỏ do queue |

Cả hai phiên kiểm tra đủ 78 đặc trưng, 15 xác suất lớp, metadata version/IP, đổi đơn vị duration và dữ liệu UI qua Streamlit AppTest. Bằng chứng: [20 giây](capture_v2_live_smoke_20261016.json), [100 giây](capture_v2_live_validation_20261016.json).

Phiên 100 giây có **5 flow tới API khi vẫn đang sniff**, và 140 flow tới trước khi tiến trình capture thoát (gồm giai đoạn flush sau khi ngừng sniff). Không đánh đồng hai số này: phần lớn flow được xuất khi flush; đây là pipeline theo flow/timeout, chưa phải dự đoán tức thì từng packet. 20 giây chỉ ghi chỉ số trước khi tiến trình thoát, không đủ căn cứ xác định bao nhiêu flow tới khi còn sniff. Đối soát packet chỉ tính các packet adapter đã nhận, không chứng minh NIC/Npcap không mất gói. Các nhãn Hulk là dự đoán, không phải xác nhận tấn công hay phép đo FPR.

Chưa chứng nhận tương thích toàn bộ đặc trưng train/live; cần nguồn cleaning và cặp original PCAP–CSV. Chưa train lại, chưa thay cấu hình LIME; chưa đo FPR trên traffic cá nhân không có nhãn. Packet đang giữ trong capture RAM vẫn mất nếu tiến trình capture chết trước khi xuất CSV; checkpoint chỉ bảo vệ phần CSV đã ghi. Chưa benchmark chạy nhiều giờ/tải cao hoặc bắt đủ packet tại NIC. Giao diện vẫn chưa có nút điều khiển start/stop capture riêng.
