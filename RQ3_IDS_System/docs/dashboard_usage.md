# Hướng dẫn chạy và đọc giao diện IDS

**Hotfix local 18/10/2026:** nếu từng thấy thông báo đỏ dù mở trên chính máy, đã sửa trường hợp Streamlit trả IP None cho localhost. Dừng riêng terminal UI bằng Ctrl+C rồi chạy lại lệnh Streamlit với `--server.address 127.0.0.1`; giữ cùng token API. Không cần reset DB hoặc mở thêm capture/feeder. Không chạy qua LAN/proxy/tunnel. Pipeline/model không đổi; xem kết quả test và giới hạn trong operations.md.

**Đọc hướng dẫn hiện hành tại [Bắt đầu/Dừng Realtime](#capture-control).** Những mô tả “chưa có nút” ở nhật ký mốc cũ không còn là trạng thái UI hiện tại. Điều khiển đã có nhưng chưa chứng nhận chạy lâu/tải cao; xem đầy đủ giới hạn bên dưới.

**HT3 (18/10/2026):** capture v3 có cap 4096 flow mở / 20000 packet đang giữ / 32 MiB byte packet và bảo vệ dung lượng ổ CSV. Đây không phải giới hạn tổng traffic của lượt. Nếu CLI báo quá tải/lỗi writer, phiên không đầy đủ: xem lỗi terminal, không coi UI còn hiển thị dữ liệu cũ là capture đang khỏe. UI PCAP không gửi dữ liệu khi lệnh trích xuất thất bại. Các counter cap hiện ở terminal, chưa có panel telemetry capture. Queue SHAP vẫn 200, bỏ giải thích khi đầy nhưng giữ cảnh báo; recovery được xen kẽ khi traffic mới vẫn đến. Xem tham số và xử lý lỗi trong [vận hành](operations.md).

Tài liệu hợp nhất ngày 16/10/2026. Chỉ còn 5 tài liệu RQ3 chính: [kiến trúc và kế hoạch](plan.md), [chạy và đọc UI](dashboard_usage.md), [vận hành](operations.md), [kiểm chứng XAI](xai_validation.md), [tương thích đặc trưng](feature_compatibility.md).

> Trạng thái hiện hành (HT2, 18/10/2026): capture project lifecycle v3; v2 còn chọn được bằng `--extractor project-v2`; feeder checkpoint/chống gửi trùng; SHAP queue 200 và phục hồi sau restart. Giữ XGBoost/78 đặc trưng, cấu hình LIME RQ2 và nhánh A/B. Nhật ký bên dưới giữ số liệu của phiên bản được ghi tại thời điểm kiểm thử. Chưa chứng nhận tương thích đầy đủ train–PCAP hoặc độ ổn định live dài hạn; nhãn live chưa phải ground truth.

## Bắt đầu ở đây

<a id="clean-retest"></a>

### Test lại sau reset DB ngày 18/10/2026

DB mặc định đã sạch (6 bảng bằng 0); lịch sử cũ có backup đã verify trong `backups/before_reset_20261018_user_retest_01`. API/UI chưa được mở sẵn. Mở VS Code tại thư mục RQ3_IDS_System và làm hai terminal theo mục ngay dưới. Nếu terminal tự kích hoạt venv demo capture cũ, chạy `deactivate` rồi chọn Python API/UI đã cài dependencies; không dùng `.venv_capture` để chạy API/UI.

Test lần lượt, không nạp nhiều nguồn cùng lúc để dễ đối soát:

1. **Realtime:** tab Realtime → `Wi-Fi` → Bắt đầu capture, đợi Đang bắt → lướt web → Dừng capture → đợi Đã hoàn tất → Xem flow của phiên này. Không cần mở terminal capture/feeder. Packet tăng nhưng CSV/API chưa tăng ngay có thể do flow chưa đóng/timeout; đây không phải dự đoán từng packet. Nếu Failed, đọc lỗi thật và giữ log, không coi đó là phiên đầy đủ hoặc tự tăng cap.
2. **CSV:** Nạp CSV / PCAP → CSV đặc trưng → chọn CSV đủ 78 đặc trưng → chỉ bật đổi đơn vị nếu CSV thực sự dùng giây như output capture tương ứng → Gửi CSV vào /predict. Không áp dụng đổi đơn vị cho CSV dataset đã dùng micro giây. Xem số gửi thành công/lỗi rồi chọn đúng lượt trong Giám sát flow.
3. **PCAP:** Nạp CSV / PCAP → PCAP đã ghi → chọn `test.pcapng` hoặc `tesst2.pcapng` trong thư mục SELF_KLTN → Trích xuất và gửi → đợi kết quả → Giám sát flow, chọn đúng lượt. Không cần bắt Wi-Fi khi phát lại PCAP.
4. Chọn một flow, kiểm tra IP/cổng nếu nguồn có metadata, nhãn/xác suất, SHAP và LIME theo yêu cầu. LIME có cảnh báo suy biến phải giữ cảnh báo, không coi đó là giải thích hợp lệ; nhãn tấn công chưa phải ground truth/FPR.

Không tiếp tục feeder dùng checkpoint cũ sau reset (ACK cũ có thể khiến bỏ qua dữ liệu). UI tạo lượt mới; không cần xóa CSV/PCAP để test lại. Các lượt mới được lưu chung DB và tách bằng bộ lọc lượt/nguồn; không tự xóa lịch sử giữa mỗi test.

<a id="capture-control"></a>

### Hiện hành: chạy nút Bắt đầu/Dừng trong tab Realtime

Đã tích hợp điều khiển, các đoạn “chưa có nút” trong nhật ký phía dưới mô tả mốc cũ. Chỉ cần **hai terminal API + UI**, không mở capture/feeder riêng khi dùng nút. Backend tự tạo CSV/checkpoint/lượt mới, không reset DB. Giữ cap mặc định; có thể dừng lỗi khi tải cao: lượt 30s đã chạm cap, smoke 10s mới PASS, chưa phải chứng nhận chạy lâu.

1. Mở VS Code bằng quyền Administrator nếu Npcap yêu cầu. Hai terminal đều ở `C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System`; dùng Python có dependencies API/UI đã cài và `.venv_capture` hiện có. Không mở API thứ hai cùng DB/registry.
2. Terminal API, tạo token riêng cho lần chạy (không commit token):

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
Remove-Item Env:IDS_DB_PATH -ErrorAction SilentlyContinue
Remove-Item Env:IDS_CAPTURE_SESSION_DIR -ErrorAction SilentlyContinue
$env:IDS_CAPTURE_CONTROL_TOKEN = [guid]::NewGuid().ToString('N')
$env:IDS_CAPTURE_CONTROL_TOKEN
$env:IDS_CAPTURE_API_URL = 'http://127.0.0.1:8000'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Dòng `$env:IDS_CAPTURE_CONTROL_TOKEN` hiển thị token để bạn sao chép vào terminal UI. Hai lệnh Remove-Item chỉ bỏ biến môi trường của terminal hiện tại để dùng DB/registry mặc định, không xóa file. Không chia sẻ/chụp token; không dùng `--reload` hoặc nhiều worker khi bắt mạng.

3. Terminal UI, thay placeholder bằng **đúng token vừa tạo**, không tạo token khác:

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
$env:IDS_CAPTURE_CONTROL_TOKEN = 'DAN_TOKEN_TU_TERMINAL_API_VAO_DAY'
$env:IDS_API_URL = 'http://127.0.0.1:8000'
python -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501
```

4. Mở `http://127.0.0.1:8501` trên chính máy → **Realtime** → nhập interface đúng (ví dụ `Wi-Fi`, xem `Get-NetAdapter`) → **Bắt đầu capture**. Đợi “Đang bắt”; chưa có flow ngay không phải lỗi vì đang gom packet. Traffic nền cũng được bắt. UI hiển thị packet/flow/ACK và heartbeat thực, không suy ra từ lịch sử cũ.
5. Lướt web bình thường; bấm **Xem flow của phiên này** rồi tab **Giám sát flow** để xem biểu đồ/chi tiết/SHAP/LIME. Nguồn live là `feeder_live`; lượt CSV/PCAP vẫn được giữ riêng. Nếu sidebar đang lọc nhãn/thời gian/nguồn khác, đổi lại cho phù hợp.
6. Bấm **Dừng capture** và đợi **Đã hoàn tất**. “Đang gửi nốt flow” chưa phải xong. Không đóng API trước khi drain xong. Nút không giới hạn 60 giây nhưng cap tài nguyên/lỗi có thể dừng sớm. Failed nghĩa là phiên chưa đầy đủ; không dùng số flow hiển thị để kết luận không mất dữ liệu.
7. Sau API restart, phiên cũ có thể là **Cần đối soát**. Bấm **Đối soát sau restart** chỉ kiểm tra OS, không kill/start lại. Nếu vẫn unknown, giữ journal/CSV và xem lỗi/log trong `data/capture_sessions/<run_id>/`; không xóa file để ép mở khóa. Retry cùng lệnh Start không tạo process trùng, refresh chỉ đọc trạng thái.

Control chưa bật/token sai: kiểm tra cùng token ở cả hai terminal rồi restart API/UI; model/DB không cần reset. Không đưa API/UI control lên LAN/proxy. Cách terminal thủ công bên dưới vẫn dùng được **thay thế**, không chạy đồng thời với nút.

### Nhật ký các mốc trước (không phải trạng thái hiện hành)

**HT4.3b:** supervisor backend đã nối capture/feeder, kiểm thử riêng bằng fixture. API/UI nối ở mốc kế tiếp; đây không phải bằng chứng đã bắt mạng thật. State worker không nằm trong Streamlit; CSV/checkpoint/log thuộc phiên do backend quản lý.

**Cập nhật HT4.3a (18/10):** đã kiểm thử đọc định danh process và đối soát phiên sau restart ở thư viện backend. Chưa gắn vào API/UI, chưa thay cách chạy terminal. Không hiển thị trạng thái “đang bắt” từ PID đơn lẻ hoặc dữ liệu flow cũ; nút capture vẫn chờ HT4.3b supervisor và kiểm thử tích hợp. Không cần reset DB/restart ứng dụng cho riêng thay đổi thư viện này.

**Cập nhật HT4.2 (18/10):** code capture/feeder đã có giao thức điều khiển nội bộ được kiểm thử, nhưng chưa có supervisor/API nối vào UI. Chưa có nút Bắt đầu/Dừng hoạt động; tiếp tục dùng các lệnh terminal bên dưới, không tự thêm `--control-dir`/`--worker-token`. Không cần reset DB hay đổi model. Giao thức worker không phải trạng thái capture trực tiếp trên Dashboard; HT4.3 sẽ nối quản lý tiến trình trước khi mở nút.

### UI bước 1 — trình bày, chưa điều khiển capture (18/10/2026)

Cập nhật HT4.1: đã có thư viện trạng thái bền/khóa sở hữu với test riêng, nhưng chưa nối API hoặc tiến trình thật. Không thay cách chạy terminal hiện tại; chưa có nút Start/Stop hoạt động. Trạng thái worker do Streamlit giữ vẫn không được dùng làm bằng chứng capture đang chạy.

Giữ ba tab chính để không đổi workflow nạp dữ liệu. Trong **Giám sát flow**, phần Tổng quan ghi tên lượt/nguồn/khoảng thời gian, 6 ô số liệu dùng toàn bộ bộ lọc. Hai tab biểu đồ: **Xu hướng & nhãn dự đoán** (Benign xanh, cảnh báo cam, có chú giải) và **Tiến độ giải thích trong phạm vi** (chờ/xong/bỏ/lỗi). Trạng thái SHAP toàn hệ thống được thu gọn, ghi rõ không theo bộ lọc; cảnh báo không phải ground truth/FPR.

Phần **Lịch sử & phân tích flow** có Trang trước/Trang sau và nhập số trang ngay cạnh bảng. Đổi phạm vi đưa về trang 1; trang vượt giới hạn được chặn. Chuyển trang hoặc tự refresh giữ flow đã chọn, có lời nhắc nếu flow nằm ngoài trang hiện tại. Nguồn/đích hiển thị cả IP và cổng; thiếu dữ liệu ghi rõ, cổng 443 thay cho 443.0, giao thức TCP/UDP thay mã 6/17. Mã flow đầy đủ trong khung sao chép; biểu đồ xác suất dùng trục 0–100%. Giữ nguyên các tab SHAP/LIME/đối chứng/đánh giá/78 đặc trưng và timing.

Không có nút capture hoạt động hoặc số liệu heartbeat giả. HT4 là bước backend riêng: API sở hữu tiến trình capture/feeder, có metadata bền và đối soát sau restart, khóa start trùng, stop/drain rõ trạng thái; Streamlit chỉ GET trạng thái và gửi lệnh, không làm chủ vòng đời tiến trình. Test HT4 riêng trước khi nối nút vào UI. Restart Streamlit để xem thay đổi, không cần reset DB hoặc train model.

**HT3.6 — lưu trữ:** trong tab Giám sát flow, mở **Dung lượng lưu trữ · chỉ theo dõi, không tự xóa** để xem dung lượng trống và các nhóm DB/CSV/log/checkpoint. Chỉ thống kê file trực tiếp trong thư mục DB, không đại diện mọi vị trí capture/backup. Dưới 1 GiB hiển thị cảnh báo; API không đọc được thì hiển thị chưa rõ, không báo đủ dung lượng. Mục này cập nhật cùng bảng flow (tạm dừng tự làm mới cũng dừng cập nhật). Restart API/UI sau khi cập nhật code; không reset DB. Backup/verify/restore qua CLI theo [HT3.6 trong vận hành](operations.md#ht36--dung-lượng-backup-và-khôi-phục-an-toàn-18102026), chưa có nút sửa/xóa dữ liệu trên UI.

UI gồm **Giám sát flow**, **Hướng dẫn live**, **Nạp CSV / PCAP**. Tab Hướng dẫn live chỉ cung cấp các bước/lệnh terminal; chưa điều khiển start/stop capture. Giám sát vẫn dùng chung cho cả ba nguồn, chọn Nguồn và Lượt dữ liệu ở sidebar để không trộn phiên. Chọn một flow để xem xác suất, SHAP, LIME theo yêu cầu, đối chứng đặc trưng và timing.

Chạy hai lệnh API/UI bên dưới từ thư mục RQ3_IDS_System, mở http://127.0.0.1:8501. Muốn xem lại PCAP: Nạp CSV / PCAP → Phát lại PCAP → chọn file → trích xuất/gửi → Giám sát flow. Không cần reset DB. Muốn live: mở Hướng dẫn live và dùng CSV mới. Model/luật cảnh báo không thay đổi theo tab.

- [Chuẩn bị và chạy API/UI](#start-api-ui)
- [Test CSV](#test-csv) · [Test PCAP](#test-pcap) · [Realtime liên tục](#test-live)
- [Tiếp tục phiên/checkpoint](#resume)
- [Hiểu tên đặc trưng và SHAP/LIME](#read-xai)

---

<a id="run-ui"></a>

## 1. Chuẩn bị trong VS Code

Hướng dẫn khớp code đến commit `b24f93c` ngày 16/10/2026. **Giữ cách chạy terminal; nút Bắt đầu/Dừng capture trên UI để sau.** Live mặc định chạy liên tục tới khi bạn dừng, không cần giới hạn 60 giây.

1. VS Code → **File → Open Folder** → chọn `C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System`.
2. **Terminal → New Terminal**, chọn PowerShell. Bấm **+** để mở các terminal khác; mỗi terminal phải ở thư mục RQ3_IDS_System.
3. Nếu đang kích hoạt `cicflowmeter_capture_demo\.venv` cũ, chạy `deactivate` trước; chỉ dùng lệnh này khi môi trường đó đang kích hoạt. Dùng Python đã chạy API thành công; capture có Python riêng.
4. Không cài lại, tạo lại nền LIME hoặc train model mỗi lần test.

Kiểm tra môi trường khi cần (không bật server):

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
python -c "import sys; print(sys.executable); import fastapi, streamlit, xgboost, shap, lime; print('API/UI imports OK')"
.\.venv_capture\Scripts\python.exe -c "from importlib.metadata import version; print('cicflowmeter', version('cicflowmeter'))"
Test-Path data\train_stats.json
Test-Path data\lime_background.npy
Test-Path data\clean_holdout_set.csv
```

Model/encoder phải tồn tại theo `config.yaml`. Thiếu thư viện API thì cài `python -m pip install -r requirements.txt` trong môi trường đã chọn, không tự nâng phiên bản. Capture dùng `.venv_capture` với CICFlowMeter 0.5.0 và `requirements-capture.txt` riêng. Nếu thiếu nền/thống kê, xem phần chuẩn bị README; không ghi đè chúng khi chỉ muốn xem UI.

| Cách test | Terminal giữ chạy | Nguồn trên UI |
|---|---|---|
| CSV qua UI | 1: API, 2: Dashboard | `csv_upload` |
| PCAP/PCAPNG qua UI | 1: API, 2: Dashboard | `pcap_replay` |
| Traffic live | 1: API, 2: Dashboard, 3: capture, 4: feeder | `feeder_live` |

<a id="start-api-ui"></a>

## 2. Bật API và Dashboard — dùng chung cho ba cách test

**Terminal 1 — API/model:**

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Đợi `Application startup complete`, giữ terminal chạy. Chỉ một API process cho mỗi DB; không thêm `--workers` hoặc `--reload` khi demo.

**Terminal 2 — Dashboard:**

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
python -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501
```

Mở **http://127.0.0.1:8501** bằng trình duyệt. API docs: http://127.0.0.1:8000/docs. Kiểm tra API từ terminal phụ: `Invoke-RestMethod http://127.0.0.1:8000/health`.

UI gồm **Giám sát flow · Hướng dẫn live · Nạp CSV / PCAP**. Tab Hướng dẫn live chỉ hướng dẫn terminal, chưa bật/dừng capture. Nếu server cũ đang chạy, dừng đúng terminal cũ trước; không mở thêm cùng cổng. Restart không xóa lịch sử DB.

<a id="test-csv"></a>

## 3. Test CSV có đặc trưng sẵn

1. Giữ API/UI chạy; không cần capture hoặc feeder.
2. Vào **Nạp CSV / PCAP → CSV đặc trưng → Chọn CSV**.
3. File mẫu sẵn: `RQ3_IDS_System\data\clean_holdout_set.csv`. Không chọn file JSON hoặc PCAP vào tab CSV.
4. Chọn ô **Đổi giây → micro giây (CSV CICFlowMeter thật)** theo nguồn file:

| Loại CSV | Đổi đơn vị |
|---|---|
| Tập A/B, `clean_holdout_set.csv` hoặc dữ liệu thời gian đã là micro giây | **Không tích** |
| CSV từ adapter Python CICFlowMeter 0.5.0 của dự án, thời gian còn là giây | **Tích** |
| CSV từ extractor khác/không biết đơn vị | Xác minh trước; không mặc định mọi CSV CICFlowMeter đều cần đổi |

5. Chọn **Múi giờ timestamp trong CSV**: `+07:00` nếu biết là giờ Việt Nam/Thái Lan, `+00:00` nếu UTC; không rõ thì giữ **Không rõ**.
6. Bấm **Gửi CSV vào /predict** một lần, đợi số flow thành công/dòng lỗi; mở **Chi tiết lỗi gửi** nếu có.
7. Sang **Giám sát flow**, chọn đúng lượt tên file, Nguồn = `csv_upload`, thời gian = **Toàn bộ lượt**; bỏ **Chỉ cảnh báo** để thấy Benign.
8. Bấm một dòng để xem dự đoán, SHAP; LIME chỉ chạy khi yêu cầu trên flow cảnh báo.

File cần UTF-8 và đủ 78 đặc trưng tên chuẩn hoặc tên mapping hỗ trợ, không có NaN/Infinity. IP/timestamp chỉ hiện nếu file cung cấp; dataset không có IP là bình thường. Không suy ra IP từ 78 đặc trưng. Upload không tự trở thành phép đo FPR chỉ vì CSV có cột nhãn; không coi nhãn dự đoán là ground truth.

Refresh không tự gửi lại; **bấm gửi lần nữa tạo lượt mới**, có thể lặp nội dung. Upload UI chưa có checkpoint phục hồi qua restart trình duyệt như feeder.

<a id="test-pcap"></a>

## 4. Test PCAP/PCAPNG đã ghi

1. Giữ API/UI chạy. Không cần terminal capture/feeder cho cách này.
2. **Nạp CSV / PCAP → PCAP đã ghi → Chọn PCAP**.
3. Chọn file, ví dụ `C:\Users\LOQ\Downloads\SELF_KLTN\tesst2.pcapng` hoặc `test.pcapng`.
4. Bấm **Trích xuất và gửi**. UI tự chạy Python trong `.venv_capture`, trích flow bằng project lifecycle v3 rồi gửi cùng `/predict`. Flow lịch sử vẫn giữ version cũ; không trích lại tự động.
5. Đợi số flow thành công/lỗi, sang **Giám sát flow**, chọn lượt tên PCAP và Nguồn = `pcap_replay`.
6. Xem IP/cổng, thời điểm gói đầu khác lúc API nhận, nhãn/xác suất và SHAP/LIME của flow đã chọn.

Đây là **đọc file offline**, không phát gói ra mạng bằng tcpreplay. UI tự đổi giây→micro giây cho CSV extractor sinh; không dùng ô đổi đơn vị của tab CSV. Timestamp PCAP được extractor chuyển theo múi giờ máy chạy, UI hiển thị mốc đã biết ở GMT+7.

Giới hạn trích xuất trên UI là **120 giây xử lý**, không phải thời lượng traffic trong file. Nếu vượt, thử file nhỏ hơn hoặc trích offline bằng CLI với tên CSV mới:

```powershell
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --pcap-input ..\tesst2.pcapng --output data\replay_review_01.csv
```

Đợi xong rồi upload CSV này theo mục 3, tích đổi đơn vị. Lượt đó có nguồn `csv_upload` (không phải `pcap_replay`), cần ghi đúng nguồn gốc khi báo cáo. CLI này không có timeout subprocess 120 giây của UI. Không dùng `--overwrite` để ghi đè file feeder đang theo dõi.

Nếu cần tự tạo PCAP: dùng Wireshark chọn đúng card → Start → thao tác trên máy → Stop → Save As .pcapng, rồi upload theo các bước trên. Chỉ bắt mạng bạn được phép kiểm thử.

<a id="test-live"></a>

## 5. Test realtime liên tục — đến khi chủ động dừng

Giữ terminal 1/API và 2/UI, mở thêm terminal 3 và 4. **Không thêm `--seconds`: không giới hạn 60 giây.**

Xem card đang dùng:

```powershell
Get-NetAdapter | Select-Object Name,Status,InterfaceDescription
```

Thay `Wi-Fi` nếu đang dùng card khác. Npcap cần sẵn sàng; nếu thiếu quyền, dừng đúng tiến trình rồi mở VS Code bằng **Run as administrator** và chạy lại. Không tắt bảo mật hoặc thay ExecutionPolicy toàn máy.

**Terminal 3 — capture:**

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --interface "Wi-Fi" --output data\live_review_01.csv
```

**Terminal 4 — feeder:**

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
python app\feeder.py --watch data\live_review_01.csv --convert-units --capture-timezone +07:00
```

- Cả hai phải cùng đường dẫn CSV. Nếu tên đã có dữ liệu, đổi **cả hai lệnh** sang `live_review_02.csv` hoặc tên mới.
- `+07:00` chỉ đúng nếu timestamp capture theo giờ Việt Nam/Thái Lan.
- Lướt web **trên laptop đang capture**. Traffic nền vẫn có khi chưa thao tác; laptop không tự nhìn thấy toàn bộ traffic của mọi máy chung Wi-Fi/hotspot.
- Capture báo `[capture] receiving_started`; chế độ này không in từng packet, UI chưa có bộ đếm packet trực tiếp.
- Feeder báo `Dòng mới #…: GỬI OK` khi API đã trả kết quả.
- UI chọn lượt `live_review_01.csv`, Nguồn = `feeder_live`, **Toàn bộ lượt**. Lượt chỉ hiện khi API nhận flow; bấm **Làm mới ngay** nếu danh sách chưa cập nhật.

### Vì sao lướt web mà chưa thấy flow?

Dự đoán **theo flow**, không từng packet. Project v3 xuất khi tuổi flow tính từ packet đầu đạt 90 giây (GC live kiểm tra định kỳ), quan sát RST, đủ FIN/ACK hai chiều, SYN mở phiên mới hoặc flush lúc dừng. Không phải 90 giây từ lúc bật chương trình. FIN một chiều chưa đủ để đóng; packet lệch timestamp được xuất riêng với `flow_end_reason=late_packet` trong CSV. Idle 240 giây vẫn có trong policy nhưng tuổi tối đa 90 giây đến trước với cấu hình mặc định. V1/v2 giữ cách timeout cũ; xem version của từng lượt. Chưa có chứng nhận tương thích train hoặc benchmark chạy lâu v3.

Kiểm tra ở terminal phụ:

```powershell
Get-Item data\live_review_01.csv | Select-Object Length,LastWriteTime
Get-Content data\live_review_01.csv.feeder-state.json
Invoke-RestMethod http://127.0.0.1:8000/explain_queue_status
```

`acknowledged_rows` là số dòng đã được API xác nhận. CSV 0 byte có thể là chưa xuất flow, không đủ để khẳng định không bắt được gói. API khỏe cũng không chứng minh capture còn chạy.

### Dừng đúng thứ tự

1. Bấm vào **terminal 3/capture**, Esc nếu đang chọn chữ, nhấn **Ctrl+C một lần**.
2. Đợi yêu cầu dừng, `[capture] receiving_stopped`, số packet/flow và **Đã dừng. Kiểm tra file…**. Bản từ `b24f93c` tránh join vô hạn; chỉ áp dụng cho capture khởi chạy mới.
3. **Giữ feeder** tới khi gửi hết CSV đã flush. Có thể đối chiếu `acknowledged_rows` với `exported_flows` của capture nếu CSV chỉ do phiên hiện tại tạo.
4. Ctrl+C **terminal 4/feeder**. Giữ API/UI nếu tiếp tục xem; nếu nghỉ, đợi SHAP hoàn tất khi cần rồi Ctrl+C UI và API.
5. Không dùng thùng rác/Stop-Process làm cách dừng thường lệ: flow trong RAM có thể mất.

Nếu vẫn không dừng, kiểm tra đúng terminal và giữ log để chẩn đoán. Báo lỗi “thread còn chạy/chưa thể ghi nốt an toàn” nghĩa là chưa xác nhận flush thành công. `--seconds N` chỉ là tùy chọn kiểm thử, không bắt buộc.

<a id="resume"></a>

## 6. Tiếp tục hoặc tạo phiên mới

- **Feeder ngắt:** chạy lại cùng CSV/API/đơn vị/múi giờ và checkpoint. Tiếp tục từ dòng đã xác nhận, retry cùng khóa không tạo flow trùng.
- **API ngắt:** bật lại API, giữ feeder/checkpoint. Lỗi kết nối tạm được thử lại; SHAP đang chờ bị ngắt khôi phục dần từ DB.
- **Capture đã dừng:** phiên mới dùng CSV mới. Chỉ muốn gửi nốt CSV cũ thì chạy feeder, không khởi chạy capture ghi đè.
- **Phát lại CSV có chủ đích:** dùng checkpoint mới chưa tồn tại, ví dụ thêm `--checkpoint data\replay_again_01.feeder-state.json`. Đây là lượt mới, có thể lặp nội dung.
- **Sau reset DB:** checkpoint cũ vẫn nhớ các dòng đã gửi. Test UI tạo lượt mới; feeder phát lại CSV cũ cần checkpoint mới. Không xóa checkpoint khi feeder đang chạy.
- Không cần reset DB mỗi lần test, chỉ lọc lượt. Sao lưu nhất quán trước mọi reset có chủ đích.

## 7. Lỗi thường gặp

| Hiện tượng | Kiểm tra / xử lý |
|---|---|
| Không mở được UI | Terminal UI còn chạy không, đúng cổng 8501 không |
| UI không kết nối API | API có startup complete không; gọi `/health`, kiểm tra đúng Python |
| Cổng bận/DB có worker khác | Không bật API thứ hai; xác minh tiến trình cũ, không tắt toàn bộ Python |
| CSV có dữ liệu, chưa `GỬI OK` | Kiểm tra cùng đường dẫn capture/feeder, log lỗi và API/checkpoint |
| Không thấy lượt live | Chưa nhận flow hoặc lọc nhầm; Làm mới ngay, chọn đúng lượt/nguồn |
| Feeder DỪNG/HTTP 422 | Xem cột, NaN/Infinity, đơn vị; con trỏ giữ nguyên, không tự bỏ dòng |
| File thay đổi/truncate | Không ghi đè CSV đang theo dõi; tạo phiên CSV mới |
| Thiếu IP | Nguồn có cung cấp metadata IP không; không suy ra từ vector feature |
| Queue đầy | 200 chỉ giới hạn SHAP chờ; vẫn lưu prediction/alert, dropped không tự retry |
| LIME không có biểu đồ | Đọc trạng thái/chẩn đoán; thiếu lân cận không có nghĩa chưa dự đoán |
| Hulk khi lướt web | Nhãn model chưa xác minh; kiểm tra feature/train–capture, không tính FPR live khi thiếu nhãn thật |
| Cảnh báo phiên bản sklearn/model | Giới hạn môi trường đã biết; không tự nâng/gỡ thư viện hoặc train lại để che cảnh báo |

## 8. Checklist xem kết quả

- Đúng lượt/nguồn, bỏ **Chỉ cảnh báo** để thấy cả Benign.
- Có số gửi thành công/lỗi; không chỉ nhìn packet capture.
- Chọn flow xem IP nếu có, thời gian gói đầu/API nhận, xác suất 15 lớp.
- Cảnh báo có SHAP tự động; Benign không cần cảnh báo/SHAP/LIME theo kiến trúc hiện tại.
- Yêu cầu LIME thủ công; suy biến thì giữ thông báo, không coi Top-5 bằng 0 là bằng chứng.
- Test pipeline chạy được không tự chứng minh accuracy/FPR ngoài thực tế.

## Đọc màn hình

### LIME và đối chứng đặc trưng (bổ sung)

**Cách đọc mới:** ngay dưới biểu đồ SHAP/LIME có “Đọc từng đặc trưng bằng lời”. Mở một mục để xem tên tiếng Việt, ý nghĩa, giá trị flow và hướng tác động tới lớp đang giải thích. Tab Đối chứng ưu tiên tra cứu một đặc trưng; bảng thống kê và chẩn đoán được thu gọn. Xem [hướng dẫn đọc SHAP/LIME](dashboard_usage.md#read-xai).

Sau cập nhật, khởi động lại API và Streamlit. Không cần xóa DB hoặc upload lại PCAP chỉ để xem đối chứng.
Chọn flow → **LIME theo yêu cầu** → **Yêu cầu / kiểm tra lại LIME** để bổ sung chẩn đoán cho kết quả cũ.
Nếu LIME suy biến, UI hiện cảnh báo thay vì biểu đồ toàn số 0 và R²=1 gây hiểu nhầm. Chạy lại cùng dữ liệu/config không đảm bảo hết suy biến.

Tab **Đối chứng đặc trưng**: chọn tên đặc trưng để đọc giải nghĩa và giá trị, ưu tiên tên xuất hiện trong SHAP/LIME. Mở “So sánh số liệu tham chiếu” để xem P05/median/P95 của nền LIME, Benign và lớp dự đoán kèm cỡ mẫu. “Tra cứu toàn bộ 78 đặc trưng” và “Chẩn đoán lệch mẫu nền” nằm trong phần mở rộng. Bảng chẩn đoán xếp theo lệch mẫu nền, **không phải thứ hạng SHAP**. Mẫu theo lớp lấy từ tập B nhỏ, không đại diện toàn bộ lớp hay chứng minh tấn công.

Chi tiết nguyên nhân và giới hạn: [LIME validity và đối chứng](xai_validation.md#lime-validity).

**Cập nhật audit đặc trưng:** [audit trước sửa](feature_compatibility.md#baseline-audit) ghi nhận lỗi Python extractor; adapter v1 đã sửa 5 lỗi kiểm chứng được, còn quy ước khác train chưa xác minh đầy đủ. UI có đủ kết quả hoặc SHAP cộng đúng không chứng nhận mọi đặc trưng PCAP tương thích dataset V3.

- Mặc định là **lượt nhận dữ liệu gần nhất**, không mặc định tất cả lịch sử. Nếu upload CSV/PCAP hoặc có nguồn khác gửi sau đó, chọn cố định lượt live của bạn trong sidebar. Danh sách lựa chọn lượt cập nhật khi bấm Làm mới ngay.
- Mọi chỉ số/biểu đồ lấy toàn bộ phạm vi bộ lọc; bảng phân trang 50 flow. Thời gian là lúc API nhận, mới nhất trước.
- Chọn dòng bảng để mở chi tiết. Flow đang đọc được giữ qua lần làm mới; đổi phạm vi sẽ chọn lại. Có nút tạm dừng tự làm mới.
- Chi tiết: IP/cổng nếu nguồn cung cấp, xác suất lớp, gói đầu tiên, lúc nhận/dự đoán, SHAP, LIME thủ công, cờ/nhánh và timing. Giờ mặc định GMT+7; raw timestamp còn trong phần metadata.
- Dữ liệu cũ không biết múi giờ/IP/lượt vẫn còn; hiển thị thiếu thông tin, không tự đoán.
- Nhóm cảnh báo chỉ gom hiển thị trong cửa sổ 5 phút; có thể chọn từng flow con và phân trang. Không xóa cảnh báo.
- LIME không tự chạy khi refresh. Benign không tạo cảnh báo/SHAP/LIME theo kiến trúc.
- Xác suất cao hay nhãn Hulk không chứng minh traffic Facebook là tấn công thật. SHAP giải thích model, không xác nhận nhãn thật.
- Có packet nhưng chưa có flow mới: kiểm tra CICFlowMeter đã ghi CSV và feeder có log GỬI OK chưa. Dashboard không thể biết chắc bộ bắt còn hoạt động chỉ từ API; không tuyên bố đang bắt khi chưa có telemetry.
- `recovery_pending` nghĩa là cảnh báo đã lưu và chờ khôi phục SHAP sau restart; worker xử lý dần khi queue rảnh. UI hiện trạng thái và số còn chờ; dữ liệu không được tự đổi nhãn.

## Kiểm thử đã thực hiện

```powershell
python scripts\stage14_test_dashboard_redesign.py
```

Test tự tạo DB tạm và API cổng riêng rồi dừng tiến trình đó. Không dùng DB demo.
Đã PASS: migration 2 lần giữ dữ liệu cũ; 205 flow fixture kiểm tra tổng số/phân trang; timezone; API lọc/404/422; dự đoán bằng model thật; metadata không đổi xác suất; SHAP bất đồng bộ; Benign và cảnh báo; AppTest chọn lượt/chi tiết/LIME/giữ lựa chọn; CSV không gửi lại khi refresh; PCAP thật qua CICFlowMeter rồi /predict; feeder gặp dòng trống không gửi lặp.
`stage13_test_dashboard.py` chuyển tiếp sang bộ test cô lập này, không còn phụ thuộc dropdown cũ.

Đây là kiểm thử chức năng, không phải đánh giá lại accuracy hay xác nhận traffic tấn công. Sau bản capture v1 đã kiểm tra Wi-Fi thật 20s/100s qua feeder/API và AppTest UI trên DB tạm: phiên 100s có 88 flow lên trong lúc vẫn bắt. Xem [báo cáo capture v1](feature_compatibility.md#adapter-v1). Chưa nghiệm thu thao tác chuột trên trình duyệt thật với phiên Wi-Fi này; AppTest xác minh trạng thái render và dữ liệu, không thay kiểm tra trực quan đầy đủ.

Bản v2 đã kiểm tra lại Wi-Fi 20s/100s sau sửa CSV Windows: lần lượt 48/48 và 150/150 flow từ CSV tới API; phiên 100s có 44.156 packet được adapter nhận và xuất đủ, 27 SHAP hoàn tất, không bỏ do queue. Phép đo mới tách rõ **5 flow tới khi còn sniff** với **140 flow tới trước khi tiến trình thoát**, vì giai đoạn flush cũng xảy ra trước khi thoát. Không dùng số trước khi tiến trình thoát để khẳng định tất cả đã được dự đoán trong lúc sniff. Chi tiết, checkpoint và test restart: [cập nhật độ ổn định v2](operations.md#stability-v2).

Đã chạy thêm `stage04_test_normalize.py` và `stage05_test_predict.py`: PASS; 50/50 flow đối chiếu khớp dự đoán RQ2. Runtime vẫn cảnh báo model/LabelEncoder được lưu từ phiên bản thư viện khác; không thay hoặc huấn luyện lại model trong lần chỉnh UI này.

## API quan sát

- `/runs`: các lượt dữ liệu.
- `/flows`: `capture_run_id`, `source`, `label`, `branch`, `since`, `until`, `alerts_only`, `group_key`, `limit` (1–1000), `offset`.
- `/flows/{flow_id}`: mọi flow, kể cả Benign; đặc trưng, xác suất, metadata, XAI và timing.
- `/dashboard/summary`: cùng bộ lọc, số đếm/toàn bộ timeline/nhãn và tối đa 100 nhóm mới nhất.
- `/alerts`: tương thích tên trạng thái hoàn tất cũ; thêm lọc lượt/nguồn và phân trang. `count` là tổng khớp bộ lọc, không phải số dòng trang.
- `since`/`until` cần ISO kèm múi giờ và lọc theo lúc API nhận. `capture_run_id=__legacy__` chọn dữ liệu chưa gắn lượt.
- `IDS_DB_PATH` và `IDS_API_URL`: override dành cho test độc lập; không cần đặt khi demo mặc định.

Đầu vào `/predict` vẫn là 78 đặc trưng số. Metadata mới là query tùy chọn, không làm thay đổi đầu vào model.

---

<a id="read-xai"></a>

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
- `CWE Flag Count` trong dataset liên quan CWR. Lỗi sao chép Fwd URG Flags thuộc upstream Python 0.5.0/legacy; adapter project v1/v2 đã sửa đếm CWR độc lập. Xem phiên bản extractor của flow, không áp nhận định baseline cho mọi phiên mới.
- Các khác biệt ngữ nghĩa còn lại phải đối chiếu [hợp đồng đặc trưng](feature_compatibility.md); giao diện giải nghĩa không chứng nhận khả năng tổng quát hóa của model.

## 5. Kiểm thử và chạy lại

```powershell
python -B RQ3_IDS_System/scripts/stage16_test_feature_help.py
python -B RQ3_IDS_System/scripts/stage15_test_lime_validity.py
python -B RQ3_IDS_System/scripts/stage14_test_dashboard_redesign.py
```

Stage16 kiểm tra đủ 78 tên/đơn vị, định dạng số và hướng diễn giải; Stage15 kiểm tra LIME số học; Stage14 kiểm tra API/UI, chọn FIN để tra cứu, trạng thái LIME lỗi, CSV/PCAP trên DB tạm. Không cần reset DB để dùng UI mới. Khởi động lại API và Streamlit sau cập nhật; tự-refresh không tự chạy lại LIME.
