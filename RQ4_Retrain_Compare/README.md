# RQ4 — Huấn luyện lại XGBoost trên dữ liệu đã sửa lỗi và so sánh với dữ liệu cũ

Mục đích: kiểm tra giả thuyết rằng báo nhầm Hulk trên lưu lượng thật đến từ khoảng trống của
CSE-CIC-IDS2018 bản CSV gốc (thiếu Benign "đóng bằng FIN có dữ liệu"), bằng cách huấn luyện lại
**đúng quy trình RQ1 và RQ2** trên bản improved rồi so sánh.

## RQ4 nằm ở đâu trong câu chuyện

| RQ | Việc làm | Kết quả dẫn sang bước sau |
|---|---|---|
| RQ1 | Huấn luyện M0 (XGBoost, dữ liệu gốc, 15 lớp) | Accuracy 97,91%, nhưng test có dòng trùng với train |
| RQ2 | So sánh SHAP và LIME | SHAP luôn bật, LIME theo yêu cầu |
| RQ3 | Hệ thống IDS trực tuyến (`RQ3_IDS_System/`) | M0 báo Hulk trên lưu lượng bình thường của máy thu |
| RQ4 | Truy nguyên nguyên nhân, huấn luyện lại M1 trên dữ liệu đã sửa | Lỗi biến mất trên các flow bình thường đã thu, nguyên nhân gốc vẫn là giả thuyết |

Bài báo IEEE kể câu chuyện này ở `../Paper_IEEE/`.

## Nguyên tắc: làm y như mô hình cũ

| Hạng mục | Mô hình cũ (RQ1, RQ2) | Mô hình mới (RQ4) |
|---|---|---|
| Thuật toán | XGBClassifier, tree_method hist, n_estimators 100, random_state 42 | Giống hệt |
| Siêu tham số | Chọn bằng quét 7 cấu hình ở RQ1: độ sâu 8, learning rate 0,08 | Dùng đúng cấu hình đó, không quét lại |
| Đặc trưng | 78 đặc trưng, float32, không Timestamp, không IP | Giống hệt (đổi tên theo bảng ánh xạ) |
| Cách lấy mẫu | 3,5 triệu dòng, 70 % Benign và 30 % tấn công, giữ 100 % lớp hiếm | Cùng công thức, trần theo số mẫu sẵn có |
| Chia dữ liệu | Stratified 80/20 | Giống hệt: stratified 80/20, seed 42, lấy ngẫu nhiên từ toàn bộ dữ liệu, không bộ giữ riêng nào |
| Chỉ số | Accuracy, Macro P/R/F1, FPR Benign, FNR tấn công (`ids_metrics.py`) | Giống hệt |
| Giải thích | SHAP toàn cục và từng flow, LIME khóa cấu hình, độ đồng thuận, cổng chất lượng, độ ổn định, faithfulness, miền tri thức, nhóm lỗi (RQ2 GĐ0 đến 13) | Chạy lại cùng các giai đoạn trên mô hình mới |

Những chỗ **không** thể giống hệt, và cách xử lý:
- Bản improved không có SlowHTTPTest, và FTP-BruteForce chỉ có dạng "Attempted". Cả hai lớp bị bỏ, nên
  không gian nhãn của mô hình mới là 13 lớp. Để công bằng, mô hình cũ cũng được huấn luyện lại trên 13 lớp
  này (M0b) bên cạnh M0 gốc 15 lớp.
- Các nhãn "Attempted" được bỏ, bốn loại Infiltration gộp thành một lớp.
- Bộ trích xuất flow và nhãn của hai bản khác nhau, nên M0 và M1 học từ **hai miền dữ liệu khác nhau**. Phép thử "dữ liệu là nguyên nhân" vì vậy không tách được ảnh hưởng của bộ trích xuất khỏi ảnh hưởng của nhãn.
- Chưa tìm thấy mã tạo `train_set.parquet` nên cách lấy mẫu của RQ1 được dựng lại từ báo cáo dataset 3,5 triệu dòng.

## Các mô hình

| Mã | Dữ liệu huấn luyện | Vai trò |
|---|---|---|
| M0 | Train cũ 15 lớp (đã có, RQ1) | Mô hình gốc để tham chiếu |
| M0b | Train cũ giới hạn 13 lớp chung | Điểm so sánh công bằng về không gian nhãn |
| M1 | Train lấy từ bản improved | Dữ liệu đã sửa lỗi có giúp không |
| M2 (hoãn) | Train cũ cộng Benign "FIN có dữ liệu" lấy từ improved | Tách "thiếu mẫu" khỏi "khác định nghĩa đặc trưng". Theo yêu cầu của người dùng, tạm không chạy. Mã đã có (`04_build_datasets.py`, `05_train_models.py m2_10000`) để chạy sau |

## Bộ đánh giá

| Mã | Nội dung | Ghi chú |
|---|---|---|
| T1 | Test cũ (`test_set.parquet`) | Trong phân phối của M0, M0b, M2 |
| T2 | Test stratified 20 % của bản improved | Trong phân phối của M1 |
| T3 | 784 flow thực của máy người dùng (`feeder_live`, bốn phiên ngày 22/10/2026) | Đo báo nhầm trên lưu lượng thật. Nhãn Benign dựa vào lời xác nhận của người dùng (26/10/2026), không có nhật ký hoạt động chi tiết. Không dùng PCAP đã nạp |

Siêu tham số XGBoost và cấu hình SHAP, LIME giữ nguyên của RQ1 và RQ2, không quét hay chọn lại.

## Bố cục thư mục

| Thư mục | Nội dung | Commit? |
|---|---|---|
| `scripts/` | Mã theo thứ tự đánh số (bảng bên dưới) và `rq4_common.py` (hằng số, bảng ánh xạ, định nghĩa vùng FIN đọc từ cấu hình RQ3) | Có |
| `results/` | Kết quả CSV, JSON, log của từng bước. `results/lab_m1/` là kết quả flow lab và LIME | Có |
| `lab_captures/` | Các bản bắt gói của lab hai máy ảo (`A07`, `B03`, `C01`, `D01`, `SQL-I01`, `WEB-B01`) kèm giờ và nhật ký tấn công | Có |
| `report/` | Bộ dựng báo cáo, ảnh demo, bản tổng hợp sơ bộ | Có |
| `xai_pipeline/`, `xai_runs/` | Mã và kết quả chạy lại SHAP, LIME của RQ2 cho M1 | Mã có, kết quả theo `.gitignore` |
| `data/` | Dữ liệu trung gian (`d2_train.parquet`, `d2_test.parquet`, tập T3, các phần improved) | Không (quá lớn) |
| `models/` | `m0b_*` và `m1_*` (`.pkl`) | Không |

Bản sao hệ thống chạy M1 nằm ở `../IDS_M1_Lab/` (xem README ở đó). Nó phải đứng cạnh `RQ3_IDS_System/` vì mã tính gốc repo bằng "lên hai cấp".

## Các script

| Script | Việc làm |
|---|---|
| `01_mapping_tables.py` | Bảng ánh xạ đặc trưng và nhãn giữa bản gốc và bản improved |
| `02_compare_train_sets.py` | So sánh hai bộ train, đếm vùng FIN, tần suất cờ FIN |
| `03_build_improved_cache.py` | Đọc bản improved theo ngày, lọc lớp và dòng lỗi, lưu cache Parquet |
| `04_build_datasets.py` | Dựng train và test của M1 theo công thức lấy mẫu của RQ1 |
| `05_train_models.py` | Huấn luyện M0b, M1 (và M2 khi cần) với tham số RQ1 |
| `06_prepare_t3_realtime.py`, `06b_confirm_t3.py` | Dựng tập T3 từ flow `feeder_live` và nhật ký phiên |
| `07_evaluate_cross.py` | Đánh giá M0, M0b, M1 trên T1, T2a, T3, có bản bỏ dòng trùng |
| `08_run_xai.py` | Chạy SHAP và LIME cho mô hình mới theo cấu hình RQ2 |
| `09_diagnose_m1.py` | Kiểm tra riêng M1: rò rỉ, độ quan trọng đặc trưng, bỏ đặc trưng môi trường |
| `10_t3_explain.py` | SHAP của 148 flow trong vùng FIN, thử đổi một đặc trưng trên M0 |
| `11_report_data.py` | Gom số liệu cho báo cáo |
| `13_audit_m1_standalone.py` | Kiểm tra M1 độc lập: nhãn xáo trộn, đường cong học, cây nông, gần trùng |
| `14_blocked_cv_m1.py` | Đánh giá M1 theo năm khối thời gian, có khoảng đệm, có bản bỏ dòng trùng |
| `15_system_test_csv.py` | Thử hệ thống với CSV mẫu có nhãn cho cả M0 và M1 |
| `16_verify_rq1_preprocessing.py` | Kiểm tra cách dựng train, test RQ1 từ mười file Parquet nguồn |
| `17_paper_checks.py` | Số liệu bổ sung cho bài báo: khoảng tin cậy, SHAP cùng lớp đầu ra, kiểm tra cộng dồn, vùng FIN theo phiên, độ trễ, mã băm tệp |
| `18_lab_predict_m0_m1.py` | Trích flow từ các bản bắt gói lab bằng cùng bộ trích xuất, dự đoán M0 và M1 |
| `19_lab_lime_validity.py` | LIME trên 313 flow thật: M0 với nền gốc, M1 với nền đã sửa, kèm phản chứng đặt FIN về 0 |
| `20_lime_kernel_sweep.py` | Quét độ rộng kernel của LIME trên 313 flow thật |

Hai script 18 đến 20 đọc cơ sở dữ liệu của `../IDS_M1_Lab/` (không commit), nên chỉ chạy lại được trên máy có thư mục đó.

## Kết quả chính

Chi tiết ở `results/cross_evaluation.csv`, `results/t3_explain.json`, `results/paper_checks.json`.

| Mô hình | Tập kiểm thử | Accuracy | Macro F1 (13 lớp) | Cảnh báo trên flow Benign |
|---|---|---|---|---|
| M0 | T1, test cũ | 98,09% | 88,96% | 0,23% |
| M0 | T2a, test improved | 74,14% | 65,97% | 21,12% (99,998% flow Benign trong vùng FIN bị báo Hulk) |
| M0 | T3, 784 flow thực | không áp dụng | không áp dụng | 19,01% (149 flow, 148 flow là Hulk) |
| M1 | T2a, test improved | 99,996% | 99,30% | 0,0015% |
| M1 | T3, 784 flow thực | không áp dụng | không áp dụng | 0% (cận trên 95% là 0,47%) |

- Vùng FIN (số cờ FIN từ 1, `Fwd Pkt Len Max` từ 66, `Fwd Seg Size Min` dưới 32) chứa 148 trong 149 cảnh báo thực và 100.817 trong 100.849 cảnh báo sai trên test Benign improved.
- Trong train gốc vùng này có 445 flow, tất cả là Hulk. Trong train improved có 405.347 Benign và 330 Hulk, cùng flow của nhiều lớp tấn công khác.
- Đặt `FIN Flag Cnt` về 0 đổi nhãn cả 148 flow trong vùng. Đây là độ nhạy của mô hình, không phải bằng chứng nhân quả.
- Điểm của M1 trên test improved không dự báo hiệu năng ngoài thực tế: 16,9% test trùng train, cây độ sâu 3 đạt 96,4%, theo khối thời gian macro F1 từ 98,1% đến 99,99%.
- M1 chỉ nằm trong phân phối của dữ liệu improved. Trên test cũ M1 cho accuracy 72,56% và nhận đúng 3,7% flow Hulk, nên hai mô hình không thay thế được cho nhau giữa hai miền.

## Chạy lại

Từ thư mục `RQ4_Retrain_Compare/`, theo thứ tự `01` đến `11`, rồi `13`, `14`, `15`. Mỗi script đọc đường dẫn từ `scripts/rq4_common.py`. Các bước dựng dữ liệu và huấn luyện cần `dataset/` (gốc và improved) và nặng. Dựng lại báo cáo: `python scripts/11_report_data.py` rồi `node report/build_report.js <đầu ra.docx> <văn bản.txt>`.

Dữ liệu trung gian (`data/`) và mô hình (`models/`) không được commit. Kết quả CSV, mã và tài liệu được commit.

## Giới hạn

- Nguyên nhân do bộ trích xuất cắt flow tại gói FIN đầu tiên là giả thuyết, chưa kiểm tra trên gói tin thô.
- Nhãn Benign của T3 dựa vào lời xác nhận, một máy tính, bốn phiên, các flow trong phiên có tương quan.
- Bằng chứng tấn công thật chỉ gồm vài flow lab; chưa đo tỷ lệ phát hiện của M1 trên tấn công thật.
- Chỉ thử XGBoost và một bộ dữ liệu đã sửa.

## Trạng thái (31/10/2026)

| Hạng mục | Trạng thái |
|---|---|
| Bảng ánh xạ, so sánh hai bộ train (cũ và improved) | Xong |
| Dựng train và test M1 theo công thức lấy mẫu của RQ1 | Xong |
| Huấn luyện M0b và M1 (tham số RQ1, không quét lại) | Xong |
| Đánh giá chéo T1, T2a, T3, có bản bỏ dòng trùng | Xong |
| SHAP và LIME cho M1 (cấu hình RQ2 đã khóa, bỏ GĐ5 và GĐ9) | Xong |
| M2 (thêm Benign vào train cũ) | Hoãn theo yêu cầu người dùng |
| Kiểm tra riêng M1 (nhãn xáo trộn, đường cong học, gần trùng, Src IP theo lớp) | Xong |
| Đánh giá M1 theo khối thời gian | Xong (`14_blocked_cv_m1.py`) |
| Kiểm tra cho bài báo: khoảng tin cậy, SHAP cùng lớp, cộng dồn, vùng FIN theo phiên, độ trễ | Xong (`17_paper_checks.py`) |
| Flow lab qua cùng bộ trích xuất, dự đoán M0 và M1 | Xong (`18_lab_predict_m0_m1.py`). Bài chỉ dùng ca duyệt web và hai flow SSH đã xác nhận nhãn |
| LIME trên flow thật với nền đã sửa và quét độ rộng kernel | Xong (`19_`, `20_`) |
| Kiểm tra theo khối thời gian cho M0 trên dữ liệu gốc | Không làm |
| Bài báo IEEE (tiếng Anh và tiếng Việt) | Bản nháp ở `../Paper_IEEE/` |
| Báo cáo đầy đủ | `report/Bao_cao_RQ4_so_sanh_dataset_cu_va_moi.docx`, dựng bằng `report/build_report.js` |
