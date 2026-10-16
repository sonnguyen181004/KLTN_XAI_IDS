# Kế hoạch cải thiện Dashboard IDS RQ3

Trạng thái: **đã triển khai dashboard mới và PASS test cô lập; chờ nghiệm thu một lượt Wi-Fi live trên máy người dùng**. Cập nhật: 16/10/2026 (Asia/Bangkok).

Mục tiêu: khi bắt traffic thật, người xem nhận ra ngay flow nào thuộc lượt bắt hiện tại, thấy kết quả dự đoán mới mà không phải bấm F5, và chọn **bất kỳ flow nào** để xem đủ thông tin phù hợp với kiến trúc IDS có giải thích.

## 1. Nguồn thiết kế và nguyên tắc không được đổi

- Nguồn: `Kiến trúc hệ thống IDS.docx`, đặc biệt **Khối 7 — Bảng điều khiển cho analyst** và **Mô hình logic hợp nhất** (mục này được tài liệu chỉ định ưu tiên khi các phần cũ khác nhau); `RQ3_IDS_System/docs/plan.md`; code hiện tại trong `app/`.
- Một flow hợp lệ được chuẩn hóa thành đúng 78 đặc trưng rồi XGBoost trả xác suất 15 lớp. Metadata như IP, cổng, nguồn và lượt bắt **không** được đưa thêm vào 78 đặc trưng hoặc thay model RQ1.
- Nhãn khác Benign tạo cảnh báo ngay. SHAP tự động chạy nền cho cảnh báo; LIME chỉ chạy khi analyst bấm yêu cầu. Flow Benign vẫn xem được dự đoán nhưng không có SHAP/LIME mặc định.
- Nhánh A/B chỉ thay cách hiển thị và lời nhắc; không sửa nhãn, không xóa/ẩn cảnh báo. Theo mô hình logic hợp nhất, luật A/B hiện chỉ dựa vào cờ môi trường và cờ lớp hiếm. Agreement/faithfulness không tự trở thành ngưỡng quyết định.
- Dashboard chỉ truy cập dữ liệu qua API. Không đọc SQLite trực tiếp từ Streamlit.
- Đồ thị SHAP và LIME giữ dấu, nhưng phải tách tab/trục vì SHAP hiện giải thích raw margin, LIME giải thích xác suất. Không diễn giải hai độ lớn là cùng đơn vị.
- `faithfulness_proxy_drop` chỉ là proxy nhanh; cờ môi trường chỉ là dấu hiệu cần xem xét. Nhãn dự đoán và xác suất không phải nhãn thật hay bằng chứng tấn công đã xác nhận.

## 2. Vấn đề đã thấy khi test ngày 16/10/2026

| Hiện tượng | Nguyên nhân trong code hiện tại | Hướng xử lý |
|---|---|---|
| Flow mới khó thấy, phải bấm F5 | Dashboard chỉ gọi `/flows` và `/alerts` khi Streamlit chạy lại; feeder cập nhật DB nhưng không kích hoạt trang | Làm mới vùng giám sát theo chu kỳ, có nút tạm dừng |
| Dữ liệu nhiều lần test trộn lẫn | `FlowRecord` có `source` nhưng chưa có mã lượt bắt; DB giữ dữ liệu cũ | Gắn `capture_run_id` cho flow mới, mặc định xem lượt hiện tại; có lựa chọn xem lịch sử |
| Bảng dài, muốn xem flow phải tìm cảnh báo trong dropdown | Chi tiết hiện chỉ chọn `AlertRecord`; Benign không có trang chi tiết | Chọn trực tiếp một dòng ở bảng mọi flow và mở panel chi tiết qua `flow_id` |
| Giờ `07:21` đứng cạnh `00:23+00:00` gây nhầm | Thời gian gốc CICFlowMeter không có múi giờ, còn `received_at` là UTC; UI in ISO thô | Chuẩn hóa mốc giờ, hiển thị giờ Việt Nam và giải thích từng mốc |
| Thứ tự mới/cũ có thể khó hiểu | SQL `ORDER BY COALESCE(flow_timestamp, received_at)` đang so chuỗi local không múi giờ với UTC | Danh sách live xếp theo lúc hệ thống nhận; thời gian gốc là cột riêng và có chế độ xem theo mốc gốc |
| Không thấy IP nguồn/đích trong chi tiết | Feeder bỏ cột chuỗi `src_ip`/`dst_ip` khi tạo payload số; DB chưa lưu metadata này | Truyền/lưu metadata riêng, giữ nguyên đầu vào model |
| Nhiều cảnh báo Hulk giống nhau làm ngập bảng | Dashboard hiện từng Alert; `group_key` hiện chỉ dùng nhãn dự đoán | Gom **cách hiển thị** theo lượt bắt + cặp IP/cổng + lớp và khoảng thời gian; luôn mở ra được từng cảnh báo |
| Có packet nhưng chưa có dự đoán | CICFlowMeter chỉ xuất flow khi đóng/hết hạn hoặc lúc dừng bắt để `flush_flows()` | Hiển thị trạng thái “đang bắt, chưa có flow hoàn tất”; không hứa dự đoán theo từng packet |

Ảnh test cho thấy flow có `source=feeder_live`, `flow_timestamp` khoảng **07:21**, còn lúc hệ thống xử lý `00:23+00:00` tương ứng khoảng **07:23 GMT+7**. Sự khác biệt định dạng này dễ làm dữ liệu mới trông như dữ liệu cũ. Cần kiểm tra thêm liệu `timestamp` của CICFlowMeter là thời điểm bắt đầu flow hay mốc nào trước khi đổi nhãn cột trong UI.

## 3. Màn hình đề xuất

### 3.1. Tổng quan live

1. Thanh đầu trang: trạng thái API/model; thời điểm **flow cuối được API nhận**; hàng đợi SHAP, số tác vụ bị bỏ; tên lượt bắt đang xem. Nếu không có flow mới, hiển thị “chưa có flow hoàn tất” thay vì suy đoán bộ bắt đã dừng.
2. Bộ lọc gọn: `Lượt hiện tại / Lịch sử`, nguồn (`feeder_live`, CSV, PCAP), thời gian, Benign/cảnh báo, lớp dự đoán, nhánh A/B. Mặc định lượt hiện tại và mới nhất trước.
3. Thẻ chỉ số cho lượt/bộ lọc đang chọn: số flow, Benign, cảnh báo, SHAP chờ/xong/bị bỏ. Mọi số phải ghi rõ mẫu số và phạm vi.
4. Biểu đồ tổng quan: số flow theo phút; Benign so với cảnh báo theo thời gian; số cảnh báo theo lớp. Đây là **số dự đoán**, không phải số vụ tấn công đã được kiểm chứng.
5. Bảng flow chính: giờ Việt Nam, nguồn/lượt bắt, IP/cổng nếu có, nhãn, xác suất lớp thắng, trạng thái cảnh báo/XAI. Cột dài/ít dùng nằm trong chi tiết. Một cú chọn dòng mở chi tiết bên cạnh hoặc ngay dưới bảng.
6. Khu nạp CSV/PCAP chuyển vào tab riêng để không chiếm phần đầu màn hình giám sát live.
7. Vùng bảng và chỉ số tự làm mới khoảng 3–5 giây/lần. Có `Tạm dừng làm mới` khi analyst đang đọc chi tiết; bộ lọc và flow đang chọn không bị nhảy. Không tự gửi lại file hoặc tự gọi LIME khi trang làm mới.

### 3.2. Chi tiết một flow được chọn

| Khu vực | Nội dung |
|---|---|
| Nhận diện | Flow ID đầy đủ, lượt bắt, nguồn, IP nguồn/đích, cổng, protocol, thời lượng nếu có; thiếu dữ liệu thì ghi “nguồn không cung cấp” |
| Thời gian | Mốc traffic gốc, lúc API nhận, lúc dự đoán, lúc SHAP hoàn tất nếu có; một định dạng `dd/MM/yyyy HH:mm:ss` GMT+7, có thể mở mốc UTC/raw |
| Dự đoán | Nhãn thắng và xác suất; biểu đồ xác suất 15 lớp (hoặc Top-5 và nút mở đủ 15); phiên bản model; nhãn thật chỉ hiện khi nguồn có cung cấp |
| Benign | Ghi “Đã lưu dự đoán bình thường; không tạo cảnh báo/SHAP theo thiết kế” |
| Cảnh báo | Alert ID, trạng thái SHAP `chờ / xong / bị bỏ`, nhánh A/B và lý do; cảnh báo vẫn thấy khi XAI chưa xong |
| SHAP | Top-5 thanh ngang hai phía trục 0, màu/legend nhất quán; tên đặc trưng, giá trị gốc và φ; chú thích dấu nghĩa là đẩy về/ra khỏi **lớp đang giải thích** |
| LIME | Nút yêu cầu thủ công, trạng thái đang chạy, Top-5 ở tab riêng, Local R² nếu API trả, Jaccard@5 chỉ khi đủ cả SHAP và LIME |
| Độ tin cậy | Faithfulness proxy, cờ môi trường `n/3`, cờ lớp hiếm, số tham chiếu RQ2 theo lớp khi bước 10 triển khai; thiếu thì ghi “chưa có”, không hiển thị `None` hoặc một “điểm tin cậy” tổng hợp giả tạo |
| Độ trễ | Các bước đã ghi trong `Timing`; không gọi các số live là kết quả median/p95 E1 chính thức khi thí nghiệm E1 chưa làm |

### 3.3. Cảnh báo liên quan

Cho phép nhóm để dễ đọc khi có nhiều flow giống nhau, nhưng không xóa bản ghi con. Chỉ nhóm bằng IP/cổng khi metadata thực sự có; nguồn Tập A/B thiếu IP thì dùng nhóm theo lớp và ghi rõ giới hạn. Người xem mở nhóm vẫn tới được từng `flow_id`/`alert_id`.

## 4. Việc cần thay trong dữ liệu và API

- [x] `app/feeder.py`: tạo mã lượt bắt một lần khi khởi động; gửi `capture_run_id` và metadata IP/cổng/protocol của dòng CICFlowMeter qua tham số/đối tượng metadata tách khỏi 78 đặc trưng. Không mặc định lọc IP máy chủ trong đợt cải thiện UI này.
- [x] `app/main.py`: chấp nhận metadata **tùy chọn** để lời gọi `/predict` cũ còn hoạt động; không đưa metadata vào `Detector.predict_flow()`.
- [x] `app/db.py`: migration không mất dữ liệu cho `capture_run_id`, IP/cổng và thời gian gốc được chuẩn hóa; bản ghi cũ không có metadata vẫn đọc được.
- [x] API danh sách: lọc theo lượt bắt, nguồn và thời gian; phân trang tại DB cho `/flows` và `/alerts` thay vì kéo toàn bộ cảnh báo rồi cắt 100 dòng trong UI. Phạm vi/tổng số trả về phải rõ.
- [x] API chi tiết theo `flow_id`: ghép FlowRecord + Prediction + AlertRecord nếu có + Reliability + Timing. Có kết quả chi tiết cho cả Benign.
- [x] API số liệu tổng quan: trả số đếm và các bucket thời gian từ **toàn bộ phạm vi lọc**, không tính biểu đồ trên 200 dòng gần nhất rồi gọi đó là tổng hệ thống.
- [x] Trạng thái SHAP: phân biệt `queued`, `processed`, `dropped_queue_full`; hiện tại `get_alerts()` gộp chưa xử lý và bị bỏ thành `pending_or_dropped`.
- [ ] Timezone: lưu/so sánh bằng mốc UTC có múi giờ khi nguồn xác định được múi giờ; giữ raw timestamp để truy vết. Với dữ liệu cũ không rõ múi giờ, không âm thầm suy ra chính xác giả. Danh sách live xếp theo `received_at`, chế độ phát lại có thể xếp theo thời gian gốc đã chuẩn hóa.

## 5. Thứ tự triển khai dự kiến

1. **Pha A — sửa quan sát live:** phân biệt lượt bắt, thời gian, thứ tự mới nhất, tự làm mới, bảng flow gọn. Đây là phần giải quyết trực tiếp vấn đề trong ảnh.
2. **Pha B — chi tiết một flow:** API chi tiết và chọn dòng; xác suất 15 lớp, metadata, trạng thái Benign/cảnh báo; SHAP/LIME/độ tin cậy/Timing.
3. **Pha C — biểu đồ và cảnh báo liên quan:** số liệu tổng quan tính từ API, nhóm cảnh báo chỉ ở lớp hiển thị, cải thiện cách đọc cờ và giới hạn mô hình.
4. **Pha D — kiểm thử và cập nhật tài liệu:** test API, Streamlit AppTest, CSV/PCAP và một lượt live mới; cập nhật `README.md` và `docs/plan.md` sau khi code thực sự xong.

## 6. Tiêu chí nghiệm thu

- [ ] Feeder gửi một flow mới thì nó xuất hiện ở màn hình live trong một chu kỳ làm mới sau khi API ghi xong; lần test cũ không trộn vào chế độ “lượt hiện tại”. Nếu CICFlowMeter chưa xuất flow, UI nói rõ chưa có flow hoàn tất.
- [x] Chọn được cả flow Benign và flow tạo cảnh báo; một flow có một màn chi tiết nhất quán qua `flow_id`.
- [x] Cảnh báo xuất hiện trước SHAP; khi SHAP xong cùng cảnh báo được cập nhật. LIME chỉ chạy khi bấm.
- [x] Xác suất 15 lớp khớp dữ liệu Prediction; Top-5 SHAP/LIME và dấu khớp bản ghi API; nhánh B giữ nguyên nhãn/cảnh báo và hiển thị lý do.
- [x] Thời gian ở bảng là GMT+7 dễ đọc; UTC/raw nằm trong chi tiết; sắp xếp theo lúc API nhận trong live; PCAP cũ gửi lại vẫn được nhận biết là lượt xử lý mới với thời gian traffic gốc riêng.
- [x] Biểu đồ/tổng số tôn trọng cùng bộ lọc và không chỉ dựa vào giới hạn 200 flow/100 alert của UI.
- [ ] Metadata không làm thay đổi thứ tự, đơn vị hay số lượng 78 đặc trưng model; các API cũ và test bước 6–13 vẫn chạy.
- [x] Không xóa `data/ids_system.db`, CSV/PCAP hay dữ liệu thử hiện có để triển khai UI. Migration và dữ liệu mới được kiểm tra bằng bản sao/test riêng trước khi dùng DB hiện tại.

## 7. Ngoài phạm vi lượt cải thiện UI

- Huấn luyện lại model hoặc coi cảnh báo Hulk trên traffic web bình thường là tấn công đã xác thực.
- Chạy SHAP mặc định cho Benign hoặc LIME tự động cho mọi flow.
- Thay đổi luật nhánh A/B, tự đặt ngưỡng faithfulness/agreement, hoặc trình bày hai cột stability/robustness là đã có dữ liệu trước khi bước 10 được triển khai.
- Giải quyết độ trễ nội tại của CICFlowMeter bằng cách ép ghi các flow đang mở theo chu kỳ tùy ý. Việc đó có thể làm thay đổi đặc trưng flow và cần một thiết kế/kiểm chứng riêng.

## 8. Nhật ký tiến độ

### Kiểm tra tương thích 78 đặc trưng (16/10/2026)

- [x] Quét đủ train 2,8 triệu dòng, các cột trọng tâm trên 10 daily cleaned (15.589.784 dòng), đọc DB PCAP ở mode=ro.
- [x] 8 fixture TCP/UDP tái hiện lỗi đếm đầu flow, CWR, IAT một khoảng, active/idle và thiếu protocol trong khóa flow; một fixture đối chiếu đường `run_live_capture.py` thực tế.
- [x] Xuất [báo cáo](feature_compatibility_audit_20261016.md), [ma trận đủ 78 cột](feature_compatibility_matrix_20261016.md) và JSON bằng chứng; đính chính nhận định quy toàn bộ cảnh báo nhầm cho model trong README/kế hoạch.
- [ ] Sửa extractor có phiên bản trong mã dự án, kiểm chứng chuẩn length/header/std/subflow/window và nguồn preprocessing; chưa tự sửa site-packages, clip cờ hoặc zero bulk.

### Mở rộng hàng đợi SHAP theo yêu cầu (16/10/2026)

- [x] Tăng cấu hình từ 50 lên 200 tác vụ chờ; không đổi worker hoặc luật khi queue đầy.
- [x] UI tiếp tục đọc `maxsize` qua API, không gán cứng mẫu số; bảng vẫn 50 flow/trang.
- [x] Cập nhật README, hướng dẫn chạy và kế hoạch RQ3; giữ số liệu test queue 50 trong nhật ký lịch sử.
- [x] Kiểm tra `submit()` khi worker dừng trong bộ nhớ: nhận đủ 200 tác vụ, tác vụ 201 trả `dropped_queue_full`, queue vẫn 200; không ghi DB. Chạy lại `stage14_test_dashboard_redesign.py`: toàn bộ regression API/UI/CSV/PCAP PASS trên DB tạm với cấu hình mới. Đây không phải benchmark tải.
- [ ] Đo tải để chọn dung lượng phù hợp; chưa cải thiện tốc độ xử lý, retry feeder hoặc khôi phục queue RAM.

Áp dụng bằng khởi động lại API. Đây là thay đổi cấu hình dung lượng, không phải kết quả benchmark hoặc sửa độ tin cậy giao nhận dữ liệu.

### Audit hai PCAP theo yêu cầu người dùng (16/10/2026)

- [x] Đọc 92 flow, tính lại model: 92/92 khớp nhãn/xác suất; trích lại PCAP: 59/59 và 33/33 khớp 78 đặc trưng.
- [x] 8/8 SHAP khớp và additivity sai số tối đa ≈2,861e-6; 8/8 LIME ESS≈1.
- [x] Phân biệt 2 flow có weight underflow về 0 và 6 flow có weight khác 0 nhưng cực nhỏ; không kết luận đồng loạt 999 weight bằng 0.
- [x] Kiểm tra cờ/bulk trên toàn bộ 2,8 triệu dòng train và 13 mẫu LIME đối chứng.
- [ ] Chưa thay adapter đặc trưng/cấu hình LIME; cần một bước sửa phương pháp có đánh giá riêng. Sửa UI trước đó chỉ làm rõ tính không hợp lệ.

Chi tiết: [pcap_xai_audit_20261016.md](pcap_xai_audit_20261016.md). Lệnh kiểm tra chỉ đọc: `scripts/stage17_audit_pcap_xai.py`.

### Điều chỉnh theo phản hồi: cần hiểu tên đặc trưng (16/10/2026)

- [x] Định nghĩa tiếng Việt + đơn vị + lưu ý cho đủ 78 tên đầu vào, dùng chung API/UI; không còn placeholder trong danh mục.
- [x] SHAP/LIME có phần đọc từng đặc trưng bằng lời ngay dưới biểu đồ, phân biệt giá trị đầu vào và hệ số giải thích.
- [x] Tra cứu một đặc trưng là giao diện chính; bảng rộng 78 cột số liệu tham chiếu chuyển vào phần mở rộng gọn hơn.
- [x] LIME lỗi giải thích quy trình, số mẫu mất trọng số và ý nghĩa kết quả bằng ngôn ngữ phổ thông; kỹ thuật/JSON thu gọn.
- [x] Giữ nguyên mô hình, đầu vào, cấu hình LIME và luật A/B; không biến diễn giải thành quy tắc phát hiện mới.

Hướng dẫn: [reading_shap_lime.md](reading_shap_lime.md). Test `stage16_test_feature_help.py` kiểm tra đủ 78 tên, đơn vị, dấu và định dạng số.

### Bổ sung theo test PCAP: LIME và đối chứng (16/10/2026)

- [x] Xác định LIME toàn trọng số 0: 999/1000 mẫu lân cận có kernel weight bằng 0; cỡ mẫu hiệu dụng bằng 1.
- [x] Lưu chẩn đoán; không công bố R²/Jaccard/Top-5 có ý nghĩa khi LIME suy biến; nhận diện kết quả cũ toàn 0 mà không sửa lịch sử DB.
- [x] Khóa RNG LIME khi có nhiều request đồng thời để giữ tái lập theo flow.
- [x] Tab đối chứng đủ 78 đặc trưng, nền LIME và P05/median/P95 tập B theo nhãn; số mẫu/nguồn/giới hạn ghi rõ.
- [x] Test số học bình thường/suy biến/hằng, đa luồng và kết quả legacy; test API/UI/CSV/PCAP bằng DB tạm.
- [ ] Đánh giá riêng độ tương thích định nghĩa đặc trưng extractor live với dataset train; chưa thay extractor hoặc cấu hình RQ2 để ép LIME có thanh.

Xem [báo cáo kỹ thuật và cách sử dụng](lime_validity_and_comparison.md). Đây là sửa tính trung thực của kết quả/UI, không phải tuyên bố đã khắc phục dịch chuyển phân bố traffic thật.

| Ngày | Mục | Trạng thái | Bằng chứng/ghi chú |
|---|---|---|---|
| 16/10/2026 | Lập kế hoạch theo ảnh test live và tài liệu kiến trúc | Xong | Chưa sửa code |

Khi bắt đầu triển khai, cập nhật checkbox và nhật ký này sau từng pha để không bỏ sót việc.

### Cập nhật triển khai 16/10/2026

- Pha A/B/C: đã có metadata riêng, migration cộng thêm cột/index, API chi tiết/số liệu/lượt và phân trang; UI tự cập nhật 5 giây, bộ lọc lượt, chọn mọi flow, biểu đồ tổng quan/xác suất/SHAP/LIME/timing, nhóm cảnh báo 5 phút.
- Pha D: PASS `scripts/stage14_test_dashboard_redesign.py` trên DB tạm, API cổng riêng, model thật và Streamlit AppTest. Có kiểm tra CSV và PCAP qua CICFlowMeter thật, không chỉ kiểm tra HTTP server khởi động. Test bước 13 đã chuyển tiếp sang bộ test mới để không ghi vào DB demo.
- Kiểm tra metadata không làm thay đổi xác suất model với cùng 78 đặc trưng; không thay luật dự đoán, SHAP/LIME hay nhánh A/B.
- Test bước 4 (chuẩn hóa) và bước 5 (dự đoán) PASS; 50/50 mẫu đối chiếu khớp RQ2. Có cảnh báo phiên bản thư viện model cũ, được ghi trong hướng dẫn.
- Feeder sửa lỗi dòng trống có thể làm lệch con trỏ và gửi lặp. Dòng cuối chưa đủ cột được chờ ở lượt đọc sau.
- Không xóa dữ liệu demo; chưa tự restart API/feeder đang chạy của người dùng.
- Hướng dẫn chạy lại: [dashboard_usage.md](dashboard_usage.md).

### Phần chưa nghiệm thu / giới hạn được giữ rõ

- Chưa chạy một lượt Wi-Fi live mới sau cập nhật, chưa xác nhận tự-refresh/click bằng trình duyệt thật; AppTest đã chạy các nhánh UI.
- Chưa chạy lại toàn bộ test bước 6–12; không đánh dấu tương thích toàn bộ chỉ dựa trên bộ smoke/regression mới.
- UI hiện xếp theo lúc API nhận. Chế độ sắp xếp riêng theo timestamp gốc cho replay chưa thêm; vẫn xem được timestamp gốc trong chi tiết, không trộn với UTC.
- Bộ lọc UI cung cấp toàn bộ lượt/5 phút/15 phút/1 giờ/hôm nay; khoảng tùy ý dùng API since/until, chưa có date-picker.
- Nhóm chỉ hiển thị 100 nhóm mới nhất trong phạm vi, từng nhóm có phân trang; bảng flow chính vẫn cho xem mọi flow.
- API chỉ biết flow đã được gửi đến, không có heartbeat của capture. Trạng thái queued còn lại sau restart chưa có cơ chế phục hồi tác vụ RAM.
