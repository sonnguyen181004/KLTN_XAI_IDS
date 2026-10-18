# KLTN_XAI_IDS

**HT3 — 18/10/2026:** đã sửa ACK/checkpoint, báo lỗi capture nền, thêm cap v3 (4096 flow mở / 20000 packet đang giữ / 32 MiB byte packet), bảo vệ dung lượng ổ CSV và tránh bỏ đói SHAP recovery. Quá tải dừng có lỗi, không âm thầm bỏ packet hoặc báo phiên đầy đủ. Cap không phải tổng traffic cả phiên hoặc RSS Python. [Vận hành](RQ3_IDS_System/docs/operations.md) ghi lệnh test và giới hạn còn lại: chưa chứng nhận Wi-Fi dài hạn, chưa tự retention/backup. Restart API và bắt lượt CSV mới để áp dụng, không reset DB.

Khóa luận tốt nghiệp: **nghiên cứu và ứng dụng Explainable AI (XAI) cho hệ thống phát hiện xâm nhập (IDS)** trên bộ dữ liệu CSE-CIC-IDS2018. Mô hình phát hiện là XGBoost (so sánh với Random Forest ở RQ1); phần giải thích dùng **SHAP** và **LIME**.

- Dữ liệu: CSE-CIC-IDS2018 đã xử lý, 78 đặc trưng, 15 lớp (1 Benign + 14 loại tấn công), test set 700.000 flow.
- Trạng thái: **RQ1 xong · RQ2 chạy lại từ đầu (2026-10-09) theo pipeline 14 giai đoạn, đủ kết quả cho cả 5 câu hỏi (agreement, quality gate, stability/robustness, faithfulness, domain validation) + cohort lỗi · RQ3 đang xây dựng, Bước 1–13/16 xong (API + SHAP/LIME + Dashboard chạy được, test thật bằng traffic thật qua Wireshark/CICFlowMeter), còn Docker Compose + 2 thí nghiệm E1/E5 + mốc traffic tấn công thật (M4/M5).**

---

## 1. Cấu trúc dự án

**RQ3 — chỉ cần 5 tài liệu chính** (đã gộp 11 file cũ, giữ bằng chứng JSON):

| Bạn muốn xem | Tài liệu |
|---|---|
| Chạy hệ thống, live/CSV/PCAP và hiểu SHAP/LIME | [Hướng dẫn sử dụng](RQ3_IDS_System/docs/dashboard_usage.md) |
| Kiến trúc, đã làm gì và tiếp theo làm gì, gồm hoàn thiện UI | [Kiến trúc và kế hoạch](RQ3_IDS_System/docs/plan.md) |
| Capture v3, checkpoint, queue 200, phục hồi và kết quả test | [Vận hành](RQ3_IDS_System/docs/operations.md) |
| Vì sao LIME chưa giải thích được, kết quả đối chiếu PCAP | [Kiểm chứng XAI](RQ3_IDS_System/docs/xai_validation.md) |
| Ma trận 78 đặc trưng, khác biệt train/capture và giới hạn | [Tương thích đặc trưng](RQ3_IDS_System/docs/feature_compatibility.md) |

UI có Giám sát flow, Hướng dẫn live và Nạp CSV / PCAP; chưa có nút điều khiển capture. Giữ nguyên XGBoost, LIME RQ2, nhánh A/B; chưa chứng nhận đầu vào train/PCAP hoàn toàn tương thích hoặc FPR live.

**HT2 — 18/10/2026:** mặc định CLI/PCAP dùng `rq3-cfm-0.5.0-lifecycle-v3`: biên timeout nhất quán, nhận biết dấu hiệu đóng/mở TCP, tách rõ packet lệch timestamp. Không đổi model hoặc ép cờ nhị phân. Hai PCAP bảo toàn 1.148 packet; 99 flow thay cho 92 do phân phiên mới, không phải bằng chứng giảm FPR. Tra mục đích, kiểm thử và giới hạn ở [tương thích đặc trưng](RQ3_IDS_System/docs/feature_compatibility.md); lịch sử/commit ở [tiến độ HT2](RQ3_IDS_System/docs/plan.md). Chọn `--extractor project-v2` nếu cần đối chiếu baseline; không trộn hai bản trong cùng CSV.

```text
SELF_KLTN/
├── dataset/                         # Dữ liệu CICIDS2018 đã xử lý (parquet bị .gitignore)
├── RQ1_Model_Training_xboost/       # Tuning, huấn luyện, model .pkl, kết quả RQ1
├── RQ1_docx/                        # Báo cáo RQ1 (+ Tai_lieu_ho_tro: cẩm nang tham số XGBoost/RF)
├── RQ2/                              # Chạy lại từ đầu 2026-10-09 — xem mục 4
│   ├── docs/plan.md                  # Kế hoạch 14 giai đoạn (GĐ0–GĐ13)
│   ├── config.yaml                   # Mọi tham số (seed, path, cấu hình LIME đã khóa...)
│   ├── scripts/                      # stage00_*.py … stage13_*.py + build_report_*.py
│   └── runs/<ngày>/                  # Kết quả mỗi lần chạy (CSV/JSON/PNG/docx), không ghi đè
├── v1_archive/RQ2_old_20260929/      # Toàn bộ kết quả RQ2 lần chạy trước (lưu trữ)
├── xai-ids-study-hub/                # Trang demo tương tác, số liệu kéo từ RQ2/runs mới nhất
├── WorkFlow/                        # Sơ đồ workflow tổng quan (workflow_v3.mmd / .png)
├── RQ3_IDS_System/                  # RQ3: hệ thống IDS realtime có giải thích — xem mục 5
│   ├── docs/plan.md                  # Kế hoạch + tiến độ chi tiết từng bước (1→16)
│   ├── config.yaml                   # Mọi tham số (seed, path, LIME khóa theo RQ2, ngưỡng cờ...)
│   ├── app/                          # main.py (API), dashboard.py (Streamlit), db.py, predict.py, explain_shap.py, explain_lime.py, reliability.py, feeder.py
│   ├── scripts/                      # stage0N_*.py (test từng bước) + run_live_capture.py + make_synthetic_pcap.py
│   └── data/                         # DB SQLite + dữ liệu chạy (không commit — xem .gitignore)
├── cicflowmeter_capture_demo/       # (CŨ, không dùng nữa — RQ3 xây lại từ đầu ở RQ3_IDS_System/)
├── Tai_lieu_tham_khao/              # Nhãn CICIDS2018, bài báo, hỏi–đáp bảo vệ
├── Report/                          # Proposal và hướng dẫn khóa luận
├── Kiem_thu_noi_bo/                 # PDF/PNG kiểm thử khi dựng tài liệu (không phải kết quả nghiên cứu)
├── pptskill/                        # Công cụ tạo slide, tách biệt khỏi mã nghiên cứu
├── Tong_hop_XAI_IDS_5_tai_lieu.docx # Tổng hợp 5 tài liệu XAI cho IDS
└── README.md
```

## 2. Các câu hỏi nghiên cứu (theo proposal)

| RQ | Nội dung | Thư mục |
|---|---|---|
| RQ1 | 1.1 F1/Precision của RF vs XGBoost sau tuning; 1.2 tỉ lệ báo động giả trên Benign | `RQ1_*` |
| RQ2 | 2.1 độ tương đồng Top-k SHAP vs LIME (agreement); 2.2 tính ổn định và chịu nhiễu (stability/robustness); 2.3 độ trung thực (faithfulness); 2.4 kiểm chứng theo tri thức miền (domain validation) | `RQ2/` |
| RQ3 | 3.1 độ trễ SHAP vs LIME; 3.2 biểu đồ/UI cho SOC, dashboard, Docker | `RQ3_IDS_System/` |

> Đánh số tiểu mục RQ2 dùng thống nhất theo [`RQ2/docs/plan.md`](RQ2/docs/plan.md) (2.1 agreement, 2.2 stability/robustness, 2.3 faithfulness, 2.4 domain validation) — khác thứ tự trình bày trong mục 4 dưới đây, vốn đi theo mạch kể chuyện (domain validation và faithfulness có thể đổi chỗ khi trình bày). Cần hỏi thầy hướng dẫn trước khi đổi số trong tài liệu chính thức.

---

## 3. RQ1 — Hiệu năng phát hiện (đã xong)

- **Mô hình chọn:** XGBoost, 100 cây, `max_depth=8`, `learning_rate=0.08`, `tree_method=hist`, `multi:softprob`, 15 lớp.
- **Kết quả trên test set:** Accuracy 97,91% · Macro Precision 90,84% · Macro Recall 83,99% · **Macro F1 85,81%** · thời gian huấn luyện ≈ 2,67 phút.
- **Tuning:** 7 cấu hình; cấu hình depth 12 / lr 0,08 đạt F1 85,95% nhưng bản depth 8 được giữ làm mô hình giải thích.
- **Hạn chế cần nói rõ:** test set được dùng để chọn cấu hình (không có validation riêng) nên số liệu hơi lạc quan.
- **Đính chính FPR (16/10/2026):** code và bảng kết quả đã tách FPR = 1.139 / 490.000 ≈ **0,2324%** (Benign bị báo thành Attack) với FNR = 12.071 / 210.000 ≈ **5,7481%** (Attack bị bỏ sót thành Benign). Bảng tuning cũ được đổi tên cột sai thành FNR, không suy đoán FPR của từng cấu hình. Xem [định nghĩa và giới hạn](RQ1_Model_Training_xboost/FPR_CORRECTION.md). Đây là số liệu test dataset, không phải FPR traffic live.

Chạy lại:

```powershell
python .\RQ1_Model_Training_xboost\1_hyperparameter_tuning.py
python .\RQ1_Model_Training_xboost\2_train_optimal_model.py
```

---

## 4. RQ2 — Khả năng giải thích SHAP vs LIME (trọng tâm)

> **Chạy lại từ đầu ngày 2026-10-09** theo kế hoạch 14 giai đoạn (GĐ0→GĐ13) trong [`RQ2/docs/plan.md`](RQ2/docs/plan.md). Nhật ký cũ ghi bản lưu ở `v1_archive/RQ2_old_20260929/`; đường dẫn này hiện không có trong checkout, cần xác minh nơi lưu nếu muốn đối chiếu bản cũ. Pipeline mới nằm ở `RQ2/scripts/` (14 script `stage00_*.py` → `stage13_*.py` + 4 script `build_report_*.py`), mỗi lần chạy ghi vào `RQ2/runs/<ngày>/` (không ghi đè, có `config.yaml` chốt tham số, log, checksum).

### 4.1 Ý tưởng thiết kế

Để so sánh SHAP và LIME công bằng, cả hai giải thích **cùng một mô hình, cùng 78 đặc trưng, cùng từng flow**:

- **Cohort đánh giá:** 1.339 flow mà mô hình dự đoán **đúng**, tối đa 100 flow/lớp (lớp hiếm giữ hết: Brute Force -XSS 44, Brute Force -Web 86, SQL Injection 9), phân tầng, seed 42.
- **Tập dev** (250 flow, tách riêng khỏi cohort) dùng để **chốt cấu hình LIME TRƯỚC khi** chạy chính thức (GĐ5) — tránh việc chỉnh tham số theo kết quả mong muốn.
- **Giải thích đúng lớp đã dự đoán** (`predicted_label`), không phải `true_label`.
- **Cohort lỗi** (151 flow dự đoán sai, lấy tối đa 20/lớp) giữ riêng làm case study (GĐ12), không trộn vào trung bình chính.
- **Không chọn cấu hình LIME theo mức "giống SHAP"** — cổng kiểm soát duy nhất là Local R² và chi phí thời gian.
- Mọi số liệu tổng hợp đi kèm **khoảng tin cậy bootstrap**; so SHAP–LIME bằng kiểm định **Wilcoxon** bắt cặp.

### 4.2 Cấu hình (chốt ở GĐ5, dò trên tập dev)

| | SHAP | LIME |
|---|---|---|
| Thư viện | `shap.TreeExplainer` | `LimeTabularExplainer` (Ridge surrogate) |
| Thiết lập | margin thô (raw), kiểm tra additivity | `kernel_width ≈ 3,312` (0,5× mặc định 6,624), `num_samples = 1000`, `discretize_continuous = False`, nền 2.000 dòng mẫu từ train set |
| Đầu ra giải thích | margin thô của lớp dự đoán | xác suất lớp dự đoán |
| Sai số/chất lượng | additivity 5,72e-6 (mẫu 300/700k flow), 1,34e-5 (cohort) | Local R² (`explanation.score`) |

> So với cấu hình cũ (kernel_width=6,624 tuyệt đối, `discretize_continuous=True`, `num_samples=5000`, nền 8.002 flow): tắt discretize và giảm kernel_width là hai thay đổi cải thiện Local R² nhiều nhất (xem 4.4).

### 4.3 Các bước thực hiện và kết quả (run `RQ2/runs/20261009/`)

**(a) GĐ0–1 — Chuẩn bị & kiểm tra.** Chạy lại model trên test set: Accuracy 97,9076% / Macro F1 85,8058% — khớp RQ1 (lệch <0,01 điểm %). Checksum model/encoder/train/test, schema 78 đặc trưng, 15 lớp — đều đạt.

**(b) GĐ2 — SHAP toàn cục** trên toàn 700.000 flow, cả 15 lớp (bao gồm Benign — khác bản cũ không có Benign). `gd2_shap_global/` (Top-5/lớp, biểu đồ, additivity report).

**(c) GĐ3 — Cohort, tập dev, cohort lỗi** (1.339 / 250 / 151 flow, không giao nhau — kiểm tra bằng code).

**(d) GĐ4, GĐ6 — SHAP và LIME per-flow trên cohort.** `gd4_shap_per_flow/`, `gd6_lime_per_flow/`.

**(e) GĐ5 — Chốt cấu hình LIME trên tập dev** (lưới 18 tổ hợp × 150 flow, sau đó xác nhận trên toàn 250 flow dev). Xem 4.2.

**(f) Sub-RQ 2.1 — Agreement** (GĐ7, bootstrap CI, trên cohort 1.339 flow):

| k | Jaccard@k | Spearman (toàn bộ 78 đặc trưng) | Đồng thuận dấu |
|---|---|---|---|
| 3 | 0,163 | 0,284 | 0,948 |
| 5 | 0,141 | 0,284 | 0,840 |
| 10 | 0,162 | 0,284 | 0,710 |

→ Jaccard thấp nhưng cao hơn ngẫu nhiên 2,3–6,8 lần (xem `rq2_1_random_baseline.csv`). Spearman tính trên **toàn bộ 78 đặc trưng** (không chỉ Top-k) vì phiên bản tính trên tập con Top-k có một **sai lệch thống kê (selection bias)** khiến nó lệch âm giả dù hai phương pháp không hề nghịch nhau — phát hiện và sửa trong lúc chạy lại, xem `RQ2/scripts/stage07_agreement.py` và `full_rank_correlation()` trong `lib/agreement_metrics.py`. Số đúng cho thấy **không có lớp nào** có Spearman âm (khác bản cũ từng báo DDoS-LOIC-HTTP = −0,65, vốn bị ảnh hưởng bởi lỗi này).

**(g) GĐ8 — Quality gate LIME:** 85,96% flow cohort đạt R² ≥ 0,3 (so với 12,3% ở bản cũ). Đồng thuận SHAP–LIME **không tăng đều** theo mức R² — bất đồng không được giải thích đầy đủ chỉ bằng chất lượng surrogate của LIME.

**(h) Sub-RQ 2.2 — Stability & Robustness** (GĐ9, **cho cả SHAP và LIME** — bản cũ chỉ có LIME):

- Ổn định qua 10 seed: LIME Jaccard@5 trung bình giữa các lần ≈ **0,581**; SHAP xác định tuyệt đối (100% khớp khi chạy lại).
- Chịu nhiễu Gaussian trên **cả 78 đặc trưng** (biên độ = % độ lệch chuẩn toàn cục), σ=1/5/10%: Jaccard@5 SHAP 0,51→0,48→0,46; LIME 0,35→0,25→0,18 (SHAP ổn định hơn ở mọi mức). Tỉ lệ model đổi nhãn dự đoán 76,3%/80,2%/81,0% — cao vì một số đặc trưng (Flow Duration, IAT...) lệch dày (heavy-tailed), "nhiễu 1%" theo độ lệch chuẩn toàn cục có thể là bước nhảy tuyệt đối rất lớn so với một flow thường — hạn chế của cách định nghĩa mức nhiễu, không phải lỗi tính toán.

**(i) Sub-RQ 2.4 — Faithfulness** (GĐ10, đổi protocol: xoá Top-k → giá trị NỀN thay vì donor-swap, đo giảm XÁC SUẤT thay vì margin, 3 giá trị nền, coverage 100%):

| k | SHAP thắng LIME | Giảm % trung bình: SHAP / Random / LIME |
|---|---|---|
| 3 | 64,5% | 77,5 / 6,9 / 40,3 |
| 5 | 78,3% | 82,5 / 10,6 / 45,6 |
| 10 | 86,4% | 85,9 / 19,1 / 57,0 |

→ Cả hai vượt xa đối chứng ngẫu nhiên; SHAP thắng LIME ở mọi k, p<0,001 (Wilcoxon) ở cả 3 giá trị nền.

**(j) Sub-RQ 2.3/2.4 — Domain validation** (GĐ11, bảng tri thức 2 bản chặt/rộng, lập TRƯỚC khi xem Top-5):

| | SHAP | LIME |
|---|---|---|
| F1 domain (bản chặt) | **0,190** | 0,095 |
| F1 domain (bản rộng) | **0,201** | 0,107 |

→ SHAP bám tri thức miền tốt hơn LIME ở cả hai bản. Tỷ lệ đặc trưng "dấu vân tay môi trường" (`Fwd Seg Size Min`, `Dst Port`, `Init Fwd Win Byts`) trong Top-5: SHAP ≈29%, LIME ≈17%.

**(k) GĐ12 — Cohort lỗi (151 flow, thăm dò):** mức tập trung SHAP Top-5 và Jaccard@5 SHAP-LIME không khác rõ giữa flow đúng/sai trong mẫu nhỏ này — chưa đủ bằng chứng cho ý tưởng "bất đồng làm tín hiệu lỗi" (để RQ3 thử lại với mẫu lớn hơn).

### 4.4 Vì sao Local R² của LIME thấp?

Local R² cho biết mô hình tuyến tính đơn giản của LIME "bắt chước" XGBoost quanh flow đang giải thích tốt đến đâu.

- **Trên tập dev** (250 flow dùng để CHỌN cấu hình): trung vị 0,258, 38,4% flow đạt R² ≥ 0,3.
- **Trên cohort đánh giá** (1.339 flow, dùng cấu hình đã chốt): trung vị **0,58**, **85,96%** flow đạt ngưỡng — cải thiện rõ so với bản cũ (trung vị ≈0,068, 12,3%).

Nguyên nhân R² còn chưa đạt lý tưởng trên tập dev: (1) XGBoost cho đầu ra dạng bậc thang, đường thẳng khó khớp; (2) không gian 78 chiều làm "vùng lân cận" rất thưa. Hai thay đổi giúp cải thiện nhiều nhất: **tắt** `discretize_continuous` và **giảm** `kernel_width` xuống 0,5× mặc định — ngược với giả định ban đầu rằng tăng `num_samples` sẽ giúp (GĐ9 cho thấy R² **giảm** khi `num_samples` tăng, xem `rq2_2_lime_convergence.csv`).

### 4.5 Phát hiện về đặc trưng

- Đặc trưng "dấu vân tay môi trường" xuất hiện đáng kể trong Top-5 (SHAP ≈29%, LIME ≈17%) → mô hình có nguy cơ học đặc điểm của bộ dữ liệu thay vì hành vi tấn công. Đây là cầu nối sang RQ3.
- Lớp Bot: SHAP gần như hoàn toàn dựa vào `Dst Port` (mean|φ|≈7,4, gấp ~90 lần đặc trưng thứ 2) — cần kiểm tra tính tổng quát trên mạng khác.

### 4.6 Khoảng trống còn lại của RQ2

- Nhiễu ở GĐ9 dùng % độ lệch chuẩn **toàn cục** (không theo từng flow) — nên đổi sang % theo giá trị từng flow ở lần chạy sau (xem 4.3h).
- Bảng tri thức miền (GĐ11) do nhóm tự tổng hợp từ tài liệu gốc CSE-CIC-IDS2018 — không phải benchmark chính thức.
- LIME Top-5-theo-lớp (GĐ11) tính trên cohort (≤100 flow/lớp), SHAP tính trên toàn 700k test set — khác quy mô dữ liệu giữa hai cột so sánh.
- Cohort lỗi (151 flow) quá nhỏ để khẳng định xu hướng ở GĐ12.
- Background của LIME (2.000 dòng, seed 42) là lựa chọn cố định, không đưa vào lưới tìm kiếm GĐ5.

### 4.7 Chạy lại RQ2 (thứ tự)

Từ thư mục gốc dự án:

```powershell
cd RQ2\scripts
python stage00_prepare_run.py
python stage01_verify_env.py        # DỪNG ở đây nếu không đạt
python stage02_shap_global.py
python stage03_cohorts.py
python stage04_shap_per_flow.py
python stage05_lock_lime_config.py  # ghi lime.locked_config vào ..\config.yaml
python stage06_lime_per_flow.py
python stage07_agreement.py
python stage08_quality_gate.py
python stage09_stability_robustness.py
python stage10_faithfulness.py
python stage11_domain_validation.py
python stage12_error_cohort.py
python stage13_build_report_data.py
python build_report_theory.py
python build_report_shap.py
python build_report_lime.py
python build_report_process.py
python build_report_final.py
```

Mỗi stage ghi vào `RQ2/runs/<ngày>/gdN_.../` cùng log (`RQ2/runs/<ngày>/logs/`). Tham số tập trung trong `RQ2/config.yaml` (seed 42) — không script nào ghi cứng tham số. Môi trường đã dùng: Python 3.14.7, shap 0.52.0, lime 0.2.0.1, xgboost 3.4.1, scikit-learn 1.9.1.

### 4.8 Tài liệu RQ2

| File | Nội dung |
|---|---|
| `RQ2/docs/plan.md` | Kế hoạch 14 giai đoạn đầy đủ (nguồn cho mục 4 này) |
| `RQ2/runs/<ngày>/gd13_report/docx/RQ2_Bao_cao_Tong_hop_Final.docx` | Báo cáo tổng hợp chính thức, theo mạch 5 câu hỏi, mọi hình có phân tích |
| `RQ2/runs/<ngày>/gd13_report/docx/RQ2_Bao_cao_SHAP_chi_tiet.docx` | Trọng số SHAP đầy đủ theo từng lớp |
| `RQ2/runs/<ngày>/gd13_report/docx/RQ2_Bao_cao_LIME_chi_tiet.docx` | Trọng số LIME đầy đủ theo từng lớp |
| `RQ2/runs/<ngày>/gd13_report/docx/RQ2_Kien_thuc_chung_Ly_thuyet.docx` | Lý thuyết SHAP/LIME + định nghĩa mọi chỉ số, dễ hiểu |
| `RQ2/runs/<ngày>/gd13_report/docx/RQ2_Quy_trinh_Thuc_Hien_Chi_Tiet.docx` | Từng giai đoạn GĐ0–GĐ13 đã làm gì, làm thế nào |
| `v1_archive/RQ2_old_20260929/` | Toàn bộ kết quả lần chạy trước (lưu trữ, không chạy tiếp) |
| `xai-ids-study-hub/` | Trang demo tương tác, số liệu kéo từ run RQ2 mới nhất (xem mục 4.9) |

### 4.9 Trang demo tương tác (`xai-ids-study-hub/`)

Một trang tĩnh (`xai-ids-study-hub/dist/index.html`) trình bày lại toàn bộ RQ1–RQ2 dưới dạng demo tương tác (waterfall SHAP, vùng lân cận LIME, so sánh SHAP/LIME trên flow thật, Attack Atlas 14 kịch bản, flashcard/quiz ôn thi). Số liệu "Real Project Data" lấy trực tiếp từ `RQ2/runs/<ngày mới nhất>/` qua script:

```powershell
python xai-ids-study-hub\tools\build_data.py   # ghi lại dist/data.js
```

Chạy lại script này sau mỗi lần chạy RQ2 mới để đồng bộ số liệu. Mở `xai-ids-study-hub/dist/index.html` trực tiếp bằng trình duyệt (không cần server).

---

## 5. RQ3 — Hệ thống IDS realtime có giải thích (`RQ3_IDS_System/`)

Xây **từ đầu**, không dùng lại `cicflowmeter_capture_demo/` cũ. Kiến trúc gốc: `Kiến trúc hệ thống IDS.docx` (6 tầng: Bắt gói → Chuẩn hóa → Dự đoán XGBoost → Giải thích SHAP/LIME + độ tin cậy → Nhánh hiển thị A/B → API + Dashboard). Kế hoạch + tiến độ chi tiết từng bước nằm ở [`RQ3_IDS_System/docs/plan.md`](RQ3_IDS_System/docs/plan.md) — **đây là nguồn chi tiết nhất**, README chỉ tóm tắt.

**Trạng thái: Bước 1–13/16 xong**, đã test thật bằng model+dữ liệu thật (không phải giả lập), kể cả traffic thật bắt từ máy thật qua Wireshark/CICFlowMeter.

### 5.1 Đã làm xong

| Bước | Nội dung |
|---|---|
| 1–6 | Config, SQLite (6 bảng), tập dữ liệu sạch (loại trùng train/test), chuẩn hóa flow, nạp lại model RQ1, `POST /predict` |
| 7, 7b | TreeSHAP tự động cho cảnh báo, chạy **bất đồng bộ** qua hàng đợi (tối đa 200 tác vụ chờ; đầy thì giữ cảnh báo và ghi rõ SHAP bị bỏ) |
| 8 | Độ tin cậy tính tại chỗ: faithfulness proxy, cờ môi trường, cờ lớp hiếm |
| 8b, M3 | Bộ feeder tự động (CSV→API) + **test bằng traffic Wi-Fi thật**; phiên lịch sử trả 25/25 nhãn Benign, chưa có ground truth độc lập để gọi là đoán đúng |
| 9 | LIME theo yêu cầu (`POST /explain`), đúng cấu hình đã khóa ở RQ2 |
| 11 | Luật nhánh hiển thị A/B (chỉ dựa 2 cờ ở bước 8, không dùng tập dev RQ2) |
| 12 | `GET /alerts`, `GET /flows` (xem cả flow Benign, không chỉ cảnh báo) |
| 13 | **Dashboard Streamlit** — bảng cảnh báo, biểu đồ SHAP/LIME có dấu, bảng độ tin cậy, **nạp dữ liệu trực tiếp trên Dashboard** (upload CSV hoặc `.pcap`, không cần dòng lệnh) |

**Còn thiếu:** Bước 10 (tra bảng ổn định/chịu nhiễu từ RQ2 — tạm bỏ qua, không bắt buộc), Bước 14 (Docker Compose), Bước 15–16 (đo độ trễ E1, đối chiếu nhất quán E5), M4–M5 (dựng máy ảo Attacker/Victim để test traffic tấn công thật).

**Đính chính và sửa extractor 16/10/2026:** audit đã tái hiện 5 lỗi Python CICFlowMeter 0.5.0; [adapter có phiên bản v1](RQ3_IDS_System/docs/feature_compatibility.md#adapter-v1) đã sửa đếm lặp gói đầu, CWR, IAT một khoảng, Active/Idle và khóa flow thiếu protocol. CLI/PCAP UI mặc định dùng bản mới; metadata phiên bản đi vào DB/UI. Còn khác biệt length/header và miền cờ/bulk so với train; hai PCAP trích lại vẫn có 8 dự đoán Hulk và LIME chưa đạt. Chưa thể quy hết cho model hoặc tuyên bố đầu vào đã tương thích V3. Xem [audit trước sửa](RQ3_IDS_System/docs/feature_compatibility.md#baseline-audit), [ma trận 78 cột trước sửa](RQ3_IDS_System/docs/feature_compatibility.md#matrix-78).

**Đối chiếu ngữ nghĩa tiếp theo:** [kiểm tra toàn bộ 3,5 triệu dòng train/test](RQ3_IDS_System/docs/feature_compatibility.md#semantics) đã phân biệt được sample SD độ dài, floor Down/Up, window thiếu=-1 và quan hệ hai mean n/n+1. Capture v1 chưa theo các quy ước này; subflow packet lại khớp tổng trên dữ liệu đủ điều kiện. Chưa đổi model/LIME hay ép cờ/bulk; cần nguồn preprocessing/cặp PCAP–CSV gốc trước khi chứng nhận tương thích.

### 5.2 Chạy trong VS Code

**Tự chạy bằng terminal, không có dịch vụ được hướng dẫn này tự mở sẵn.** Nút bật/dừng capture trên UI được hoãn; tab Hướng dẫn live hiện chỉ đưa các bước terminal. Dùng [hướng dẫn chi tiết CSV/PCAP/live](RQ3_IDS_System/docs/dashboard_usage.md) làm nguồn thao tác chính.

Mở folder `C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System` trong VS Code. Nếu đang dùng venv cũ của `cicflowmeter_capture_demo`, deactivate venv đó trước; dùng Python API đã cài `requirements.txt`, capture dùng `.venv_capture` riêng. Không cần cài lại cho mỗi lần test.

**Terminal 1 — API:**

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Đợi `Application startup complete`. Một API process cho mỗi DB, không mở chồng lên cổng đang dùng.

**Terminal 2 — UI:**

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
python -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501
```

Mở http://127.0.0.1:8501. API docs ở http://127.0.0.1:8000/docs. Giữ hai terminal chạy.

Chỉ khi khởi tạo môi trường mới và **thiếu** các file nền (cần model/dataset theo config), mới chạy:
```powershell
python scripts\stage08_compute_train_stats.py
python scripts\stage09_compute_lime_background.py
```
Không chạy lại các bước này hoặc train lại chỉ để mở UI; giữ nền RQ2 hiện hành.

### 5.3 Test CSV và PCAP — chỉ cần API/UI

| Nguồn | Thao tác đúng tên UI hiện tại | Đơn vị / lưu ý |
|---|---|---|
| CSV | **Nạp CSV / PCAP → CSV đặc trưng → Chọn CSV → Gửi CSV vào /predict** | `data\clean_holdout_set.csv`: không tích đổi đơn vị. CSV do Python extractor của dự án xuất theo giây: tích đổi giây→micro giây; CSV khác phải xác minh |
| PCAP/PCAPNG | **Nạp CSV / PCAP → PCAP đã ghi → Chọn PCAP → Trích xuất và gửi** | Tự trích/đổi đơn vị; đọc offline, không phát gói ra mạng; timeout trích xuất trên UI 120 giây |

Sau khi gửi, mở **Giám sát flow**, chọn đúng lượt và nguồn `csv_upload`/`pcap_replay`; bỏ **Chỉ cảnh báo** để thấy cả Benign. Bấm flow xem IP nếu có, thời gian, xác suất, SHAP và LIME theo yêu cầu. JSON mẫu không phải file upload CSV.

Xem từng bước, timestamp, file mẫu và xử lý PCAP lớn: [CSV](RQ3_IDS_System/docs/dashboard_usage.md#test-csv), [PCAP](RQ3_IDS_System/docs/dashboard_usage.md#test-pcap). Mỗi lần bấm gửi tạo lượt mới, refresh không tự gửi lại. Không cần reset DB để tách phiên.

### 5.4 Realtime liên tục — thêm capture và feeder

**Terminal 3 — capture:**

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
.\.venv_capture\Scripts\python.exe scripts\run_live_capture.py --interface "Wi-Fi" --output data\live_review_01.csv
```

**Terminal 4 — feeder:**

```powershell
cd C:\Users\LOQ\Downloads\SELF_KLTN\RQ3_IDS_System
python app\feeder.py --watch data\live_review_01.csv --convert-units --capture-timezone +07:00
```

Không có `--seconds`: chạy liên tục tới khi chủ động dừng, **không bắt buộc 60 giây**. Xem đúng card qua `Get-NetAdapter`; chỉ bắt mạng được phép, Npcap/quyền bắt phải sẵn sàng. Đổi tên CSV ở cả hai lệnh cho mỗi phiên mới; không ghi đè file đang theo dõi.

Lướt web trên máy capture; chọn lượt `live_review_01.csv` và nguồn `feeder_live` trên UI. V3 xuất theo tuổi tối đa 90s từ packet đầu, quan sát đóng TCP/mở phiên mới hoặc flush lúc dừng; packet trễ được xuất riêng. Đây không phải dự đoán từng packet. Lượt chỉ xuất hiện sau khi API nhận flow. Quy tắc v2 cũ chỉ áp dụng khi chọn rõ `--extractor project-v2`.

**Dừng:** Ctrl+C capture → đợi ghi nốt và “Đã dừng” → giữ feeder tới khi gửi hết → Ctrl+C feeder. Giữ API/UI để xem kết quả, hoặc dừng sau đó. Bản sửa Ctrl+C `b24f93c` chỉ áp dụng cho tiến trình mới. Xem [hướng dẫn live và chẩn đoán](RQ3_IDS_System/docs/dashboard_usage.md#test-live), [tiếp tục từ checkpoint](RQ3_IDS_System/docs/dashboard_usage.md#resume).

### 5.5 Kiểm thử và giới hạn hiện hành

Các bộ dưới đây dùng file/DB tạm, không cần tự bật API phục vụ test; đây là lệnh **tùy chọn cho kiểm thử kỹ thuật**, không phải bước bắt buộc khi demo:

```powershell
# Chạy từ RQ3_IDS_System
python scripts\stage14_test_dashboard_redesign.py
.\.venv_capture\Scripts\python.exe scripts\stage20_test_capture_adapter.py
python scripts\stage24_test_ingestion_recovery.py
```

Bằng chứng trước đợt cập nhật hướng dẫn: Stage14 API/UI/CSV/PCAP PASS; Stage20 sau sửa Ctrl+C PASS 15 test; Stage24 phục hồi/idempotency PASS. Xem [vận hành và commit](RQ3_IDS_System/docs/operations.md). Đợt sửa tài liệu không tự bật server/capture, không reset DB hay chạy lại thí nghiệm.

Giữ XGBoost RQ1/78 feature, LIME khóa RQ2, A/B chỉ trình bày. LIME có thể không đủ lân cận; nhãn Hulk không chứng minh tấn công. Chưa chứng nhận đầy đủ tương thích train–PCAP và chưa có FPR live từ traffic không có ground truth.

---

## 6. Góp ý của thầy hướng dẫn và hướng xử lý

| Góp ý | Hướng xử lý |
|---|---|
| Mô hình thiết kế: logic và vật lý, xong mới ra workflow | Vẽ sơ đồ logic và vật lý cho RQ3 trước, rồi cập nhật workflow |
| Xem lại hướng phát triển, không trùng; đổi tên đề tài khác tiểu luận ĐH Sài Gòn | Đổi tên đề tài; thêm mục Công trình liên quan (bảng dưới) |
| Làm rõ lý thuyết; vì sao đánh giá theo các yếu tố đó trên IDS | Viết chương cơ sở lý thuyết (IDS, XGBoost, SHAP/LIME, các chỉ số) và lý do chọn 4 tiêu chí |
| Vì sao phân bổ được và tính từ đâu; hệ thống âm/dương, trọng số nào quyết định | Giá trị Shapley (Shapley 1953; Lundberg & Lee 2017; TreeSHAP), ý nghĩa dấu dương/âm; trích bài báo gốc (cần kiểm tra thông tin xuất bản) |

Báo cáo tiếp thu ý kiến gửi thầy: tài liệu "Báo cáo tiếp thu ý kiến của thầy và hướng thực hiện tiếp theo" (Claude Docs).

### Điểm khác biệt so với tiểu luận XAI cho IDS của ĐH Sài Gòn

| | ĐH Sài Gòn (đề cương) | Dự án này |
|---|---|---|
| Dữ liệu | NSL-KDD | CSE-CIC-IDS2018, 78 đặc trưng, 15 lớp |
| Mô hình | RF, SVM, KNN, MLP | XGBoost tinh chỉnh, so với RF |
| XAI | SHAP | SHAP và LIME ghép cặp trên cùng từng flow |
| Đánh giá XAI | Fidelity, stability | Tương đồng, tri thức miền, ổn định và chịu nhiễu, trung thực ghép cặp |
| Triển khai | GUI học tập | Pipeline thời gian thực, đo độ trễ, Docker (kế hoạch) |

(Thông tin về tiểu luận lấy từ bản tóm tắt trang Studocu, cần đối chiếu toàn văn trước khi trích.)

## 7. Lưu ý

- Không di chuyển riêng thư mục `.venv` trong `cicflowmeter_capture_demo/` (môi trường ảo phụ thuộc đường dẫn).
- Tệp bắt đầu bằng `~$` là khóa tạm của Word, tự biến mất khi đóng tài liệu.
- Số liệu trong README lấy từ các file `summary_*.csv` / `run_info.json` mới nhất trong từng thư mục output; nếu chạy lại, hãy cập nhật.
