# KLTN_XAI_IDS

Khóa luận tốt nghiệp: **nghiên cứu và ứng dụng Explainable AI (XAI) cho hệ thống phát hiện xâm nhập (IDS)** trên bộ dữ liệu CSE-CIC-IDS2018. Mô hình phát hiện là XGBoost (so sánh với Random Forest ở RQ1); phần giải thích dùng **SHAP** và **LIME**.

- Dữ liệu: CSE-CIC-IDS2018 đã xử lý, 78 đặc trưng, 15 lớp (1 Benign + 14 loại tấn công), test set 700.000 flow.
- Trạng thái: **RQ1 xong · RQ2 chạy lại từ đầu (2026-10-09) theo pipeline 14 giai đoạn, đủ kết quả cho cả 5 câu hỏi (agreement, quality gate, stability/robustness, faithfulness, domain validation) + cohort lỗi · RQ3 mới ở giai đoạn demo/kế hoạch.**

---

## 1. Cấu trúc dự án

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
├── cicflowmeter_capture_demo/       # RQ3: demo bắt flow bằng CICFlowMeter (giữ .venv tại chỗ)
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
| RQ3 | 3.1 độ trễ SHAP vs LIME; 3.2 biểu đồ/UI cho SOC, dashboard, Docker | `cicflowmeter_capture_demo/` |

> Đánh số tiểu mục RQ2 dùng thống nhất theo [`RQ2/docs/plan.md`](RQ2/docs/plan.md) (2.1 agreement, 2.2 stability/robustness, 2.3 faithfulness, 2.4 domain validation) — khác thứ tự trình bày trong mục 4 dưới đây, vốn đi theo mạch kể chuyện (domain validation và faithfulness có thể đổi chỗ khi trình bày). Cần hỏi thầy hướng dẫn trước khi đổi số trong tài liệu chính thức.

---

## 3. RQ1 — Hiệu năng phát hiện (đã xong)

- **Mô hình chọn:** XGBoost, 100 cây, `max_depth=8`, `learning_rate=0.08`, `tree_method=hist`, `multi:softprob`, 15 lớp.
- **Kết quả trên test set:** Accuracy 97,91% · Macro Precision 90,84% · Macro Recall 83,99% · **Macro F1 85,81%** · thời gian huấn luyện ≈ 2,67 phút.
- **Tuning:** 7 cấu hình; cấu hình depth 12 / lr 0,08 đạt F1 85,95% nhưng bản depth 8 được giữ làm mô hình giải thích.
- **Hạn chế cần nói rõ:** test set được dùng để chọn cấu hình (không có validation riêng) nên số liệu hơi lạc quan.
- **Về "FPR":** con số 5,7481% trong bảng RQ1 thực chất là tỉ lệ *bỏ sót* (tấn công bị dự đoán thành Benign). Tỉ lệ báo động giả thật sự (Benign bị báo là tấn công) = 1.139 / 490.000 ≈ **0,2324%**.

Chạy lại:

```powershell
python .\RQ1_Model_Training_xboost\1_hyperparameter_tuning.py
python .\RQ1_Model_Training_xboost\2_train_optimal_model.py
```

---

## 4. RQ2 — Khả năng giải thích SHAP vs LIME (trọng tâm)

> **Chạy lại từ đầu ngày 2026-10-09** theo kế hoạch 14 giai đoạn (GĐ0→GĐ13) trong [`RQ2/docs/plan.md`](RQ2/docs/plan.md). Toàn bộ kết quả của lần chạy trước đã chuyển vào [`v1_archive/RQ2_old_20260929/`](v1_archive/RQ2_old_20260929) để lưu trữ/so sánh. Pipeline mới nằm ở `RQ2/scripts/` (14 script `stage00_*.py` → `stage13_*.py` + 4 script `build_report_*.py`), mỗi lần chạy ghi vào `RQ2/runs/<ngày>/` (không ghi đè, có `config.yaml` chốt tham số, log, checksum).

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

## 5. RQ3 — Realtime (mới ở giai đoạn demo/kế hoạch)

- **Đã có:** `cicflowmeter_capture_demo/` (`capture_live.py`, `capture.ps1`, `setup.ps1`, `verify_csv.py`, `flows.csv` với 136 flow × 82 cột; `cicflowmeter==0.5.0`).
- **Vấn đề đã phát hiện:**
  - Lệch đơn vị: CICFlowMeter bản Python xuất **giây**, còn dữ liệu huấn luyện CICIDS2018 là **micro giây** → cần nhân ×1e6 cho các đặc trưng thời gian.
  - Báo động giả trên traffic thật do các đặc trưng "dấu vân tay môi trường" (đặc biệt `Fwd Seg Size Min`).
- **Kế hoạch:** pipeline realtime (bắt gói → flow → chuẩn hóa đơn vị → XGBoost → SHAP) → dashboard cho SOC → đo latency → Docker. Kết quả RQ2 cho thấy có thể **chỉ dùng SHAP trong dashboard** (nhanh hơn ≈ 7,8×, ổn định, trung thực hơn), nhưng vẫn cần đo latency LIME một lần để trả lời Sub-RQ 3.1 — đây là điều chỉnh so với proposal cần ghi chú.

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
