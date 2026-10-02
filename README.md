# KLTN_XAI_IDS

Khóa luận tốt nghiệp: **nghiên cứu và ứng dụng Explainable AI (XAI) cho hệ thống phát hiện xâm nhập (IDS)** trên bộ dữ liệu CSE-CIC-IDS2018. Mô hình phát hiện là XGBoost (so sánh với Random Forest ở RQ1); phần giải thích dùng **SHAP** và **LIME**.

- Dữ liệu: CSE-CIC-IDS2018 đã xử lý, 78 đặc trưng, 15 lớp (1 Benign + 14 loại tấn công), test set 700.000 flow.
- Trạng thái: **RQ1 xong · RQ2 đã có đủ kết quả cho 4 nhóm chỉ số · RQ3 mới ở giai đoạn demo/kế hoạch.**

---

## 1. Cấu trúc dự án

```text
SELF_KLTN/
├── dataset/                         # Dữ liệu CICIDS2018 đã xử lý (parquet bị .gitignore)
├── RQ1_Model_Training_xboost/       # Tuning, huấn luyện, model .pkl, kết quả RQ1
├── RQ1_docx/                        # Báo cáo RQ1 (+ Tai_lieu_ho_tro: cẩm nang tham số XGBoost/RF)
├── RQ2/
│   ├── RQ2_SHAP/                    # Mã + kết quả SHAP (toàn cục 700k flow, cohort ghép cặp)
│   ├── RQ2_LIME_FI/                 # Mã + kết quả LIME, so sánh SHAP–LIME, biểu đồ (kể cả biểu đồ có dấu)
│   ├── RQ2_Tai_lieu/                # Báo cáo hoàn chỉnh, hướng dẫn chỉ số, kịch bản thuyết trình
│   └── RQ2_Tools/                   # Script dựng biểu đồ và tài liệu RQ2
├── RQ2_Tai_lieu/                    # Bộ câu hỏi và kịch bản bảo vệ Workflow RQ1–RQ3
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
| RQ2 | 2.1 độ tương đồng Top-k SHAP vs LIME; 2.2 kiểm chứng theo tri thức miền; 2.3 tính ổn định và chịu nhiễu; 2.4 độ trung thực (faithfulness) | `RQ2/` |
| RQ3 | 3.1 độ trễ SHAP vs LIME; 3.2 biểu đồ/UI cho SOC, dashboard, Docker | `cicflowmeter_capture_demo/` |

> Lưu ý: đánh số tiểu mục RQ2 chưa đồng nhất giữa các tài liệu (báo cáo SHAP cũ dùng 3 tiểu mục, faithfulness là 2.3). Báo cáo hoàn chỉnh dùng đánh số như bảng trên.

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

### 4.1 Ý tưởng thiết kế

Để so sánh SHAP và LIME công bằng, cả hai giải thích **cùng một mô hình, cùng 78 đặc trưng, cùng từng flow** (ghép cặp theo `sample_id`):

- **Cohort ghép cặp:** 1.339 flow mà mô hình dự đoán **đúng**, tối đa 100 flow/lớp (lớp hiếm giữ hết: Brute Force -XSS 44, Brute Force -Web 86, SQL Injection 9), lấy mẫu phân tầng, seed 42, có checksum SHA256 của model/encoder/test set.
- **Giải thích đúng lớp đã dự đoán** (`predicted_label`), không phải `true_label`, để hai phương pháp nói về cùng một đầu ra.
- **Error cohort** (151 flow dự đoán sai) được giữ riêng làm case study, không trộn vào trung bình chính.
- **Không chọn cấu hình LIME theo mức "giống SHAP"** để tránh thiên lệch; cổng kiểm soát duy nhất là Local R².

### 4.2 Cấu hình

| | SHAP | LIME |
|---|---|---|
| Thư viện | `shap.TreeExplainer` | `LimeTabularExplainer` (Ridge surrogate) |
| Thiết lập | `model_output='raw'`, `tree_path_dependent`, kiểm tra additivity | `kernel_width = 0,75·√78 ≈ 6,624`, `num_samples = 5000`, `discretize_continuous`, nền 8.002 flow |
| Đầu ra giải thích | margin thô của lớp dự đoán | xác suất lớp dự đoán (kiểm tra khớp xác suất, ngưỡng 0,001) |
| Sai số kiểm tra | additivity 2,29e-5 (700k flow) | Local R² (`explanation.score`) |

> Bản chạy LIME cũ (thư mục `RQ2_LIME/` cũ, kernel width 0,75 tuyệt đối) bị lỗi cấu hình, R² trung vị ≈ 5e-8, đã loại và chỉ giữ để lưu trữ. `run_log.txt` là log của lần chạy hỏng đầu tiên.

### 4.3 Các bước thực hiện và kết quả

**(a) SHAP toàn cục — Top-5 đặc trưng theo từng loại tấn công.** `RQ2/RQ2_SHAP/shap_top5_each_attack/shap_top5_each_attack.py` chạy hoàn tất trên 700.000 flow, 14 lớp tấn công (không có Benign), additivity error 2,29e-5. Kết quả trong `top5_each_attack/` và báo cáo `Bao_cao_Top5_SHAP_tung_loai_tan_cong.docx`.

**(b) SHAP per-flow cho cohort ghép cặp.** `build_cohort_and_shap.py` → `RQ2/RQ2_SHAP/rq2_paired_cohort/<timestamp>/` (`manifest_main.csv`, `manifest_error_cases.csv`, `shap_per_flow_long.csv`, `run_info.json`).

**(c) LIME per-flow cùng cohort.** `RQ2/RQ2_LIME_FI/run_lime_paired_cohort.py` → `rq2_lime_paired/`.

**(d) Sub-RQ 2.1 — Độ tương đồng SHAP vs LIME** (`evaluate_agreement.py`, macro theo 15 lớp, trung bình của trung bình lớp):

| k | Jaccard@k | Spearman (trên đặc trưng chung) | Đồng thuận dấu |
|---|---|---|---|
| 3 | 0,241 | 0,818 | 0,959 |
| 5 | 0,213 | 0,476 | 0,896 |
| 10 | 0,239 | 0,380 | 0,847 |

→ Hai phương pháp **chọn tập đặc trưng khá khác nhau** (Jaccard thấp), nhưng khi cùng chọn một đặc trưng thì **thường đồng ý về hướng ảnh hưởng** (dấu ≈ 85–96%). Jaccard cao nhất ở Bot / DDOS-HOIC / LOIC-UDP (≈ 0,49–0,50), thấp nhất ở Benign, Infilteration, SQL Injection (≈ 0–0,02). Lớp DDoS-LOIC-HTTP có Spearman trung bình âm (−0,65) — cần được thảo luận trong báo cáo cuối.

**(e) Sub-RQ 2.2 — Kiểm chứng theo tri thức miền** (`evaluate_domain.py`, Domain Precision@5 dựa trên bảng tín hiệu kỳ vọng cho từng loại tấn công):

| | SHAP | LIME |
|---|---|---|
| Precision@5 (macro, trung bình lớp) | **0,187** | 0,111 |
| Precision@5 (macro, trung vị lớp) | 0,167 | 0,067 |

→ SHAP bám tri thức miền tốt hơn LIME, nhưng cả hai đều thấp. Nguyên nhân chính: mô hình dựa nhiều vào các đặc trưng "dấu vân tay môi trường" (`Fwd Seg Size Min`, `Dst Port`, `Init Fwd Win Byts`) thay vì tín hiệu hành vi tấn công.

**(f) Sub-RQ 2.3 — Ổn định và chịu nhiễu** (`lime_stability_robustness.py`, tập con 289 flow):

- *Ổn định LIME qua 8 seed:* Jaccard@5 trung bình theo lớp ≈ 0,44 (trung vị lớp 0,45; độ lệch chuẩn giữa các lần chạy nhỏ, ≈ 0,07) — cùng flow, chạy lại vẫn ra tập đặc trưng khác đáng kể.
- *Chịu nhiễu (thời gian/tốc độ ±1/5/10%):*

| Nhiễu | Jaccard@5 trung bình | Tỉ lệ đổi dự đoán |
|---|---|---|
| 1% | 0,450 | 3,0% |
| 5% | 0,449 | 4,2% |
| 10% | 0,448 | 5,8% |

→ Độ tương đồng gần như không đổi khi tăng nhiễu; phần lớn "bất ổn" đến từ chính tính ngẫu nhiên của LIME chứ không phải từ nhiễu đầu vào.

**(g) Sub-RQ 2.4 — Độ trung thực** (`paired_faithfulness.py`, thay đặc trưng bằng donor, donor seed 173, control seed 2026, 10 donor × 20 lần, sai số hòa 1e-6). Tỉ lệ thắng so với chọn ngẫu nhiên:

| k | SHAP | LIME |
|---|---|---|
| 3 | **98,9%** | 82,6% |
| 5 | **95,7%** | 90,4% |
| 10 | **99,8%** (coverage 80,4%) | 94,8% (coverage 100%) |

→ Cả hai đều tốt hơn ngẫu nhiên; SHAP mạnh hơn ở k nhỏ, và làm mô hình giảm margin nhiều hơn (k=5: 10,87 vs 8,07). Ở k=10, SHAP chỉ đủ điều kiện ở 80,4% flow nên so sánh phải đọc kèm coverage. Không được trộn kết quả này với con số 99,31% của lần kiểm tra faithfulness toàn test set (700k flow) — đó là phép đo khác.

### 4.4 Vì sao Local R² của LIME thấp (trung vị ≈ 0,068)?

Local R² cho biết mô hình tuyến tính đơn giản của LIME "bắt chước" XGBoost quanh flow đang giải thích tốt đến đâu. Chỉ **12,3% flow đạt R² ≥ 0,3**. Đây là một **phát hiện hợp lệ, không phải lỗi mã**:

1. XGBoost rất tự tin (xác suất 0,97–0,99) và là tập hợp cây → hàm đầu ra dạng bậc thang, gần như không đổi rồi nhảy vọt; đường thẳng khó khớp.
2. Không gian 78 chiều: "vùng lân cận" của LIME rất thưa dù đã sửa kernel width.
3. Rời rạc hóa liên tục (`discretize_continuous`) làm mất thông tin mịn.

Chẩn đoán trong `diagnosis_low_r2.json` (60 flow): đổi `num_samples` = 10.000 hoặc tắt discretize **không cải thiện** (R² trung vị 0,048 / 0,029 so với 0,062 gốc). Vì vậy kết luận LIME trong báo cáo được nêu **kèm cảnh báo độ tin cậy**. Giải thích dễ hiểu hơn nằm ở mục 6.1 của báo cáo hoàn chỉnh.

### 4.5 Phát hiện về đặc trưng

- Với Benign, LIME nhấn mạnh `FIN Flag Cnt`, `Tot Fwd Pkts`; với Bot là `Dst Port`, `RST Flag Cnt` (bảng đầy đủ 15 lớp: `RQ2/RQ2_LIME_FI/lime_top5_by_class.csv`).
- Các đặc trưng "dấu vân tay môi trường" xuất hiện dày đặc trong Top-k → mô hình có nguy cơ học đặc điểm của bộ dữ liệu thay vì hành vi tấn công. Đây là lý do khi đưa vào traffic thật (RQ3) có báo động giả.

### 4.6 Khoảng trống còn lại của RQ2

- File kết quả của **SHAP faithfulness (99,31%)** và **SHAP noise robustness** chưa có thư mục output trong dự án (script `shap_faithfulness_full_test.py`, `shap_noise_full_test.py`, `shap_noise_robustness.py` có sẵn nhưng chưa thấy output) → cần chạy lại hoặc tìm lại.
- Số liệu **độ ổn định của SHAP** chưa đưa vào báo cáo hoàn chỉnh.
- Chưa đo **latency LIME** một cách chính thức (con số ≈ 148 ms/flow vs SHAP 19,11 ms ≈ 7,8× chỉ lấy từ log, chưa benchmark sạch).
- Benign không có trong SHAP toàn cục (chỉ có trong cohort).
- Cần thảo luận các lớp có Spearman âm/NaN (LOIC-HTTP, Infilteration, SQL Injection, Benign).
- `run_log.txt` chứa traceback của lần chạy đầu — nên thay bằng log sạch.
- Kịch bản thuyết trình: slide 2, 3, 4, 7 còn lỗi chính tả.

### 4.7 Chạy lại RQ2 (thứ tự)

Từ thư mục gốc dự án (sau khi gom vào `RQ2/`, các script dùng đường dẫn tương đối theo vị trí file; nếu script báo không tìm thấy dữ liệu, kiểm tra biến `ROOT` đầu file):

```powershell
# 1) Cohort ghép cặp + SHAP per-flow
python .\RQ2\RQ2_SHAP\shap_top5_each_attack\build_cohort_and_shap.py --project .
# 2) LIME cùng cohort
python .\RQ2\RQ2_LIME_FI\run_lime_paired_cohort.py
# 3) Bốn nhóm chỉ số
python .\RQ2\RQ2_LIME_FI\evaluate_agreement.py
python .\RQ2\RQ2_LIME_FI\evaluate_domain.py
python .\RQ2\RQ2_LIME_FI\lime_stability_robustness.py
python .\RQ2\RQ2_LIME_FI\paired_faithfulness.py
# 4) Dựng biểu đồ và báo cáo
python .\RQ2\RQ2_Tools\build_rq2_charts.py
python .\RQ2\RQ2_Tools\build_lime_guide.py
python .\RQ2\RQ2_Tools\build_lime_signed_charts.py   # biểu đồ LIME/SHAP có dấu (dương/âm)
python .\RQ2\RQ2_Tools\build_rq2_final_report.py
```

Mỗi script ghi vào thư mục con theo timestamp (không ghi đè) cùng `run_info.json` (checksum, phiên bản thư viện). Môi trường đã dùng: Python 3.14, shap 0.52.0, xgboost 3.4.1.

### 4.8 Tài liệu RQ2

| File | Nội dung |
|---|---|
| `RQ2/RQ2_Tai_lieu/Bao_cao_hoan_chinh_RQ2_SHAP_LIME.docx` | Báo cáo tổng hợp cuối (52 đoạn, 16 bảng, có mục giải thích Local R²) |
| `RQ2/RQ2_Tai_lieu/Huong_dan_chi_tiet_cac_chi_so_LIME_RQ2.docx` | Hướng dẫn từng chỉ số |
| `RQ2/RQ2_Tai_lieu/Bao_cao_Tong_hop_SHAP_va_Ke_hoach_LIME_RQ2.docx` | Tổng hợp SHAP + kế hoạch LIME |
| `RQ2/RQ2_Tai_lieu/Kịch bản thuyết trình RQ2 (8 slide).docx` | Kịch bản báo cáo (slide 8 = kế hoạch LIME) |
| `RQ2/RQ2_LIME_FI/RQ2_LIME_Ket_Qua_Final.docx`, `RQ2_LIME_Bao_Cao_Rieng.docx` | Báo cáo riêng của LIME |
| `RQ2/RQ2_SHAP/Bao_cao_*.docx` | Báo cáo SHAP (toàn cục, Top-5, tiến độ) |
| `Tai_lieu_tham_khao/Hoi_Dap_Bao_Ve_KLTN_RQ1_RQ2.docx` | Bộ hỏi–đáp bảo vệ |
| `RQ2_Tai_lieu/Bo_cau_hoi_va_kich_ban_bao_ve_Workflow_RQ1_RQ2_RQ3.docx` | Câu hỏi và kịch bản bảo vệ workflow |
| `RQ2/RQ2_LIME_FI/RQ2_LIME_Bao_Cao_Rieng_v2.docx` | Báo cáo riêng LIME bản mới, thêm phụ lục biểu đồ có dấu (mục 10) |
| `WorkFlow/workflow_v3.png` | Sơ đồ workflow tổng quan |

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
