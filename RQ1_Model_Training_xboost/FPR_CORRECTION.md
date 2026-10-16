# Đính chính FPR/FNR — 16/10/2026

## Quy ước

Ma trận có hàng là nhãn thật, cột là dự đoán. Attack (mọi lớp không phải Benign) là positive; Benign là negative.

- TN: Benign thật → Benign dự đoán.
- FP: Benign thật → bất kỳ lớp Attack nào.
- FN: Attack thật → Benign dự đoán.
- TP: Attack thật → bất kỳ lớp Attack nào, kể cả sai loại tấn công. Sai loại vẫn được tính trong báo cáo phân lớp, không phải bỏ sót nhị phân.
- FPR = FP / (FP + TN); FNR = FN / (FN + TP). Hàm `ids_detection_metrics` trả phần trăm; thiếu mẫu nhóm tương ứng trả NaN, không báo 0%.

## Số liệu đã lưu

Nguồn: `results/confusion_matrix_values.csv`, 15 lớp, 700.000 mẫu. Không train lại hoặc sửa confusion matrix.

| Chỉ số | Tử số | Mẫu số | Phần trăm |
|---|---:|---:|---:|
| FPR — Benign bị báo thành Attack | 1.139 | 490.000 | 0,2324% |
| FNR — Attack bị bỏ sót thành Benign | 12.071 | 210.000 | 5,7481% |

TN=488.861; TP=197.929. Công thức cũ dùng cột Benign thay vì hàng Benign và ghi nhầm tên FNR thành FPR. Số liệu chỉ áp dụng tập test này, không suy ra FPR traffic live.

## Phạm vi sửa

- Hai script RQ1 dùng chung hàm FPR/FNR; truyền đầy đủ thứ tự nhãn vào confusion_matrix.
- Script train lưu ma trận có nhãn để đối chiếu về sau.
- Bảng tổng hợp sửa FPR và giữ số cũ dưới tên FNR.
- Bảng tuning lịch sử chỉ đổi tên cột sai thành FNR, giữ nguyên số liệu. Không đủ ma trận/prediction từng cấu hình để tính FPR; không suy từ Accuracy/F1 đã làm tròn.
- Bỏ khẳng định FPR “thấp nhất” khi script chọn cấu hình theo Macro F1.
- Không thay model, encoder, DB hoặc SHAP/LIME; không huấn luyện lại.

## Kiểm thử

`python -B -m unittest discover -s RQ1_Model_Training_xboost -p test_ids_metrics.py`

Bao phủ ma trận nhiều lớp bất đối xứng, đổi thứ tự Benign, thiếu nhóm/không có lỗi, đầu vào không hợp lệ và ma trận đã lưu. NaN giúp phân biệt thiếu mẫu với tỷ lệ lỗi bằng 0.

## Giới hạn còn lại

- Tuning dùng test để chọn cấu hình; chưa sửa thiết kế train/validation/test trong thay đổi này.
- Đường dẫn huấn luyện cũ trong hai script chưa phù hợp bố cục hiện tại; không chạy chúng chỉ để cập nhật metric. Dùng lệnh kiểm thử trên, không kích hoạt train.
- Đã đính chính 4 DOCX XGBoost (báo cáo thực nghiệm, tổng hợp RF/XGBoost, giải thích chỉ số, cẩm nang) và báo cáo tổng hợp dataset 3.5M. Đổi tên cột tuning thành FNR; sửa FPR XGBoost thành 0.2324%; đánh dấu FPR RF chưa đối chiếu và bỏ kết luận chênh lệch không được xác minh. Các DOCX khác không có lỗi FPR này được giữ nguyên.
- Kiểm tra cấu trúc ZIP/XML và nội dung hoàn tất; không đổi ảnh, styles hoặc các part ngoài document.xml. Bản gốc lưu tại thư mục tạm `ids_fpr_word_qa/originals`, đồng thời bản tracked có thể khôi phục bằng Git. Render trực quan đang bị chặn vì bộ runtime thiếu LibreOffice/soffice.exe; chưa xác nhận bố cục từng trang sau sửa.
- PCAP chưa có ground truth xác minh không được dùng để tính FPR.
