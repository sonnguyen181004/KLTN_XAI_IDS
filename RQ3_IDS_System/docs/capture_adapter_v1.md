# Bản sửa extractor và kiểm tra đường realtime

Ngày cập nhật: 16/10/2026, GMT+7. Phiên bản: `rq3-cfm-0.5.0-fixes-v1`, dựa trên Python CICFlowMeter 0.5.0. Mã sửa nằm trong `app/capture_adapter.py`; không sửa site-packages.

**Tài liệu phiên bản lịch sử:** mặc định hiện tại đã chuyển sang v2 sửa thêm window=0. Xem [bản v2 và cơ chế phục hồi](stability_update_20261016.md); dùng `--extractor project-v1` để tái lập bản được mô tả tại đây. Số liệu/JSON v1 bên dưới được giữ nguyên.

## Hành vi đã sửa

1. Mỗi packet được đưa vào flow đúng một lần; constructor đã giữ gói đầu thì session không thêm lại. Bulk cũng nhận gói đầu đúng một lần.
2. Đếm CWR trực tiếp bit 128 của TCP, độc lập URG; giữ tên cột dataset `CWE Flag Count` ở bộ ánh xạ.
3. IAT có một khoảng đo vẫn có total/mean/min/max bằng khoảng đó, std=0. Không thêm IAT=0 giả do trùng gói đầu.
4. Active/Idle tính từ timestamp packet, độc lập thời điểm `latest_timestamp` được cập nhật. Gap >5 giây phân tách hoạt động; ghi idle bằng toàn khoảng nghỉ. Xuất thống kê các đoạn active đã hoàn tất cộng đoạn cuối có duration>0; export lặp không sửa danh sách.
5. Khóa flow gồm IP nguồn/đích, cổng nguồn/đích và protocol; TCP/UDP cùng endpoint/cổng tách riêng.

Session dùng lock chung cho nhận packet, GC và ghi CSV để tránh export khi dữ liệu đang đổi. Offline dùng clock của PCAP, không dùng wall-clock GC trên PCAP cũ; nhờ đó thời điểm CPU chạy không làm cắt flow tùy ý. Live dùng periodic GC 1 giây; dừng sniffer, dừng/join GC rồi flush các flow còn lại.

## Phiên bản và dữ liệu

- `run_live_capture.py` mặc định dùng `--extractor project`. `--extractor legacy` chạy baseline cũ để đối chiếu, không dùng làm bản sửa.
- CSV mới có `extractor_version`. Feeder và upload chuyển trường đó thành metadata API; migration thêm `FlowRecord.extractor_version` và UI hiển thị trong chi tiết.
- Model vẫn nhận đúng 78 số. Các flow mới lưu chính vector chuẩn hóa 78 cột; src_port và metadata số khác không còn nằm lẫn trong features_json. Metadata không đổi dự đoán của cùng vector.
- Dữ liệu cũ không bị ghi đè hoặc tự gán phiên bản. CSV cũ không có version hiển thị là nguồn chưa cung cấp phiên bản.
- Muốn dùng bản mới, restart API/Streamlit rồi dừng và khởi chạy lại capture/feeder với **tên CSV mới**. Chỉ restart giao diện không đổi tiến trình capture cũ đang chạy. Không dùng file CSV cũ làm đầu ra vì writer mở file bằng chế độ ghi mới.

Ví dụ từ thư mục `RQ3_IDS_System`:

```powershell
# Terminal API
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Terminal UI
python -m streamlit run app/dashboard.py
# Terminal capture, có quyền Npcap trên Windows
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --interface "Wi-Fi" --output data\live_v1_01.csv
# Terminal feeder
python app\feeder.py --watch data\live_v1_01.csv --convert-units --capture-timezone +07:00
```

## Timeout và ý nghĩa realtime

V1 giữ ngưỡng duration 90 giây / idle 240 giây. FIN/RST **chưa có state machine kết thúc TCP riêng**. Đặc trưng được xuất khi chạm timeout hoặc khi dừng bắt và flush; flow mới không nhất thiết xuất hiện ngay khi có packet hay FIN. Khi xuất CSV, feeder kiểm tra theo chu kỳ và gửi API, UI cập nhật khoảng 5 giây/lần. Độ trễ hoàn tất flow phải tách khỏi độ trễ model và SHAP.

Không tự giảm timeout để tạo flow nhanh hơn trong thay đổi này: việc đó thay ranh giới flow và đặc trưng, cần cấu hình/thí nghiệm riêng. Với phiên chỉ 20 giây, mọi flow có thể chỉ ra lúc dừng; đây là kết quả đo được của bài smoke test, không phải bằng chứng streaming cập nhật ngay.

## Kiểm thử đã thực hiện

`stage20_test_capture_adapter.py` chạy bằng `.venv_capture`: 10 bài kiểm thử gồm đếm gói/cờ/rate/IAT, IAT một khoảng, CWR/URG, Active/Idle, TCP/UDP, bulk, timeout/đổi chiều, flush lặp, GC đồng thời, CLI offline tái lập và phạm vi IPv4. Đều PASS. Các fixture kiểm tra số học độc lập, không coi nhãn model trên gói giả là nhãn thật.

`stage14_test_dashboard_redesign.py`: PASS toàn bộ API/UI/CSV/PCAP, migration, metadata version và giữ đúng 78 đặc trưng khi payload kèm src_port. Dùng DB tạm.

### Hai PCAP người dùng

[JSON đối chiếu trước/sau](capture_adapter_comparison_20261016.json) dùng các lượt phân tích riêng trong bộ nhớ, không gửi lại vào DB demo. Ghép một-một bằng endpoint/protocol/timestamp, 92/92 ghép được, không có key mơ hồ.

| File | Flow trước/sau | Tổng gói cũ → mới | Nhãn trước/sau |
|---|---:|---:|---|
| tesst2.pcapng | 59 → 59 | 696 → 637 | 56 Benign, 3 Hulk ở cả hai bản |
| test.pcapng | 33 → 33 | 544 → 511 | 28 Benign, 5 Hulk ở cả hai bản |

Cả 92 vector thay đổi sau sửa; không nhãn nào thay đổi. Xác suất/SHAP có thể thay đổi. Cả 8 cảnh báo vẫn LIME `insufficient_neighborhood` với cùng seed đối chiếu theo từng cặp; SHAP additivity sai số tối đa khoảng 2,861e-6. Các seed này không phải UUID alert cũ trong DB. Không có ground truth được xác minh, nên đây không phải đo accuracy hoặc FPR.

### Wi-Fi thật 20 giây

[Kết quả smoke test](capture_live_validation_20261016.json): 2.704 packet được session nhận và xuất đúng 2.704 packet trong CSV, 178 flow → 178 dự đoán qua feeder/API; 164 Benign và 14 Hulk. Không có lỗi feeder trong phiên đó, SHAP 14/14 xử lý, không bị bỏ; queue maxsize=200. Metadata version/IP, 78 đặc trưng, 15 xác suất và đổi đơn vị duration đều khớp. AppTest mở đúng dữ liệu phiên live và version extractor.

0 flow được API nhận trước khi capture kết thúc ở smoke test này; sau dừng flush thì dữ liệu lên đầy đủ. Số packet là số đã vào callback, không chứng minh NIC/Npcap không mất packet trước callback. Nhãn Hulk không được coi là tấn công đã xác nhận. Chưa phải benchmark chạy dài hoặc kiểm chứng feeder retry khi API lỗi.

### Wi-Fi thật 100 giây và cập nhật trong khi bắt

[Kết quả phiên streaming](capture_live_stream_validation_20261016.json): 42.027 packet vào callback → 42.027 packet xuất CSV, 159 flow →159 dự đoán. **88 flow đã được API nhận trước khi capture kết thúc**; phần còn lại được flush sau dừng. Kết quả gồm 130 Benign, 29 Hulk; SHAP 29/29 xử lý, không bị bỏ, không lỗi feeder trong mẫu, queue maxsize=200. Phiên này xác minh dữ liệu có thể đi từ Wi-Fi tới API ngay trong khi bắt, sau khi chạm timeout. Không diễn giải các nhãn thành tấn công thật hoặc tính FPR khi chưa có nhãn xác minh.

Cùng các kiểm tra version/IP, 78 cột, 15 lớp, đơn vị thời gian và AppTest UI đều PASS. Hai phiên tự tạo DB/cổng riêng, tự dừng tiến trình của mình và dọn CSV/DB tạm. JSON giữ tổng số và kết quả kiểm tra, không giữ payload hay IP. Việc không thấy lỗi ở hai phiên không bảo đảm không mất packet trước callback hoặc không mất dòng khi API lỗi; retry/checkpoint feeder vẫn là việc chưa làm.

## Giới hạn và bước tiếp theo

Audit tiếp theo đã thu hẹp một số quy ước bằng quan hệ trên toàn bộ train/test, không chỉ min/max: [hợp đồng ngữ nghĩa và bằng chứng mới](feature_semantics_contract_20261016.md). Có khác biệt sample SD độ dài, floor ratio, sentinel window và quan hệ hai mean; fixture còn xác nhận initial window=0 bị upstream ghi đè. Bản v1 chưa sửa những phần đó. Ngược lại subflow packet=số packet tổng khớp tập đủ điều kiện, chưa có căn cứ tự thay theo Java master.

- Length/header vẫn dùng quy ước upstream Python; chưa chuyển sang payload/header transport của bản Java tham chiếu. Std, subflow, missing window và binary flag convention chưa chứng nhận tương thích dataset V3.
- Không clip cờ >1 về 1, không zero bulk, không train lại model và không thay cấu hình LIME. LIME vẫn còn vấn đề đã ghi nhận.
- Chỉ IPv4 TCP/UDP; packet ngoài phạm vi bị bỏ và đếm trong `ignored_packets`. BPF live cũng giới hạn phạm vi này.
- FlowSession giữ packet trong RAM đến khi xuất; đây chưa phải thiết kế bắt gói tải cao. Hàng đợi SHAP 200 không giới hạn RAM của bộ bắt.
- Cần chốt hợp đồng đặc trưng train, thiết kế timeout/TCP close nếu yêu cầu độ trễ thấp hơn, sửa retry/checkpoint feeder và đo tải dài trước khi đánh giá triển khai thực tế.
