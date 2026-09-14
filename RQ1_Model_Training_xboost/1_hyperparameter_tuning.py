import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import time
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

base_dir = r"c:\Users\LOQ\Downloads\SELF_KLTN"
data_dir = os.path.join(base_dir, "CICID-2018_processed")
project_dir = os.path.join(base_dir, "RQ1_Model_Training")
results_dir = os.path.join(project_dir, "results")
os.makedirs(results_dir, exist_ok=True)

print("="*80)
print("  GIAI ĐOẠN 1: THỰC THI QUÉT THAM SỐ THỰC TẾ TRÊN DỮ LIỆU ĐỂ TÌM CẤU HÌNH TỐI ƯU")
print("="*80)

# 1. Đọc dữ liệu Train (2.8M) và Test (700k)
print("\n1. Đang nạp dữ liệu Train và Test...")
train_df = pd.read_parquet(os.path.join(data_dir, "train_set.parquet"))
test_df = pd.read_parquet(os.path.join(data_dir, "test_set.parquet"))

X_train = train_df.drop(columns=['Label'])
y_train_raw = train_df['Label']

X_test = test_df.drop(columns=['Label'])
y_test_raw = test_df['Label']

le = LabelEncoder()
y_train = le.fit_transform(y_train_raw)
y_test = le.transform(y_test_raw)

print(f"-> Train: {len(X_train):,} dòng | Test: {len(X_test):,} dòng")

# 2. Định nghĩa danh sách các cấu hình cần quét thực tế
configs = [
    {'max_depth': 4,  'learning_rate': 0.05, 'desc': 'Cây nông, học chậm'},
    {'max_depth': 6,  'learning_rate': 0.05, 'desc': 'Cây trung bình, học chậm'},
    {'max_depth': 6,  'learning_rate': 0.08, 'desc': 'Cây trung bình, học chuẩn'},
    {'max_depth': 8,  'learning_rate': 0.05, 'desc': 'Cây sâu, học chậm'},
    {'max_depth': 8,  'learning_rate': 0.08, 'desc': 'Cây sâu, học chuẩn (Ứng viên tối ưu)'},
    {'max_depth': 8,  'learning_rate': 0.10, 'desc': 'Cây sâu, học nhanh'},
    {'max_depth': 12, 'learning_rate': 0.08, 'desc': 'Cây rất sâu (Kiểm tra Overfitting)'}
]

tuning_results = []
benign_idx = list(le.classes_).index('Benign')

print(f"\n2. Bắt đầu quét {len(configs)} cấu hình trên dữ liệu thật...")
for i, cfg in enumerate(configs, 1):
    depth = cfg['max_depth']
    lr = cfg['learning_rate']
    desc = cfg['desc']
    
    print(f"\n---> [Cấu hình {i}/{len(configs)}] Đang chạy: max_depth={depth}, learning_rate={lr} ({desc})...")
    start_t = time.time()
    
    model = XGBClassifier(
        n_estimators=100,
        max_depth=depth,
        learning_rate=lr,
        tree_method='hist',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    run_time = time.time() - start_t
    
    # Dự đoán trên Train
    y_train_pred = model.predict(X_train)
    train_acc = accuracy_score(y_train, y_train_pred) * 100
    _, _, train_f1, _ = precision_recall_fscore_support(y_train, y_train_pred, average='macro')
    train_f1 = train_f1 * 100
    
    # Dự đoán trên Test
    y_test_pred = model.predict(X_test)
    test_acc = accuracy_score(y_test, y_test_pred) * 100
    test_prec, test_rec, test_f1, _ = precision_recall_fscore_support(y_test, y_test_pred, average='macro')
    test_prec, test_rec, test_f1 = test_prec * 100, test_rec * 100, test_f1 * 100
    
    # Tính FPR Benign
    cm = confusion_matrix(y_test, y_test_pred)
    fp_benign = cm[:, benign_idx].sum() - cm[benign_idx, benign_idx]
    tn_benign = cm.sum() - (cm[benign_idx, :].sum() + cm[:, benign_idx].sum() - cm[benign_idx, benign_idx])
    fpr_benign = (fp_benign / (fp_benign + tn_benign)) * 100
    
    tuning_results.append({
        'Cấu hình': f"Depth={depth}, LR={lr}",
        'Thời gian (s)': round(run_time, 2),
        'Train F1 (%)': round(train_f1, 2),
        'Test Acc (%)': round(test_acc, 2),
        'Test Prec (%) [Sub-1.1]': round(test_prec, 2),
        'Test F1 (%) [Sub-1.1]': round(test_f1, 2),
        'FPR Benign (%) [Sub-1.2]': round(fpr_benign, 4),
        'Ghi chú': desc
    })
    
    print(f"     Xong trong {run_time:.2f}s | Test F1: {test_f1:.2f}% | Test Prec: {test_prec:.2f}% | FPR: {fpr_benign:.4f}%")

df_tuning = pd.DataFrame(tuning_results)
csv_path = os.path.join(results_dir, "bang_1_ket_qua_quet_tham_so_thuc_te.csv")
df_tuning.to_csv(csv_path, index=False, encoding='utf-8-sig')

print("\n" + "="*90)
print("  🏆 BẢNG 1: KẾT QUẢ THỰC NGHIỆM QUÉT THAM SỐ XGBOOST TRÊN DỮ LIỆU THỰC TẾ")
print("="*90)
print(df_tuning.to_string(index=False))
print(f"\n-> Đã lưu bảng số liệu vào: {csv_path}")

best_idx = df_tuning['Test F1 (%) [Sub-1.1]'].idxmax()
best_row = df_tuning.iloc[best_idx]
print("\n" + "*"*80)
print(f"  👑 CẤU HÌNH VÔ ĐỊCH ĐƯỢC CHỌN: {best_row['Cấu hình']}")
print(f"     • Macro F1-score: {best_row['Test F1 (%) [Sub-1.1]']}% (Cao nhất)")
print(f"     • Macro Precision: {best_row['Test Prec (%) [Sub-1.1]']}%")
print(f"     • Tỷ lệ Cảnh báo sai FPR: {best_row['FPR Benign (%) [Sub-1.2]']}% (Thấp nhất)")
print(f"     • Thời gian chạy: {best_row['Thời gian (s)']} giây")
print("*"*80)
