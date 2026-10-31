# IDS_M1_Lab: hệ thống IDS chạy với mô hình M1

Bản chạy của hệ thống RQ3 với mô hình M1 (XGBoost huấn luyện trên dữ liệu đã sửa của Liu và cộng sự, 13 lớp). Thư mục này dùng để thử M1 trên flow thật và phục vụ bài báo trong `Paper_IEEE/`. Nó không sửa và không ghi đè file nào của RQ1, RQ2, RQ3, RQ4 hay báo cáo.

Hướng dẫn thao tác trên dashboard: [docs/dashboard_usage_m1.md](docs/dashboard_usage_m1.md).

## Khác biệt so với RQ3_IDS_System

| Mục | RQ3_IDS_System (M0) | IDS_M1_Lab (M1) |
|---|---|---|
| Mô hình | `RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl`, 15 lớp | `models/m1_xgboost_model.pkl`, 13 lớp |
| Train và test của nền SHAP, LIME và cờ lớp hiếm | `dataset/CICID-2018_processed/` | `RQ4_Retrain_Compare/data/d2_train.parquet`, `d2_test.parquet` (chỉ đọc) |
| `n_classes_expected` | 15 | 13 |
| LIME `kernel_width` | 3,312 (khóa theo RQ2) | 3000 |
| Cơ sở dữ liệu | `RQ3_IDS_System/data/ids_system.db` | `IDS_M1_Lab/data/ids_system.db` |
| Mã `app/` | gốc | bản sao, chỉ khác 3 chỗ bên dưới |

Ba chỗ khác trong mã, đều chỉ để chạy được trong thư mục này:
- `app/capture_supervisor.py` và `app/ingestion_ui.py`: nếu chưa có `.venv_capture` riêng thì dùng `RQ3_IDS_System/.venv_capture` (chỉ đọc).
- `app/dashboard.py`: hướng dẫn trong màn hình Realtime trỏ tới thư mục này và venv của RQ3.

## Vì sao kernel LIME là 3000

RQ2 khóa kernel 3,312 để so sánh SHAP và LIME. Trên flow thật (ví dụ ca A07) cấu hình này trả `insufficient_neighborhood` vì flow nằm quá xa mẫu nền. Đã quét năm độ rộng trên 313 flow thật (1.000 mẫu nhiễu, nền 2.000 flow):

| Kernel | 3,312 | 30 | 300 | 3.000 | 30.000 |
|---|---|---|---|---|---|
| M1: số flow qua ngưỡng R² từ 0,3 | 0 | 136 | 265 | 304 | 313 |
| M0 (nền gốc): số flow qua ngưỡng | 3 | 32 | 32 | 32 | 41 |

Kernel rộng làm cổng R² qua được, nhưng cỡ mẫu hiệu dụng trung vị lên 1.000, tức trọng số gần đều và mô hình tuyến tính khớp gần như toàn cục. Vì vậy 3000 là lựa chọn để LIME chạy được trong lab, không phải bằng chứng LIME giải thích tốt cục bộ. Chi tiết: `RQ4_Retrain_Compare/scripts/20_lime_kernel_sweep.py`, `RQ4_Retrain_Compare/results/lab_m1/lime_kernel_sweep*.{csv,json}`.

## Cách chạy

Chạy từ thư mục `IDS_M1_Lab`, trong môi trường đã cài `requirements.txt`:

```powershell
.\run_ids.ps1
```

Script đặt biến môi trường `IDS_CAPTURE_CONTROL_TOKEN` (token cục bộ cho nút điều khiển capture), mở API ở cổng 8000, đợi 15 giây rồi mở dashboard ở cổng 8501 (`http://127.0.0.1:8501`). Chạy tay:

```powershell
$env:IDS_CAPTURE_CONTROL_TOKEN = '<chuỗi bất kỳ dài từ 32 ký tự>'
uvicorn app.main:app --port 8000
streamlit run app/dashboard.py --server.port 8501 --server.address 127.0.0.1
```

Không bật hai API cùng dùng một DB. Bắt gói thật cần Npcap và môi trường capture (`requirements-capture.txt`); nếu `IDS_M1_Lab/.venv_capture` chưa có, hệ thống dùng `RQ3_IDS_System/.venv_capture`.

## Nội dung thư mục

| Đường dẫn | Vai trò | Có trong git |
|---|---|---|
| `app/` | API, dashboard, capture, SHAP, LIME | có |
| `scripts/` | Script kiểm thử từng bước (kế thừa từ RQ3) và hai script riêng của lab: `m1_full_test_csv.py` (gửi 236 dòng Tập B vào `/predict`, đối chiếu nhãn), `m1_lime_sweep.py` (thử cấu hình LIME trên một flow PCAP) | có |
| `config.yaml`, `run_ids.ps1`, `requirements*.txt` | Cấu hình và chạy | có |
| `models/m1_*` | M1 và bộ mã hóa nhãn, sao chép từ `RQ4_Retrain_Compare/models/` | không (file lớn, sinh lại bằng RQ4) |
| `data/` | DB SQLite chạy thật (gồm 784 flow thực đã xác nhận), `train_stats.json`, `lime_background.npy`, `clean_holdout_set.csv` (236 dòng, không trùng train), phiên capture | không |

Dựng lại `train_stats.json` và `lime_background.npy` từ train đã sửa bằng `scripts/stage08_compute_train_stats.py` và `scripts/stage09_compute_lime_background.py`; `clean_holdout_set.csv` bằng `scripts/stage03_build_clean_dataset.py`.

## Kết quả đã thu từ thư mục này

| Nội dung | Kết quả |
|---|---|
| 784 flow thực đã xác nhận bình thường | M0: 149 cảnh báo (19,01%). M1: 0 cảnh báo (cận trên 95% là 0,47%) |
| WEB-B01 (duyệt web, 21 flow) | M0: 19 trên 21 cảnh báo. M1: 0 trên 21 |
| A07 và B03 (SSH brute force) | M1: SSH-Bruteforce (độ tin cậy 0,82 và 0,78). M0: Hulk |

Số liệu và script kiểm tra nằm ở `RQ4_Retrain_Compare/results/` và `Paper_IEEE/tools/verify_numbers.py`.

## Giới hạn

- Nhãn bình thường của 784 flow dựa vào xác nhận bằng lời của nhóm, không có nhật ký hoạt động. SSH chỉ có hai flow (A07, B03), chưa đủ để tính tỷ lệ.
- Tab so sánh trên dashboard đang so M1 với chính M1. Đối chiếu M0 và M1 dùng `RQ4_Retrain_Compare/scripts/18_lab_predict_m0_m1.py`.
- Cờ "môi trường" và gợi ý Hulk FIN trong `config.yaml` viết cho lỗi của dữ liệu cũ, có thể không còn đúng với M1.
- `rq2_cohort_ids` và `rq2_master_summary` trong `config.yaml` vẫn trỏ về RQ2, chỉ các script kiểm tra cũ cần đến.
- Một số chú thích trong mã vẫn ghi `RQ3_IDS_System`.
- Bộ chuẩn của M1 dễ (16,9% dòng test trùng train, cây độ sâu 3 đạt 96,4%), nên điểm cao trên test cũ không chứng minh M1 tốt hơn.
