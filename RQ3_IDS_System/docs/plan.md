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

### 0.1. BA nguồn flow hợp lệ ở Tầng 1 — ghi rõ để khỏi quên

Tài liệu kiến trúc (Khối 1 + mô hình logic Làn A) nói **Tầng 1 có đúng 3 nguồn**, KHÔNG chỉ traffic thật:

| # | Nguồn | Cách lấy | Dùng để | Trạng thái code |
|---|---|---|---|---|
| 1 | **Mạng lab thật** (Victim + Attacker) | Npcap/tcpdump bắt gói sống + CICFlowMeter gom flow trực tiếp | Demo thật, thí nghiệm E2/E3/E4 | ❌ Chưa làm — cần máy ảo (M4) + bộ feeder (bước 8b) |
| 2 | **File PCAP đã ghi sẵn** (phát lại bằng `tcpreplay`) | Vẫn qua Npcap + CICFlowMeter (chỉ khác nguồn gói là "phát lại" thay vì "sống") | Demo không cần máy Attacker, hoặc test lại 1 tình huống cố định nhiều lần | ❌ Chưa làm — **dùng CHUNG bộ feeder với nguồn 1** (CICFlowMeter vẫn ghi ra cùng 1 file CSV, feeder không cần biết gói đến từ đâu) |
| 3 | **CSV/Parquet đã có đặc trưng sẵn** (Tập A = cohort RQ2, Tập B = dữ liệu sạch) | Đọc file trực tiếp, không cần bắt gói gì cả | Test hệ thống, E5 (so khớp RQ2) | ✅ Đang dùng từ bước 3 tới giờ |

**Điểm quan trọng nhất (đã làm ĐÚNG từ đầu, xác nhận lại):** tài liệu nói *"Cả hai nguồn đổ vào CÙNG MỘT hộp tiếp theo, nên phần còn lại không cần biết flow đến từ đâu."* — và đúng là vậy: `POST /predict` của hệ thống (từ bước 6) chỉ nhận 1 dòng 78 đặc trưng, **không quan tâm nó từ CICFlowMeter hay từ file CSV có sẵn**. Vậy nguồn 1 và 2 chỉ còn thiếu đúng 1 việc: **bộ feeder** (bước 8b, mục 5.1) đứng giữa CICFlowMeter và `/predict` — **dùng chung cho cả nguồn 1 và nguồn 2**, không cần code riêng cho từng nguồn.

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

### 5.1. Bộ "feeder" — nối CICFlowMeter với hệ thống TỰ ĐỘNG (không qua tay người)

Dùng CHUNG cho cả nguồn 1 (mạng lab thật) và nguồn 2 (phát lại PCAP) ở mục 0.1 — CICFlowMeter ghi ra CSV giống nhau bất kể gói tin là "sống" hay "phát lại", nên feeder không cần phân biệt.

CICFlowMeter tự nó chỉ làm việc "bắt gói + tính đặc trưng + ghi ra CSV" — đây là phần mềm có sẵn, không cần code. Nhưng CICFlowMeter **không tự gửi** dữ liệu sang hệ thống của mình. Cần 1 mảnh code riêng — gọi là **feeder** — đứng giữa 2 bên:

```
CICFlowMeter (bắt gói, ghi CSV)  →  [FEEDER theo dõi file, phát hiện dòng mới]  →  POST /predict  →  Dashboard
```

- **Việc của bạn** (không cần code): cài Npcap + CICFlowMeter, chạy ở chế độ **bắt trực tiếp (live capture)** trỏ vào 1 card mạng — CICFlowMeter sẽ tự ghi thêm dòng mới vào 1 file CSV mỗi khi có flow mới kết thúc.
- **Việc tôi code**: script `feeder.py` chạy nền liên tục, theo dõi file CSV đó, phát hiện dòng MỚI xuất hiện → tự đối chiếu/đổi tên cột, đổi đơn vị μs (tham số đã có sẵn ở bước 4) → tự `POST /predict` → không cần ai copy/paste tay.
- **Test được NGAY BÂY GIỜ, không cần CICFlowMeter thật**: giả lập bằng cách tự ghi từng dòng của Tập B vào 1 file CSV cách nhau vài giây (như CICFlowMeter đang chạy thật), xem feeder có tự phát hiện + tự gửi đúng không. Khi có CICFlowMeter thật, chỉ cần đổi đường dẫn file theo dõi, không sửa code.
- Xếp vào **Bước 8b** trong tiến độ bên dưới — làm độc lập, không phụ thuộc thứ tự bước 9-16.

## 6. Việc tôi làm ngay bây giờ

1. `RQ3_IDS_System/scripts/stage00_build_clean_dataset.py` — tạo Tập B (loại trùng train/test, lấy mẫu phân tầng).
2. `RQ3_IDS_System/app/` — code tầng 2–6 (FastAPI + Streamlit + SQLite schema).
3. `RQ3_IDS_System/scripts/stageE1_latency.py`, `stageE5_consistency.py` — 2 thí nghiệm M2.
4. Test toàn bộ bằng Tập A + Tập B, không cần máy ảo.

## 6.1. Các bước còn lại (Bước 9 → 16) — danh sách để không quên

Viết ra hết TRƯỚC khi làm, để không quên việc gì giữa các lần làm việc. Đánh dấu ✅ và
dời xuống mục 7 (có chi tiết đầy đủ) ngay khi xong, y như các bước 1–8 đã làm.

| Bước | Nội dung | Tầng/Khối liên quan | Input cần có |
|---|---|---|---|
| **10** | "Tra bảng có sẵn (đắt)": nạp `rq2_master_summary.json` 1 lần lúc khởi động, tra `stability_lookup` + `robustness_lookup_json` theo **lớp dự đoán** (không tính lại mỗi flow — xem `gd9_stability`, `gd9_noise` trong file đó). Ghi vào 2 cột đã có sẵn trong `Reliability` nhưng chưa ai điền. | Tầng 4 | `rq2_master_summary.json` (đã có sẵn, đường dẫn trong `config.yaml: paths.rq2_master_summary`) |
| **11** | Tầng 5 — luật quyết định nhánh A/B: không có cờ nào (env_fingerprint_flag=0 và rare_class_flag=0) → nhánh A; có ít nhất 1 cờ → nhánh B. Ghi `branch` + `branch_reason` vào `Reliability`. **Lưu ý đã chốt ở tài liệu kiến trúc (mục "Đồng bộ với phần cũ")**: CHỈ dựa vào 2 cờ lưu ý này, KHÔNG dùng ngưỡng từ tập dev 250 flow của RQ2 (184/250 là Benign, không đại diện), KHÔNG dùng Agreement làm ngưỡng chính (Jaccard\@5 trung bình RQ2 chỉ 0,141). | Tầng 5 (Khối 6) | Cần Bước 8 (cờ) đã xong — ✅ |
| **12** | `GET /alerts` — danh sách Alert kèm trạng thái giải thích, lọc theo thời gian/nhãn/nhánh (theo đúng bảng API trong tài liệu kiến trúc). | Tầng 6 | Cần Bước 11 (branch) để lọc theo nhánh |
| **13** | Streamlit Dashboard — 1 trang: bảng cảnh báo, biểu đồ SHAP/LIME có dấu (2 tab), bảng độ tin cậy, nhãn nhánh A/B, `GET /health`. | Tầng 6 (Khối 7) | Cần `/alerts`, `/explain` đã có |
| **14** | Docker Compose — gói API + Dashboard thành 2 service, chạy bằng `docker compose up` (đúng mô hình vật lý: Monitor chạy Docker Compose, bắt gói chạy NGOÀI container). | Tầng 6 | Cần 13 xong |
| **15** | `scripts/stageE1_latency.py` — M2: bơm Tập A qua `/predict` + `/explain` **qua API thật**, đo median/p95 từng khâu (normalize, predict, SHAP, LIME, reliability), so với RQ2 (SHAP~19ms, LIME~148ms). | M2 (E1) | Cần `/explain` (Bước 9) xong để đo được khâu LIME |
| **16** | `scripts/stageE5_consistency.py` — M2: Tập A qua API → so nhãn + Top-5 SHAP với kết quả gốc RQ2 (khớp 100% thì xác nhận hệ thống không lỗi). | M2 (E5) | Không phụ thuộc bước nào ở trên, có thể làm sớm hơn nếu muốn |

Sau Bước 16 mới tới **M4** (dựng 3 máy ảo Victim/Attacker/Monitor trên VirtualBox host-only) và **M5** (E2 lệch phân bố, E3 báo động giả, E4 cờ môi trường — đo trên traffic thật từ M4).

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

### Bước 7 — Tầng 4a: TreeSHAP tự động, nối vào `/predict` ✅
- **Mục đích**: mỗi cảnh báo có kèm "vì sao mô hình nghĩ vậy" — SHAP chạy TỰ ĐỘNG cho mọi Alert (khác LIME ở bước 9, chỉ chạy khi analyst bấm xin, đúng nguyên tắc kiến trúc Khối 3).
- Tạo `app/explain_shap.py` (class `ShapExplainer`), `db.upsert_reliability()` (ghi từng phần, không đè dữ liệu bước khác), nối vào `app/main.py`, `scripts/stage07_test_shap.py`.
- **Kết quả chạy thật — PASS ngay lần đầu, không gặp lỗi:**
  - Flow Bot (sample_attack.json) → `is_alert=True`, có Top-5 SHAP. **`Dst Port` φ=+7,512 — gần như một mình quyết định cả quyết định** (4 đặc trưng còn lại φ chỉ 0,01–0,05) — khớp ĐÚNG với phát hiện ở RQ2 (Bot gần như hoàn toàn dựa vào Dst Port, mean|φ|≈7,4/97,1% trọng số) → xác nhận code SHAP mới hoạt động nhất quán với phân tích RQ2 gốc.
  - Additivity: sai số = **9,537e-07** — cùng bậc với RQ2 (1e-5 đến 1e-6), xác nhận TreeSHAP tính đúng.
  - Flow Benign → `shap=None`, `is_alert=False` — đúng nguyên tắc "chỉ tính SHAP khi có cảnh báo".
  - Mở DB: bảng `Reliability` có dòng ứng với `alert_id`, `shap_top5_json` đủ 5 phần tử.
  - **Thời gian SHAP qua API: 40,79 ms** — chậm hơn ~2 lần so với con số RQ2 đo khi chạy hàng loạt theo lô (~19 ms/flow). Hợp lý: RQ2 dùng `TreeExplainer` trên nhiều flow cùng lúc (tận dụng batch), còn ở đây mỗi request API chỉ giải thích 1 flow riêng lẻ + có thêm chi phí HTTP/threadpool của FastAPI. Số liệu chính xác hơn sẽ có ở thí nghiệm **E1** (đo trên nhiều flow, lấy median/p95).
- **Bạn tự test lại thủ công qua Swagger UI** (`/docs`), độc lập với script tự động:
  - Dán `sample_attack.json` (Bot) vào `POST /predict` → xác nhận response có trường `"shap"` đầy đủ (`class_explained`, `base_value`, `top_k` 5 đặc trưng, `additivity_error`), khác hẳn lần test bước 6 lúc trường này còn chưa tồn tại.
  - Dán `sample_benign.json` vào `POST /predict` → xác nhận trường `"shap"` là `null` (đúng nguyên tắc: Benign không tạo cảnh báo nên không chạy SHAP).
- Commit: `5e39a85`.

### Bước 7b — Sửa lỗi kiến trúc: hàng đợi giải thích BẤT ĐỒNG BỘ ✅
- **Vì sao có bước này**: trước khi làm bước 8, kiểm lại 8 bước "Luồng xử lý một flow" trong tài liệu kiến trúc so với code đã viết (bước 1-7). Phát hiện: tài liệu yêu cầu *"Cảnh báo hiện lên dashboard NGAY, phần giải thích được NỐI THÊM VÀO khi tính xong"* + *"giải thích được ghi thành một tác vụ CHỜ (tối đa 50)... nếu hàng đợi đầy thì cảnh báo vẫn hiện, chỉ thiếu phần giải thích"* — nhưng code bước 7 lại tính SHAP ĐỒNG BỘ ngay trong `/predict`, không có hàng đợi, không có giới hạn 50. Đây là 1 **lỗi kiến trúc thật**, không chỉ là thiếu sót nhỏ — nếu không sửa, traffic thật dồn dập (demo DDoS) sẽ làm API chậm dây chuyền.
- **Mục đích**: tách việc tính SHAP ra khỏi request `/predict` — API tạo Alert và trả lời ngay, SHAP chạy trong 1 **thread nền riêng**, đọc việc từ 1 **hàng đợi có giới hạn** (`queue.Queue(maxsize=50)`, lấy từ `config.yaml: api.max_explain_queue`). Hàng đợi đầy → bỏ phần giải thích, GIỮ nguyên cảnh báo.
- Tạo `app/explain_queue.py` (class `ExplainQueue`: `submit()` không chặn, worker thread riêng xử lý tuần tự); sửa `app/main.py` (`/predict` gọi `explain_queue.submit()` thay vì gọi SHAP trực tiếp, trả thêm field `explanation_status`: `"queued"` / `"dropped_queue_full"` / `None`); thêm `GET /explain_queue_status` để quan sát hàng đợi; tạo `scripts/stage07b_test_async_queue.py`.
- **2 lỗi thật gặp phải khi test, đã sửa:**
  1. **Test sai thiết kế**: lần đầu gửi 60 request TUẦN TỰ để ép hàng đợi đầy — nhưng worker xử lý SHAP (~40ms) nhanh hơn tốc độ gửi tuần tự (~96ms/request) nên hàng đợi không bao giờ đầy kịp (0/60 dropped). **Sửa**: dùng `ThreadPoolExecutor` gửi 70 request ĐỒNG THỜI.
  2. **`sqlite3.OperationalError: database is locked`** (lỗi thật, quan trọng): 70 connection SQLite ghi đồng thời bị khóa lẫn nhau, nhiều request lỗi 500. **Sửa**: bật `PRAGMA journal_mode = WAL` (cho phép đọc/ghi đồng thời tốt hơn) + `timeout=10.0` khi mở connection (chờ thay vì báo lỗi ngay khi bị khóa tạm thời) trong `app/db.py`.
- **Kết quả chạy thật (sau khi sửa cả 2 lỗi) — mọi [PASS]:**
  - `/predict` không còn field `"shap"` trong response, `explanation_status="queued"` — xác nhận đã tách SHAP ra khỏi đường đồng bộ.
  - Phát hiện thêm: tổng thời gian request vẫn ~40-108ms dù đã bỏ SHAP (~40ms) ra khỏi đường đồng bộ — có ~overhead khác (có thể từ FastAPI/SQLite/Windows) **đã tồn tại từ trước bước 7b**, không phải do thay đổi này gây ra; để lại cho **E1** đo chính xác, không thuộc phạm vi bước này.
  - Đợi worker xử lý xong: `Reliability.shap_top5_json` xuất hiện đúng 5 phần tử.
  - Dội 70 request đồng thời (maxsize=50): **60 'queued', 10 'dropped_queue_full'** — đúng kỳ vọng. Alert bị dropped **vẫn tồn tại** trong `AlertRecord` (không mất cảnh báo), chỉ `Reliability` không có dòng (đúng — không được xếp hàng giải thích).
- Commit: `cf83fb6`.

### Bước 8b — Bộ "feeder" tự động (chuẩn bị cho bắt traffic thật) ✅
- **Mục đích**: trả lời câu hỏi "hệ thống có tự động bắt rồi đưa flow vào model không, hay phải làm tay?" — xem chi tiết mục 5.1. Dùng CHUNG cho cả nguồn 1 (mạng lab thật) và nguồn 2 (PCAP phát lại) ở mục 0.1 — CICFlowMeter ghi CSV giống nhau bất kể gói tin "sống" hay "phát lại".
- Tạo `app/feeder.py`: theo dõi 1 file CSV, phát hiện dòng MỚI (so độ dài file mỗi vòng lặp) → đọc, đổi đơn vị μs nếu cần (tham số `--convert-units`, dùng lại `TIME_COLUMNS` từ `app/normalize.py`) → tự `POST /predict` → log kết quả. Thêm `feeder` section vào `config.yaml` (đường dẫn theo dõi mặc định, chu kỳ kiểm tra, cờ đổi đơn vị).
- Tạo `scripts/stage08b_test_feeder.py`: GIẢ LẬP CICFlowMeter thật bằng cách tự ghi 8 dòng của Tập B vào 1 file CSV, cách nhau 1,5 giây (không cần CICFlowMeter/máy ảo gì cả).
- **2 lỗi gặp khi test (cả 2 đều ở SCRIPT TEST, không phải ở feeder) — đã sửa:**
  1. Quên bật **unbuffered** (`-u`) cho tiến trình con `feeder.py` → log chưa kịp ghi ra file khi script test đọc, tưởng feeder gửi 0 dòng (thực ra DB đã nhận đủ 8 — kiểm tra DB trực tiếp phát hiện ra feeder vẫn đúng, chỉ log đọc sai).
  2. Regex kiểm tra log dùng `\S+` (không khoảng trắng) để bắt `predicted_label` — SAI vì nhãn như "Brute Force -XSS" có khoảng trắng, chỉ khớp nhãn 1 từ (SSH-Bruteforce, Infilteration, Benign) → **sửa thành** `(.+?), is_alert=` để bắt đủ cả nhãn có khoảng trắng.
- **Kết quả chạy thật — mọi [PASS]:**
  - Feeder gửi đủ **8/8 dòng**, đúng thứ tự #1→#8, không thiếu không trùng.
  - **Nhãn dự đoán đúng 7/8** — chỉ sai đúng 1 ca: SQL Injection (lớp cực hiếm, 9-13 mẫu toàn tập) bị đoán Benign, khớp với hạn chế đã biết từ RQ1, không phải lỗi feeder.
  - Mở DB: `FlowRecord` tăng đúng 8 dòng sau khi feeder chạy.
  - Toàn bộ luồng **CSV → feeder → /predict → DB** chạy tự động hoàn toàn, không cần tay người ở giữa — đúng mục tiêu ban đầu của bước này.
- Khi có CICFlowMeter thật (M4): chỉ cần đổi `--watch` sang đường dẫn CICFlowMeter ghi ra và bật `--convert-units` (nếu CICFlowMeter xuất giây) — không cần sửa code.
- Commit: `f0f21b4`.

### M3 — Test bằng traffic thật trên chính máy bạn (KHÔNG cần máy ảo) ✅
- **Vì sao làm ngay, không đợi M4**: M3 (mục 1.2, mục 2) không phụ thuộc M4 — chỉ cần Npcap + CICFlowMeter chạy trên máy hiện tại, bắt traffic bình thường (lướt web), không cần máy Victim/Attacker. Làm ngay để xác nhận "cầu nối" CSV→feeder→hệ thống hoạt động với dữ liệu CICFlowMeter THẬT (không phải giả lập từ Tập B như bước 8b).
- **Môi trường mới riêng**: `RQ3_IDS_System/.venv_capture/` (Python 3.13, KHÔNG dùng lại venv của `cicflowmeter_capture_demo/`), cài `cicflowmeter==0.5.0` (ghi lại ở `requirements-capture.txt`). Lý do cần bản 0.5.0: bản 0.2.0 đi kèm Python 3.11 có lỗi ghi flow trên Windows (đã biết từ trước).
- **⚠️ Chỉ `scripts/run_live_capture.py` cần chạy bằng `.venv_capture`** (vì nó import trực tiếp thư viện `cicflowmeter`). `app/feeder.py` và `app/main.py` (API) vẫn chạy bằng **Python hệ thống** như mọi bước trước (cần `yaml`, `pandas`, `fastapi`... mà `.venv_capture` không có, chỉ có `cicflowmeter`/`scapy`). Dùng nhầm venv cho feeder sẽ báo `ModuleNotFoundError: No module named 'yaml'` — đã gặp thật khi hướng dẫn test, đã sửa lại hướng dẫn.
- **3 lỗi/vấn đề thật gặp phải, đã tìm ra và sửa (không phải vấn đề ở hệ thống RQ3, mà ở việc dùng CICFlowMeter đúng cách):**
  1. **Lỗi thật trong chính thư viện `cicflowmeter` 0.5.0**: `sniffer.py::main()` gọi `create_sniffer(...)` bằng tham số VỊ TRÍ nhưng thứ tự không khớp chữ ký hàm — `args.verbose` (bool) bị nhét nhầm vào tham số `fields`, gây `AttributeError: 'bool' object has no attribute 'split'` mỗi khi chạy qua CLI `cicflowmeter` thẳng. **Sửa**: viết `scripts/run_live_capture.py` gọi THẲNG hàm `create_sniffer()` bằng keyword argument (né lỗi thứ tự), không qua CLI gốc.
  2. **File CSV trống dù bắt được hàng nghìn gói tin**: CICFlowMeter chỉ ghi 1 flow ra CSV khi flow đã "đóng" (FIN/RST) hoặc hết hạn (timeout) — dừng sớm (test 15 giây) mà không ép ghi nốt thì mọi flow "đang mở" (đa số traffic HTTPS/keep-alive) bị bỏ qua, file trông như trống dù đã xử lý 4316+ gói tin. **Sửa**: gọi `session.flush_flows()` (có sẵn trong thư viện) ngay sau khi dừng sniffer, ép ghi nốt toàn bộ flow còn dang dở.
  3. **Tên cột hoàn toàn khác** (đúng như đã cảnh báo trước khi làm): CICFlowMeter 0.5.0 xuất tên cột kiểu `snake_case` (`dst_port`, `flow_duration`...) + 4 cột định danh thừa (`src_ip`, `dst_ip`, `src_port`, `timestamp`), khác hẳn 78 tên cột model cần (`Dst Port`, `Flow Duration`...). Thời gian cũng xác nhận ra là **giây** (vd `flow_duration=15.016630`), đúng như tài liệu kiến trúc đã cảnh báo. **Sửa**: thêm `CICFLOWMETER_COLUMN_MAP` (78 cặp ánh xạ 1-1, phát hiện thêm 1 điểm lệch tên: `cwr_flag_count` ↔ `CWE Flag Count`) vào `app/feeder.py`, áp dụng trước khi gửi; 4 cột định danh không có trong bảng ánh xạ cứ để nguyên, `/predict` tự bỏ qua vì không nằm trong 78 cột nó cần.
- **Kết quả chạy thật — luồng đầy đủ không giả lập bất kỳ phần nào:**
  - Bắt traffic Wi-Fi thật 15 giây trong lúc dùng máy bình thường → 4316+ gói tin, 25 flow ghi ra CSV (sau khi ép flush).
  - Chạy `feeder.py --convert-units` trên file CSV thật đó (không phải Tập B giả lập) → gửi đủ **25/25 flow** qua `/predict`.
  - **Kết quả dự đoán: 25/25 = Benign** — đúng 100%, hợp lý vì đây chỉ là traffic bình thường, không có tấn công nào.
  - Xác nhận toàn bộ chuỗi **gói tin thật → CICFlowMeter thật → feeder (đổi tên cột + đơn vị) → API → model → DB** chạy đúng, không có bước nào còn là giả lập.
- Việc còn lại để có M4 đầy đủ: traffic TẤN CÔNG thật (cần máy Attacker + Victim, mạng host-only cô lập) để xem hệ thống có phát hiện và cảnh báo đúng không — quy trình kỹ thuật (feeder, mapping cột, flush) đã kiểm chứng xong ở đây, M4 chỉ còn là việc dựng máy ảo + tạo traffic tấn công, không cần sửa code gì thêm.

### Bước 8 — Tầng 4b: Đánh giá độ tin cậy + gắn cờ ✅
- **Mục đích**: đúng mục "Tầng 4" trong plan (mục 3) — phần "Tính tại chỗ (rẻ)": faithfulness proxy nhanh + đếm cờ môi trường + cờ lớp hiếm, chạy cho MỌI Alert, NGAY SAU TreeSHAP (dùng Top-5 SHAP làm input) — khác với "tra bảng có sẵn từ RQ2" (đắt hơn, để ở bước 10).
- **⚠️ Nhắc lại overclaim** (giữ nguyên trong docstring `app/reliability.py`): faithfulness ở đây chỉ là PROXY một bước/một giá trị nền — KHÔNG phải phép đo faithfulness đầy đủ của RQ2 (xóa k=1..10, 3 giá trị nền, AUC, đối chứng ngẫu nhiên, Wilcoxon). Cờ môi trường chỉ là cờ cảnh báo/bằng chứng hỗ trợ, chưa phải kết luận đã kiểm chứng (kiểm chứng giả thuyết này là **E4**, chưa làm).
- Tạo `scripts/stage08_compute_train_stats.py`: chạy 1 lần, đọc `train_set.parquet` (2,8 triệu dòng), tính trung vị toàn cục (`global_median`) của 78 đặc trưng + số mẫu huấn luyện từng lớp, lưu ra `data/train_stats.json` (không commit, đã thêm vào `.gitignore` — tái tạo được bằng cách chạy lại script). Kết quả: chỉ **SQL Injection = 70 mẫu** dưới ngưỡng 100 (`rare_class_min_train_samples` trong `config.yaml`) — lớp hiếm duy nhất trong Tập B/C.
- Tạo `app/reliability.py` (class `ReliabilityScorer`): nạp `train_stats.json` 1 lần lúc server khởi động, hàm `score()` nhận flow đã chuẩn hóa + nhãn dự đoán + Top-5 SHAP, trả về:
  - `faithfulness_proxy_drop`: đặt Top-k (mặc định k=5, lấy từ `config.yaml: faithfulness_proxy.k`) đặc trưng SHAP về `global_median`, gọi lại `Detector.predict_flow()`, đo xác suất lớp dự đoán tụt bao nhiêu.
  - `env_fingerprint_count`/`env_fingerprint_flag`: đếm trong Top-5 có bao nhiêu đặc trưng thuộc 3 đặc trưng môi trường (`Dst Port`, `Fwd Seg Size Min`, `Init Fwd Win Byts`), bật cờ khi ≥2 (ngưỡng từ `config.yaml`).
  - `rare_class_flag`: bật khi nhãn dự đoán có dưới 100 mẫu huấn luyện (tra từ `train_stats.json`, không tính lại mỗi request).
- Nối vào `app/explain_queue.py`: `ReliabilityScorer.score()` chạy trong CÙNG worker thread, NGAY SAU SHAP (dùng lại `shap_result["top_k"]` vừa tính), ghi 4 cột mới vào `Reliability` qua `upsert_reliability()` (không đè `shap_top5_json` đã ghi trước đó), thêm `Timing(step="reliability")`. Sửa `app/main.py`: khởi tạo `ReliabilityScorer` 1 lần lúc startup (đọc `train_stats.json` + tham số từ `config.yaml`), truyền vào `ExplainQueue`.
- Tạo `scripts/stage08_test_reliability.py`: bật server con, bắn 2 flow THẬT từ Tập B (`clean_holdout_set.csv`) qua `/predict` — SQL Injection (lớp hiếm, kỳ vọng `rare_class_flag=1`) và Bot (lớp thường, kỳ vọng `rare_class_flag=0`) — chờ hàng đợi xử lý xong rồi mới đọc DB (vì SHAP/reliability chạy bất đồng bộ từ Bước 7b).
- **Kết quả chạy thật — cả 2 case [PASS]:**
  - SQL Injection: `predicted_label=SQL Injection` (đoán đúng), `faithfulness_proxy_drop=0,8202`, `env_fingerprint_count=1` → `env_fingerprint_flag=0` (dưới ngưỡng 2), `rare_class_flag=1` — đúng, lớp có 70 mẫu train < 100.
  - Bot: `faithfulness_proxy_drop=0,9957` (xác suất Bot tụt gần hết khi xóa Top-5 SHAP — khớp phát hiện RQ2 là Bot gần như chỉ dựa vào `Dst Port`), `env_fingerprint_count=1` → `env_fingerprint_flag=0`, `rare_class_flag=0` — đúng, lớp có 100.650 mẫu train.
  - Trước khi viết test, đã mở trực tiếp `ids_system.db` kiểm tra: 183 Alert cũ (tạo trước khi bước 8 có code) đúng như dự kiến có `faithfulness_proxy_drop=NULL`, chỉ 1 Alert mới nhất (lúc đang thử feeder, nhãn Bot) có đủ số liệu — xác nhận code không âm thầm ghi đè/sai dữ liệu cũ.
- Commit: `79cbe5f`.

### Bước 9 — Tầng 4b: LIME theo yêu cầu (`POST /explain`) ✅
- **Mục đích**: thêm cách giải thích thứ 2 (LIME) bên cạnh SHAP — nhưng KHÔNG tự động (chậm hơn SHAP ~8 lần: RQ2 đo LIME~148ms so SHAP~19ms), chỉ chạy khi analyst chủ động xin qua `POST /explain`.
- Tra lại đúng cách RQ2 cài đặt LIME (`RQ2/scripts/stage06_lime_per_flow.py`) để dùng chung phương pháp, so sánh được: `LimeTabularExplainer` khởi tạo 1 lần với nền 2.000 dòng (seed khóa), cách seed riêng theo từng flow (`RQ2/scripts/lib/common.py::set_lime_explainer_seed` — lime==0.2.0.1 không có tham số `random_state` ở `explain_instance()`, phải tự gán lại thủ công `explainer.random_state` + `explainer.base.random_state` trước MỖI lần gọi, nếu không kết quả không tái lập được).
- Tạo `scripts/stage09_compute_lime_background.py`: lấy sẵn 2.000 dòng nền từ `train_set.parquet` (seed khóa trong `config.yaml: lime.background_seed`), lưu `data/lime_background.npy` (không commit, gitignore) — tránh đọc lại 2,8 triệu dòng mỗi lần khởi động server.
- Tạo `app/explain_lime.py` (class `LimeExplainer`, hàm `set_lime_explainer_seed` sao chép nguyên vẹn từ RQ2): seed riêng theo từng alert bằng cách băm `alert_id` (chuỗi UUID) ra số nguyên ổn định (`sha256` — không dùng `hash()` built-in vì `PYTHONHASHSEED` ngẫu nhiên giữa các lần chạy).
- Thêm `POST /explain` vào `app/main.py`: nhận `alert_id` + `method` (chỉ nhận `"lime"`, SHAP đã tự động nên không xin lại qua đây). Chạy ĐỒNG BỘ (analyst đang chờ, không qua hàng đợi nền như SHAP), giới hạn số lượt chạy cùng lúc bằng `threading.Semaphore(config.yaml: api.max_concurrent_lime=4)` — vượt ngưỡng trả `429`; không có `alert_id` trả `404`. Ghi `lime_top5_json` + `agreement_jaccard5` vào `Reliability`.
- Thêm `db.get_alert()`, `db.get_flow_features()`, `db.get_shap_top5()` vào `app/db.py` (tra cứu lại dữ liệu đã lưu, vì request `/explain` chỉ gửi `alert_id`, không gửi lại 78 đặc trưng).
- **Agreement (Jaccard\@5) tính ĐÚNG cách RQ2 làm** (`RQ2/scripts/stage07_agreement.py`): so trực tiếp tên đặc trưng SHAP (sạch, vd `"Dst Port"`) với `feature_desc` THÔ của LIME (có thể kèm bất đẳng thức, vd `"Dst Port <= 8080.00"`) — KHÔNG tự "sửa" cho khớp đẹp hơn, vì đây chính là 1 lý do Jaccard\@5 trung bình RQ2 chỉ 0,141.
- Tạo `scripts/stage09_test_lime.py`, test qua API thật, 5 việc:
  1. Flow Bot → `/explain` trả Top-5 LIME hợp lệ, `local_r2` trong [0,1], có `agreement_jaccard5`.
  2. `alert_id` không tồn tại → `404`.
  3. `method="shap"` (không hỗ trợ qua `/explain`) → `400`.
  4. Mở DB xác nhận `lime_top5_json` (5 phần tử) + `agreement_jaccard5` đã ghi vào `Reliability`.
  5. Gọi lại `/explain` LẦN 2 cùng `alert_id` → Top-5 và `local_r2` phải GIỐNG HỆT lần 1 (seed cố định theo flow, đúng nguyên tắc tái lập của RQ2).
- **Kết quả chạy thật — cả 5 việc [PASS]**:
  - Flow Bot: `local_r2=0,4731` (model tuyến tính cục bộ của LIME khớp model gốc ở mức trung bình), Top-5 LIME hoàn toàn khác Top-5 SHAP (LIME không hề chọn `Dst Port`, dù SHAP coi đó gần như quyết định duy nhất) → `agreement_jaccard5=0,111` (chỉ 1 đặc trưng trùng trong hợp 9 đặc trưng).
  - **Phát hiện cần ghi nhận trung thực, không phải lỗi**: con số Agreement rất thấp này khớp đúng hiện tượng RQ2 đã ghi nhận (Jaccard\@5 trung bình chỉ 0,141, SHAP và LIME "ít khi đồng ý") — đây là dấu hiệu code hoạt động nhất quán với phát hiện gốc, KHÔNG phải dấu hiệu lỗi cần sửa.
  - Thời gian gọi `/explain` qua API: 66,6ms — nhanh hơn số RQ2 đo khi chạy hàng loạt (~148ms), hợp lý vì đây chỉ 1 request đơn, chưa tính network stack đầy đủ như batch RQ2; số chính xác hơn để dành cho **E1**.
  - Gọi lại lần 2: `local_r2` và Top-5 giống hệt lần 1 (sai số 0) — xác nhận seed theo flow hoạt động đúng, tái lập được.
- Commit: `4e866ca`.

### Bước 11 — Tầng 5: Luật quyết định nhánh A/B ✅
- **Mục đích**: thêm luật quyết định flow nào hiển thị "bình thường" (nhánh A), flow nào cần hiển thị kèm cảnh báo "cần xem lại" + gợi ý xem thêm LIME (nhánh B) — chỉ đổi CÁCH HIỂN THỊ, không đổi nhãn, không ẩn cảnh báo (đúng nguyên tắc cứng ở mục 0 và mục 3 của plan). Bỏ qua Bước 10 (tra bảng RQ2) theo quyết định của bạn — bước 11 không phụ thuộc bước 10, chỉ dùng 2 cờ đã có từ bước 8.
- Thêm `ReliabilityScorer._decide_branch()` vào `app/reliability.py`, gọi trong `score()`: branch = `'A'` nếu CẢ 2 cờ (`env_fingerprint_flag`, `rare_class_flag`) đều 0; `'B'` nếu có ít nhất 1 cờ được bật — **CHỈ dựa vào 2 cờ này**, đúng như plan đã chốt (không dùng ngưỡng từ tập dev 250 flow của RQ2 vì không đại diện, không dùng Agreement vì Jaccard\@5 trung bình RQ2 chỉ 0,141, không đủ ổn định làm ngưỡng). Ghi kèm `branch_reason` mô tả cờ nào gây ra nhánh B.
- Sửa `app/explain_queue.py`: ghi thêm `branch` + `branch_reason` vào `Reliability` cùng lúc với các cột bước 8 (không cần bước/worker riêng, vì đã có đủ 2 cờ ngay sau khi `score()` chạy).
- Tạo `scripts/stage11_test_branch.py`: test qua API thật với 3 case, cố tình chọn đủ cả 3 tình huống khác nhau:
  1. Bot (cả 2 cờ = 0) → kỳ vọng branch = 'A'.
  2. SQL Injection (rare_class_flag=1) → kỳ vọng branch = 'B'.
  3. DoS attacks-Hulk (dự đoán trước từ SHAP toàn cục RQ2: Top-5 gồm `Fwd Seg Size Min` + `Init Fwd Win Byts`, đủ 2 đặc trưng môi trường → env_fingerprint_flag=1) → kỳ vọng branch = 'B'.
- **Kết quả chạy thật — cả 3 case [PASS]:**
  - Bot: `env_fingerprint_flag=0, rare_class_flag=0` → `branch=A`, `branch_reason="Không có cờ nào được bật — hiển thị SHAP bình thường."`
  - SQL Injection: `rare_class_flag=1` → `branch=B`, `branch_reason` nêu đúng lý do.
  - DoS attacks-Hulk: dự đoán đúng trước khi test — `env_fingerprint_flag=1` thật (không phải giả định) → `branch=B` — xác nhận nhánh B không chỉ lý thuyết, có flow thật rơi vào đúng trường hợp này.
- Commit: `b31fe54`.

### Bước 12 — Tầng 6: `GET /alerts` ✅
- **Mục đích**: thêm API trả danh sách Alert kèm trạng thái giải thích, lọc theo thời gian/nhãn/nhánh — đúng nguyên văn bảng API trong tài liệu kiến trúc (`Kiến trúc hệ thống IDS.docx`, phần "Giao diện (API) giữa tầng 6 và các tầng dưới": *"GET /alerts | Bộ lọc thời gian, nhãn, nhánh | Danh sách Alert kèm trạng thái giải thích"*). Đây là API đầu tiên cung cấp dữ liệu "nhìn thấy được" cho Dashboard (bước 13).
- Thêm `db.get_alerts(conn, since, until, label, branch)` vào `app/db.py`: `LEFT JOIN AlertRecord` với `Reliability` (LEFT vì SHAP có thể chưa xử lý xong — hàng đợi bất đồng bộ từ bước 7b — hoặc đã bị bỏ do hàng đợi đầy, khi đó không có dòng `Reliability`), lọc động theo tham số được truyền, sắp theo `created_at` giảm dần. Tính `explanation_status` theo 3 mức: `"pending_or_dropped"` (chưa có `shap_top5_json`), `"shap_only"`, `"shap_and_lime"`.
- Thêm `GET /alerts` vào `app/main.py`: 4 tham số query tùy chọn `since`/`until` (ISO 8601, so sánh chuỗi vì `created_at` luôn ghi cùng định dạng UTC), `label` (= predicted_label), `branch` (chỉ nhận `'A'`/`'B'`, sai thì `422`).
- Tạo `scripts/stage12_test_alerts.py`, test qua API thật, 5 việc: (1) không lọc gì → thấy đủ 2 alert vừa tạo (Bot + SQL Injection); (2) lọc `label=Bot` → chỉ còn alert Bot; (3) lọc `branch=B` → chỉ còn alert branch B; (4) lọc `since=<mốc trước 2 alert mới>` → loại hết alert cũ, chỉ còn đúng 2 alert mới; (5) `branch=C` (sai) → `422`.
- **Kết quả chạy thật — cả 5 việc [PASS]:**
  - DB lúc test đã có 254 alert tích lũy từ các bước trước — `GET /alerts` không lọc trả đủ `count=254`, có cả 2 alert mới.
  - `label=Bot` → `count=78` (đúng số Alert Bot tích lũy qua nhiều lần test trước đó).
  - `branch=B` → `count=3` (đúng — 1 từ bước 11 (SQL Injection) + 1 từ bước 11 (DoS Hulk) + 1 SQL Injection mới tạo lúc test này).
  - `since=<mốc ngay trước khi tạo 2 alert mới>` → `count=2`, lọc đúng chỉ còn 2 alert mới tạo, loại hết 252 alert cũ.
  - `branch=C` → `422` đúng như kỳ vọng validate input.
- Commit: `1eabece`.

### Việc thêm trước bước 13 — Hỗ trợ đọc lại file `.pcap` (nguồn 2 ở mục 0.1) ✅
- **Mục đích**: trả lời câu hỏi "test CSV/PCAP có trích xuất đưa vào model được chưa" — xác nhận CSV đã test từ lâu (bước 3, 8b, M3); PCAP thì chưa, nhưng khi đọc lại code thư viện `cicflowmeter` phát hiện KHÔNG cần `tcpreplay` như kiến trúc dự tính ban đầu — `create_sniffer(input_file=...)` tự đọc trực tiếp 1 file `.pcap`, xử lý giống hệt bắt sống.
- Sửa `scripts/run_live_capture.py`: thêm `--pcap-input <file>` (nhóm loại trừ lẫn nhau với `--interface`) — đọc xong hết gói trong file thì tự dừng (không cần `--seconds`/Ctrl+C như khi bắt sống).
- **Chưa test được bằng chạy thật** — cần 1 file `.pcap` thật (chưa có sẵn trong máy, cần bạn tự bắt bằng Npcap giống M3 rồi lưu ra `.pcap`, hoặc cung cấp file có sẵn). Việc test thật để sau, không chặn bước 13.
- Commit: `bc9f158`.

### Bước 13 — Tầng 6 (Khối 7): Streamlit Dashboard ✅
- **Mục đích**: trang Dashboard duy nhất — bảng cảnh báo, biểu đồ SHAP/LIME có dấu (2 tab), bảng độ tin cậy, nhãn nhánh A/B, hiển thị trạng thái `/health` — đúng mục 3 "Tầng 6 — API + Dashboard" của plan. Đây là phần đầu tiên xem được trực tiếp trên trình duyệt, không chỉ qua script test.
- Cài `streamlit==1.65.0` (thêm vào `requirements.txt`) — lưu ý thật gặp phải: `pip` trên máy trỏ sang 1 môi trường Anaconda khác (`PRP201c`), khác với `python` dùng cho project này → cài nhầm môi trường, `import streamlit` báo thiếu module dù vừa cài xong. **Sửa**: dùng `python -m pip install` thay vì gọi `pip` trực tiếp, đảm bảo cài đúng vào môi trường `python` đang dùng.
- Tạo `app/dashboard.py`: gọi API qua HTTP (`requests`, giống mọi script test từ bước 6 tới giờ) — **không đọc trực tiếp file DB**, đúng tách bạch Tầng 6 API / Dashboard trong kiến trúc. Gồm: khối trạng thái `/health` + `/explain_queue_status` (model, số lớp, hàng đợi, số bị bỏ); bộ lọc + bảng cảnh báo (gọi `/alerts`, đúng bước 12); chọn 1 alert → 2 tab SHAP/LIME (biểu đồ cột có dấu `st.bar_chart`, dương/âm rõ ràng) + nút "Xin giải thích LIME" (gọi `/explain` ngay trong dashboard nếu chưa có); bảng độ tin cậy kèm đúng các cảnh báo overclaim (faithfulness chỉ là proxy, cờ môi trường chỉ là cờ cảnh báo) lấy nguyên văn từ plan.md.
- Mở rộng `db.get_alerts()` (bước 12) để trả thêm đầy đủ các cột `Reliability` còn thiếu (`shap_top5`, `lime_top5`, `agreement_jaccard5`, `faithfulness_proxy_drop`, cờ, `stability_lookup`, `robustness_lookup`) — cần cho Dashboard hiển thị chi tiết, đúng nghĩa "danh sách Alert KÈM trạng thái giải thích" trong tài liệu kiến trúc (không phải sửa lại API, chỉ bổ sung trường trả về — đã chạy lại `scripts/stage12_test_alerts.py` xác nhận không vỡ bước 12 cũ).
- Tạo `scripts/stage13_test_dashboard.py` — **phát hiện thật khi viết test**: lần đầu test bằng cách gửi HTTP GET thẳng vào trang Dashboard rồi tìm chữ "RQ3"/"IDS" trong HTML trả về — LUÔN THẤT BẠI dù dashboard chạy đúng, vì Streamlit trả về 1 khung HTML tĩnh giống nhau cho mọi app (chỉ load React, nội dung thật chỉ render sau khi có kết nối WebSocket) — cách test đó không phát hiện được lỗi thật bên trong script. **Sửa đúng cách**: dùng `streamlit.testing.v1.AppTest` (có sẵn từ Streamlit 1.65.0) — chạy THẬT script `app/dashboard.py` ở chế độ headless, bắt được exception thật nếu code có lỗi.
- Test 3 việc: (1) chạy `AppTest.from_file()` lần đầu, không được có exception; (2) trang phải có tiêu đề chứa "IDS" + ít nhất 1 bảng; (3) chọn 1 alert ĐÃ CÓ LIME trong selectbox (xin LIME trước qua `/explain`), chạy lại, không lỗi, phải thấy thêm bảng chi tiết.
- **Kết quả chạy thật — cả 3 việc [PASS], 0 exception ở cả 2 lần chạy script** (lần đầu + sau khi chọn alert có LIME):
  - Bắn 3 flow thật (Bot, SQL Injection, DoS attacks-Hulk) qua `/predict`, xin thêm LIME cho 1 alert qua `/explain`, rồi mới chạy AppTest — Dashboard hiển thị đúng dữ liệu thật, không phải dữ liệu giả.
  - Phát hiện phụ (không phải lỗi, chỉ dọn sạch): Streamlit cảnh báo `use_container_width` sẽ bị bỏ sau 2025-12-31 — đã sửa hết 4 chỗ thành `width="stretch"`, chạy lại xác nhận hết cảnh báo.
- Commit: `bc9f158`.

### Bước 13 (bổ sung theo yêu cầu) — Nạp dữ liệu ngay trên Dashboard (CSV + PCAP) ✅
- **Mục đích**: bạn hỏi muốn Dashboard có sẵn các nút gửi CSV/PCAP (và real-time để sau) thay vì phải dùng Swagger UI hay terminal riêng — thêm 1 khối "Nạp dữ liệu vào hệ thống" ngay trên Dashboard, vẫn gọi `/predict` qua HTTP như mọi nguồn khác (không tự ý gọi tắt qua hàm Python nào khác, giữ đúng nguyên tắc Dashboard chỉ là client của API).
- Thêm 2 tab vào `app/dashboard.py`:
  - **"Gửi file CSV"**: `st.file_uploader`, đọc toàn bộ dòng, dùng lại `feeder.row_to_payload()` (bước 8b) để map tên cột/đơn vị, gửi từng dòng vào `/predict`, có thanh tiến trình + bảng kết quả từng dòng (OK/lỗi/predicted_label).
  - **"Phát lại PCAP"**: `st.file_uploader` nhận `.pcap`/`.pcapng`, lưu ra `data/dashboard_uploaded_replay.pcap`, gọi `subprocess` chạy `scripts/run_live_capture.py --pcap-input ... ` bằng Python của `.venv_capture` (đúng việc mới thêm trước bước 13), đọc CSV CICFlowMeter xuất ra, map cột/đơn vị, gửi từng flow vào `/predict`. Có kiểm tra `venv_capture` chưa cài thì báo lỗi rõ ràng, trỏ tới mục M3/5.1 trong plan — không âm thầm crash.
- Mở rộng `scripts/stage13_test_dashboard.py` thêm **Việc 4**: dùng `AppTest.file_uploader[...].upload()` (có sẵn từ Streamlit 1.65.0) để giả lập người dùng thật upload file `data/clean_holdout_set.csv` (241 dòng, Tập B) vào tab CSV, bấm nút gửi, kiểm tra không exception VÀ số alert trong DB tăng lên sau khi gửi (không chỉ kiểm tra UI không lỗi, phải xác nhận dữ liệu thật đã vào hệ thống).
- **Kết quả chạy thật [PASS]:** upload 241 dòng Tập B qua tab CSV của Dashboard (không qua script/terminal nào khác) → 0 exception → số alert trong DB tăng từ 271 lên 469 (đúng — không phải mọi dòng đều là tấn công, nhiều dòng Benign không tạo alert).
- **Tab PCAP chưa test chạy thật được** — vẫn thiếu 1 file `.pcap` mẫu như đã ghi ở mục trước bước 13. Code đã viết xong, đường ống đã rõ, chỉ còn thiếu dữ liệu để kiểm chứng — không được coi là "đã xong" cho tới khi chạy thật ra kết quả.
- **Chưa làm (để sau theo yêu cầu của bạn)**: nút "Bắt real-time" ngay trên Dashboard (cần Streamlit chạy với quyền Administrator để Npcap hoạt động, phức tạp hơn do phải quản lý tiến trình nền + tự làm mới trang trong khi đang bắt) — hiện tại bắt real-time vẫn làm qua terminal như hướng dẫn cũ (`scripts/run_live_capture.py --interface ...`).
- Commit: `84e423f`.

### Bước 13 (sửa lỗi) — Tab PCAP crash thật khi bạn tự test + né tcpdump + tự làm mới bảng ✅
- **Vì sao có mục này**: bạn tự test tab "Phát lại PCAP" với file `.pcap` thật của bạn và gặp crash `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'` tại `st.code(proc.stdout + proc.stderr)` — đúng kiểu lỗi phải sửa ngay vì bạn gặp khi tự test, không phải tôi đoán ra. Cũng yêu cầu thêm: gửi/bắt xong phải thấy bảng cảnh báo tự cập nhật ngay (trước đó phải tự bấm lọc/F5).
- **3 lỗi thật, tìm ra theo đúng thứ tự khi lần theo lỗi gốc (không phải sửa mò):**
  1. **Lỗi hiển thị (sửa trước, chưa phải gốc rễ)**: `proc.stdout`/`proc.stderr` có thể là `None` trong 1 số tình huống (timeout, tiến trình chết sớm) — code cũ cộng thẳng 2 chuỗi không phòng hờ `None`. **Sửa**: `(proc_stdout or "") + (proc_stderr or "")`, thêm `except subprocess.TimeoutExpired` báo lỗi rõ ràng thay vì để crash.
  2. **Lỗi gốc rễ thật trong thư viện `cicflowmeter`**: `create_sniffer(input_file=...)` gắn CỨNG bộ lọc BPF `filter="ip and (tcp or udp)"` cho cả chế độ đọc file — với file pcap, scapy áp bộ lọc này bằng cách tự shell ra chạy `tcpdump -w -`, nhưng **Windows không có sẵn `tcpdump`** → luôn lỗi `Scapy_Exception: tcpdump is not available` ngay khi chạy, làm tiến trình con chết sớm, góp phần gây ra tình huống (1) ở trên. **Sửa**: `scripts/run_live_capture.py` không gọi `create_sniffer()` cho chế độ pcap nữa — tự dựng `AsyncSniffer(offline=..., prn=session.process, store=False)` thẳng, BỎ HẲN tham số `filter` (không mất gì vì `FlowSession.process()` bên trong thư viện đã tự bỏ qua gói không phải TCP/UDP, đúng việc bộ lọc kia định làm).
  3. **Lỗi thật thứ 2, tái hiện được y hệt lỗi bạn gặp khi viết test đầy đủ**: sau khi sửa (2), chạy test với file pcap thật thì vẫn gặp `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90` trong 1 thread nền của `subprocess.run()` — vì mặc định nó đọc output bằng encoding hệ thống (cp1252 trên Windows), nhưng log DEBUG của CICFlowMeter có byte không giải mã được bằng cp1252. Thread đó CHẾT ÂM THẦM (in traceback ra console, không ném lên luồng chính) và để `proc.stdout = None` — **đây mới là nguyên nhân sâu xa thật sự** của lỗi (1) bạn gặp ban đầu. **Sửa**: thêm `encoding="utf-8", errors="replace"` vào `subprocess.run()` trong `app/dashboard.py`, khớp với `sys.stdout.reconfigure(encoding="utf-8")` ở các script con.
- **Theo yêu cầu "gửi/bắt xong phải thấy bảng cảnh báo tự cập nhật"**: cả 2 tab (CSV + PCAP) đổi từ `st.info("...bấm lọc/F5...")` sang `st.toast(...) ; st.rerun()` — gửi xong tự chạy lại toàn trang, bảng cảnh báo bên dưới tự lấy dữ liệu mới, không cần bạn tự bấm gì thêm.
- Tạo `scripts/make_synthetic_pcap.py`: dựng 6 gói tin TCP giả (SYN/SYN-ACK/ACK/PSH+data/FIN/FIN) bằng `scapy`, lưu ra `.pcap` — **không cần Npcap/quyền Administrator, không bắt gói thật nào** — dùng để test tab PCAP lặp lại được bất cứ lúc nào, không phải chờ có file pcap thật.
- Mở rộng `scripts/stage13_test_dashboard.py` thêm **Việc 5**: tạo pcap giả lập bằng script trên, dùng `AppTest.file_uploader.upload()` giả lập upload qua đúng tab PCAP của Dashboard, bấm nút, kiểm tra không exception.
- **Kết quả chạy thật — cả 5 việc [PASS], 0 exception**: test Việc 5 **tái hiện lại chính xác lỗi `UnicodeDecodeError`** bạn gặp (xác nhận đây đúng là lỗi thật, không phải ngẫu nhiên riêng máy bạn) trước khi sửa (3); sau khi sửa cả 3 lỗi, chạy lại thì sạch hoàn toàn, trích đúng 1 flow từ pcap giả lập, gửi vào `/predict` thành công.
- **Dọn dữ liệu test tích lũy** (theo yêu cầu "xóa mấy cái đang ở tạm/mẫu để tôi test"): xóa `data/ids_system.db` (tích lũy 1471 alert từ các lần tôi test — không commit vào git, xóa an toàn, khởi động lại server sẽ tự tạo lại 6 bảng rỗng) + dọn hết các file `.csv`/`.log` tạm còn sót lại trong `data/` từ các bước test trước, chỉ giữ lại file thật cần dùng (`clean_holdout_set.csv`, `train_stats.json`, `lime_background.npy`, `samples/`).
- Commit: `201801b`.

### Bước 13 (bổ sung 2) — `GET /flows` (xem cả Benign) + phát hiện thật: model sai lệch vì cờ FIN ✅

**Phần 1 — `GET /flows` (theo yêu cầu "tôi cũng cần các flow bình thường hiện ra màn hình nữa"):**
- **Vì sao cần**: `GET /alerts` (bước 12) chỉ trả Alert — mà Alert CHỈ được tạo khi nhãn dự đoán khác Benign (đúng nguyên tắc kiến trúc). Flow Benign (traffic bình thường, không tấn công) không bao giờ tạo Alert nên không bao giờ xuất hiện trên Dashboard trước đây — bạn test xong không thấy traffic bình thường đâu cả, chỉ thấy toàn cảnh báo.
- Thêm `db.get_flows()`: `LEFT JOIN FlowRecord` với `Prediction`, lọc theo thời gian/nhãn, trả cả flow Benign lẫn flow tạo cảnh báo, kèm cờ `is_alert` tính sẵn. Thêm `GET /flows` vào `app/main.py` — **đây là điểm gọi API thứ 5, NGOÀI 4 điểm gọi gốc trong tài liệu kiến trúc** (`POST /predict`, `POST /explain`, `GET /alerts`, `GET /health`) — ghi rõ trong code là bổ sung theo nhu cầu thực tế khi test, không phải một phần đặc tả gốc.
- Thêm bảng "Tất cả flow đã xử lý (kể cả Benign)" vào `app/dashboard.py`, đặt TRƯỚC bảng cảnh báo (không phải sau) — vì bảng cảnh báo có `st.stop()` khi rỗng, đặt sau sẽ bị chặn không hiện ra lúc DB chưa có cảnh báo nào.
- **Lỗi thật khi viết test cho phần này**: `scripts/stage13_test_dashboard.py` Việc 3 (chọn alert có LIME) dùng `max(select_boxes, key=lambda sb: len(sb.options))` để đoán ô nào là ô "chọn cảnh báo" — hoạt động được bao lâu nay vì DB luôn có hàng trăm alert tích lũy (ô chọn alert luôn có nhiều lựa chọn nhất). Sau khi dọn sạch DB (chỉ còn 3 alert) để test sạch, ô lọc nhánh (3 lựa chọn: tất cả/A/B) bị TRÙNG số lượng với ô chọn alert → chọn nhầm ô → test FAIL dù `dashboard.py` hoàn toàn không có lỗi. **Sửa**: nhận diện theo `label` ("Chọn cảnh báo để xem chi tiết") thay vì đếm số lựa chọn.
- **Kết quả chạy thật — lại 5/5 việc [PASS]** sau khi sửa.

**Phần 2 — Phát hiện thật khi bạn tự test bằng file `.pcap` của chính bạn (traffic duyệt web bình thường):**
- Bạn báo model đoán sai nhiều — 5/33 flow bị đoán nhầm "DoS attacks-Hulk" dù chỉ là traffic duyệt web HTTPS bình thường. Tôi mở lại đúng file CSV CICFlowMeter đã trích ra từ pcap của bạn (`172.20.10.8` nói chuyện HTTPS với nhiều server — rõ ràng là traffic bình thường) để tìm nguyên nhân, không đoán mò.
- **Tìm ra nguyên nhân rõ ràng bằng cách so sánh trực tiếp**: cả 5 flow bị đoán nhầm đều có `fin_flag_cnt ≥ 1` (1 hoặc 2); cả 28 flow còn lại (đoán đúng Benign) **đều có `fin_flag_cnt = 0`**, không ngoại lệ. Tra thêm SHAP của 1 ca: `FIN Flag Cnt` là đặc trưng đóng góp mạnh nhất (phi=+5,87), áp đảo các đặc trưng khác.
- **Đây KHÔNG phải lỗi code** (đã xác nhận CICFlowMeter trích xuất đúng, feeder map cột đúng, API hoạt động đúng) — mà là **một giới hạn thật của chính model** (huấn luyện trên CICIDS2018, 2018): rất có thể trong bộ dữ liệu gốc, các phiên "Benign" (bắt gói nhiều giờ liên tục) hiếm khi được chụp đủ để thấy gói FIN đóng kết nối (bị cắt giữa chừng do hết thời gian bắt), còn traffic tấn công (công cụ tự động, mở/đóng kết nối nhanh) lại hay có FIN rõ ràng — khiến model học nhầm "có FIN = khả nghi" thay vì học đúng bản chất tấn công Hulk. Khi bạn bắt 1 đoạn traffic NGẮN của chính mình, nhiều phiên HTTPS kịp đóng hẳn trong lúc bắt → có FIN → rơi đúng vào điểm mù này.
- **Không sửa model** (ngoài phạm vi RQ3 — RQ3 dùng lại nguyên model đã huấn luyện từ RQ1, không huấn luyện lại) — ghi nhận đây là **bằng chứng thật, giá trị**, đúng loại phát hiện RQ3 được thiết kế để phơi bày (model có thể dựa vào đặc điểm "môi trường bắt gói" thay vì bản chất tấn công — cùng tinh thần với cờ môi trường ở bước 8, dù `FIN Flag Cnt` không nằm trong 3 đặc trưng cờ môi trường đã định nghĩa sẵn). Nên đưa vào báo cáo cuối như 1 ví dụ thật, cụ thể, có số liệu, về giới hạn tổng quát hoá của model khi gặp traffic thật ngoài phòng lab — việc kiểm chứng bài bản giả thuyết này (không chỉ riêng FIN flag) vẫn để dành cho **E2/E4** ở M5.
- Dọn sạch `data/ids_system.db` (đã tích lũy >1400 alert do tôi gửi lại nhiều lần cùng 33 flow để chẩn đoán) bằng `DELETE` qua SQL (không xóa file, vì server bạn có thể đang chạy — an toàn hơn nhờ chế độ WAL), giữ nguyên schema — Dashboard giờ về trạng thái sạch, sẵn sàng để bạn test lại từ đầu.
- Commit: `62c1a6f`.
