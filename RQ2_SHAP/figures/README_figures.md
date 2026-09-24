# Biểu đồ SHAP

1. `01_xgboost_accuracy_by_class.png`: tỷ lệ XGBoost dự đoán đúng theo lớp trong tập 1.363 flow.
2. `02_shap_top1_frequency_by_class.png`: feature Top-1 xuất hiện nhiều nhất và tỷ lệ xuất hiện của nó.
3. `03_shap_top5_mean_by_class.png`: Top-5 mean absolute SHAP của các flow dự đoán đúng theo từng lớp.
4. `04_shap_local_top5_representatives.png`: giải thích có dấu của một flow đại diện. Xanh dương đẩy model về lớp dự đoán, cam kéo model ra khỏi lớp đó.

Biểu đồ 3 dùng để đọc xu hướng theo lớp. Biểu đồ 4 dùng để giải thích một cảnh báo cụ thể. Không dùng biểu đồ 4 để kết luận cho toàn bộ lớp.
