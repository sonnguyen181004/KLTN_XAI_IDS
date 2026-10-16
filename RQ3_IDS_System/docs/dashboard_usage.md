# Dashboard IDS mới — 16/10/2026

## Chạy trong VS Code

**Bản hiện hành:** capture mặc định `rq3-cfm-0.5.0-fixes-v2`, feeder có checkpoint/chống gửi trùng, SHAP có phục hồi sau restart. Xem [hướng dẫn nâng cấp và kết quả](stability_update_20261016.md). Restart API/UI và dùng CSV mới cho phiên nâng cấp. Timeout vẫn duration 90 giây/idle 240 giây hoặc flush lúc dừng; chưa chứng nhận tương thích đầy đủ train/V3.

Không cần xóa DB hoặc file dữ liệu cũ. Bản cập nhật không đổi model, luật dự đoán hay luật nhánh A/B.
Nếu API/Streamlit cũ đang chạy, dùng Ctrl+C trong đúng terminal của từng tiến trình rồi chạy lại.
Không cần dừng bộ bắt traffic chỉ để cập nhật màn hình. Feeder cùng checkpoint tiếp tục cùng lượt sau restart; muốn lượt mới phải dùng CSV/checkpoint mới.

Tất cả terminal dưới đây đặt tại thư mục `C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System`.

Terminal 1 — API (Python đã cài requirements):

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — giao diện:

```powershell
python -m streamlit run app/dashboard.py
```

Mở http://localhost:8501. Khi cần cài đủ thư viện: `python -m pip install -r requirements.txt`.
Lần API mới khởi động sẽ tự thêm cột và index vào DB hiện có; không xóa bản ghi cũ.

## Một lượt live mới, tránh trộn dữ liệu cũ

### Giới hạn hàng đợi SHAP

Cập nhật 16/10/2026: `api.max_explain_queue` tăng từ 50 lên **200 tác vụ chờ**, ngoài tác vụ worker đang xử lý. Khởi động lại API để áp dụng; dashboard đọc giới hạn từ `/explain_queue_status`, nên sẽ hiện `…/200` sau khi API mới lên.

Đây không phải giới hạn số flow được bắt, dự đoán hoặc lịch sử. Đầy queue thì SHAP mới bị bỏ (`dropped_queue_full`), prediction/alert vẫn còn. Việc đang chờ bị ngắt do restart được khôi phục dần từ DB; việc đã dropped/failed không tự retry. Backlog DB hiển thị riêng với queue RAM 200. Chạy một API process cho mỗi DB. Bảng vẫn 50 flow/trang; tăng queue không làm SHAP tính nhanh hơn, chưa đo tải để kết luận 200 tối ưu.

Terminal 3, quyền Administrator nếu môi trường bắt gói yêu cầu. Đổi tên file cho **mỗi lần demo**:

```powershell
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --interface "Wi-Fi" --output data\live_ui_01.csv
```

Terminal 4:

```powershell
python app\feeder.py --watch data\live_ui_01.csv --convert-units --capture-timezone +07:00
```

Tên Wi-Fi phải đúng interface trên máy. Feeder mặc định lấy múi giờ máy; tham số +07:00 chỉ đúng nếu timestamp CSV là giờ Việt Nam/Thái Lan.
Feeder sinh `capture_run_id` và lưu trong `<CSV>.feeder-state.json`. Khởi động lại cùng lệnh **tiếp tục cùng lượt từ dòng đã được xác nhận**, không tự gửi lại từ đầu. Giữ checkpoint khi tiếp tục; chọn `--checkpoint` mới nếu chủ động phát lại toàn bộ. File CSV phải chỉ append, không ghi đè khi đang theo dõi. CSV tải lên/PCAP phát lại trên UI vẫn có mã lượt riêng mỗi lần gửi.

## Đọc màn hình

### LIME và đối chứng đặc trưng (bổ sung)

**Cách đọc mới:** ngay dưới biểu đồ SHAP/LIME có “Đọc từng đặc trưng bằng lời”. Mở một mục để xem tên tiếng Việt, ý nghĩa, giá trị flow và hướng tác động tới lớp đang giải thích. Tab Đối chứng ưu tiên tra cứu một đặc trưng; bảng thống kê và chẩn đoán được thu gọn. Xem [hướng dẫn đọc SHAP/LIME](reading_shap_lime.md).

Sau cập nhật, khởi động lại API và Streamlit. Không cần xóa DB hoặc upload lại PCAP chỉ để xem đối chứng.
Chọn flow → **LIME theo yêu cầu** → **Yêu cầu / kiểm tra lại LIME** để bổ sung chẩn đoán cho kết quả cũ.
Nếu LIME suy biến, UI hiện cảnh báo thay vì biểu đồ toàn số 0 và R²=1 gây hiểu nhầm. Chạy lại cùng dữ liệu/config không đảm bảo hết suy biến.

Tab **Đối chứng đặc trưng**: chọn tên đặc trưng để đọc giải nghĩa và giá trị, ưu tiên tên xuất hiện trong SHAP/LIME. Mở “So sánh số liệu tham chiếu” để xem P05/median/P95 của nền LIME, Benign và lớp dự đoán kèm cỡ mẫu. “Tra cứu toàn bộ 78 đặc trưng” và “Chẩn đoán lệch mẫu nền” nằm trong phần mở rộng. Bảng chẩn đoán xếp theo lệch mẫu nền, **không phải thứ hạng SHAP**. Mẫu theo lớp lấy từ tập B nhỏ, không đại diện toàn bộ lớp hay chứng minh tấn công.

Chi tiết nguyên nhân và giới hạn: [LIME validity và đối chứng](lime_validity_and_comparison.md).

**Cập nhật audit đặc trưng:** [audit trước sửa](feature_compatibility_audit_20261016.md) ghi nhận lỗi Python extractor; adapter v1 đã sửa 5 lỗi kiểm chứng được, còn quy ước khác train chưa xác minh đầy đủ. UI có đủ kết quả hoặc SHAP cộng đúng không chứng nhận mọi đặc trưng PCAP tương thích dataset V3.

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

Đây là kiểm thử chức năng, không phải đánh giá lại accuracy hay xác nhận traffic tấn công. Sau bản capture v1 đã kiểm tra Wi-Fi thật 20s/100s qua feeder/API và AppTest UI trên DB tạm: phiên 100s có 88 flow lên trong lúc vẫn bắt. Xem [báo cáo capture v1](capture_adapter_v1.md). Chưa nghiệm thu thao tác chuột trên trình duyệt thật với phiên Wi-Fi này; AppTest xác minh trạng thái render và dữ liệu, không thay kiểm tra trực quan đầy đủ.

Bản v2 đã kiểm tra lại Wi-Fi 20s/100s sau sửa CSV Windows: lần lượt 48/48 và 150/150 flow từ CSV tới API; phiên 100s có 44.156 packet được adapter nhận và xuất đủ, 27 SHAP hoàn tất, không bỏ do queue. Phép đo mới tách rõ **5 flow tới khi còn sniff** với **140 flow tới trước khi tiến trình thoát**, vì giai đoạn flush cũng xảy ra trước khi thoát. Không dùng số trước khi tiến trình thoát để khẳng định tất cả đã được dự đoán trong lúc sniff. Chi tiết, checkpoint và test restart: [cập nhật độ ổn định v2](stability_update_20261016.md).

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
