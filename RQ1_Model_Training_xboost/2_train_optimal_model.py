import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import time
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support

base_dir = r"c:\Users\LOQ\Downloads\SELF_KLTN"
data_dir = os.path.join(base_dir, "CICID-2018_processed")
project_dir = os.path.join(base_dir, "RQ1_Model_Training")
saved_models_dir = os.path.join(project_dir, "saved_models")
results_dir = os.path.join(project_dir, "results")

os.makedirs(saved_models_dir, exist_ok=True)
os.makedirs(results_dir, exist_ok=True)

print("="*80)
print("  GIAI ĐOẠN 2: HUẤN LUYỆN MÔ HÌNH XGBOOST TỐI ƯU & LƯU TRỮ ARTIFACTS")
print("="*80)

# 1. Nạp dữ liệu Train & Test
print("\n1. Đang nạp dữ liệu Train (2.8M dòng) và Test (700k dòng)...")
train_df = pd.read_parquet(os.path.join(data_dir, "train_set.parquet"))
test_df = pd.read_parquet(os.path.join(data_dir, "test_set.parquet"))

X_train = train_df.drop(columns=['Label'])
y_train_raw = train_df['Label']

X_test = test_df.drop(columns=['Label'])
y_test_raw = test_df['Label']

le = LabelEncoder()
y_train = le.fit_transform(y_train_raw)
y_test = le.transform(y_test_raw)

# 2. Huấn luyện cấu hình Vô địch (max_depth=8, learning_rate=0.08)
print("\n2. Bắt đầu huấn luyện mô hình XGBoost Tối ưu (max_depth=8, learning_rate=0.08, n_estimators=100)...")
start_time = time.time()

best_xgb = XGBClassifier(
    n_estimators=100,
    max_depth=8,
    learning_rate=0.08,
    tree_method='hist',
    random_state=42,
    n_jobs=-1
)
best_xgb.fit(X_train, y_train)
train_duration = time.time() - start_time
print(f"-> Huấn luyện thành công trong: {train_duration/60:.2f} phút ({train_duration:.2f} giây)!")

# 3. Đánh giá toàn diện trên 700,000 dòng Test
print("\n3. Đang đánh giá toàn diện trên 700,000 dòng Test độc lập...")
y_pred = best_xgb.predict(X_test)

acc = accuracy_score(y_test, y_pred) * 100
prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='macro')
prec, rec, f1 = prec * 100, rec * 100, f1 * 100

# Tính FPR trên Benign cho Sub-RQ 1.2
cm = confusion_matrix(y_test, y_pred)
benign_idx = list(le.classes_).index('Benign')
fp_benign = cm[:, benign_idx].sum() - cm[benign_idx, benign_idx]
tn_benign = cm.sum() - (cm[benign_idx, :].sum() + cm[:, benign_idx].sum() - cm[benign_idx, benign_idx])
fpr_benign = (fp_benign / (fp_benign + tn_benign)) * 100

# Báo cáo chi tiết 15 phân lớp
report_dict = classification_report(y_test, y_pred, target_names=le.classes_, output_dict=True)
df_class_report = pd.DataFrame(report_dict).transpose()
report_csv = os.path.join(results_dir, "bang_chi_tiet_15_lop_tan_cong.csv")
df_class_report.to_csv(report_csv, encoding='utf-8-sig')

# Bảng 2: Tổng hợp 6 chỉ số chính thức cho RQ1
summary_metrics = {
    'Chỉ số Đánh giá': [
        'Độ chính xác toàn cục (Accuracy)',
        'Macro Precision [Sub-RQ 1.1]',
        'Macro Recall',
        'Macro F1-score [Sub-RQ 1.1]',
        'Tỷ lệ Cảnh báo sai FPR trên Benign [Sub-RQ 1.2]',
        'Thời gian Huấn luyện'
    ],
    'Kết quả XGBoost Tối ưu': [
        f"{acc:.2f}%",
        f"{prec:.2f}%",
        f"{rec:.2f}%",
        f"{f1:.2f}%",
        f"{fpr_benign:.4f}% (FP={fp_benign}, TN={tn_benign})",
        f"{train_duration/60:.2f} phút ({train_duration:.2f}s)"
    ]
}
df_summary = pd.DataFrame(summary_metrics)
summary_csv = os.path.join(results_dir, "bang_2_ket_qua_chinh_thuc_rq1.csv")
df_summary.to_csv(summary_csv, index=False, encoding='utf-8-sig')

print("\n" + "="*80)
print("  🏆 BẢNG 2: KẾT QUẢ HIỆU NĂNG CHÍNH THỨC CỦA XGBOOST CHO RQ1, SUB-1.1 VÀ SUB-1.2")
print("="*80)
print(df_summary.to_string(index=False))

print("\n--- BÁO CÁO CHI TIẾT 15 PHÂN LỚP TẤN CÔNG (PRECISION / RECALL / F1) ---")
print(classification_report(y_test, y_pred, target_names=le.classes_, digits=4))

# 4. LƯU MÔ HÌNH VÀ BỘ MÃ HÓA
print("\n4. Đang lưu mô hình nhị phân và bộ giải mã nhãn...")
model_file = os.path.join(saved_models_dir, "best_xgboost_model.pkl")
encoder_file = os.path.join(saved_models_dir, "label_encoder.pkl")

joblib.dump(best_xgb, model_file)
joblib.dump(le, encoder_file)

print(f"-> [THÀNH CÔNG] Đã lưu mô hình tối ưu vào: {model_file}")
print(f"-> [THÀNH CÔNG] Đã lưu bộ giải mã nhãn vào: {encoder_file}")
print("\n🎉 HOÀN TẤT TOÀN BỘ GIAI ĐOẠN HUẤN LUYỆN VÀ LƯU TRỮ MODEL!")
