# Vận hành, phục hồi và kiểm thử RQ3

Tài liệu hợp nhất ngày 16/10/2026. Chỉ còn 5 tài liệu RQ3 chính: [kiến trúc và kế hoạch](plan.md), [chạy và đọc UI](dashboard_usage.md), [vận hành](operations.md), [kiểm chứng XAI](xai_validation.md), [tương thích đặc trưng](feature_compatibility.md).

> Trạng thái hiện hành: capture project v2; feeder checkpoint/chống gửi trùng; SHAP queue 200 và phục hồi sau restart. Giữ XGBoost/78 đặc trưng, cấu hình LIME RQ2 và nhánh A/B. Các mục audit/nhật ký bên dưới giữ số liệu của phiên bản được ghi tại thời điểm kiểm thử, không phải mọi nhận định đều mô tả bản hiện tại. Chưa chứng nhận tương thích đầy đủ train–PCAP; nhãn live chưa phải ground truth.

- [Capture v2, phục hồi và kiểm thử](#stability-v2)

## Áp dụng trên máy người dùng — 16/10/2026

### Sửa capture không phản hồi Ctrl+C

Phiên live chờ `sniffer.join()` vô hạn trong main thread; đây là điểm có thể trì hoãn xử lý Ctrl+C trong môi trường Windows/Python đang dùng. Đã thay bằng vòng chờ ngắn 0,1 giây, handler SIGINT/SIGBREAK chỉ yêu cầu dừng, `stop(join=False)` rồi đợi thread kết thúc trước khi flush CSV. Handler giữ trong lúc cleanup để Ctrl+C lặp không ngắt giữa chừng. Chờ shutdown tối đa 15 giây; nếu thread vẫn chạy thì báo lỗi, không giả định đã dừng an toàn hoặc flush đồng thời với thread.

Giữ nguyên công thức feature, extractor version v2, timeout flow 90s/240s và model/XAI. Stage20 hiện PASS 15 test, gồm tín hiệu phát bằng `signal.raise_signal`, hẹn giờ, lỗi sniffer, khôi phục handler và CLI PCAP thật; chưa phải kiểm thử end-to-end phím Ctrl+C trong mọi phiên terminal VS Code/Npcap. Bản sửa chỉ có hiệu lực khi khởi chạy capture mới.

Để test ngắn có thời hạn:

```powershell
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --interface "Wi-Fi" --output data\live_manual_02.csv --seconds 60
```

Chạy feeder theo đúng CSV đó. Nếu tên đã dùng, đổi tên ở cả capture và feeder. Đợi capture báo `receiving_stopped` và ghi nốt flow; đợi feeder gửi hết trước khi dừng feeder. Không đóng cưỡng bức terminal trừ khi chấp nhận mất flow chưa xuất.

- Bật API tại `127.0.0.1:8000` và Streamlit tại `127.0.0.1:8501`; health xác nhận model `52eb5a671ee82109`, 78 đặc trưng, 15 lớp, idempotency và queue 200. Không chạy thêm API cùng DB.
- Không reset DB, không gửi thêm flow và không tự bật capture. DB hiện có 176 flow/88 cảnh báo; worker tự tiếp tục các SHAP bị ngắt theo cơ chế phục hồi v2. Việc cập nhật giải thích không phải tạo thêm traffic.
- Có bản sao SQLite nhất quán `data/ids_system_backup_ui_20261016_112528.db`, không đưa vào Git. Bản sao được tạo sau lúc API khởi động (lần sao lưu trước bị quyền sandbox chặn), vì vậy có thể đã chứa một phần trạng thái SHAP được phục hồi.
- UI được mở và kiểm tra trên trình duyệt: thấy ba tab, dữ liệu lịch sử/biểu đồ và hướng dẫn live. Kiểm thử tự động Stage14 dùng DB tạm, không nạp fixture vào DB này. Đây chưa phải nghiệm thu mọi kích thước màn hình hoặc điều khiển capture trực tiếp.
- Stage14 sau thay UI PASS, gồm assertion ba tab/lệnh capture, regression CSV/PCAP, chọn flow và LIME. Kiểm tra liên kết tới file cục bộ của năm tài liệu PASS. Sau startup, 50 tác vụ SHAP được phục hồi hoàn tất, backlog về 0; không tự thử lại các việc đã dropped.
- Hai dịch vụ được bật nền để xem lại. Muốn chuyển sang chạy terminal VS Code, dừng đúng hai tiến trình này trước; không dừng toàn bộ Python. PID của phiên mở này: API `17032`, UI `45184` (phải xác minh command line trước khi dừng; PID có thể được tái sử dụng về sau).

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
