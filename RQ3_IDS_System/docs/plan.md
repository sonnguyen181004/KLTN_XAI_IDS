# Kế hoạch xây dựng hệ thống IDS có giải thích (RQ3)

> Dự án **mới hoàn toàn**, không tái sử dụng `cicflowmeter_capture_demo/` cũ. Đặc tả gốc: `Kiến trúc hệ thống IDS.docx` (kiến trúc 7 khối / 6 tầng, mô hình logic 3 làn, mô hình vật lý, API, thực thể dữ liệu, 5 thí nghiệm E1–E5) — tài liệu đó là nguồn sự thật, kế hoạch này là cách triển khai nó thành code.

## 0. Bức tranh tổng thể

```
Tầng 1        Tầng 2              Tầng 3       Tầng 4                Tầng 5         Tầng 6
Traffic  →  Bắt gói & gom   →   Model đoán  →  Giải thích +      →  Quyết định   →  API +
vào          thành flow          (XGBoost)      chấm tin cậy          hiển thị       Dashboard
```

Nguyên tắc cứng (lấy từ tài liệu kiến trúc, không được vi phạm):
- Cảnh báo tạo ngay từ Prediction, **không chờ** giải thích xong.
- SHAP (TreeSHAP) là giải thích **mặc định, tự động**. LIME **chỉ chạy khi analyst bấm xin** (dùng đúng cấu hình đã khóa ở RQ2: `kernel_width=3,312`, `num_samples=1000`, `discretize_continuous=False`, nền 2.000 dòng, seed 42).
- Tầng 5 (nhánh A/B) chỉ đổi **cách hiển thị**, không đổi nhãn, không ẩn cảnh báo.
- Mọi bước ghi lại mốc thời gian (phục vụ thí nghiệm E1).
- Model, 78 cột và thứ tự cột phải **giống hệt** RQ1/RQ2 để so sánh được.

## 1. Hai câu đã chốt trước khi code

### 1.1. Dữ liệu dùng để test — không phải "model học thuộc"
- Khi gọi `/predict`, hệ thống **chỉ gửi 78 con số đặc trưng**, không gửi nhãn thật → model luôn đoán thật, không "tra bảng đáp án". Nhãn thật chỉ giữ riêng để tự so sánh sau.
- Dùng **2 tập dữ liệu**, mục đích khác nhau:
  - **Tập A — cohort 1.339 flow của RQ2** (giữ nguyên, không đổi): bắt buộc dùng để **E5** (so khớp kết quả hệ thống mới với kết quả RQ2 đã có).
  - **Tập B — tập mới, "sạch"**: lấy từ `test_set.parquet`, **loại bỏ hẳn** các dòng trùng với `train_set.parquet` (train/test của CSE-CIC-IDS2018 trùng ~27,7% dòng — vấn đề đã ghi nhận ở RQ2 GĐ1), rồi lấy mẫu ngẫu nhiên phân tầng theo lớp (~200–300 flow). Tập này **chắc chắn model chưa từng thấy dưới bất kỳ hình thức nào** — dùng để demo và test hệ thống nói chung, tránh mọi tranh cãi "có phải học thuộc không".

### 1.2. Test tầng 2 (bắt gói) độc lập, trước khi có lab tấn công
- Việc cài Npcap + CICFlowMeter và thử bắt traffic bình thường của chính máy bạn (mở vài trang web, bắt gói 1–2 phút) là một bước kiểm tra **tách biệt hoàn toàn** khỏi việc dựng máy attacker/victim.
- Mục đích: xác nhận cơ chế "bắt gói → gom flow → ra đúng 78 cột" chạy đúng kỹ thuật, trước khi lo tới việc tấn công thật.
- Việc này bạn tự làm trên máy mình (cài phần mềm), song song với lúc tôi viết code tầng 3–6.

## 2. Các mốc thực hiện (M1 → M5)

| Mốc | Nội dung | Cần máy ảo? | Ai làm |
|---|---|---|---|
| **M0** | Khung dự án: `RQ3_IDS_System/`, `config.yaml`, schema SQLite (6 bảng) | Không | Tôi |
| **M1** | Tầng 2 (chuẩn hóa) + Tầng 3 (dự đoán) + Tầng 4 (SHAP/LIME/độ tin cậy) + Tầng 5 (nhánh A/B) + Tầng 6 (API + Dashboard + Docker), chạy bằng Tập A + Tập B | Không | Tôi |
| **M2** | Thí nghiệm **E1** (đo độ trễ thật qua API) và **E5** (so khớp Tập A với RQ2) | Không | Tôi |
| **M3** | Bạn tự cài Npcap + CICFlowMeter, test bắt gói trên máy mình (mục 1.2) — song song làm với M1 | 1 máy (máy bạn) | Bạn (tôi hướng dẫn) |
| **M4** | Dựng 3 máy ảo VirtualBox (Victim, Attacker, Monitor) trên mạng host-only cô lập, nối hệ thống vào traffic thật | 3 máy ảo | Bạn dựng, tôi hướng dẫn từng lệnh |
| **M5** | Thí nghiệm **E2** (lệch phân bố), **E3** (báo động giả trên traffic thật), **E4** (kiểm chứng cờ môi trường) trên traffic thật từ M4 | 3 máy ảo | Cùng làm |

M0–M2 làm được trọn vẹn ngay bây giờ, không cần chờ gì. M3 làm song song, không phụ thuộc M1/M2. M4–M5 cần bạn chuẩn bị máy ảo trước.

## 3. Chi tiết M1 — xây 6 tầng

### Tầng 2 — Chuẩn hóa flow
- Input: 1 dòng 78+ cột (từ Tập A/B, hoặc sau này từ CICFlowMeter thật).
- Kiểm tra: đủ 78 cột không, có NaN không → thiếu thì trả lỗi `422`, lưu vào bảng `DataError`, **không đoán bừa**.
- Chuẩn hóa: đổi cột thời gian ×1.000.000 (giây → micro giây), xếp đúng thứ tự cột như lúc huấn luyện model.

### Tầng 3 — Dự đoán
- Nạp lại `best_xgboost_model.pkl` + `label_encoder.pkl` từ RQ1 (dùng lại nguyên file, không huấn luyện lại).
- `POST /predict`: trả nhãn + xác suất 15 lớp. Nhãn ≠ Benign → tạo `AlertRecord` ngay.

### Tầng 4 — Giải thích + độ tin cậy
- **TreeSHAP tự động**: mọi Alert đều chạy, lấy Top-5 có dấu, ghi kèm additivity check.
- **LIME theo yêu cầu**: `POST /explain` với `method=lime`, dùng đúng cấu hình khóa ở RQ2.
- **Tính tại chỗ (rẻ)**: faithfulness nhanh + đếm cờ môi trường — **xem lưu ý quan trọng ngay dưới đây, hai thứ này KHÔNG phải bằng chứng kết luận**.
- **Tra bảng có sẵn (đắt)**: độ ổn định + độ chịu nhiễu theo từng lớp — lấy thẳng từ `rq2_master_summary.json` của RQ2, nạp 1 lần lúc khởi động, không tính lại mỗi flow.
- Cờ lớp hiếm: nhãn dự đoán có dưới 100 mẫu huấn luyện thì bật cờ (hiện chỉ SQL Injection).

**⚠️ Lưu ý quan trọng — tránh overclaim:**

- **Cờ môi trường chỉ là cờ cảnh báo, không phải bằng chứng.** Đếm xem Top-5 có bao nhiêu trong 3 đặc trưng (Dst Port, Fwd Seg Size Min, Init Fwd Win Byts) chỉ nói "lời giải thích CÓ KHẢ NĂNG dựa vào đặc điểm môi trường lab, nên xem kỹ hơn" — đây là **giả thuyết tự đặt** (RQ2 mục L3.5), **chưa được kiểm chứng**; việc kiểm chứng thật sự là thí nghiệm **E4** (huấn luyện lại không dùng 3 đặc trưng, so độ chính xác trong/chéo miền). Cờ không chứng minh model sai, không đổi nhãn, không ẩn cảnh báo.
- **Faithfulness tính tại chỗ là PROXY nhanh, không phải phép đo faithfulness đầy đủ của RQ2.** RQ2 đo bài bản: xóa k=1→10, **3 giá trị nền** (median toàn tập, mean toàn tập, median lớp Benign), tính AUC trên cả deletion lẫn insertion, có đối chứng ngẫu nhiên, kiểm định Wilcoxon, chạy hàng nghìn flow. Bản runtime chỉ kịp làm **một bước xóa, một giá trị nền (median toàn tập), một con số duy nhất** — không AUC, không đối chứng ngẫu nhiên đi kèm mỗi lần. Chỉ dùng để so với một **ngưỡng đơn giản tính sẵn từ RQ2** (phục vụ quyết định nhánh A/B ở tầng 5), **không được trích dẫn như một phép đo faithfulness chuẩn** trong báo cáo.

### Tầng 5 — Nhánh A/B
- Ngưỡng tính từ **cohort 1.339 flow theo từng lớp** (ví dụ phân vị thấp của faithfulness) — **không dùng** tập dev 250 flow của RQ2 (184/250 là Benign, không đại diện).
- Nhánh A: mọi chỉ số ổn → hiện SHAP bình thường.
- Nhánh B: 1 chỉ số dưới ngưỡng, hoặc ≥2 cờ môi trường, hoặc lớp hiếm → hiện SHAP kèm dòng "cần xem lại" + nút xem LIME.

### Tầng 6 — API + Dashboard
- **FastAPI**: `POST /predict`, `POST /explain`, `GET /alerts`, `GET /health`.
- **Streamlit**: 1 trang — bảng cảnh báo, biểu đồ SHAP/LIME có dấu, bảng độ tin cậy, nhãn nhánh A/B.
- **Docker Compose**: gói 2 service, chạy bằng `docker compose up`.
- **Lưu trữ**: SQLite (6 bảng: `FlowRecord`, `DataError`, `Prediction`, `AlertRecord`, `Reliability`, `Timing`).

## 4. Chi tiết M2 — E1 và E5

- **E1 (độ trễ)**: bơm Tập A qua `/predict` rồi `/explain` **qua API thật** (HTTP, không gọi hàm Python trực tiếp), đo median và p95 từng khâu (chuẩn hóa, dự đoán, SHAP, LIME, đánh giá tin cậy) — so với số đo "thô" ở RQ2 (SHAP ~19ms, LIME ~148ms) để biết chạy qua API có chậm thêm không.
- **E5 (nhất quán offline)**: Tập A qua API → so nhãn dự đoán và Top-5 SHAP với kết quả gốc đã có từ RQ2. Khớp 100% thì xác nhận code hệ thống không có lỗi (sai cột, sai đơn vị, sai model) so với pipeline RQ2 gốc.

## 5. Chi tiết M4 — dựng traffic thật (để khi tới lúc)

- VirtualBox, 3 máy ảo trên 1 mạng **host-only** (cô lập, không nối internet):
  - **Victim**: Linux, chạy sẵn 1 dịch vụ (nginx hoặc SSH) để có cái tấn công vào.
  - **Attacker**: Linux/Kali, công cụ `hydra` (brute-force), `nmap` (quét cổng), `hping3` (DDoS giả lập).
  - **Monitor**: chạy Npcap/tcpdump + CICFlowMeter + hệ thống (API + Dashboard) của M1.
- Cách đơn giản nhất để bắt đầu: Monitor và Victim **là cùng một máy** (bắt traffic đến/đi chính nó) — không cần cấu hình mạng phức tạp.
- Cách đúng kiến trúc (làm sau): Monitor là máy riêng, bật **promiscuous mode** trên card mạng host-only để "nghe" được cả traffic giữa Victim và Attacker.
- Phương án dự phòng không cần máy Attacker: dùng `tcpreplay` phát lại 1 file pcap mẫu có sẵn, Npcap/CICFlowMeter trên Monitor vẫn bắt được như traffic thật.

## 6. Việc tôi làm ngay bây giờ

1. `RQ3_IDS_System/scripts/stage00_build_clean_dataset.py` — tạo Tập B (loại trùng train/test, lấy mẫu phân tầng).
2. `RQ3_IDS_System/app/` — code tầng 2–6 (FastAPI + Streamlit + SQLite schema).
3. `RQ3_IDS_System/scripts/stageE1_latency.py`, `stageE5_consistency.py` — 2 thí nghiệm M2.
4. Test toàn bộ bằng Tập A + Tập B, không cần máy ảo.

## 7. Tiến độ (cập nhật sau mỗi bước)

### Bước 1 — `config.yaml` ✅
- **Mục đích**: gom mọi tham số dự án vào 1 file, không ghi cứng đường dẫn/số liệu rải rác trong code.
- Tạo `RQ3_IDS_System/config.yaml`: đường dẫn model/dữ liệu RQ1/RQ2, cấu hình LIME khóa y hệt RQ2 (kernel_width=3,312, num_samples=1000, discretize_continuous=false), 3 đặc trưng cờ môi trường, ngưỡng lớp hiếm (<100 mẫu train), tham số Tập B.
- Kiểm tra: đọc file thành công, xác nhận cả 7 đường dẫn tới dữ liệu/model có sẵn đều tồn tại trên đĩa.
- Sửa 1 lần: bỏ đường dẫn `rq2_domain_knowledge` (trỏ sang file `.py` của RQ2) vì dư thừa — 3 tên đặc trưng môi trường đã có sẵn ngay trong `config.yaml`, không script nào cần đọc thêm file đó.
- Commit: `8218ec3`, `99f3c53`.

### Bước 2 — Schema SQLite (6 bảng) ✅
- **Mục đích**: tạo "nơi chứa" cho mọi dữ liệu hệ thống sẽ ghi ra khi chạy thật (flow, lỗi, dự đoán, cảnh báo, độ tin cậy, thời gian từng bước) — chuẩn bị trước khi có logic xử lý.
- Tạo `app/db.py`: định nghĩa 6 bảng `FlowRecord`, `DataError`, `Prediction`, `AlertRecord`, `Reliability`, `Timing` (có khóa ngoại nối nhau). 78 đặc trưng gộp vào 1 cột JSON (`features_json`) thay vì 78 cột SQL riêng, vì tên đặc trưng có khoảng trắng/dấu `/`.
- Tạo `scripts/stage02_init_db.py`: chạy tạo DB thật + tự kiểm tra 3 việc — (1) đủ 6/6 bảng, (2) đúng cột từng bảng, (3) chèn 1 flow giả (78 "đặc trưng") rồi đọc lại khớp 100%, sau đó tự xóa dòng test.
- Thêm `*.db`, `*.csv` của `RQ3_IDS_System/data/` vào `.gitignore` (dữ liệu sinh ra, không commit).
- Commit: `e5b3f06`.

### Bước 3 — Tập B (dữ liệu sạch, loại trùng train/test) ✅
- **Mục đích**: có một tập flow để demo/test mà chắc chắn model chưa từng thấy dưới bất kỳ hình thức nào (kể cả trùng lặp ẩn với train), tránh mọi tranh cãi "model học thuộc".
- Tạo `scripts/stage03_build_clean_dataset.py`: băm 78 cột của train_set và test_set, loại khỏi test_set mọi dòng trùng hash với train_set, rồi lấy mẫu phân tầng (seed 42, tối đa 30 dòng/lớp) từ phần còn lại.
- **Kết quả chạy thật**: 194.149/700.000 dòng test (27,74%) trùng train — khớp đúng con số RQ2 đã ghi nhận trước đó. Sau khi loại trùng còn 505.851 dòng "sạch". Lấy mẫu được **241 flow, 13/15 lớp**.
- **Phát hiện cần ghi nhận trung thực**: 2 lớp `DoS attacks-SlowHTTPTest` và `FTP-BruteForce` **100% dòng test trùng với train** (1.735/1.735 và 3.507/3.507) → **0 dòng sạch còn lại**, nên **không có mặt trong Tập B**. Đây là đặc điểm thật của cách lấy mẫu gốc của CSE-CIC-IDS2018, không phải lỗi code — khi demo/báo cáo cần nói rõ Tập B chỉ phủ được 13/15 lớp, 2 lớp này phải dùng Tập A (cohort RQ2) hoặc traffic thật để minh họa.
- Tự kiểm tra lại: băm 241 dòng của Tập B, xác nhận 0 dòng trùng train_set — [PASS].
- File ra: `RQ3_IDS_System/data/clean_holdout_set.csv` (không commit git, đã gitignore).
- Commit: `6ba128a`.

### Bước 4 — Tầng 2: hàm chuẩn hóa flow ✅
- **Mục đích**: đứng giữa "dữ liệu thô nhận được" và "model" — đảm bảo chỉ dữ liệu đủ điều kiện (đủ 78 cột, không NaN, đúng thứ tự cột) mới được đưa vào model dự đoán; dữ liệu thiếu/lỗi bị từ chối có lý do rõ ràng (422) thay vì để model đoán bừa và sai âm thầm.
- Tạo `app/normalize.py`: hàm `normalize_flow()` kiểm tra đủ cột, kiểm tra NaN/Inf, tự sắp lại đúng thứ tự cột theo model; tham số `convert_seconds_to_microseconds` (mặc định tắt) chuẩn bị sẵn cho traffic thật ở M4, chưa dùng tới lúc này vì Tập A/B đã đúng đơn vị micro giây từ gốc.
- Tạo `scripts/stage04_test_normalize.py`, chạy 4 tình huống trên dữ liệu thật (Tập B):
  1. 3 dòng thật từ Tập B → PASS, đúng thứ tự cột.
  2. Cố ý xóa cột `Fwd Pkt Len Std` → bị từ chối đúng lý do, đúng tên cột liệt kê.
  3. Cố ý đặt `Flow IAT Min = NaN` → bị từ chối đúng lý do, đúng tên cột liệt kê.
  4. Đảo ngược toàn bộ thứ tự 78 cột ở input → hàm tự sắp lại đúng thứ tự model mong đợi, không từ chối oan.
- Kết quả chạy thật: cả 4 tình huống đều đúng như kỳ vọng — xem log chạy, không có [FAIL] nào.
- Commit: `cf8cff4`.

### Bước 5 — Tầng 3: nạp model, hàm dự đoán ✅
- **Mục đích**: nối ngay sau hàm chuẩn hóa — nhận 1 dòng đã chuẩn hóa, trả về nhãn + xác suất 15 lớp, kèm "phiên bản model" (hash SHA-256 file .pkl) để truy vết sau này.
- Tạo `app/predict.py` (class `Detector`): nạp model/encoder RQ1 (không huấn luyện lại), `model_version` = 16 ký tự đầu SHA-256 của file model (`52eb5a671ee82109`), hàm `predict_flow()`.
- Tạo `scripts/stage05_test_predict.py`, 3 việc kiểm tra bằng dữ liệu thật:
  1. **Tự nhất quán**: tổng xác suất 15 lớp = 0,99999994 (≈1.0), lớp xác suất cao nhất khớp `predicted_label` — [PASS].
  2. **So với Tập B** (241 flow, đã biết đáp án): độ chính xác tổng 212/241 = **88,0%**. Theo lớp: hầu hết 94,7–100%, nhưng **Infilteration chỉ 15,8%** (3/19), Brute Force-Web 63,2%, SQL Injection 69,2% — ba con số này **khớp đúng** với 3 lớp "khó" đã ghi nhận sẵn trong tài liệu kiến trúc (Infilteration Recall ~16% trên toàn test set) → một dấu hiệu nhất quán tốt, không phải trùng hợp.
  3. **So với `pred_label` có sẵn trong cohort_ids.csv của RQ2** (50 flow lấy ngẫu nhiên từ Tập A, seed 42): **khớp y hệt 50/50 = 100%** — xác nhận hàm dự đoán mới không có lỗi nạp model/sai thứ tự cột so với pipeline RQ2 gốc (kiểm tra sớm, thu nhỏ của thí nghiệm E5).
- Commit: `2cae3b1`.

### Bước 6 — FastAPI: `POST /predict`, `GET /health` ✅
- **Mục đích**: ghép tầng 2 (chuẩn hóa) + tầng 3 (dự đoán) + ghi DB thành 1 dịch vụ web thật, gọi được qua HTTP thay vì chỉ gọi hàm Python trực tiếp — lần đầu hệ thống "chạy được" theo đúng nghĩa.
- Cài `fastapi`, `uvicorn`, `requests`. Tạo `app/main.py` (`POST /predict`, `GET /health`) và `scripts/stage06_test_api.py`.
- **3 lỗi thật gặp phải khi test — ghi lại để không lặp lại:**
  1. **Deadlock subprocess**: ban đầu bắt log server qua `subprocess.PIPE` nhưng không đọc liên tục → ống dẫn đầy làm uvicorn bị treo khi ghi log, server "giả treo" không trả lời request nào. **Sửa**: ghi log server ra file trên đĩa (`data/stage06_server.log`) thay vì PIPE.
  2. **`sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`**: dùng 1 connection SQLite chung mở lúc khởi động, nhưng FastAPI chạy mỗi request sync trong 1 thread riêng của thread pool → SQLite (mặc định `check_same_thread=True`) chặn. **Sửa**: thêm `db.get_connection()`, mở 1 connection MỚI cho MỖI request, đóng lại sau khi xong.
  3. **`sqlite3.IntegrityError: FOREIGN KEY constraint failed`**: ghi `Timing` (có khóa ngoại tới `FlowRecord.flow_id`) TRƯỚC KHI ghi `FlowRecord` → vi phạm khóa ngoại. **Sửa**: đổi thứ tự, ghi `FlowRecord` trước, `Timing` sau.
- **Kết quả chạy thật (sau khi sửa cả 3 lỗi) — log đầy đủ, mọi [PASS]:**
  - `GET /health` → 200, `model_loaded=True`.
  - 3 flow thật từ Tập B qua `POST /predict` → cả 3 trả 200, nhãn đúng, `timing_ms` ví dụ dòng 0: normalize=4,5ms, predict=13,3ms, total=75,6ms.
  - Flow thiếu cột `Idle Min` → 422, đúng lý do, đúng tên cột.
  - Mở lại file DB: cả 3 flow có đủ `FlowRecord`, `Prediction`, 3 dòng `Timing`; bảng `DataError` có 2 dòng (đúng số lỗi đã tạo ra trong lúc test).
- **Bạn (người dùng) tự test lại thủ công, độc lập với script tự động** — xác nhận kết quả trùng khớp:
  - Chạy `python -m uvicorn app.main:app --port 8000` để tự bật server, mở `http://127.0.0.1:8000/docs` (giao diện Swagger UI do FastAPI tự sinh) để gọi `/predict` bằng tay, không qua script.
  - **Sự cố gặp phải**: terminal có `(.venv)` ở đầu dòng nhắc, nhưng là venv của **`cicflowmeter_capture_demo/`** (thư mục demo cũ) tự kích hoạt, không phải môi trường đã cài `fastapi`/`uvicorn` (cài vào Python hệ thống) → báo lỗi `No module named uvicorn`. **Sửa**: chạy `deactivate` để thoát venv cũ trước khi gọi `python -m uvicorn...`. Đây là một lời nhắc tốt: venv cũ vẫn có thể tự kích hoạt trong terminal nếu không cẩn thận, dù code không hề đụng tới thư mục đó.
  - Để tiện bấm thử qua Swagger UI, đã xuất sẵn 2 file mẫu (lấy từ Tập B, flow model chưa từng thấy): `data/samples/sample_benign.json` (đáp án đúng = Benign) và `data/samples/sample_attack.json` (đáp án đúng = Bot).
  - Bạn dán `sample_attack.json` vào `/predict` qua Swagger UI và chạy thành công.
- Commit: `41949ed`.

### Bước 7 — Tầng 4a: TreeSHAP tự động, nối vào `/predict` 🔄 (đang làm)
- **Mục đích**: mỗi cảnh báo có kèm "vì sao mô hình nghĩ vậy" — SHAP chạy TỰ ĐỘNG cho mọi Alert (khác LIME ở bước 9, chỉ chạy khi analyst bấm xin, đúng nguyên tắc kiến trúc Khối 3).
- Sẽ làm: `app/explain_shap.py` (TreeSHAP, Top-5 có dấu cho đúng lớp dự đoán, kiểm tra additivity); nối vào `app/main.py` sau khi tạo Alert; thêm `db.upsert_reliability()` (ghi từng phần vào bảng `Reliability`, vì các bước 8-11 sau sẽ tiếp tục điền thêm cột khác cho CÙNG alert_id).
- Test dự kiến: gửi flow tấn công (sample_attack.json) → có Top-5 SHAP trong response; gửi flow Benign → KHÔNG có SHAP (đúng nguyên tắc); additivity sai số phải cùng bậc với RQ2 (~1e-5/1e-6); mở DB xác nhận bảng Reliability có dữ liệu; so thời gian với RQ2 (~19ms/flow).

### Bước 7 — Tầng 4a: TreeSHAP tự động, nối vào `/predict` ✅
- Tạo `app/explain_shap.py` (class `ShapExplainer`), `db.upsert_reliability()` (ghi từng phần, không đè dữ liệu bước khác), nối vào `app/main.py`, `scripts/stage07_test_shap.py`.
- **Kết quả chạy thật — PASS ngay lần đầu, không gặp lỗi:**
  - Flow Bot (sample_attack.json) → `is_alert=True`, có Top-5 SHAP. **`Dst Port` φ=+7,512 — gần như một mình quyết định cả quyết định** (4 đặc trưng còn lại φ chỉ 0,01–0,05) — khớp ĐÚNG với phát hiện ở RQ2 (Bot gần như hoàn toàn dựa vào Dst Port, mean|φ|≈7,4/97,1% trọng số) → xác nhận code SHAP mới hoạt động nhất quán với phân tích RQ2 gốc.
  - Additivity: sai số = **9,537e-07** — cùng bậc với RQ2 (1e-5 đến 1e-6), xác nhận TreeSHAP tính đúng.
  - Flow Benign → `shap=None`, `is_alert=False` — đúng nguyên tắc "chỉ tính SHAP khi có cảnh báo".
  - Mở DB: bảng `Reliability` có dòng ứng với `alert_id`, `shap_top5_json` đủ 5 phần tử.
  - **Thời gian SHAP qua API: 40,79 ms** — chậm hơn ~2 lần so với con số RQ2 đo khi chạy hàng loạt theo lô (~19 ms/flow). Hợp lý: RQ2 dùng `TreeExplainer` trên nhiều flow cùng lúc (tận dụng batch), còn ở đây mỗi request API chỉ giải thích 1 flow riêng lẻ + có thêm chi phí HTTP/threadpool của FastAPI. Số liệu chính xác hơn sẽ có ở thí nghiệm **E1** (đo trên nhiều flow, lấy median/p95).
- Commit: (sắp tới).
