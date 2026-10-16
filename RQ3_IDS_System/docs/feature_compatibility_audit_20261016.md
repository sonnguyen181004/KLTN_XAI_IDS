# Kiểm tra tương thích đặc trưng train và PCAP

Ngày kiểm tra: 16/10/2026, GMT+7. Model hiện tại: `52eb5a671ee82109`. Extractor cài trong `.venv_capture`: Python CICFlowMeter 0.5.0.

**Kết luận:** ánh xạ tên và thứ tự đủ 78 cột, nhưng chưa đạt tương thích ngữ nghĩa. Đã tái hiện lỗi extractor bằng PCAP có thể đếm độc lập. Vì vậy chưa được quy toàn bộ cảnh báo nhầm cho dịch chuyển phân bố hoặc lượng dữ liệu train ít. Chưa sửa extractor, adapter, model, cấu hình LIME hoặc kết quả DB trong bước kiểm tra này.

## Phạm vi và bằng chứng

- Quét đủ 78 cột trên 2.800.000 dòng train: min/max, số hữu hạn, khác 0, âm, lớn hơn 1 và không nguyên.
- Quét nhóm cờ TCP, bulk, active/idle trên toàn bộ 10 Parquet theo ngày: 15.589.784 dòng. Đây là file **đã cleaned**, không phải CSV/PCAP nguyên bản từ tác giả dataset.
- Đối chiếu 92 flow PCAP đang lưu bằng SQLite `mode=ro`, không gọi API hoặc thêm dữ liệu demo.
- Tạo 8 fixture TCP/UDP, chỉ ghi/đọc PCAP trong thư mục tạm, không phát gói lên mạng. Oracle tính từ gói đọc lại, độc lập các hàm extractor.
- Fixture TCP 6 gói còn được chạy qua chính `run_live_capture.py --pcap-input`; đầu ra khớp đường xử lý `FlowSession` được kiểm tra, xác nhận vấn đề có trên đường chạy của ứng dụng.
- Phân tích source `flow.py` để nối mỗi cột model tới biểu thức extractor; lưu SHA256 các file source extractor để xác định phiên bản đã kiểm tra.

Tái lập từ thư mục gốc:

```powershell
python -B RQ3_IDS_System/scripts/stage19_audit_feature_compatibility.py --output RQ3_IDS_System/docs/feature_compatibility_evidence_20261016.json
```

Script cần môi trường chính có numpy/pyarrow và `.venv_capture` hiện có. Nếu môi trường sandbox chặn thư mục tạm/SQLite, chạy với quyền truy cập phù hợp; không cần quyền bắt gói để đọc các fixture PCAP. Script đọc toàn bộ dữ liệu nên thời gian phụ thuộc máy.

- [Bằng chứng JSON và số liệu từng cột](feature_compatibility_evidence_20261016.json).
- [Ma trận đủ 78 đặc trưng](feature_compatibility_matrix_20261016.md).

## Các lỗi và khác biệt đã kiểm chứng

| Mục | Giá trị kiểm tra độc lập | Kết quả Python hiện tại | Ý nghĩa |
|---|---|---|---|
| Đếm gói TCP | 6 gói, 4 forward + 2 backward | 7 gói, 5 forward + 2 backward | Gói đầu được lưu trong `Flow.__init__` rồi thêm lại ở `FlowSession.process` |
| Đếm SYN | 2 gói có SYN trong fixture trên | 3 | Cờ gói đầu bị đếm lặp, ảnh hưởng cả thống kê phụ thuộc |
| Flow IAT mean | 5 khoảng đều 0,1s | 0,083333s | Thêm khoảng 0 do gói đầu bị lặp |
| Bwd IAT total | 2 gói backward cách 0,3s | 0 | `get_statistics` trả toàn 0 khi danh sách chỉ có 1 khoảng; sau đổi đơn vị vẫn 0, thay vì 300.000 µs |
| CWR có, URG không | 1 gói CWR | `cwr_flag_count=0` | Cột này sao chép Fwd URG thay vì đếm CWR |
| URG có, CWR không | CWR=0 | `cwr_flag_count=2` | Vừa sai nguồn cờ, vừa chịu đếm lặp gói đầu |
| Active/Idle | Các gói ở 0; 0,1; 8,1; 8,2s, có khoảng nghỉ 8s | Cả 8 cột active/idle đều 0 | `latest_timestamp` được cập nhật trước khi `update_subflow` tính chênh lệch, nên đường này không cập nhật active/idle với chuỗi thời gian tăng |
| Tổng độ dài forward | 100 byte payload; 316 byte tổng frame thật | 370 | Python cộng `len(packet)` gồm header/lớp link và gói đầu bị lặp; không thể hiểu là 370 byte payload |
| Header UDP forward | 2 gói UDP có tổng header transport 16 byte, header IPv4 40 byte | 60 | Python cộng header IPv4 và lặp gói đầu; không tương đương header transport |
| Bulk | 5 payload mỗi gói 100 byte | 500 byte/bulk; 5 gói/bulk; 1250 byte/s | Có giá trị khác 0 dù toàn bộ 6 cột bulk của train/daily đều 0 |
| Nhóm flow theo giao thức | TCP và UDP cùng cặp IP/cổng phải là các flow khác giao thức | 1 flow, ghi protocol=6 | Flow key Python chỉ có 4 thành phần, thiếu protocol; có thể trộn TCP/UDP khi cùng endpoint/cổng |

Các fixture cũng cho UDP 3 gói → 4; TCP 2 gói → 3. Lỗi đếm đầu flow không chỉ xuất hiện ở TCP. Khi sửa cần xem lại tổng gói/byte, rate, IAT, flag, ratio và các thống kê phụ thuộc cùng lúc.

Không được gọi 78 tên cột đều sai hoặc dùng số nhóm trong ma trận làm tỷ lệ lỗi. Có cột chỉ được kiểm tra trên fixture, cột chịu ảnh hưởng gián tiếp, và cột khác bản tham chiếu nhưng chưa có binary gốc để xác nhận quy ước lịch sử.

## Dữ liệu train khác PCAP ở đâu

### Khác biệt đã có trước khi lấy tập con train

Trên cả 10 file daily cleaned (15.589.784 dòng), tất cả 12 cột cờ được kiểm tra chỉ có 0/1 hoặc hằng 0, không có giá trị >1. Cả 6 cột bulk đều 0. Tập train giữ hiện tượng này; Bwd PSH Flags và Bwd URG Flags cũng hằng 0.

Vì vậy tăng từ tập con 3,5 triệu lên toàn bộ những Parquet cleaned này **không tự giải quyết** khác biệt miền đếm cờ/bulk với extractor live. Chưa xác minh công đoạn nào đã tạo ra các giá trị đó: thiếu CSV/PCAP nguyên bản, script cleaning và script sampling/split. Trong Git chỉ tìm được script huấn luyện đọc train/test đã có, không tìm thấy pipeline tạo ra chúng. Metadata Parquet cho biết kiểu float32, nhưng không chứng minh đã/không binarize cờ.

### Các dấu hiệu khác

- `Init Fwd/Bwd Win Byts` trong train có -1, Python khởi tạo 0 khi không có TCP/không có chiều đó. Python còn dùng window=0 làm điều kiện cập nhật lại, cần phân biệt window thực sự bằng 0 và trạng thái chưa quan sát.
- `Down/Up Ratio` trong train luôn nguyên; Python chia số thực (fixture 2/5=0,4 do đếm lặp, ratio theo gói thật là 2/4=0,5). Chưa tự làm tròn để ép khớp train.
- `Pkt Len Min` của 2.175.512/2.800.000 dòng train bằng 0. Python dùng toàn frame nên TCP ACK không payload vẫn có độ dài frame dương. Đây là bằng chứng hỗ trợ khác miền định nghĩa, không phải chỉ khác tên cột.
- Train vẫn có **9.815/1.960.000 flow Benign mang FIN khác 0**, và 445/155.042 flow Hulk có FIN khác 0. Không thể suy luận chỉ cần FIN là tấn công, hoặc dataset không chứa Benign có FIN. Cần phân tích các đặc trưng kết hợp và extractor.
- 13 cột có ít nhất một giá trị của 92 flow PCAP nằm ngoài min/max train, bao gồm ACK (75 flow), PSH (53), Bwd PSH (51), Fwd PSH (48). Ngoài min/max là dấu hiệu cần xem xét, không phải nhãn sai hoặc bằng chứng tấn công.

## Những phần đã khớp ở mức kỹ thuật

- 78 ánh xạ tên có đích duy nhất và khớp bộ cột model. Mọi fixture đi qua `row_to_payload` và `normalize_flow` đều có đúng shape (1,78), đúng thứ tự.
- 23 cột thời gian được đổi giây → µs; duration fixture 0,5s thành 500.000µs. Rate tính theo giây không nhân 1e6. Việc đổi đơn vị đúng không khôi phục được IAT mà extractor đã trả 0.
- Dst Port, mã Protocol và duration đúng trên fixture đơn giao thức. Trường hợp lẫn TCP/UDP vẫn phải sửa khóa flow; đây không phải chứng nhận segmentation và timeout tương thích dataset.

## Đối chiếu nguồn tham chiếu

Dataset chính thức công bố dùng CICFlowMeter-V3: [UNB CSE-CIC-IDS2018](https://www.unb.ca/cic/datasets/ids-2018.html). Tài liệu không bảo đảm mọi bản Python cùng tên có cùng hành vi.

Trong source Java **master hiện tại**, [PacketReader.java](https://github.com/ahlashkari/CICFlowMeter/blob/master/src/main/java/cic/cs/unb/ca/jnetpcap/PacketReader.java) lấy độ dài payload và header transport; [BasicFlow.java](https://github.com/ahlashkari/CICFlowMeter/blob/master/src/main/java/cic/cs/unb/ca/jnetpcap/BasicFlow.java) dùng chúng cho length/header, có subflow và phép chia nguyên ở Down/Up Ratio. Python đã cài dùng `len(packet)`, header IPv4, sao chép tổng sang subflow và chia thực. Thống kê Python dùng population variance; Java dùng SummaryStatistics nên cần kiểm tra quy ước sample variance khi tái hiện lịch sử.

**Giới hạn:** chưa xác nhận master hiện tại là revision/binary V3 đã sinh dữ liệu 2018, chưa chạy Java trên cùng fixture. Không dùng việc xem source hiện tại để tuyên bố đã tái tạo 78 đặc trưng dataset gốc.

## Ảnh hưởng tới kết luận SHAP và LIME trước đó

Audit trước xác nhận trích lại cùng extractor cho cùng kết quả và SHAP cộng đúng về điểm model. Điều đó chứng minh tái lập tính toán, **không chứng minh extractor tính đúng ngữ nghĩa**. Lỗi xác định ở bước này có thể góp vào sai khác đặc trưng và LIME neighborhood suy biến. Chưa định lượng bao nhiêu cảnh báo nhầm do từng lỗi, chưa có căn cứ kết luận sửa extractor sẽ giải quyết toàn bộ LIME hoặc model live.

## Việc tiếp theo

1. Tạo adapter/extractor trong mã dự án có phiên bản và regression fixture; không sửa trực tiếp site-packages. Sửa nhóm lỗi tái hiện được: đếm gói đầu, CWR, IAT một khoảng, active/idle và flow key có protocol.
2. Chốt hợp đồng length/header/std/subflow/window/timeout dựa trên nguồn train, lấy original CSV/PCAP hoặc pipeline preprocessing để xử lý phần chưa rõ. Giữ raw và transformed features để truy vết; không tự clip cờ >1 về 1 hoặc zero bulk.
3. Trích lại PCAP vào lượt thử nghiệm riêng, so sánh feature/dự đoán/SHAP/LIME với bản cũ. Giữ model làm baseline; nếu đổi định nghĩa đầu vào phải ghi rõ phiên bản và chạy lại đánh giá.
4. Chỉ quyết định train mới sau khi hoàn thành đối chiếu và có tập đánh giá có nhãn được xác minh. Tách vấn đề giao nhận feeder/hàng đợi khỏi tính đúng đặc trưng.
