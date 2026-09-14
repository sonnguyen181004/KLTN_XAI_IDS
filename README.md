# KLTN_XAI_IDS

Khóa Luận Tốt Nghiệp: Nghiên cứu và ứng dụng XAI (Explainable AI) trong Hệ thống Phát hiện Xâm nhập (IDS).

## Cấu trúc thư mục

- `Report/`: Tài liệu đề cương, hướng dẫn khóa luận tốt nghiệp (Proposal, Student Guide).
- `RQ1_docx/`: Các tài liệu báo cáo thực nghiệm chi tiết cho RQ1 (XGBoost, Random Forest, so sánh tham số và chỉ số).
- `RQ1_Model_Training_xboost/`: Mã nguồn huấn luyện mô hình XGBoost, tinh chỉnh siêu tham số, bảng kết quả, ma trận nhầm lẫn (confusion matrix) và mô hình đã lưu (`best_xgboost_model.pkl`).
- `dataset/`: Báo cáo phân tích dữ liệu CICIDS2018 (lưu ý: các tệp dữ liệu dung lượng lớn .parquet/.csv được loại trừ khỏi git).

## Hướng dẫn chạy mã nguồn

1. Cài đặt các thư viện cần thiết:
   ```bash
   pip install numpy pandas scikit-learn xgboost matplotlib seaborn joblib
   ```

2. Huấn luyện mô hình và tinh chỉnh siêu tham số:
   ```bash
   python RQ1_Model_Training_xboost/1_hyperparameter_tuning.py
   python RQ1_Model_Training_xboost/2_train_optimal_model.py
   ```
