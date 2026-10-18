# Tương thích đặc trưng train và capture

## HT2.4 — nghiệm thu và áp dụng lifecycle v3 (18/10/2026)

**Mục đích:** chốt bản phân flow có kiểm thử, áp dụng cùng đường live/PCAP và giữ bằng chứng model/XAI. Commit: `feat(rq3): validate and enable lifecycle v3 capture`.

- Mặc định `project` nay là v3; `project-v3` alias tường minh, `project-v2` giữ nguyên baseline. Không sửa model, 78 cột/thứ tự, cờ, công thức v2 hay cấu hình RQ2.
- Hoàn thiện trong nghiệm thu: bỏ Ethernet padding khỏi số sequence FIN, chọn lý do timeout theo deadline đến trước (không phụ thuộc GC chạy trễ), dùng watermark timestamp **toàn session** cho packet trễ để kết quả không tùy flow cũ còn trong bộ nhớ hay đã được GC. Đây là policy bảo thủ: packet của tuple khác nhưng timestamp lùi cũng được tách riêng; chưa có reorder buffer. Ghi rõ giới hạn này thay vì ép thời gian về 0.
- Stage26 **22/22 PASS**; Stage20 **21/21 PASS** giữ các characterization v2; Stage23 self-test **3/3 PASS**. Stage14 kiểm tra model/API/UI trên DB tạm, thêm assert PCAP lưu version v3 và đủ 78 đặc trưng. Có kiểm tra đóng/flush, lỗi writer, GC đồng thời; không thay thế benchmark dài hạn/tải cao.
- Stage21 trích mỗi PCAP/bản hai lần, yêu cầu CSV giống hệt; kiểm tra số packet bằng bộ đọc Scapy độc lập; normalize/predict mọi flow, SHAP/LIME mọi cảnh báo (kể cả flow không ghép cặp). Ghép theo tuple+timestamp chỉ là đối chiếu, không coi flow mới là false positive hoặc ground truth.
- Bằng chứng cuối: `lifecycle_v3_final_evidence_20261018.json` (checksum code/PCAP/model version). `lifecycle_v3_evidence_20261018.json` là lượt trước kiểm tra padding/GC cuối cùng, giữ để truy vết, không thay thế bản cuối. Script từ chối ghi đè bằng chứng.

**Điều kiện còn thiếu để chứng nhận tương thích:** pipeline tạo daily/train Parquet, commit/cấu hình extractor lịch sử hoặc cặp PCAP–CSV gốc. Ma trận 78 cột và các sai khác SD/mean/window/bulk trước đây vẫn có hiệu lực; HT2 không tự điều chỉnh công thức theo suy đoán. Không tuyên bố đã giải quyết báo nhầm hoặc hoàn thành E4. Kiểm thử Wi-Fi dài hạn, tài nguyên, giao nhận khi lỗi thuộc HT3/HT7; chưa chạy trong HT2.

Kết quả Stage21 cuối (v2 → v3):

| PCAP | Packet IPv4 TCP/UDP bảo toàn | Số flow | Nhãn v3 | Cặp đối chiếu / đổi vector / đổi nhãn |
|---|---:|---:|---|---|
| `test.pcapng` | 511/511 | 33 → 38 | 33 Benign, 5 Hulk | 33 / 3 / 0 |
| `tesst2.pcapng` | 637/637 | 59 → 61 | 58 Benign, 3 Hulk | 59 / 1 / 0 |

Hai PCAP có tổng 1.148 packet; 92 flow baseline thành 99 flow v3. Bảy flow bổ sung đều dự đoán Benign; không gọi đây là giảm FPR. Mọi CSV lặp cùng mode giống byte; 8 cảnh báo được tính lại SHAP/LIME, sai số cộng dồn SHAP lớn nhất khoảng `2.862e-6`, cả 8 LIME `insufficient_neighborhood`. Không có packet trễ ở hai PCAP này; policy late được kiểm bằng fixture, không suy rộng từ PCAP. Có cảnh báo artifact pickle XGBoost/LabelEncoder khác phiên bản thư viện; chưa chuyển đổi artifact trong HT2.

## HT2.2 — timeout và packet lệch thời gian (18/10/2026)

### HT2.3 — kết thúc và tái sử dụng phiên TCP

- **Mục đích:** không gộp nhiều phiên cùng tuple; không kết thúc chỉ vì FIN một chiều. Commit: `fix(rq3): track observed TCP close and connection reuse`.
- V3 ghi `tcp_rst_observed` sau khi nhận RST; `tcp_fin_ack_observed` chỉ sau khi thấy FIN hai chiều và ACK phủ số thứ tự cuối FIN tương ứng. Tính cả payload, SYN, FIN và vòng số thứ tự 32 bit. SYN cùng ISN trong phiên đang mở được giữ như retransmission; SYN khác ISN hoặc SYN sau dữ liệu midstream tách bằng `tcp_new_syn`. Hai SYN mở đồng thời được giữ cùng flow.
- Đây là bộ gom flow thụ động theo dấu hiệu đã quan sát, **không phải TCP stack/reassembly hoàn chỉnh**: không xác minh tính hợp lệ RST, cửa sổ sequence, checksum hoặc TIME-WAIT; packet retransmission sau khi đã xuất sẽ thuộc flow khác. Mất gói có thể khiến thiếu ACK/FIN, lúc đó timeout/flush vẫn kết thúc. Không suy ra trạng thái máy đầu cuối từ riêng cờ đã bắt.
- Tham khảo trạng thái TCP và FIN/ACK: [RFC 9293, mục 3.6](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.6). Quy tắc phân flow là chính sách riêng đã version, không tuyên bố tái tạo CICFlowMeter2018.
- **Kiểm thử:** Stage26 16/16 PASS, gồm FIN payload/wraparound/retransmission, half-close, RST, SYN mới/lặp, simultaneous open và TCP/UDP độc lập. Mỗi fixture đọc CSV và kiểm tra bảo toàn packet. Quét toàn bộ flow tối đa mỗi giây capture; tuple nhận packet vẫn kiểm tra timeout ngay tại admission. Chưa có benchmark tải dài hạn; mặc định CLI vẫn v2 ở commit này, chờ đối chiếu hai PCAP.

- **Mục đích:** bỏ phụ thuộc thứ tự GC/admission tại biên timeout; không để packet lệch thứ tự tạo IAT âm. Commit: `fix(rq3): version deterministic flow timeout and late-packet policy`.
- **Triển khai:** `capture_lifecycle.py`, mode thử nghiệm `--extractor project-v3`; v1/v2 và mặc định `project` chưa đổi tại commit này. Cùng điều kiện `>=` trước admission và trong GC. Tuổi flow tối đa 90s tính từ packet đầu, kể cả flow im lặng; idle 240s là ngưỡng dự phòng (với mặc định tuổi 90s sẽ đến trước). Cửa sổ nửa mở: packet ở đúng biên thuộc flow mới. Đây là quy ước vận hành mới, không giả định tương đương train.
- **Packet trễ:** nếu timestamp lùi so với packet cuối của tuple đang mở, xuất thành flow một packet có `flow_end_reason=late_packet`; nếu tuple không còn mở, đối chiếu watermark packet toàn session. Không sửa timestamp, không âm thầm bỏ packet, không sửa dòng đã xuất. Không dùng clock GC làm watermark packet. Giới hạn: flow một packet không tái dựng được phiên gốc và có thể làm thay đổi dự đoán; lý do xuất nằm trong CSV, chưa thêm vào schema API/UI.
- **Kiểm tra:** Stage26 có 8 fixture về biên active/idle trước–sau GC, flow im lặng, late trong/sau flow, timestamp bằng nhau, lỗi writer và flush lặp; kiểm tra bảo toàn số packet xuất/nhận. Kiểm thử bằng packet tổng hợp, không phải chạy Wi-Fi dài hạn.
- **Nguồn train:** đã đọc toàn bộ đoạn văn/bảng của hai báo cáo `Bao_Cao_Phan_Tich_Dataset_CICIDS2018.docx` và `Bao_Cao_Tong_Hop_Dataset_3.5M_CICIDS2018.docx` trong `dataset/CICID-2018_processed`. Báo cáo nêu lấy mẫu 3,5M, chia phân tầng 80/20, bỏ Timestamp; không cung cấp script tái tạo, phiên bản extractor hay bước nhị phân hóa cờ. Các khẳng định tương thích realtime trong báo cáo không thay thế được kiểm chứng công thức. Không sửa hai tài liệu nguồn trong bước này.
- **Giữ nguyên:** 78 đầu vào, model, công thức đặc trưng v2, cấu hình SHAP/LIME. Chưa chứng nhận tương thích train, chưa kết luận giảm FPR hoặc hoàn tất E4.

Tài liệu hợp nhất ngày 16/10/2026. Chỉ còn 5 tài liệu RQ3 chính: [kiến trúc và kế hoạch](plan.md), [chạy và đọc UI](dashboard_usage.md), [vận hành](operations.md), [kiểm chứng XAI](xai_validation.md), [tương thích đặc trưng](feature_compatibility.md).

> Trạng thái hiện hành (HT2, 18/10/2026): capture project lifecycle v3; v2 còn chọn được bằng `--extractor project-v2`; feeder checkpoint/chống gửi trùng; SHAP queue 200 và phục hồi sau restart. Giữ XGBoost/78 đặc trưng, cấu hình LIME RQ2 và nhánh A/B. Nhật ký bên dưới giữ số liệu của phiên bản được ghi tại thời điểm kiểm thử. Chưa chứng nhận tương thích đầy đủ train–PCAP hoặc độ ổn định live dài hạn; nhãn live chưa phải ground truth.

- [Hợp đồng ngữ nghĩa và bằng chứng train](#semantics)
- [Lịch sử adapter v1](#adapter-v1)
- [Audit baseline trước sửa](#baseline-audit)
- [Ma trận đủ 78 đặc trưng](#matrix-78)
- [HT2.1: độ nhạy cờ TCP và vòng đời flow](#ht21)

Stage19 mặc định chỉ xuất JSON bằng chứng; dùng `--matrix-output <đường-dẫn.md>` nếu cần xuất ma trận riêng có chủ đích. Script không tự tạo lại file tài liệu đã gộp hoặc ghi đè ma trận lịch sử bên dưới.

<a id="ht21"></a>

## HT2.1 — Điều tra nguồn train, độ nhạy cờ TCP và vòng đời flow (18/10/2026)

**Mục đích:** chọn bước sửa có bằng chứng, không nhị phân hóa cờ chỉ để mong giảm Hulk; xác định hành vi capture v2 cần xử lý trước khi hoàn thiện realtime. Chỉ thêm kiểm thử/diagnostic/tài liệu, không đổi adapter mặc định, model, LIME, timeout, DB hoặc hai PCAP gốc. HT2 tổng thể chưa hoàn tất.

### Truy vết nguồn và mức độ kết luận

- Rà tên file/script hiện có và tên file mã trong `git log --all`: chưa tìm thấy script tạo daily cleaned hoặc split `train_set.parquet`/`test_set.parquet`. Hai script RQ1 `1_hyperparameter_tuning.py` và `2_train_optimal_model.py` đọc Parquet đã có; `stage03_build_clean_dataset.py` tạo tập B, không tạo dữ liệu train gốc.
- Thư mục processed hiện có hai Parquet và hai báo cáo Word. HT2.1 chưa phân tích nội dung hai Word này; không tuyên bố đã loại trừ mọi thông tin nguồn trong tài liệu, bản sao bên ngoài hay dữ liệu không có trong Git. Truy vấn lịch sử đường dẫn Parquet không trả commit; không suy ra ngày/nguồn tạo từ điều đó.
- Bằng chứng 0/1 của cờ và bulk hằng 0 trên daily cleaned/train/test kế thừa audit 16/10, **không quét lại toàn bộ 15,6 triệu dòng ở bước này**. Nó xác nhận miền giá trị khác, chưa xác định preprocessing hay extractor lịch sử nào gây ra.
- Kiểm tra [BasicFlow.java chính thức](https://github.com/ahlashkari/CICFlowMeter/blob/master/src/main/java/cic/cs/unb/ca/jnetpcap/BasicFlow.java) tại nhánh `master` ngày 18/10: `firstPacket` và `addPacket` gọi `checkFlags`; bộ đếm tổng FIN/SYN/ACK… dùng `MutableInt.increment()` tăng giá trị và xuất giá trị đếm. Các trường cờ theo chiều có đường cập nhật riêng, không được gộp tất cả thành cùng một kết luận. Đây là bản nguồn tham khảo đang truy cập, chưa được xác minh là binary/commit tạo dataset 2018. Không lấy Java master làm oracle cho toàn bộ train.

### Kiểm chứng trực tiếp giả thuyết “đếm cờ >1 làm model đổi nhánh”

Thêm `scripts/stage25_audit_flag_sensitivity.py`. Script trích lại hai PCAP bằng project v2 vào thư mục tạm, chuẩn hóa bằng cùng feeder/normalize, nạp model thật và kiểm tra mọi ngưỡng split của 12 cột có `Flag` trong tên. Chỉ tạo bản sao vector **trong bộ nhớ**, đổi cờ nguyên không âm thành `(value > 0)`, rồi so cả xác suất 15 lớp và lá cây. Không tính FPR vì PCAP chưa có ground truth xác minh.

Model `52eb5a671ee82109`: các cột cờ được dùng trong cây chỉ có ngưỡng `1`; các cột còn lại không có split. Với split số `x < 1`, giá trị nguyên dương 1 và 18 đi cùng nhánh; 0 giữ nguyên. Do đó phép nhị phân hóa này bảo toàn đường cây khi giữ nguyên các đặc trưng khác, với model hiện tại và miền cờ nguyên không âm đã kiểm tra. Không suy rộng sang model khác, cờ âm/NaN hoặc những phép biến đổi feature khác.

| PCAP | Flow | Vector đổi vì nhị phân hóa cờ | Nhãn đổi | Chênh xác suất lớn nhất | Lá cây | Nhãn trước và sau |
|---|---:|---:|---:|---:|---|---|
| `test.pcapng` | 33 | 29 | 0 | 0 | Giống hoàn toàn | 28 Benign, 5 Hulk |
| `tesst2.pcapng` | 59 | 45 | 0 | 0 | Giống hoàn toàn | 56 Benign, 3 Hulk |

**Kết luận:** giả thuyết chỉ đổi count→has_flag sẽ giảm Hulk không được ủng hộ trên model/hai PCAP này; 74/92 vector đổi nhưng 92/92 dự đoán/xác suất/lá giữ nguyên. Chưa tìm ra nguyên nhân đầy đủ của 8 nhãn Hulk; chúng vẫn là dự đoán, không phải nhãn tấn công đã xác minh. Lệch cờ có thể tác động khoảng cách lấy mẫu LIME dù không đổi nhánh XGBoost; script này **không tính lại SHAP/LIME**, không kết luận hiệu ứng của phép biến đổi lên chúng.

Bằng chứng aggregate và checksum model/encoder/PCAP/code: [flag_sensitivity_evidence_20261018.json](flag_sensitivity_evidence_20261018.json). Không chứa packet payload/IP hoặc từng vector cá nhân. Môi trường lần chạy: Python chính 3.14.7, XGBoost 3.4.1, sklearn 1.9.1, NumPy 2.5.3, pandas 3.0.6; capture Python 3.13.0, CICFlowMeter 0.5.0, Scapy 2.8.0, NumPy 2.5.4. Có cảnh báo pickle XGBoost và encoder sklearn được lưu bằng 1.8.0; ghi nhận giới hạn tái lập, chưa coi là nguyên nhân báo nhầm và không tự ghi đè artifacts.

### Sáu fixture vòng đời v2 mới — xác nhận hành vi, chưa sửa lỗi

| Fixture trong Stage20 | Quan sát tái hiện được | Ý nghĩa cho bước sửa tiếp |
|---|---|---|
| Một gói rồi im lặng | GC tại tuổi 90s/239s chưa xuất; đúng idle 240s xuất | Duration 90s là khoảng timestamp packet, không phải timer tuổi wall-clock cho mọi flow |
| FIN hoặc RST | Flow vẫn mở cho đến timeout/flush | Chưa có state machine kết thúc TCP; cần thiết kế riêng cho FIN hai chiều, RST, retransmission |
| Packet tại mốc duration | Chuỗi 0,89,90 xuất 3 packet; chuỗi 0,89,180 xuất một flow duration 180s | Gói kích hoạt được thêm trước kiểm tra; 90s không phải trần duration cứng |
| Idle đúng 240s | Nếu GC chạy trước packet mới: 2 flow; nếu chưa chạy: 1 flow, đều bảo toàn 2 packet | `process` dùng `>240`, GC dùng `>=240`; segmentation phụ thuộc thứ tự GC tại ranh giới |
| Tái sử dụng cùng tuple | SYN, SYN-ACK, RST, SYN mới vẫn thành một flow trước timeout | Kết nối mới có thể lẫn với kết nối trước; chỉ đổi timeout chưa đủ |
| Packet timestamp 0,2,1 | `flow_iat_min` và `fwd_iat_min` bằng -1 | Active/Idle đã né gap âm nhưng IAT vẫn tính theo thứ tự nhận; cần chính sách rõ cho packet lệch thứ tự |

Các test có tên `test_v2_*` ghi lại **baseline hiện hành**, không phải tiêu chí mong muốn cho adapter mới. PASS nghĩa tái hiện được giới hạn, không có nghĩa đã sửa. Khi sửa phiên bản mới phải giữ kiểm thử baseline tương ứng và thêm kỳ vọng mới; không đổi assertion cho đẹp kết quả.

### Kiểm thử và tái lập

Từ thư mục gốc, không cần chạy API/UI, không phát traffic:

```powershell
.\RQ3_IDS_System\.venv_capture\Scripts\python.exe -B RQ3_IDS_System/scripts/stage20_test_capture_adapter.py
python -B RQ3_IDS_System/scripts/stage23_audit_feature_semantics.py --self-test
python -B RQ3_IDS_System/scripts/stage25_audit_flag_sensitivity.py
```

Kết quả mới ngày 18/10: **Stage20 21/21 PASS** (15 cũ + 6 characterization), **Stage23 self-test 3/3 PASS**, Stage25 trích và so đủ 92 flow, 0 nhãn/xác suất đổi. Stage23 self-test chỉ kiểm tra công thức audit, không chạy full scan. Stage25 có `--output <JSON mới>` nếu muốn lưu lại; từ chối ghi đè bằng chứng cũ. Lượt này đã dùng tham số đó để tạo JSON liên kết phía trên. Không chạy lại stage14/24 hoặc bắt live ở HT2.1.

### Quyết định sau HT2.1

1. Không nhị phân hóa cờ trong runtime; không train lại và không thay LIME để tạo biểu đồ.
2. Chưa chứng nhận tương thích train–PCAP. Cần đọc tiếp tài liệu nguồn và tìm preprocessing/bản extractor lịch sử hoặc cặp original PCAP–CSV. Không để việc thiếu nguồn chặn kiểm thử vòng đời độc lập.
3. **HT2.2 đề xuất:** chốt chính sách vòng đời trước khi sửa: ranh giới idle nhất quán, packet lệch thứ tự, giới hạn duration, FIN/RST và tuple tái sử dụng. Triển khai từng phần có version, kiểm thử bảo toàn packet, đối chiếu lại hai PCAP; không gộp mọi thay đổi vào một commit lớn. Ưu tiên lỗi ranh giới idle đã có fixture nhỏ tái hiện.
4. HT2.1 không hoàn thành E2/E3/E4/E5; đây là bằng chứng chẩn đoán và regression phục vụ chúng. Xem tiến độ trong [plan.md](plan.md).

---

<a id="semantics"></a>

# Hợp đồng đặc trưng: bằng chứng train/test và capture v1

Ngày 16/10/2026. Trạng thái: **đã thu hẹp các quy ước; chưa chứng nhận tương thích V3 và chưa đổi đầu vào production**.

**Bước triển khai tiếp theo đã có:** [v2 và candidate thử nghiệm](operations.md#stability-v2). V2 sửa lỗi initial window=0; candidate chỉ thay ba nhóm quy ước được nêu rõ, chưa chứng nhận tương thích toàn bộ. Báo cáo và JSON tại đây giữ kết quả audit v1; stage23 chọn class v1 tường minh khi tái lập.

Đây là bước tiếp nối [audit baseline](feature_compatibility.md#baseline-audit) và [adapter v1](feature_compatibility.md#adapter-v1), không thay thế bằng chứng trước sửa. Script mới kiểm tra quan hệ từng dòng trên **toàn bộ 2.800.000 train + 700.000 test**, không lấy mẫu. Test từng được dùng trong tuning RQ1; việc đọc lại này không làm nó thành tập đánh giá độc lập.

## Kết quả có thể khẳng định từ dữ liệu hiện có

| Quy ước | Bằng chứng train | Bằng chứng test | Capture v1 hiện tại / quyết định |
|---|---|---|---|
| Std độ dài forward, đúng 2 gói có min/max khác nhau | 35.079/35.079 khớp sample SD, 0 khớp population SD | 8.814/8.814 khớp sample, 0 population | v1 dùng population. Có bằng chứng phân biệt trực tiếp, không chỉ đoán từ source Java. |
| Std độ dài backward, cùng điều kiện | 59.954/59.954 sample, 0 population | 14.901/14.901 sample, 0 population | Tương tự forward; chưa được suy rộng thành mọi cột std. |
| Down/Up ở những flow có `bwd/fwd` không nguyên | 1.057.559/1.057.559 khớp floor, 0 khớp chia thực | 264.686/264.686 floor, 0 chia thực | v1 chia thực; fixture 2 forward/1 backward trả 0,5. |
| Window UDP cả hai chiều | 622.298/622.298 đều -1 | 155.488/155.488 đều -1 | v1 trả 0; cần sentinel riêng thay vì dùng 0 làm “chưa thấy”. |
| Window backward khi TCP không có gói backward | 826.983/826.983 đều -1 | 206.246/206.246 đều -1 | v1 trả 0. |
| Quan hệ `Pkt Size Avg × n = Pkt Len Mean × (n+1)`, n = fwd+bwd | 2.800.000/2.800.000 khớp | 700.000/700.000 khớp | v1 gán hai mean bằng nhau. Không thể chỉ đổi frame sang payload rồi coi đã khớp. |
| Subflow packet = tổng packet, xét chiều có gói | Khớp toàn bộ forward/backward đủ điều kiện | Khớp toàn bộ đủ điều kiện | v1 cũng sao chép tổng. Chưa có bằng chứng cần đổi cột này theo thuật toán Java master khác. |

So sánh dùng `rtol=2e-5`, `atol=1e-3` vì Parquet là float32. “Khớp” là trong dung sai đó, không phải bằng nhau từng bit. Với SD hai quan sát, chỉ xét chênh lệch min/max ≥1 để hai công thức không trùng nhau khi bằng 0. Mẫu đủ điều kiện forward và backward có thể thuộc cùng flow, không cộng chúng thành số flow duy nhất.

Đối với quan hệ độ dài trung bình, có nhiều dòng toàn 0 thỏa đẳng thức một cách hiển nhiên. Nhưng trên riêng dòng có `Pkt Len Mean > 0`, giả thuyết hai mean bằng nhau chỉ khớp 1.640/1.816.319 train và 407/454.300 test. Vì vậy khác biệt không chỉ do các dòng 0. Kiểm tra này **không chứng minh packet đầu bị đếm hai lần** trong extractor lịch sử; chỉ phát hiện quan hệ số học phải tái hiện/giải thích trước khi tuyên bố tương thích.

## Những phần chưa được chốt

- **IAT std:** với 3 packet một chiều (giả thuyết có 2 khoảng), sample SD khớp Fwd 450.678/463.061 train, 112.772/115.780 test; Bwd 66.771/67.362 train, 16.611/16.766 test. Population SD khớp 0 ở các tập đủ điều kiện. Vẫn có ngoại lệ, nên chưa tự đổi tất cả IAT sang sample SD hoặc kết luận số khoảng lịch sử luôn n−1.
- **Payload/frame/header:** fixture tách rõ hai TCP packet có payload [0,100], frame [62,154], transport header [28,20]. v1 trả tổng byte 216, header 40 (header IPv4) và SD 46 (population của frame); sample SD payload sẽ khoảng 70,7107. Đây là những đầu vào khác nhau, không phải khác đơn vị. Header `20×n` chỉ khớp 828.708/2.800.000 forward train, 259.805/1.924.318 backward train; chỉ quan hệ số học này chưa xác định header lịch sử gồm những lớp nào.
- **Subflow byte:** forward khớp tổng byte ở mọi dòng có byte; backward còn 10 ngoại lệ train và 1 test. Không ép các ngoại lệ về giá trị mong muốn hoặc gọi tất cả subflow sai.
- **Cờ TCP và bulk:** bằng chứng từ audit trước vẫn còn: cả daily cleaned đã có cờ 0/1 và bulk hằng 0. Chưa tìm thấy bước preprocessing hay bản extractor đã sinh ra chúng; không clip cờ/zero bulk để ép miền dữ liệu.
- **Timeout/TCP close:** v1 vẫn 90s duration /240s idle, chưa có TCP close state machine. Không xác nhận đó là segmentation đã sinh train. Thay timeout có thể đổi toàn bộ nhóm thống kê.

Một lỗi độc lập nữa được fixture xác nhận: window TCP đầu =0, gói sau =4096 thì v1 trả “initial window”=4096. Đó là hậu quả upstream dùng 0 làm trạng thái chưa quan sát, không phải thiếu mẫu train. Lỗi được ghi nhận để sửa trong phiên bản adapter tiếp theo cùng các test bảo toàn window=0; **chưa sửa runtime trong đợt audit này**.

## Truy vết nguồn train

Đã chạy thêm cùng phép kiểm tra trên toàn bộ **10 daily cleaned, 15.589.784 dòng**. Các kết quả sau đã có trước khi tạo tập con train/test: SD độ dài sample khớp Fwd 230.478/230.478, Bwd 395.974/395.974 trường hợp phân biệt được; floor ratio khớp 6.113.560/6.113.560; window UDP=-1 khớp 4.128.854/4.128.854 và TCP thiếu backward=-1 khớp 3.641.860/3.641.860; quan hệ mean n/n+1 khớp toàn bộ 15.589.784 dòng. Subflow packet cũng khớp tổng trên mọi dòng đủ điều kiện, nhưng subflow byte backward còn 52 ngoại lệ/10.130.056. Daily và train/test có thể trùng dữ liệu, **không cộng số dòng làm các quan sát độc lập**. Những kết quả này xác định hiện tượng đã có ở daily cleaned, không xác định nó có sẵn ở original CSV trước cleaning hay không.

- Trong workspace có daily `*_clean.parquet`, train/test đã xử lý và mã RQ1 đọc trực tiếp hai tập đó.
- `stage03_build_clean_dataset.py` chỉ tạo Tập B từ train/test đã có; không phải script tạo daily cleaned hay split train/test ban đầu.
- Kiểm tra tên file mã trong lịch sử Git chưa tìm thấy pipeline tạo các tập đầu vào 2018, original 2018 CSV hay cặp original PCAP–CSV tương ứng. Các CSV CICIDS2017/UNSW-NB15 là dataset khác, không dùng chứng nhận model 2018. Hai PCAP cá nhân cũng không phải PCAP gốc ứng với các dòng train.
- Vì vậy chưa thể xác định cờ/bulk/quan hệ mean là hành vi extractor lịch sử hay tác động preprocessing. Đây là giới hạn truy vết, không phải kết luận dữ liệu vô dụng.

## Điều kiện để chuyển sang adapter tương thích train

1. Tìm lại script/notebook cleaning/sampling/split 2018 hoặc nguồn tải có phiên bản/checksum. Ưu tiên một PCAP gốc kèm CSV sinh từ cùng bản CICFlowMeter và tham số timeout.
2. Chốt hợp đồng theo từng nhóm, ghi rõ phần tái hiện quy ước lịch sử và phần sửa lỗi số học; không dùng nhãn model dự đoán làm oracle chọn công thức.
3. Tạo adapter phiên bản mới **ở chế độ thử nghiệm**, giữ vector trước/sau và khóa model/LIME làm baseline. Kiểm thử payload/header/options/window=0/missing window/sample SD/ratio/mean/timeout độc lập.
4. Trích lại hai PCAP, so sánh feature, xác suất, SHAP additivity và LIME neighborhood. Chỉ gọi accuracy/FPR khi có ground truth xác minh; “Hulk giảm” chưa đủ chứng minh extractor đúng.
5. Chỉ đổi mặc định sau khi có báo cáo sai khác và kiểm thử hồi quy. Dữ liệu/DB cũ phải giữ version cũ hoặc unknown, không sửa ngược cho đẹp kết quả.

Trong lúc chờ bằng chứng nguồn, có thể làm riêng retry/checkpoint/idempotency cho feeder: việc đó cải thiện giao nhận nhưng không giải quyết tính đúng đặc trưng. Không cần train lại hoặc thay kernel LIME để hoàn thành bước audit này.

## Tái lập và phạm vi kiểm thử

Từ thư mục gốc:

```powershell
python -B RQ3_IDS_System/scripts/stage23_audit_feature_semantics.py --self-test
python -B RQ3_IDS_System/scripts/stage23_audit_feature_semantics.py --include-daily --output RQ3_IDS_System/docs/feature_semantics_evidence_20261016.json
```

Môi trường chính cần numpy/pyarrow/PyYAML; fixture chạy trong `.venv_capture` đã cài sẵn. Nếu sandbox chặn quyền ghi thư mục tạm giữa hai Python, cần cấp quyền chạy phù hợp. Script không phát gói, không gọi API, không đọc/ghi DB demo, không chạy train và không sửa model/LIME/CSV live. JSON chỉ chứa số tổng hợp và fixture địa chỉ tài liệu RFC5737, không giữ IP cá nhân/payload bắt thực tế.

- 3 self-test PASS: phân biệt công thức SD/ratio, mẫu đủ điều kiện, lọc giá trị không hữu hạn và mẫu rỗng.
- Chạy lại 10 regression test adapter v1 (`stage20_test_capture_adapter.py`): PASS. Không có thay đổi runtime trong đợt này.
- Các assertion fixture capture v1 PASS: length/header/std, window thiếu, window=0 bị ghi đè, ratio, subflow và bulk. Assertion xác nhận lỗi còn tồn tại không có nghĩa lỗi đã được sửa.
- [JSON đầy đủ và mẫu số từng giả thuyết](feature_semantics_evidence_20261016.json); có SHA256 file dữ liệu và mã audit/adapter để truy vết lần chạy. Không dùng `--include-daily` nếu chỉ muốn quét train/test (sẽ tạo báo cáo phạm vi nhỏ hơn).

**Kết luận sử dụng:** đường bắt–CSV–API–UI đã chạy được trong các phiên đo trước; ngữ nghĩa train/PCAP chưa hoàn tất. Chưa thể hứa cảnh báo nhầm hoặc LIME đã được xử lý chỉ nhờ sửa năm lỗi của adapter v1.

---

<a id="adapter-v1"></a>

# Bản sửa extractor và kiểm tra đường realtime

Ngày cập nhật: 16/10/2026, GMT+7. Phiên bản: `rq3-cfm-0.5.0-fixes-v1`, dựa trên Python CICFlowMeter 0.5.0. Mã sửa nằm trong `app/capture_adapter.py`; không sửa site-packages.

**Tài liệu phiên bản lịch sử:** mặc định hiện tại đã chuyển sang v2 sửa thêm window=0. Xem [bản v2 và cơ chế phục hồi](operations.md#stability-v2); dùng `--extractor project-v1` để tái lập bản được mô tả tại đây. Số liệu/JSON v1 bên dưới được giữ nguyên.

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

Audit tiếp theo đã thu hẹp một số quy ước bằng quan hệ trên toàn bộ train/test, không chỉ min/max: [hợp đồng ngữ nghĩa và bằng chứng mới](feature_compatibility.md#semantics). Có khác biệt sample SD độ dài, floor ratio, sentinel window và quan hệ hai mean; fixture còn xác nhận initial window=0 bị upstream ghi đè. Bản v1 chưa sửa những phần đó. Ngược lại subflow packet=số packet tổng khớp tập đủ điều kiện, chưa có căn cứ tự thay theo Java master.

- Length/header vẫn dùng quy ước upstream Python; chưa chuyển sang payload/header transport của bản Java tham chiếu. Std, subflow, missing window và binary flag convention chưa chứng nhận tương thích dataset V3.
- Không clip cờ >1 về 1, không zero bulk, không train lại model và không thay cấu hình LIME. LIME vẫn còn vấn đề đã ghi nhận.
- Chỉ IPv4 TCP/UDP; packet ngoài phạm vi bị bỏ và đếm trong `ignored_packets`. BPF live cũng giới hạn phạm vi này.
- FlowSession giữ packet trong RAM đến khi xuất; đây chưa phải thiết kế bắt gói tải cao. Hàng đợi SHAP 200 không giới hạn RAM của bộ bắt.
- Cần chốt hợp đồng đặc trưng train, thiết kế timeout/TCP close nếu yêu cầu độ trễ thấp hơn, sửa retry/checkpoint feeder và đo tải dài trước khi đánh giá triển khai thực tế.

---

<a id="baseline-audit"></a>

# Kiểm tra tương thích đặc trưng train và PCAP

Ngày kiểm tra: 16/10/2026, GMT+7. Model hiện tại: `52eb5a671ee82109`. Extractor cài trong `.venv_capture`: Python CICFlowMeter 0.5.0.

**Đã có bước sửa sau audit:** [adapter v1](feature_compatibility.md#adapter-v1) sửa 5 lỗi tái hiện được và là mặc định capture mới. Báo cáo/ma trận này giữ nguyên chứng cứ baseline trước sửa; script stage19 dùng `--extractor legacy` ở phép kiểm tra production baseline. Không dùng các nhận định lịch sử này để bỏ qua các thay đổi phiên bản.

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
- [Ma trận đủ 78 đặc trưng](feature_compatibility.md#matrix-78).

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

**Cập nhật sau adapter v1:** [audit ngữ nghĩa từng dòng train/test](feature_compatibility.md#semantics) bổ sung bằng chứng sample SD độ dài, floor ratio, missing window, quan hệ mean n/n+1 và subflow. Các số baseline/ma trận ở trên được giữ nguyên; không phải trạng thái hiện hành của từng lỗi đã sửa.

1. Tạo adapter/extractor trong mã dự án có phiên bản và regression fixture; không sửa trực tiếp site-packages. Sửa nhóm lỗi tái hiện được: đếm gói đầu, CWR, IAT một khoảng, active/idle và flow key có protocol.
2. Chốt hợp đồng length/header/std/subflow/window/timeout dựa trên nguồn train, lấy original CSV/PCAP hoặc pipeline preprocessing để xử lý phần chưa rõ. Giữ raw và transformed features để truy vết; không tự clip cờ >1 về 1 hoặc zero bulk.
3. Trích lại PCAP vào lượt thử nghiệm riêng, so sánh feature/dự đoán/SHAP/LIME với bản cũ. Giữ model làm baseline; nếu đổi định nghĩa đầu vào phải ghi rõ phiên bản và chạy lại đánh giá.
4. Chỉ quyết định train mới sau khi hoàn thành đối chiếu và có tập đánh giá có nhãn được xác minh. Tách vấn đề giao nhận feeder/hàng đợi khỏi tính đúng đặc trưng.

---

<a id="matrix-78"></a>

# Đối chiếu đủ 78 đặc trưng

Sinh từ stage19; schema khớp không đồng nghĩa ngữ nghĩa tương thích. Trạng thái dựa trên fixture và source đã kiểm tra. Java master chỉ là tham chiếu hiện tại, chưa xác nhận đúng binary V3 đã tạo dataset 2018.

| # | Đặc trưng model | Cột Python | Nhận định | Bằng chứng/giới hạn |
|---|---|---|---|---|
| 1 | Dst Port | dst_port | checked_fixture_only | Giá trị/đổi đơn vị khớp fixture đơn giao thức; chưa chứng nhận toàn bộ flow segmentation. |
| 2 | Protocol | protocol | checked_fixture_only | Giá trị/đổi đơn vị khớp fixture đơn giao thức; chưa chứng nhận toàn bộ flow segmentation. |
| 3 | Flow Duration | flow_duration | checked_fixture_only | Giá trị/đổi đơn vị khớp fixture đơn giao thức; chưa chứng nhận toàn bộ flow segmentation. |
| 4 | Tot Fwd Pkts | tot_fwd_pkts | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 5 | Tot Bwd Pkts | tot_bwd_pkts | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 6 | TotLen Fwd Pkts | totlen_fwd_pkts | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 7 | TotLen Bwd Pkts | totlen_bwd_pkts | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 8 | Fwd Pkt Len Max | fwd_pkt_len_max | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 9 | Fwd Pkt Len Min | fwd_pkt_len_min | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 10 | Fwd Pkt Len Mean | fwd_pkt_len_mean | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 11 | Fwd Pkt Len Std | fwd_pkt_len_std | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 12 | Bwd Pkt Len Max | bwd_pkt_len_max | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 13 | Bwd Pkt Len Min | bwd_pkt_len_min | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 14 | Bwd Pkt Len Mean | bwd_pkt_len_mean | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 15 | Bwd Pkt Len Std | bwd_pkt_len_std | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 16 | Flow Byts/s | flow_byts_s | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 17 | Flow Pkts/s | flow_pkts_s | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 18 | Flow IAT Mean | flow_iat_mean | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 19 | Flow IAT Std | flow_iat_std | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 20 | Flow IAT Max | flow_iat_max | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 21 | Flow IAT Min | flow_iat_min | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 22 | Fwd IAT Tot | fwd_iat_tot | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 23 | Fwd IAT Mean | fwd_iat_mean | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 24 | Fwd IAT Std | fwd_iat_std | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 25 | Fwd IAT Max | fwd_iat_max | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 26 | Fwd IAT Min | fwd_iat_min | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 27 | Bwd IAT Tot | bwd_iat_tot | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 28 | Bwd IAT Mean | bwd_iat_mean | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 29 | Bwd IAT Std | bwd_iat_std | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 30 | Bwd IAT Max | bwd_iat_max | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 31 | Bwd IAT Min | bwd_iat_min | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 32 | Fwd PSH Flags | fwd_psh_flags | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 33 | Bwd PSH Flags | bwd_psh_flags | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 34 | Fwd URG Flags | fwd_urg_flags | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 35 | Bwd URG Flags | bwd_urg_flags | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 36 | Fwd Header Len | fwd_header_len | definition_mismatch_reference | Python dùng header IPv4; Java tham chiếu dùng header transport; fixture UDP/options phân biệt được. |
| 37 | Bwd Header Len | bwd_header_len | definition_mismatch_reference | Python dùng header IPv4; Java tham chiếu dùng header transport; fixture UDP/options phân biệt được. |
| 38 | Fwd Pkts/s | fwd_pkts_s | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 39 | Bwd Pkts/s | bwd_pkts_s | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 40 | Pkt Len Min | pkt_len_min | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 41 | Pkt Len Max | pkt_len_max | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 42 | Pkt Len Mean | pkt_len_mean | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 43 | Pkt Len Std | pkt_len_std | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 44 | Pkt Len Var | pkt_len_var | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 45 | FIN Flag Cnt | fin_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 46 | SYN Flag Cnt | syn_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 47 | RST Flag Cnt | rst_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 48 | PSH Flag Cnt | psh_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 49 | ACK Flag Cnt | ack_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 50 | URG Flag Cnt | urg_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 51 | CWE Flag Count | cwr_flag_count | confirmed_extractor_defect | Cột CWR sao chép Fwd URG Flags; fixture tách CWR/URG xác nhận sai. |
| 52 | ECE Flag Cnt | ece_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 53 | Down/Up Ratio | down_up_ratio | definition_mismatch_reference | Python chia số thực và chịu lặp gói đầu; train chỉ quan sát số nguyên; Java tham chiếu chia nguyên. |
| 54 | Pkt Size Avg | pkt_size_avg | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 55 | Fwd Seg Size Avg | fwd_seg_size_avg | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 56 | Bwd Seg Size Avg | bwd_seg_size_avg | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 57 | Fwd Byts/b Avg | fwd_byts_b_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 58 | Fwd Pkts/b Avg | fwd_pkts_b_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 59 | Fwd Blk Rate Avg | fwd_blk_rate_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 60 | Bwd Byts/b Avg | bwd_byts_b_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 61 | Bwd Pkts/b Avg | bwd_pkts_b_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 62 | Bwd Blk Rate Avg | bwd_blk_rate_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 63 | Subflow Fwd Pkts | subflow_fwd_pkts | definition_unverified | Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train. |
| 64 | Subflow Fwd Byts | subflow_fwd_byts | definition_unverified | Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train. |
| 65 | Subflow Bwd Pkts | subflow_bwd_pkts | definition_unverified | Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train. |
| 66 | Subflow Bwd Byts | subflow_bwd_byts | definition_unverified | Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train. |
| 67 | Init Fwd Win Byts | init_fwd_win_byts | sentinel_mismatch | Train có -1; Python khởi tạo 0 khi thiếu chiều/TCP, dùng 0 làm điều kiện cập nhật lại window. |
| 68 | Init Bwd Win Byts | init_bwd_win_byts | sentinel_mismatch | Train có -1; Python khởi tạo 0 khi thiếu chiều/TCP, dùng 0 làm điều kiện cập nhật lại window. |
| 69 | Fwd Act Data Pkts | fwd_act_data_pkts | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 70 | Fwd Seg Size Min | fwd_seg_size_min | definition_mismatch_reference | Python dùng header IPv4; Java tham chiếu dùng header transport; fixture UDP/options phân biệt được. |
| 71 | Active Mean | active_mean | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 72 | Active Std | active_std | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 73 | Active Max | active_max | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 74 | Active Min | active_min | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 75 | Idle Mean | idle_mean | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 76 | Idle Std | idle_std | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 77 | Idle Max | idle_max | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 78 | Idle Min | idle_min | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
