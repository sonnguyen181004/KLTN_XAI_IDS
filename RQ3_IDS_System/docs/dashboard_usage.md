# Hướng dẫn chạy và đọc giao diện IDS

Tài liệu hợp nhất ngày 16/10/2026. Chỉ còn 5 tài liệu RQ3 chính: [kiến trúc và kế hoạch](plan.md), [chạy và đọc UI](dashboard_usage.md), [vận hành](operations.md), [kiểm chứng XAI](xai_validation.md), [tương thích đặc trưng](feature_compatibility.md).

> Trạng thái hiện hành: capture project v2; feeder checkpoint/chống gửi trùng; SHAP queue 200 và phục hồi sau restart. Giữ XGBoost/78 đặc trưng, cấu hình LIME RQ2 và nhánh A/B. Các mục audit/nhật ký bên dưới giữ số liệu của phiên bản được ghi tại thời điểm kiểm thử, không phải mọi nhận định đều mô tả bản hiện tại. Chưa chứng nhận tương thích đầy đủ train–PCAP; nhãn live chưa phải ground truth.

## Bắt đầu ở đây

UI gồm **Giám sát flow**, **Hướng dẫn live**, **Nạp CSV / PCAP**. Tab Hướng dẫn live chỉ cung cấp các bước/lệnh terminal; chưa điều khiển start/stop capture. Giám sát vẫn dùng chung cho cả ba nguồn, chọn Nguồn và Lượt dữ liệu ở sidebar để không trộn phiên. Chọn một flow để xem xác suất, SHAP, LIME theo yêu cầu, đối chứng đặc trưng và timing.

Chạy hai lệnh API/UI bên dưới từ thư mục RQ3_IDS_System, mở http://127.0.0.1:8501. Muốn xem lại PCAP: Nạp CSV / PCAP → Phát lại PCAP → chọn file → trích xuất/gửi → Giám sát flow. Không cần reset DB. Muốn live: mở Hướng dẫn live và dùng CSV mới. Model/luật cảnh báo không thay đổi theo tab.

- [Chạy và đọc UI](#run-ui)
- [Hiểu tên đặc trưng và SHAP/LIME](#read-xai)

---

<a id="run-ui"></a>

# Dashboard IDS mới — 16/10/2026

## Chạy trong VS Code

**Bản hiện hành:** capture mặc định `rq3-cfm-0.5.0-fixes-v2`, feeder có checkpoint/chống gửi trùng, SHAP có phục hồi sau restart. Xem [hướng dẫn nâng cấp và kết quả](operations.md#stability-v2). Restart API/UI và dùng CSV mới cho phiên nâng cấp. Timeout vẫn duration 90 giây/idle 240 giây hoặc flush lúc dừng; chưa chứng nhận tương thích đầy đủ train/V3.

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
- `CWE Flag Count` trong dataset liên quan CWR, nhưng extractor Python 0.5.0 hiện sao chép Fwd URG Flags vào cột xuất tương ứng. UI cảnh báo để không diễn giải nhầm thành phép đếm CWR độc lập.
- Cách tính đặc trưng/cờ live có thể khác dataset; bản này không sửa extractor hay đánh giá lại khả năng tổng quát hóa model.

## 5. Kiểm thử và chạy lại

```powershell
python -B RQ3_IDS_System/scripts/stage16_test_feature_help.py
python -B RQ3_IDS_System/scripts/stage15_test_lime_validity.py
python -B RQ3_IDS_System/scripts/stage14_test_dashboard_redesign.py
```

Stage16 kiểm tra đủ 78 tên/đơn vị, định dạng số và hướng diễn giải; Stage15 kiểm tra LIME số học; Stage14 kiểm tra API/UI, chọn FIN để tra cứu, trạng thái LIME lỗi, CSV/PCAP trên DB tạm. Không cần reset DB để dùng UI mới. Khởi động lại API và Streamlit sau cập nhật; tự-refresh không tự chạy lại LIME.
