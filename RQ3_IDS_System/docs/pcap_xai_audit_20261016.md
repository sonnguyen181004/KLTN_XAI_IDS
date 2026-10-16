# Kiểm tra lại model, SHAP và LIME trên hai PCAP — 16/10/2026

## Phạm vi và cách làm

Đọc snapshot toàn bộ các flow nguồn `pcap_replay` trong DB ở chế độ `mode=ro`. Không gọi `/predict` hoặc `/explain`, không sửa kết quả demo. Nạp đúng model/encoder hiện tại, tính lại dự đoán 92 flow; tính SHAP/LIME cho cả 8 cảnh báo trong bộ nhớ. Trích lại hai PCAP gốc bằng cùng CICFlowMeter vào thư mục tạm rồi đối chiếu 78 đặc trưng cùng metadata IP/cổng.

Lệnh tái lập: `python -B RQ3_IDS_System/scripts/stage17_audit_pcap_xai.py`. Script in từng cảnh báo và tổng hợp JSON, không ghi DB. Kết quả dưới đây là ảnh chụp kiểm tra tại thời điểm này; chạy lại khi có thêm dữ liệu sẽ có tổng số khác.

## Kết quả theo file

| File | Flow | Benign | Hulk | Đặc trưng trích lại khớp |
|---|---:|---:|---:|---:|
| tesst2.pcapng | 59 | 56 | 3 | 59/59 |
| test.pcapng | 33 | 28 | 5 | 33/33 |

- 92/92 nhãn dự đoán và toàn bộ xác suất khớp kết quả lưu; sai số xác suất lớn nhất = 0.
- 8/8 Top-5 SHAP khớp tên, giá trị và phi khi tính lại. Sai số additivity lớn nhất ≈ 2,861 × 10⁻⁶ trên raw margin.
- Các phi giống nhau giữa nhiều flow, ví dụ FIN phi ≈ 5,86522, cũng tái tạo được bằng TreeSHAP thật; không phải số được gán cứng trong UI.
- Đây là **tính nhất quán tính toán**, không phải chứng minh 8 flow thực sự là tấn công. PCAP không có nhãn thật được xác nhận trong DB.

## LIME của từng cảnh báo

| Flow ID rút gọn | File | P(Hulk) | Mẫu weight khác 0 | Weight lớn nhất ngoài mẫu gốc | ESS | Nguyên nhân nổi bật trong các đặc trưng lệch nền |
|---|---|---:|---:|---:|---:|---|
| b1e78518 | tesst2 | 96,89% | 1000 | 2,16e-93 | ≈1 | ACK=28, FIN=2 |
| 4546093c | tesst2 | 72,97% | 1 | 0 | 1 | Bwd Blk Rate Avg≈1,264e9; Bwd Byts/b Avg=5184 |
| e8f84c26 | tesst2 | 96,79% | 1000 | 5,15e-15 | ≈1 | FIN=1 hiếm trong nền; Fwd PSH=3, ACK=5 |
| d8edff45 | test | 97,27% | 1000 | 8,18e-51 | ≈1 | FIN=2, ACK=16 |
| 8c2be2b6 | test | 96,88% | 1000 | 2,56e-103 | ≈1 | ACK=30, FIN=2 |
| 0993535d | test | 93,19% | 1000 | 1,30e-34 | ≈1 | FIN=2, ACK=6, Fwd PSH=2 |
| 2dae051e | test | 97,17% | 1000 | 1,09e-15 | ≈1 | FIN=1 hiếm trong nền; ACK=8, Fwd PSH=2 |
| 066e6990 | test | 78,74% | 1 | 0 | 1 | Fwd bulk rate≈3,299e6, Bwd bulk rate≈24239 |

Cả 8 lần tính lại đều `insufficient_neighborhood`. Bốn flow đã có diagnostics lưu trong DB tái lập đúng toàn bộ diagnostics; bốn flow chưa yêu cầu LIME trước đó chỉ được tính trong bộ nhớ của audit, không tự ghi kết quả vào UI.

**Phân biệt quan trọng:** chỉ 2/8 flow có 999 trọng số bằng đúng 0. Sáu flow còn lại có 1000 trọng số khác 0 nhưng phần ngoài mẫu gốc nhỏ đến mức gần như không góp vào phép hồi quy. Không được dùng câu “999 trọng số bằng 0” cho mọi flow. Với flow b1e78518 trong ảnh mới, raw R² = 0, không phải 1; R²=1 là trường hợp 4546093c/066e6990. ESS gần 1 mới là điểm chung.

## Đối chiếu toàn bộ tập train, không chỉ 2.000 mẫu nền

Đã đọc theo batch các cột liên quan trong 2.800.000 dòng `train_set.parquet`:

- FIN/ACK/SYN/RST/PSH/Fwd PSH đều chỉ nằm trong [0,1], không có giá trị >1.
- FIN khác 0 ở 10.574/2.800.000 dòng; FIN=1 có thể hợp lệ nhưng là giá trị hiếm, do đó độ lệch chuẩn hóa lớn vẫn có thể xuất hiện mà không vượt min/max.
- Bwd Blk Rate Avg, Fwd Blk Rate Avg, Bwd Byts/b Avg đều bằng 0 trên toàn bộ tập train đã kiểm tra.
- Extractor PCAP hiện tại đếm số gói mang cờ thực tế nên ACK có thể 28/30, FIN có thể 2; bulk thực tế có thể khác 0. Đây là khác biệt hỗ trợ/phân bố đặc trưng cần xử lý, không chỉ vấn đề cỡ mẫu nền.

Chưa khẳng định công đoạn nào đã làm các cờ trong dataset trở thành [0,1], và chưa tự sửa extractor hoặc ép flag >1 về 1. Cần xác minh quy ước dataset trước khi đổi adapter.

## Vì sao LIME sinh mẫu không phù hợp?

Đối chiếu mã thư viện đang cài và cấu hình RQ2/RQ3:

- `discretize_continuous=False`, không khai báo categorical features.
- `sample_around_instance=False` là mặc định: mẫu số được sinh quanh mean/scale của nền, không quanh chính giá trị của flow hiện tại.
- Kernel width = 3.312. Khoảng cách chuẩn hóa lớn làm trọng số kernel cực nhỏ hoặc underflow về 0.
- Mẫu gốc vẫn có distance=0/weight=1, nên gần như một mình chi phối mô hình hồi quy LIME.
- Các cờ/cổng hiện được perturb như biến liên tục; cần đánh giá tính hợp lệ miền của mẫu sinh nếu thiết kế một chế độ LIME mới.

Đây là nguyên nhân số học được kiểm tra; không thể chỉ thay thông báo UI là giải quyết được neighborhood.

## Mẫu đối chứng tập B

Lấy một dòng đầu của mỗi lớp có trong tập B (13 dòng), giải thích lớp model dự đoán với seed audit cố định. Cùng implementation LIME cho:

- 10/13 vượt các kiểm tra chống suy biến tối thiểu; R² dao động khoảng 0,306–0,985, ESS khoảng 2,01–229,75.
- 3/13 vẫn suy biến: mẫu tham chiếu Brute Force -Web, Brute Force -XSS và DDOS attack-LOIC-UDP.
- Mẫu tham chiếu Hulk: ESS≈207,11, R²≈0,526; mẫu Benign: ESS≈40,76, R²≈0,306.

Vì vậy LIME không bị vô hiệu hóa hoặc UI ép mọi flow thất bại. Nhưng lỗi không chỉ xuất hiện trên traffic live: cấu hình khóa cũng có giới hạn đối với một số dòng đối chứng. “ok” chỉ nghĩa không vướng guard số học, không chứng nhận giải thích chất lượng cao. 13 mẫu này không phải thống kê đại diện toàn bộ tập B/RQ2.

## Kiểm tra nội dung explain có gán cứng không?

- Nhãn/xác suất lấy từ model; Top-5 và dấu lấy từ SHAP/LIME; số mẫu/ESS/weight lấy từ diagnostics của flow. Không tìm thấy nhãn Hulk, 96,89%, FIN phi hay 999 mẫu bị gán cố định để làm kết quả.
- Từ điển định nghĩa đặc trưng và mẫu câu giải thích là nội dung tĩnh có chủ đích. Giá trị, tên lớp và dấu được điền từ dữ liệu từng flow; đây không phải lời giải thích sinh tự do.
- Câu mẫu chung nói về trường hợp R²=1 có thể gây hiểu nhầm khi flow thực tế raw R²=0. Nên trình bày raw R² đúng flow và tách rõ ví dụ tổng quát.
- Phần nêu đặc trưng lệch hiện ưu tiên cột nền hằng. Điều đó phù hợp với flow bulk, nhưng chưa kể đầy đủ trường hợp ACK/FIN lệch mạnh dù nền không hằng. Cần dùng diagnostics riêng từng flow nếu cải thiện câu giải thích nguyên nhân.

## Kết luận và hướng sửa tiếp theo

Bản sửa trước đã ngăn UI trình bày LIME suy biến như giải thích tốt, **chưa giải quyết nguyên nhân neighborhood suy biến**. Audit này không thay model, features, cấu hình nghiên cứu hoặc DB demo.

Hướng triển khai cần kiểm chứng riêng, không chỉ đổi văn bản:

1. Xác minh quy ước đặc trưng extractor/train (cờ, bulk, header…) rồi thiết kế adapter có phiên bản, không ép số để tăng Benign.
2. Tách chế độ LIME thực nghiệm cho traffic live khỏi cấu hình RQ2 khóa; kiểm tra sampling/biến rời rạc/cột hằng và tính hợp lệ mẫu sinh.
3. Đánh giá ESS, độ khớp, dự đoán cục bộ, độ ổn định theo seed và thời gian; không coi “có thanh” là đạt.
4. UI phải đọc số liệu thực của mỗi flow để phân biệt weight=0 với weight cực nhỏ; không dùng kết luận của flow bulk cho flow lệch cờ TCP.

Không kết luận accuracy/FPR live từ 92 flow không có ground truth.

## Kiểm tra sâu sampling — stage18

Chạy `python -B RQ3_IDS_System/scripts/stage18_probe_lime_sampling.py`: 8 cảnh báo × 3 seed × 2 chế độ = 48 lần giải thích. Seed đầu giống production; hai seed sau là kiểm tra độ nhạy. Chỉ đổi `sample_around_instance` trên explainer trong bộ nhớ, không đổi config/model/DB. Đọc mã LIME đang cài xác nhận `False` sinh quanh mean nền, `True` sinh quanh instance; scale và kernel giữ nguyên.

| Chế độ | Kết quả 24 lần | ESS | Nhận xét |
|---|---|---|---|
| RQ2 hiện tại, quanh mean nền | 24/24 insufficient_neighborhood | ≈1 | Đổi seed không giải quyết suy biến |
| Thử nghiệm quanh instance | 24/24 vượt guard số học | 416–500 | Không đồng nghĩa giải thích đáng tin |

Thử nghiệm quanh instance có R² khoảng 0,245–0,636; sai số tuyệt đối giữa dự đoán surrogate LIME tại flow và xác suất model khoảng 0,011–0,729 (1,1–72,9 điểm phần trăm). Riêng flow b1e78518: model 96,8877%, surrogate 45,6653–47,2820%, ESS 472–483 và R² 0,582–0,597. Đây là ví dụ rõ rằng ESS tốt/R² dương vẫn không đủ xác nhận fidelity tại flow.

Top-5 Jaccard trung bình giữa ba seed của từng flow chỉ 0,204–0,369 trong chế độ quanh instance; không diễn giải thành độ chính xác. 100% mẫu nhân tạo (không tính dòng gốc) ở cả hai chế độ có ít nhất một cờ TCP hoặc Protocol mang giá trị không nguyên. Đây là bằng chứng sampling chưa tôn trọng miền biến rời rạc; kiểm tra này chưa bao phủ mọi ràng buộc chéo giữa 78 đặc trưng.

Kết luận: không thể chỉ bật `sample_around_instance=True` rồi coi LIME đã sửa xong. Cần thiết kế/đánh giá sampling phù hợp miền đặc trưng và kiểm tra fidelity tại điểm gốc, độ ổn định cùng tính hợp lệ mẫu. Guard hiện tại chỉ chống suy biến tối thiểu, không phải chứng nhận chất lượng. Chưa triển khai chế độ thử nghiệm vào API/UI.

Môi trường vẫn báo cảnh báo pickle XGBoost khác phiên bản và LabelEncoder sklearn 1.8.0 so với runtime 1.9.1; audit không tự nâng/hạ phiên bản. Đây là vấn đề tái lập riêng cần quản lý, chưa có bằng chứng nó là nguyên nhân collapse trọng số nêu trên.
