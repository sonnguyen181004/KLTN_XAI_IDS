# Chốt kế hoạch: dữ liệu test trên lab, hệ thống IDS, hướng tiếp theo

Dựa trên góp ý của hai thầy ([GOP_Y_HAI_THAY.md](GOP_Y_HAI_THAY.md)) và các kết quả đã chạy thử trong `IDS_M1_Lab/`. File này chốt lại ba phần: dữ liệu test trên lab nên như thế nào, hệ thống IDS hiện ra sao và còn thiếu gì, hướng làm tiếp theo.

## 1. Những gì đã phát hiện được (bằng chứng, không phải giả định)

Chạy M0 (dataset cũ) và M1 (dataset improved, `IDS_M1_Lab`) trên traffic thật từ lab:

| Tình huống | M0 | M1 | Nguyên nhân |
|---|---|---|---|
| Web duyệt bình thường (WEB-B01, 21 flow) | 19/21 báo nhầm Hulk | 0/21 báo nhầm | Dataset cũ thiếu Benign "đóng FIN + có dữ liệu" → M0 học tắt "FIN + data = Hulk" |
| Hulk thật (hulk-rs, 211 flow) | 209/211 bắt đúng | 0/211, toàn Benign | M0 bắt đúng *nhờ đúng cái lỗi trên* (Hulk thật cũng đóng FIN), M1 đã sửa lỗi đó nên mất luôn tín hiệu |
| SSH brute force thật (698 flow, nhiều kết nối rất ngắn) | 60,7% báo động, chỉ 20,7% đúng loại (còn lại gọi nhầm Hulk) | 0/698, toàn Benign | Flow thật chỉ 3 gói/vài ms, khác hẳn SSH-Bruteforce trong train (23 gói, 0,37s, 16 cờ PSH) |
| SSH brute force dài (A07, B03 — 1 kết nối dài nhiều lần thử) | gọi nhầm Hulk | đúng SSH-Bruteforce (0,78–0,82) | Phiên dài, nhiều cờ PSH, giống train hơn |
| UDP cổng cao hợp lệ (có thể Zalo, chưa xác nhận) | đúng Benign | 57 flow báo nhầm Infilteration | Train Benign UDP 0% có cổng đích ≥10000, trong khi Infilteration UDP 56% có |
| CSV test chuẩn (236 flow, giống phân phối train) | — | 235/236 đúng | Khi traffic giống train thì M1 rất tốt |

**Kết luận chung:** cả hai model đều không sai một cách ngẫu nhiên — mỗi model học đúng theo *những gì dataset của nó có*, và traffic thật trong lab liên tục rơi vào đúng những chỗ dataset thiếu. Đây là bằng chứng mạnh cho luận điểm "cần đánh giá trên traffic thật, không chỉ trên test set có sẵn" mà hai thầy nói.

## 2. Dữ liệu test trên lab nên như thế nào

### 2.1 Nguyên tắc
- **Có nhãn đúng theo nhật ký**, không suy luận từ kết quả model. Mỗi phiên bắt traffic phải ghi: công cụ dùng, tham số, IP nguồn/đích, giờ bắt đầu — giờ kết thúc (giờ địa phương, đổi sang UTC khi đối chiếu DB).
- **Có cả tấn công lẫn bình thường**, cùng môi trường lab. Không chỉ bắt lúc tấn công — nếu không, mọi đặc điểm riêng của máy ảo (cửa sổ TCP, độ trễ) sẽ bị học nhầm thành "dấu hiệu tấn công".
- **Nhiều lần, nhiều kịch bản**, không chạy một lần rồi coi là đủ. Đổi tốc độ, đổi công cụ, đổi số luồng để tránh học thuộc một cấu hình duy nhất.
- **Giữ riêng ít nhất 1–2 phiên làm test**, không bao giờ đưa vào train, kể cả khi train lại nhiều lần sau này.

### 2.2 Danh sách kịch bản cần thu (ưu tiên theo mức tiện lợi)

| Loại | Công cụ gợi ý | Trạng thái |
|---|---|---|
| SSH brute force | đã chạy (công cụ chưa xác nhận tên) | Đã có 698 flow thật, cần nhật ký để dán nhãn chính thức |
| DoS Hulk | hulk-rs (GitHub) | Đã có 211 flow, đã xác nhận công cụ |
| DDoS LOIC-HTTP | LOIC | Chưa chạy |
| DDoS HOIC | HOIC | Chưa chạy |
| Quét cổng | nmap | Chưa chạy |
| SQL Injection | sqlmap hoặc thủ công | Có traffic cũ (SQL-I01, 22 flow) nhưng chưa có nhật ký |
| Benign đối chứng | duyệt web, gọi Zalo/video call, SSH đăng nhập thường | Có WEB-B01 (21 flow) và UDP nghi Zalo (57 flow, chưa xác nhận ứng dụng); cần thêm nhiều phiên khác |

### 2.3 Cách dán nhãn và đánh giá
1. Ghi nhật ký mỗi phiên (file text đơn giản là đủ: thời gian bắt đầu/kết thúc, công cụ, IP).
2. Dùng thời gian để lọc đúng flow trong DB (`received_at`, đã làm được ở bước đối chiếu SSH 18:15).
3. Gắn `label_true` thủ công cho các flow trong khung giờ đó.
4. Tính lại: tỉ lệ phát hiện đúng (recall), tỉ lệ báo giả trên Benign (FPR), theo từng loại tấn công, cho cả M0 và M1 (và sau này M2).

## 3. Hệ thống IDS hiện tại — đã làm được gì, còn thiếu gì

### 3.1 Đã chạy được (`IDS_M1_Lab/`)
- Ba đường vào traffic: CSV, PCAP (phát lại), realtime (bắt trực tiếp Wi-Fi/LAN qua Npcap) — đều đã test.
- SHAP tự động cho mọi cảnh báo; **mới thêm** SHAP theo yêu cầu cho cả flow Benign (chọn lớp bất kỳ để xem vì sao điểm thấp/cao).
- LIME theo yêu cầu — đã phát hiện cấu hình gốc (`kernel_width=3,312`, khóa theo RQ2) không chạy được trên flow thật (`insufficient_neighborhood` ở 313/313 flow thử), đã đổi sang `3000` cho riêng lab này (không đổi cấu hình RQ2/RQ3), chạy được nhưng cần ghi rõ đây không còn là giải thích thật sự cục bộ.
- Script đối chiếu M0 và M1 trên toàn bộ DB thật (`IDS_M1_Lab/scripts/m1_vs_m0_on_db.py`).
- M1 đã train lại từ đầu (17/11/2026), kết quả trên Hulk và SSH thật không đổi (vẫn 0%), xác nhận vấn đề nằm ở dữ liệu chứ không ở lần train.
- Kiểm tra overfit/underfit của M0 (20/11/2026): không overfit đáng kể (chênh train và validation 1,91 điểm macro F1), underfit ở các lớp có nhãn mâu thuẫn. Chi tiết ở `RQ1_Model_Training_xboost/results/cv_diagnostics/BAO_CAO_CACH1.md` và mục RQ1 của README gốc.

### 3.2 Còn thiếu / cần làm
- **Tab "Đối chiếu M0/M1" trên dashboard** hiện so M1 với chính nó (hạn chế đã ghi trong README), cần nối với script đối chiếu thật đã viết.
- **Nhật ký lab chưa có quy trình chuẩn** — hiện chỉ xác nhận bằng lời, cần một quy ước ghi file đơn giản như mục 2.3.
- **Cờ "môi trường" và gợi ý Hulk-FIN trong `config.yaml`** viết cho lỗi của dataset cũ, cần đánh giá lại có còn đúng với M1/M2 không.
- **Sơ đồ kiến trúc hệ thống** (máy tấn công – máy nạn nhân – máy IDS, vị trí đặt các khối: bắt gói, trích đặc trưng, XGBoost, SHAP/LIME, cảnh báo) — chưa vẽ, cần làm cho báo cáo.
- **`rq2_cohort_ids`, `rq2_master_summary`** trong config vẫn trỏ về RQ2 cũ, chỉ ảnh hưởng vài script kiểm tra cũ, không khẩn cấp.

## 4. Hướng dữ liệu tiếp theo (M2)

Đã thống nhất: **không gộp y nguyên hai dataset cũ và mới**, vì so trực tiếp cho thấy chúng là hai nguồn flow khác nhau (0 dòng trùng khi so các cột số chính của lớp Hulk), và bộ cũ còn mang lỗi đã biết (thiếu Benign đóng FIN có dữ liệu).

**Công thức M2 = bộ improved (nền chính) + 2 lớp chỉ có ở bộ cũ + dữ liệu lab thật**

1. **Nền chính:** `RQ4_Retrain_Compare/data/d2_train.parquet` (bộ improved, 13 lớp) — giữ nguyên.
2. **Thêm 2 lớp thiếu** lấy riêng từ bộ cũ: `FTP-BruteForce`, `DoS attacks-SlowHTTPTest` — chỉ lấy đúng 2 lớp này, không lấy lẫn Benign/Hulk của bộ cũ — để quay lại đủ 15 lớp nếu cần.
3. **Thêm dữ liệu lab thật**, cả hai chiều:
   - Tấn công: Hulk, SSH brute force (đa dạng công cụ/tốc độ), và các loại mới sẽ chạy (LOIC, HOIC, quét cổng, SQLi).
   - Bình thường: web duyệt, gọi thoại/video (UDP cổng cao), SSH đăng nhập thường — đặc biệt cần nhiều mẫu Benign "đóng FIN + có dữ liệu" để sửa đúng lỗi đã phát hiện ở Hulk.
4. **Giữ riêng 1–2 phiên lab** (không đưa vào bước 3) làm test độc lập.
5. Train ra **M2**, không ghi đè M1. So M0, M1, M2 trên: test cũ, test improved, và phiên lab giữ riêng.
6. Dùng SHAP so sánh lý do quyết định của M1 và M2 trên cùng flow Hulk/SSH thật, để chỉ ra model mới có chuyển sang dùng đặc trưng đúng bản chất (ví dụ tốc độ gửi `Flow Pkts/s`) thay vì cờ FIN hay không.

## 5. Thứ tự làm tiếp theo

1. Viết quy ước nhật ký lab (mục 2.3) và áp dụng cho các phiên đã có (Hulk, SSH 18:15, WEB-B01, UDP nghi Zalo) — xác nhận lại công cụ/ứng dụng dùng cho từng phiên.
2. Chạy thêm các kịch bản còn thiếu: LOIC-HTTP, HOIC, quét cổng, thêm SQLi có nhật ký, thêm nhiều phiên Benign đối chứng.
3. Dán nhãn toàn bộ, tính recall/FPR hiện tại của M0 và M1 theo từng loại — đây là số liệu RQ2 có thể dùng ngay (so dữ liệu thực tế với dữ liệu có sẵn).
4. Build M2 theo công thức mục 4, đánh giá lại trên phiên giữ riêng.
5. Vẽ sơ đồ kiến trúc hệ thống, nối tab đối chiếu M0/M1(/M2) trên dashboard.
6. Viết lại scope, mục tiêu, RQ trong báo cáo theo khung đã chốt ở [GOP_Y_HAI_THAY.md](GOP_Y_HAI_THAY.md) mục 3, có dẫn số liệu thật từ các bước trên.
7. Hỏi lại thầy hai điểm còn chưa chắc: thuật ngữ "rule-based"/đối chiếu thầy muốn, và mức độ lab (máy ảo hiện tại có đủ không).

## 6. Giới hạn cần ghi rõ trong báo cáo

- Lab hiện là máy ảo, đặc trưng như cửa sổ TCP, `Fwd Seg Size Min` mang dấu vết môi trường ảo hóa, chưa chắc giữ nguyên trên mạng thật.
- Nhãn traffic thật hiện dựa một phần vào suy luận từ đặc điểm flow (ví dụ UDP nghi Zalo) chưa có xác nhận bằng công cụ giám sát tiến trình — cần làm rõ trước khi đưa vào báo cáo chính thức.
- LIME trên flow thật cần kernel rộng hơn mới chạy được, nên không còn là giải thích cục bộ chặt chẽ như trên dữ liệu test cũ — cần nêu như một hạn chế của phương pháp, không che giấu.
