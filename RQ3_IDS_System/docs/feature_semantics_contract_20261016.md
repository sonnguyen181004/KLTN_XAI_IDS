# Hợp đồng đặc trưng: bằng chứng train/test và capture v1

Ngày 16/10/2026. Trạng thái: **đã thu hẹp các quy ước; chưa chứng nhận tương thích V3 và chưa đổi đầu vào production**.

**Bước triển khai tiếp theo đã có:** [v2 và candidate thử nghiệm](stability_update_20261016.md). V2 sửa lỗi initial window=0; candidate chỉ thay ba nhóm quy ước được nêu rõ, chưa chứng nhận tương thích toàn bộ. Báo cáo và JSON tại đây giữ kết quả audit v1; stage23 chọn class v1 tường minh khi tái lập.

Đây là bước tiếp nối [audit baseline](feature_compatibility_audit_20261016.md) và [adapter v1](capture_adapter_v1.md), không thay thế bằng chứng trước sửa. Script mới kiểm tra quan hệ từng dòng trên **toàn bộ 2.800.000 train + 700.000 test**, không lấy mẫu. Test từng được dùng trong tuning RQ1; việc đọc lại này không làm nó thành tập đánh giá độc lập.

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
