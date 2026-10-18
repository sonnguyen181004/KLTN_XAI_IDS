# Vận hành, phục hồi và kiểm thử RQ3

## HT4.4 hiện hành — API/UI điều khiển và nghiệm thu (18/10/2026)

**Mục đích:** dùng nút UI thay hai terminal capture/feeder, không đổi tầng chuẩn hóa/model/XAI/DB thật. `/capture/status`, `/capture/start`, `/capture/stop`, `/capture/reconcile` chỉ bật khi API có `IDS_CAPTURE_CONTROL_TOKEN` >=32 ký tự; UI dùng cùng token qua header server-side. API kiểm tra client loopback, Host local, token constant-time, từ chối Origin/cross-site; UI từ chối browser IP không local/không xác minh được. Chỉ bind API/UI `127.0.0.1`, không deploy qua proxy/LAN; token không bảo vệ một UI cố ý công khai như hệ thống đăng nhập. API một worker, không reload khi capture. Không có token: prediction và UI cũ vẫn chạy, control disabled.

`IDS_CAPTURE_SESSION_DIR` mặc định `data/capture_sessions` (Git ignore), tách journal/control/CSV/checkpoint/log theo run UUID. `IDS_CAPTURE_API_URL` phải trỏ đúng API loopback đang chạy (mặc định 8000); đổi port phải đổi biến này. API giữ single-owner OS lock suốt lifespan; một API khác cùng registry không được sở hữu. UI chỉ GET mỗi 3s, POST khi bấm; không giữ process/PID, start retry cùng request ID không spawn lại. CSV/PCAP/biểu đồ/XAI tiếp tục dùng API dự đoán cũ; mã lượt dự đoán từ checkpoint dùng nút **Xem flow của phiên này**.

Stop là bất đồng bộ: starting/running → stopping → draining → completed chỉ khi hai exit=0, CSV/ACK khớp. Không tự dừng sau 60s; cap/disk guard vẫn có thể dừng phiên lỗi. **Dừng capture và đợi completed trước khi tắt API**; API shutdown khi feeder chưa gửi hết có thể làm phiên failed, không hứa flush/ACK thành công khi kill API. Journal unknown sau restart phải đối soát; worker cũ còn sống/không chứng minh được thì khóa giữ nguyên. Không tự nhận nuôi PID, không tự kill/giải phóng spawn gap. CSV/checkpoint/log giữ để kiểm tra, không tự xóa/rotation.

Sửa phát hiện khi nghiệm thu: latch lỗi health đầu tiên ngay cả khi lần kiểm tra cuối thành công; lỗi đó không được biến thành thoát an toàn. Read/write file control retry PermissionError có giới hạn (6 lần, tổng chờ 0,3s). Wrapper không ghi đè lỗi worker bằng SystemExit chung chung; registry giữ reason lỗi đầu tiên, supervisor lưu `supervisor_error.json`. UI hiển thị error_message thực, không gán cứng giải thích. Counter cuối capture được chốt lại sau flush (sửa độ trễ telemetry ghi nhận ở smoke test).

### Kết quả test và giới hạn

Rà soát cuối bổ sung test race worker exit/Popen poll: đọc final report sau khi xác nhận exit, cho tối đa 5s để launcher reaped nếu worker vừa biến mất giữa hai lần đọc OS. Không dùng race này để bỏ kiểm tra identity hoặc báo completed sớm. Stage36 tăng từ 6 lên 7 test PASS; Stage33 xác nhận lỗi rollback không ghi đè nguyên nhân đầu tiên.

- Stage36 7/7 process fixture; Stage37 4/4 auth/Host/Origin/client/UI refresh/buttons; Stage14 model/CSV/PCAP/SHAP/LIME/UI PASS trên DB tạm. Stage20 22/22, Stage33/35 12/12 mỗi bộ, Stage34 9/9. Stage37/38 AppTest mock kiểm tra IP browser vì không có kết nối browser thật; API vẫn kiểm tra HTTP/token thật trong Stage38. Chưa QA thủ công trên nhiều kích thước trình duyệt.
- `live_ht4_control_20261018.json`: **FAIL**, yêu cầu 30s, lỗi ~25,1s do cap 20.000 buffered packet. Log: nhận=xuất 20.056 packet, 57 flow CSV, limit_rejected=1, feeder ACK=7 rồi abort. CSV còn giữ, không báo dữ liệu đầy đủ. Cap giữ nguyên, không dùng nhãn làm FPR.
- `live_ht4_stop_smoke_20261018.json`: **FAIL**, yêu cầu 10s, phát hiện dừng sớm ở lần kiểm tra 5s, không cap; log 1.539 packet/14 flow, không đủ log nguyên nhân đầu tiên. Không khẳng định retry file là nguyên nhân gốc đã chứng minh; latch health được chứng minh riêng bằng test.
- `live_ht4_stop_diagnostic_20261018.json`: **FAIL ở harness trước capture**, AppTest thiếu browser IP thật nên không có widget. Không tính là lượt Wi-Fi đã chạy; sửa mock test thay vì nới guard thật.
- `live_ht4_stop_retry_20261018.json`: **PASS smoke** sau cửa sổ running 10,034s; stop/drain 2,133s; 267 packet nhận=xuất, limit_rejected=0; 19 flow CSV=API=ACK; hai worker exit0; SHAP queued=processed=1, dropped=0, queue cuối0. UI Start/Stop/refresh qua AppTest, Wi-Fi/model/API thật. Telemetry snapshot trước flush từng chậm hơn counter cuối log; đã sửa và thêm assertion fixture. Không thay kết quả lịch sử.

Mọi lượt dùng API/DB riêng trong Temp, API test đã dừng; raw CSV/log còn trong evidence_directory của từng JSON để chẩn đoán, không đưa vào Git. Chưa chứng nhận chịu tải dài hạn: thất bại cap 30s vẫn mở. Không dùng PASS 10s thay cho FAIL 30s. Không reset DB thật hoặc đổi model. Commit: `feat(rq3): expose local capture controls and realtime dashboard`.

## HT4.3b — supervisor nối registry và worker (18/10/2026)

Mục đích: quản lý vòng đời ở backend, không phụ thuộc Streamlit. `CaptureSupervisor` dùng một thread điều phối + ownership registry. `managed_worker.py` báo PID/birth/token rồi đợi gate; phía cha đọc OS birth và parent PID (hỗ trợ launcher venv Windows) trước attach/release. Một CSV/checkpoint/thư mục control riêng cho mỗi run. Không dùng shell, không nhận lệnh tùy ý từ UI. `status()` bỏ worker token, liên kết lượt feeder bằng checkpoint.

Start trả trạng thái starting, retry request ID không spawn lại; sau readiness mới running. Stop hợp tác → capture flush/exit → kiểm tra CSV size → feeder drain → đối soát ACK và exit cả hai mới completed. Heartbeat timeout 90s (bao gồm HTTP timeout/backoff), readiness 45s, stop/drain tối đa 120s trước đường lỗi; thời lượng capture bình thường không giới hạn 60s. Lease 45s và rollback chờ tối đa 65s, không tự kill. Lỗi/thiếu bằng chứng giữ failed hoặc unknown, không giả completed. Unknown vẫn chặn phiên mới.

Popen lỗi trước khi trả handle được hủy intent chưa spawn; worker đã attach phải reaped trước đóng failed. Crash/timeout giữa spawn và attach vẫn giữ intent unknown cần kiểm tra, chưa tự giải phóng. Không quản lý capture terminal bên ngoài; không chạy cả hai cách đồng thời. Log/CSV được giữ, chưa rotation tự động; cap/disk guard cũ giữ nguyên.

Kiểm thử Stage36 **6/6 PASS** dùng sniffer fixture, worker process và HTTP ACK fixture: duplicate start, stop/drain, shutdown, lỗi script, interpreter thiếu, lỗi spawn đầu và spawn thứ hai/rollback. Không gọi fixture là test Wi-Fi/model. Stage33–35 giữ hợp đồng cũ; API/UI được nối ở mốc tiếp theo. Commit: `feat(rq3): supervise owned capture and feeder workers`.

## HT4.3a — định danh OS và đối soát sau restart (18/10/2026)

**Mục đích:** ngăn start trùng/nhận nhầm PID cũ sau API restart trước khi mở điều khiển capture. Phạm vi là thư viện backend + test, chưa có supervisor khởi chạy hoặc endpoint/UI. Không đổi prediction DB 6 bảng, model, extractor, XAI hay cap; không chạy Wi-Fi hoặc sửa DB thật.

- `process_identity.birth_of` trên Windows mở handle chỉ query/synchronize, kiểm tra process đã thoát và đọc creation FILETIME; token tương thích `worker_control.process_birth`. Không gửi tín hiệu/kill. `probe_identity` phân biệt `alive`, `absent`, `reused`, `unknown`; thiếu quyền hoặc lỗi đọc không được coi là process đã mất. Nhánh Linux `/proc` có code nhưng chưa nghiệm thu Linux.
- Registry có `begin_launch(run_id, role, worker_token)` phải commit **trước** spawn; nếu ghi lỗi, caller không được tạo process. `attach` chỉ nhận token khớp intent rồi xóa intent trong cùng transaction; caller tương lai vẫn phải xác minh OS và quan hệ process trước attach. Journal mới ghi version 1; không đổi schema bảng SQLite, metadata nằm trong payload.
- `active()` đọc phiên chưa giải phóng. `reconcile(run_id)` chỉ áp dụng phiên unknown, tự đọc bằng chứng OS, không nhận PID/status từ UI. Nếu mọi worker đã absent/reused và không còn intent, giải phóng active với `failed/reconciled_workers_gone_outcome_unverified`. Không điền exit code giả, không báo completed hoặc suy ra flush/ACK. Gọi lại phiên đã đóng trả lịch sử, request ID cũ không được khởi chạy lại.
- Worker còn sống, thiếu quyền kiểm tra hoặc intent chưa giải quyết → giữ unknown/chặn start. Journal cũ thiếu launch protocol và thiếu worker cũng bị chặn vì không chứng minh được đã spawn hay chưa. Journal mới chưa từng begin_launch có thể đóng failed an toàn sau restart. Lỗi lưu kết quả đối soát rollback, không giải phóng phiên.
- **Giới hạn quan trọng:** crash giữa spawn và attach có thể để lại intent không có PID, chưa tự giải quyết. Không xóa journal/intent để ép mở khóa, không kill PID chưa xác minh. API chưa sử dụng thư viện nên chưa ảnh hưởng phiên terminal. Chưa có xác thực nguồn gọi hoặc bảo vệ endpoint, vì chưa mở endpoint. Vòng giám sát/lease, startup timeout/rollback, xác minh launcher venv và shutdown chờ HT4.3b.

Kiểm thử: `python scripts/stage35_test_process_reconciliation.py` **12/12 PASS** trên Windows, dùng registry tạm và process con chờ stdin (không NIC): creation time thực, worker sống/thoát, PID reuse mô phỏng với process còn sống không bị tác động, access denied, spawn gap, legacy journal, token/intent sai, lỗi ghi và rollback. Fixture SQLite dùng explicit close để không giữ file khi dọn thư mục tạm. Hồi quy Stage33 **12/12 PASS**, Stage34 **9/9 PASS**. Không chạy lại Stage14/model vì không có đường import từ runtime/API vào registry thay đổi này; không coi đây là nghiệm thu live hay accuracy.

Commit: `feat(rq3): reconcile capture journals against OS process identity`. Tiếp theo HT4.3b nối supervisor/worker với test riêng; sau đó mới nối API/UI. Nhật ký phía dưới giữ nguyên phạm vi các bước trước.

## HT4.2 — giao thức worker, chưa tích hợp supervisor (18/10/2026)

**Mục đích:** chuẩn bị đường dừng/flush/drain có bằng chứng, độc lập refresh Streamlit. `app/worker_control.py` được capture và feeder dùng khi có cặp tham số nội bộ `--control-dir`/`--worker-token`; không có tham số này thì giữ workflow terminal cũ. Không đổi model/78 đặc trưng/SHAP/LIME, cap hoặc DB thật. Chưa có launcher, endpoint hay nút Start/Stop.

- Mỗi worker dùng thư mục riêng do chủ quản tin cậy chuẩn bị. Chủ ghi atomic `lease.json` (`worker_token`, `monotonic`) và `command.json`; worker ghi atomic `status.json` gồm role, PID thực, thời điểm tạo OS, token, sequence, heartbeat và trạng thái. Token gắn phiên, không phải cơ chế xác thực mạng; thư mục phải có quyền truy cập phù hợp. Lease dùng đồng hồ monotonic cùng máy/lần boot, hết hạn 45 giây hoặc thời gian tương lai bị từ chối.
- Capture lifecycle v3 nhận `action=stop`, dừng nhận rồi flush có kiểm tra; chỉ báo finished với `flushed`, `rows`, `csv_size` sau khi thành công. Lỗi lease/health đi qua cleanup và thoát lỗi, không báo hoàn tất giả. Lỗi khởi tạo có thể chỉ có exit code, chưa có status cuối. Không áp đặt thời lượng 60 giây; chế độ thủ công liên tục vẫn giữ nguyên.
- Feeder nhận `abort` (thoát lỗi, giữ checkpoint) hoặc `drain` với kích thước/số dòng cuối do chủ quản cung cấp sau khi capture đóng file. Chỉ finished khi CSV không đổi kích thước, offset hết file và ACK khớp số dòng; thiếu CSV, dòng cuối dở hoặc lệch ACK đều thất bại. Retry/timeout HTTP và checkpoint hiện có giữ nguyên.
- Heartbeat phát từ vòng xử lý, không có thread riêng giả khỏe. Feeder đang chờ HTTP/backoff có thể chậm heartbeat; supervisor tương lai phải tính cả request timeout/backoff, không dùng lease của chính nó làm bằng chứng worker sống. Status finished không đủ: phía cha còn phải xác minh identity OS, exit code cả hai process và đối soát flush/ACK. Windows venv có thể có launcher PID khác worker PID.

**Kiểm thử:** `python scripts/stage34_test_worker_control.py` **9/9 PASS**: identity/token, lease cũ/tương lai, capture PCAP thật → CSV → feeder process/API ACK fixture, stop khi sniffer fixture đang chạy, abort, CSV rỗng/ACK lệch và dòng dở. `stage34_capture_fixture.py` chỉ thay sniffer bằng nguồn packet tổng hợp, không bắt NIC. Đây là test giao thức, không phải model accuracy hoặc nghiệm thu live. Stage27 **8/8**, Stage33 **12/12**, Stage20 **21/21**, Stage28 **5/5** PASS hồi quy.

**Giới hạn/tiếp theo HT4.3:** registry HT4.1 chưa được nối với các worker này; chưa xác minh worker từ phía supervisor, chưa rollback startup một phần/reconcile sau restart, chưa bảo vệ endpoint điều khiển. Cần hoàn thiện các phần đó và test lỗi riêng trước khi bật UI. Không hướng dẫn người dùng tự dựng file điều khiển để thay workflow đã có. Không bắt Wi-Fi, reset DB, tăng cap hay push trong bước này. Commit: `feat(rq3): add managed worker heartbeat and graceful drain protocol`.

Chạy lặp phát hiện race lease (lấy thời gian trước khi đọc lease vừa gia hạn) và Windows từ chối replace khi reader mở file. Đã lấy thời gian sau read, thêm `write_control` retry PermissionError tối đa 6 lần (tổng chờ 0,3 giây), vẫn ném lỗi nếu kéo dài. Chủ quản tương lai phải dùng helper này cho lease/command. Test bổ sung tái hiện race và retry hữu hạn; lỗi thread gia hạn fixture nay làm test thất bại, không bị bỏ qua.

Hồi quy tích hợp Stage14 sau HT4.2: **PASS toàn bộ** trên DB tạm/model thật, gồm CSV/PCAP qua UI, feeder, SHAP/LIME, phân trang và storage. Không coi các nhãn trong test là FPR.

## HT4.1 — nền tảng trạng thái bền và ownership (18/10/2026)

**Đã triển khai thư viện, CHƯA nối vào API/runtime.** `capture_registry.py` không sinh/kill tiến trình và không bắt mạng. Mục đích: có state machine kiểm thử được trước khi mở endpoint điều khiển. Runtime hiện tại vẫn dùng capture/feeder thủ công như trước, UI chưa có Start/Stop.

- Một registry dùng khóa file OS cho một supervisor; thử tranh khóa từ process thứ hai bị từ chối. SQLite vận hành riêng `sessions.sqlite3` lưu phiên/command ID/trạng thái/định danh worker trong transaction; không thêm bảng vào DB dự đoán 6 bảng.
- Reserve đồng thời: unique active-session + transaction/thread lock chỉ cấp một `start_granted=True`; retry cùng request ID trả phiên cũ với `False`, không được spawn lại. Cùng request ID khác interface bị từ chối. Chưa kiểm tra interface thực/Npcap ở bước này.
- Hai worker capture/feeder có PID + birth token + worker token riêng. Mọi heartbeat/exit phải khớp cả ba, không dùng PID đơn lẻ. **Các giá trị này hiện là fixture đầu vào nội bộ, chưa có OS probe/heartbeat transport thật.** Supervisor tương lai phải tự xác minh, không lấy exit/flush/ACK từ payload người dùng.
- `starting → running` chỉ khi cả hai worker đã ready; yêu cầu stop → `stopping`; capture exit 0 + flush + số dòng đã xuất → `draining`; chỉ completed khi hai worker được reap, code 0 và số dòng CSV bằng ACK feeder. SHAP hoàn tất là thông tin riêng, không điều kiện đồng nghĩa completed.
- Capture/feeder thoát bất thường hoặc thiếu xác nhận → failed, vẫn chặn start mới khi chưa xác nhận cả hai worker đã thoát. Retry stop không chuyển trạng thái lỗi về running. Writer registry lỗi không ghi trạng thái thành công giả.
- Reopen registry có phiên active → `unknown`, giữ dữ liệu cũ và chặn start/heartbeat/finalize. Không tự restart, không tự kill PID. Phiên completed/failed đã đóng giữ lịch sử và không chặn lượt mới. **Đối soát OS để thoát unknown, rollback khởi động dở/cancel trước attach chưa triển khai**; vì thế thư viện chưa được gắn vào API.

Kiểm thử: `python scripts/stage33_test_capture_registry.py` **12/12 PASS** ngày 18/10/2026, dùng registry tạm, không DB thật/capture thật; fixture concurrency, khóa liên-process, restart, PID reuse/token sai, crash, stop lặp, ACK lệch, ghi lỗi và lịch sử completed. Đây không phải nghiệm thu toàn HT4 hoặc test tiến trình Npcap. Không chạy lại model/UI vì chưa có đường import runtime tới thư viện này.

**HT4.2 tiếp theo:** giao thức quản lý worker thật (readiness/heartbeat/stop/flush/drain), định danh PID + thời điểm tạo + token được xác minh, xử lý startup một phần và supervisor restart; test process fixture riêng trước Wi-Fi. Sau đó mới nối API Start/Stop và cuối cùng UI. Endpoint phải kiểm tra nguồn gọi/quyền điều khiển local; khóa registry chỉ bảo vệ phiên do supervisor quản lý, chưa chặn capture terminal chạy ngoài hệ thống.

## UI bước 1 — trực quan hóa trên API sẵn có (18/10/2026)

Mục đích: đọc kết quả nhanh hơn, tách rõ phạm vi dữ liệu và tình trạng toàn hệ thống; không đổi schema, API prediction, model, extractor hoặc XAI. Thêm biểu đồ trạng thái SHAP theo bộ lọc, màu/chú giải Benign–cảnh báo, trục xác suất %, tên IP:cổng/giao thức dễ đọc; phân trang sát bảng có Trước/Sau, reset khi đổi scope và giữ flow khi refresh/chuyển trang. Không đoán capture sống từ API/flow mới, không đổi tỷ lệ cảnh báo thành FPR. Hướng dẫn ở dashboard_usage.md.

HT4 chưa được gộp vào bước này: cần API sở hữu capture + feeder, lưu metadata phiên bền vững, đối soát PID/định danh tiến trình/heartbeat sau restart, chặn start đồng thời và test stop/drain/crash riêng. State trong RAM API không đủ cho restart; Streamlit chỉ giữ lựa chọn hiển thị, không sở hữu PID hoặc sinh process khi render. Chưa thêm nút Start/Stop và chưa thu telemetry chưa có từ backend.

Kiểm thử 18/10: Stage32 **3/3 PASS** (định dạng, dữ liệu thiếu, giới hạn trang); Stage14 **PASS toàn bộ** trên DB tạm/model thật, bổ sung nút Trang sau/trước, trang cuối 205 flow, giữ lựa chọn và reset khi đổi lượt; giữ hồi quy CSV/PCAP/SHAP/LIME/storage. Đã kiểm tra render bằng AppTest, chưa duyệt thủ công nhiều kích thước trình duyệt. Commit: `feat(rq3): improve dashboard overview and flow navigation`.

## HT3.6 — dung lượng, backup và khôi phục an toàn (18/10/2026)

**Mục đích:** quan sát tăng trưởng file và có snapshot SQLite kiểm chứng được, không đổi 6 bảng/model/SHAP/LIME, không tự xóa hoặc thay DB đang dùng.

- API đọc `GET /storage_status`; UI mục **Dung lượng lưu trữ** trong Giám sát flow cập nhật cùng bảng flow. Cảnh báo khi ổ DB còn dưới `storage.warning_free_bytes` (mặc định 1 GiB), không phải quota. Chỉ tính file trực tiếp trong thư mục DB: DB/WAL/SHM (gồm DB backup cũ nếu cùng thư mục), CSV, log, checkpoint, khác; không tính thư mục con/ổ capture khác. Không đọc được hiển thị chưa rõ, không báo còn đủ. Cap dung lượng ổ CSV vẫn là cơ chế riêng.
- Backup dùng SQLite Online Backup API từ connection read-only, lấy dữ liệu đã commit kể cả WAL; không copy thô file DB đang chạy. Kiểm tra `integrity_check`, `foreign_key_check`, 6 bảng, số dòng/model version; ghi SHA-256/kích thước vào manifest hoàn tất. Không bao gồm CSV, checkpoint, log, model hoặc packet RAM. Backup lỗi giữ thư mục dở để chẩn đoán, không có manifest hoàn tất; thử lại bằng tên mới. Có deadline 30s cho bước chuyển trang backup, dự trữ dung lượng 256 MiB; kiểm tra dung lượng không bảo đảm chống ổ đầy do tác vụ khác.
- Verify kiểm tra checksum, integrity, khóa ngoại và metadata; từ chối sidecar WAL/SHM/journal, symlink DB hoặc đường dẫn DB khác `snapshot.db`. Checksum phát hiện hỏng, không phải chữ ký chống kẻ sửa cả DB lẫn manifest.
- Restore chỉ tạo thư mục **mới** chứa `snapshot.db` và manifest; không ghi đè/reset DB thật, không tự chuyển API sang bản phục hồi. Model và code tương thích phải được giữ riêng; manifest chỉ liệt kê model version đã có trong Prediction.
- Không tự backup định kỳ/rotation/retention. Không sao chép CSV/checkpoint/log đang mở. File backup có IP/đặc trưng và lịch sử: chưa mã hóa; lưu nơi có quyền truy cập phù hợp, sao chép bundle hoàn chỉnh ra ổ khác nếu cần chống hỏng ổ. Thư mục `RQ3_IDS_System/backups/` và `restores/` được Git ignore.

### Lệnh vận hành (từ thư mục RQ3_IDS_System)

```powershell
python scripts/manage_storage.py status
python scripts/manage_storage.py backup --bundle backups/manual_01
python scripts/manage_storage.py verify --bundle backups/manual_01
python scripts/manage_storage.py restore --bundle backups/manual_01 --destination restores/manual_01
```

Tên thư mục phải chưa tồn tại; lần sau dùng tên khác. Nguồn mặc định theo `IDS_DB_PATH` nếu có, nếu không theo config.yaml; dùng `--db đường_dẫn` để chỉ rõ nguồn khi backup/status. Backup SQLite có thể chạy khi API hoạt động, nhưng trạng thái snapshot phản ánh thời điểm backup, không bảo đảm cùng thời điểm với CSV/checkpoint.

### Dùng bản phục hồi mà không ghi đè bản cũ

1. Verify bundle; restore sang thư mục mới như trên. Giữ bản backup nguyên vẹn, không chạy API trực tiếp trên backup.
2. Dừng capture an toàn, đợi feeder gửi xong rồi dừng feeder; dừng API cũ trước khi chuyển DB. Không kill để giả lập hoàn tất.
3. Trong terminal chạy API mới, đặt đường dẫn DB phục hồi rồi chạy lệnh API quen thuộc:

```powershell
$env:IDS_DB_PATH = (Resolve-Path restores/manual_01/snapshot.db).Path
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

4. Kiểm tra số flow/lịch sử/model, trạng thái SHAP recovery. API có thể migrate/ghi thêm vào DB phục hồi; đây là bản làm việc, không còn là bundle bất biến để verify theo hash ban đầu. Quay lại DB cũ: dừng API mới, bỏ biến `IDS_DB_PATH` trong terminal rồi khởi động lại; không xóa bản nào.
5. **Không tự dùng lại feeder checkpoint mới hơn snapshot DB**: có thể bỏ qua flow DB chưa có. Phát lại toàn bộ CSV bằng checkpoint mới cũng có thể tạo bản trùng; cần đối soát idempotency key/offset riêng trước replay. Để bắt traffic mới, dùng CSV/lượt mới. Backup DB không hứa phục hồi packet chưa xuất, không phải snapshot nguyên khối toàn pipeline.

### Kiểm thử

`python scripts/stage31_test_storage.py`: DB tạm, WAL đang mở/giao dịch chưa commit, giữ ingestion key/trạng thái XAI, restore mới, từ chối ghi đè/checksum hỏng/sidecar/manifest sai/DB không đúng schema/khóa ngoại lỗi/dung lượng thấp/deadline; kiểm tra CSV/checkpoint không bị sửa. Stage14 bổ sung API và UI dung lượng bình thường/thấp/không đọc được; chạy cùng hồi quy model/CSV/PCAP/LIME trên DB tạm. Không chạy backup hoặc restore trên DB người dùng trong đợt triển khai.

**Kết quả 18/10/2026:** Stage31 **8/8 PASS**; Stage14 **PASS toàn bộ**, gồm API/Streamlit AppTest ba trạng thái storage, upload CSV, trích PCAP, model thật, SHAP nền, LIME validity, chọn flow và chống gửi lặp. CLI status chạy chỉ đọc: ổ DB còn khoảng 28,7 GiB tại lần kiểm tra, 34 file trực tiếp, không lỗi scan. Số dung lượng là snapshot, không phải mức cố định. Lượt test đầu vướng fixture chưa đóng connection SQLite trên Windows; đã đóng rõ ràng và chạy lại đạt, không sửa dữ liệu thật. Commit triển khai: `feat(rq3): add verified SQLite backups and storage visibility`. Không thêm MD mới; chưa triển khai retention xóa tự động hoặc backup toàn pipeline.

## HT3.5 — giảm bộ nhớ packet (18/10/2026)

Mục đích: không giữ payload/Scapy graph trong flow chờ xuất. V3 lưu bản ghi gọn sau khi xử lý bulk/window/TCP trên packet gốc; không thay model, 78 đặc trưng, lifecycle, queue hoặc giới hạn mặc định. `buffered_packet_bytes` vẫn là tổng frame byte logic chưa xuất, không phải RAM thực cấp phát. Đây vẫn là O(số packet), không phải thống kê O(1); bản tối ưu vẫn có thể chạm cap 20000 mặc định ở cùng tải.

Stage30 trên hai PCAP: CSV, 78 cột sau chuẩn hóa và mọi nhãn/xác suất model khớp chính xác (99 flow/1.148 packet). Đo tracemalloc với cùng 1.000 packet payload 1.200 byte: retained 5.635.553 → 370.351 byte (~93,4% giảm), peak 5.816.954 → 829.198 byte. Không so thành RSS hoặc tốc độ thực. Bằng chứng đầy đủ `packet_record_validation_20261018.json`. Stage20/26/28/29 lần lượt 21/22/5/6 test PASS. Bộ test dùng DB/file tạm, không sửa lịch sử demo.

Smoke live đầu (`packet_record_live_20261018.json`) FAIL do WinError 5 khi thay file báo cáo JSON nguyên tử, chưa hoàn tất capture/đối soát. Không gọi là lỗi model hay PASS. Harness Stage22 thêm tối đa 10 lần đợi 100ms cho PermissionError, vẫn thay file nguyên tử, lỗi kéo dài vẫn báo FAIL; kiểm thử giả lập lỗi nhất thời và lỗi kéo dài đều đạt. Không áp dụng retry này vào writer CSV của hệ thống. Đã kiểm tra không còn python.exe trước khi chạy lại smoke.

Chạy lại từ SELF_KLTN (truyền đường dẫn Python chính đã cài model, không dùng Python venv capture cho worker model):

```powershell
$modelPython = (Get-Command python).Source
RQ3_IDS_System/.venv_capture/Scripts/python.exe RQ3_IDS_System/scripts/stage30_test_packet_records.py RQ3_IDS_System/docs/packet_record_validation_NEW.json $modelPython
```

Áp dụng: dừng capture hiện tại an toàn, đợi feeder gửi hết rồi bắt lượt CSV mới bằng lệnh cũ. Không cần reset DB/train model hoặc thay lệnh UI PCAP. Giữ v3 vì ngữ nghĩa không đổi; commit Git phân biệt triển khai lưu trữ. Không tự tăng cap, không tuyên bố giảm FPR. Lượt soak 20 phút HT3.4 là trước tối ưu; cần kiểm chứng dài hơn cho bản mới.

Smoke chạy lại 120 giây PASS (`packet_record_live_retry_20261018.json`): capture process 122,58s, 9.352 packet nhận/xuất/CSV khớp, 193 flow CSV/API khớp, 105 flow tới API khi còn sniff. SHAP 41/41, queue/dropped/recovery=0, feeder không lỗi, metadata IP/version/78 đặc trưng/15 xác suất/đổi duration và Streamlit AppTest đạt. Peak RSS capture lấy mẫu 137.531.392 byte (~131,2 MiB), peak buffered packets 4.682, cuối lượt byte=0. Dùng cap thử 50.000/64 MiB; không so trực tiếp RSS với soak cũ vì tải và thời lượng khác. Nhãn 152 Benign/41 Hulk chỉ là dự đoán, không phải FPR. Script exit 0 và tiến trình được dọn. Kiểm tra weakref cũng xác nhận packet Scapy gốc được giải phóng sau constructor và add_packet.

## HT3.3 — giới hạn tài nguyên và phục hồi công bằng (18/10/2026)

**Mục đích:** chặn bộ đệm tăng vô hạn, báo quá tải rõ ràng, tránh bỏ đói tác vụ SHAP cần phục hồi. Commit: `feat(rq3): bound capture resources and schedule SHAP recovery`.

Mặc định v3, đổi qua CLI, không nhận 0/unlimited:

| Tham số | Mặc định | Ý nghĩa |
|---|---:|---|
| `--max-open-flows` | 4096 | Flow đang giữ, không phải tổng flow cả lượt |
| `--max-buffered-packets` | 20000 | Packet chưa xuất |
| `--max-buffered-bytes` | 33554432 | Byte packet đang giữ, **không phải RSS** của Python |
| `--min-free-disk-bytes` | 268435456 | Ngưỡng 256 MiB trống trên ổ CSV; kiểm tra trước export, cache tối đa 1 giây |

Đạt giới hạn buffer: từ chối packet kích hoạt trước admission, dừng với exit code lỗi, flush phần đã nhận nếu writer còn an toàn. Không chia flow âm thầm để né cap, không báo phiên đầy đủ. CLI in `limit_rejected`, `peak_open_flows`, `peak_buffered_packets`, `buffered_packet_bytes`. Traffic sau khi dừng không có trong CSV. UI PCAP coi exit lỗi là trích xuất thất bại, không gửi CSV thiếu. V1/v2/legacy không có cap v3.

Thiếu dung lượng hoặc writer lỗi: không retry ghi mù, không tự xóa lịch sử, không khẳng định flush thành công. Kiểm tra disk không bảo đảm chống mọi lỗi đầy ổ do tiến trình khác ghi đồng thời. CSV/DB vẫn tăng theo dữ liệu: chưa tự rotation/retention hoặc backup; cần theo dõi dung lượng, chọn lượt CSV mới. Packet RAM chưa xuất không được bảo đảm phục hồi sau kill/mất điện.

SHAP giữ 200 tác vụ chờ + tối đa 1 đang xử lý. Đầy queue chỉ bỏ giải thích mới, giữ Prediction/Alert. Cấu hình maxsize <=0 bị từ chối. Sau 10 tác vụ RAM, worker kiểm tra một tác vụ recovery; khi queue trống cũng kiểm tra recovery. Công bằng theo số tác vụ, không phải cam kết độ trễ theo giây.

**Kiểm thử:** Stage27 8/8, Stage28 5/5, Stage29 5 fixture PASS và fixture low-disk bổ sung PASS riêng (tổng 6); Stage26 22/22. Stage24 restart/mất ACK/rollback/chống trùng/recovery PASS; Stage14 API/UI với model thật và DB tạm PASS trong lượt HT3. Tải tổng hợp Stage29: 50 lần drain, nhận/xuất 3.200/3.200 packet, peak buffer 64, buffer rỗng sau mỗi drain; 125,169s với tracemalloc, peak cấp phát Python 10.042.600 byte. Không dùng đây làm throughput hoặc RSS thực tế. Cap là mức bảo vệ ban đầu, chưa tuning bằng Wi-Fi dài hạn.

Lệnh từ thư mục `RQ3_IDS_System`:

```powershell
python scripts\stage27_test_feeder_faults.py
python scripts\stage28_test_capture_health.py
.\.venv_capture\Scripts\python.exe scripts\stage29_test_capture_limits.py
python scripts\stage24_test_ingestion_recovery.py
```

Restart API để áp dụng scheduler; dừng/flush capture cũ rồi dùng lượt CSV mới để áp dụng cap. Không reset DB/xóa checkpoint. Chưa đóng nghiệm thu live dài hạn/RSS/CPU/tốc độ, retention/backup và độ bền packet RAM; không tuyên bố production-ready.

## HT3.1 — xác nhận giao nhận (18/10/2026)

### HT3.2 — lỗi nền capture không được giả thành thành công

Mục đích: chuyển lỗi GC/writer/callback về luồng điều khiển, kể cả khi Scapy bắt và chỉ log exception. Project capture dùng GC có trạng thái lỗi và callback bảo vệ; yêu cầu dừng capture khi lỗi, kiểm tra GC đã kết thúc trước flush, chỉ in “Đã dừng an toàn” khi toàn bộ quá trình thành công. Nếu lỗi ghi có thể để lại CSV dở, không tự retry/flush vì có nguy cơ nhân đôi hoặc nối sai dòng. Giữ file để kiểm tra, không tự xóa/ghi đè. Packet chưa xuất còn trong RAM **không được bảo đảm phục hồi sau kill/mất điện**; muốn phục hồi cần PCAP nguồn hoặc thiết kế spool riêng. Không gọi đây là exactly-once capture.

Stage28 4/4 PASS: lỗi GC, lỗi callback, GC không dừng, dừng bình thường. Stage20 21/21 PASS gồm signal/flush; Stage24 PASS API restart, checkpoint, mất ACK, SHAP recovery. Legacy vẫn có GC upstream, không được chứng nhận có cùng bảo vệ lỗi nền. Commit: `fix(rq3): propagate capture background failures safely`.

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

### HT3.4 — thử thụ động 20 phút, ngày 18/10/2026

Lượt đầu chạm cap 20.000 packet sau khoảng 2 phút, không đạt nghiệm thu. RSS capture đo cao nhất khoảng 286 MiB. Nhận/xuất 29.160 packet, CSV 176 flow; chưa đối soát API cuối lượt. Bằng chứng: `live_20min_ht3_20261018.json`. Không tính FPR từ các nhãn chưa có ground truth.

Lượt tiếp dùng cap thử riêng 50.000 packet / 64 MiB packet bytes, không đổi mặc định. Stage22 dùng DB tạm, theo dõi RSS/CPU/queue và đối soát packet/flow/metadata/UI. Chạm cap vẫn kiểm tra CSV đã flush nhưng toàn bài FAIL. Chạy từ SELF_KLTN:

```powershell
python -u RQ3_IDS_System/scripts/stage22_test_live_pipeline.py --interface Wi-Fi --seconds 1200 --max-buffered-packets 50000 --max-buffered-bytes 67108864 --output RQ3_IDS_System/docs/live_20min_ht3_retry_20261018.json
```

Không ghi đè output cũ, không xóa DB demo. JSON chỉ lưu số liệu tổng hợp; CSV/DB thô tạm được dọn sau test. Cap byte không giới hạn RSS của đối tượng Scapy. Thành công 20 phút chưa chứng nhận chạy nhiều giờ hoặc không mất gói tại NIC.

**Kết quả lượt thử lại: PASS**, bằng chứng `live_20min_ht3_retry_20261018.json`. Capture process chạy 1.202,61 giây với yêu cầu sniff 1.200 giây; cả lượt gồm khởi động, drain và kiểm tra khoảng 20 phút 39,5 giây. Exit 0, không chạm cap; đã xác nhận không còn python.exe sau test.

- Packet nhận = xuất = tổng CSV: 176.425; flow CSV = API: 1.225; 1.142 flow tới API khi còn sniff.
- SHAP xử lý 251/251, hàng đợi 0/200, dropped=0, recovery_pending=0; feeder_error_count=0.
- Đủ 78 đặc trưng, 15 xác suất; metadata IP/version và đổi đơn vị duration đạt; Dashboard Streamlit AppTest đạt (không thay thế thao tác trình duyệt thủ công).
- Peak RSS trong các mẫu: capture 522,9 MiB, API 463,1 MiB, feeder 97,7 MiB. CPU tích lũy cao nhất quan sát: capture 124,55 giây CPU, API 1.300,67, feeder 7,80; đây không phải phần trăm CPU hay toàn bộ CPU giai đoạn drain. Mẫu cuối ở 1.194,3 giây; RSS giữa các lần lấy mẫu có thể cao hơn.
- Peak open flows=113; peak buffered packets=48.495/50.000 (96,99%); limit_rejected=0, buffered_packet_bytes cuối=0. Dư địa còn thấp, không nâng mặc định hoặc bỏ giới hạn dựa vào một lượt PASS.
- Nhãn model: 974 Benign, 250 Hulk, 1 Infilteration; chưa có ground truth nên không quy thành FPR/độ chính xác hoặc xác nhận tấn công.

Mục tiêu kiểm thử đã đạt trong tải quan sát này, không đóng toàn bộ HT3. Bước tiếp theo cần đánh giá cách giảm lưu packet trong RAM/dư địa bộ đệm mà giữ đúng định nghĩa đặc trưng, rồi kiểm thử hồi quy và tải dài; retention/backup và hard-kill vẫn là giới hạn mở. Không đổi model/RQ1/RQ2, không ảnh hưởng DB demo.

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
