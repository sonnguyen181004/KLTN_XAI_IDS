# RQ1 – Cách 1: độ ổn định và chẩn đoán overfit/underfit của XGBoost

Cấu hình cố định: max_depth=8, learning_rate=0.08, n_estimators=100, tree_method=hist (đúng mô hình chính thức). Không chọn lại siêu tham số, mô hình chính thức trong saved_models/ không bị thay đổi.

## 1. Dòng trùng và nhãn mâu thuẫn (train + test)

| Chỉ số | Giá trị |
|---|---|
| Tổng số dòng | 3,500,000 |
| Số vector đặc trưng khác nhau | 2,655,542 |
| Dòng trùng hoàn toàn (cùng đặc trưng, cùng nhãn) | 828,570 (23.67%) |
| Dòng có nhãn mâu thuẫn (cùng đặc trưng, khác nhãn) | 190,548 (5.444%) |
| Dòng test giống hệt một dòng train (tập chia chính thức) | 194,149 (27.74%) |
| Trần accuracy lý thuyết | 99.207% |

Trần accuracy là mức cao nhất mà bất kỳ mô hình nào đạt được khi chỉ nhìn 78 đặc trưng: với một vector xuất hiện dưới nhiều nhãn, mô hình chỉ đoán đúng được nhãn chiếm đa số.

Theo từng lớp (xếp theo tỷ lệ mâu thuẫn nhãn):

| Lớp | Số dòng | Trùng hoàn toàn % | Mâu thuẫn nhãn % | Trần recall % | Test trùng train % |
|---|---|---|---|---|---|
| DoS attacks-SlowHTTPTest | 8,673 | 99.41 | 99.98 | 39.86 | 100.00 |
| FTP-BruteForce | 17,535 | 99.70 | 99.95 | 91.83 | 100.00 |
| Infilteration | 71,573 | 9.26 | 30.74 | 81.51 | 29.82 |
| SQL Injection | 87 | 3.45 | 9.20 | 93.10 | 23.53 |
| Benign | 2,450,000 | 17.22 | 5.81 | 99.95 | 20.49 |
| Brute Force -Web | 609 | 9.20 | 3.12 | 100.00 | 13.11 |
| Brute Force -XSS | 230 | 0.87 | 0.43 | 100.00 | 2.17 |
| SSH-Bruteforce | 52,285 | 19.69 | 0.01 | 99.99 | 20.01 |
| Bot | 125,812 | 48.55 | 0.00 | 100.00 | 49.12 |
| DDOS attack-HOIC | 297,900 | 65.00 | 0.00 | 100.00 | 72.42 |
| DDOS attack-LOIC-UDP | 1,730 | 0.00 | 0.00 | 100.00 | 0.00 |
| DDoS attacks-LOIC-HTTP | 256,771 | 0.08 | 0.00 | 100.00 | 0.12 |
| DoS attacks-GoldenEye | 18,468 | 0.06 | 0.00 | 100.00 | 0.08 |
| DoS attacks-Hulk | 193,802 | 56.05 | 0.00 | 100.00 | 68.44 |
| DoS attacks-Slowloris | 4,525 | 3.20 | 0.00 | 100.00 | 3.65 |

Các nhóm nhãn hay dùng chung một vector đặc trưng (số vector):

| Nhóm nhãn | Số vector |
|---|---|
| Benign | Infilteration | 15,828 |
| DoS attacks-SlowHTTPTest | FTP-BruteForce | 46 |
| Brute Force -Web | SQL Injection | 5 |
| DoS attacks-SlowHTTPTest | FTP-BruteForce | SSH-Bruteforce | 3 |
| Benign | Brute Force -Web | 2 |
| Brute Force -XSS | SQL Injection | 1 |

## 2. Cross-validation 5 fold trên tập train (tập test chính thức không dùng)

Giá trị: trung bình ± độ lệch chuẩn qua các fold, đơn vị %.

| Chỉ số | Phần train của fold | Validation | Validation sạch | Chính thức RQ1 (test) |
|---|---|---|---|---|
| Accuracy | 97.93 ± 0.00 | 97.90 ± 0.01 | 98.17 ± 0.01 | 97.91 |
| Macro Precision | 92.95 ± 0.11 | 92.18 ± 0.21 | 90.01 ± 5.48 | 90.84 |
| Macro Recall | 87.07 ± 0.18 | 84.49 ± 0.79 | 82.64 ± 4.54 | 83.99 |
| Macro F1 | 88.54 ± 0.12 | 86.63 ± 0.59 | 85.00 ± 4.76 | 85.81 |
| FPR (báo động giả) | 0.222 ± 0.004 | 0.238 ± 0.013 | 0.270 ± 0.013 | 0.232 |
| FNR (bỏ sót) | 5.73 ± 0.02 | 5.79 ± 0.03 | 7.01 ± 0.03 | 5.75 |

Validation sạch: bỏ các dòng validation giống hệt một dòng train của cùng fold (trung bình 26.8% số dòng validation).

**Đọc kết quả:**

- Độ ổn định: Macro F1 validation dao động 0.59 điểm giữa các fold (thấp nhất 85.75, cao nhất 87.15), mô hình ổn định.
- Overfit: Macro F1 trên phần train cao hơn validation trung bình 1.91 điểm, không có dấu hiệu overfit đáng kể (quy ước: ≤ 2 điểm là không đáng kể, 2–5 điểm là nhẹ, > 5 điểm là rõ).
- Underfit: Macro F1 ngay trên phần train chỉ đạt 88.54%, tức mô hình chưa khớp được một số lớp ngay cả trên dữ liệu đã học. Bảng theo lớp bên dưới cho biết đó là lớp nào; đối chiếu với tỷ lệ mâu thuẫn nhãn ở mục 1.

- So với tập test chính thức: Macro F1 test = 85.81%, nằm trong khoảng trung bình ± 2 độ lệch chuẩn của CV (85.45–87.81).

F1 theo từng lớp (%, trung bình qua các fold):

| Lớp | Mẫu val | Train F1 | Val F1 | ± std | Val sạch F1 | Chênh | Mâu thuẫn % | Trần recall % | Nhận xét |
|---|---|---|---|---|---|---|---|---|---|
| Infilteration | 57,258 | 26.14 | 25.04 | 0.49 | 30.69 | 1.10 | 30.74 | 81.51 | Underfit: train cũng thấp (do mâu thuẫn nhãn) |
| DoS attacks-SlowHTTPTest | 6,938 | 51.87 | 51.64 | 1.25 | 0.00 | 0.23 | 99.98 | 39.86 | Underfit: train cũng thấp (do mâu thuẫn nhãn) |
| SQL Injection | 70 | 94.78 | 76.58 | 7.91 | 78.33 | 18.20 | 9.20 | 93.10 | Overfit: train cao, val thấp (lớp rất ít mẫu) |
| Brute Force -Web | 487 | 81.44 | 77.53 | 2.19 | 74.41 | 3.92 | 3.12 | 100.00 | Underfit: train cũng thấp |
| FTP-BruteForce | 14,028 | 83.01 | 82.90 | 0.36 | 0.00 | 0.11 | 99.95 | 91.83 | Underfit: train cũng thấp (do mâu thuẫn nhãn) |
| Brute Force -XSS | 184 | 96.93 | 93.70 | 2.12 | 94.15 | 3.23 | 0.43 | 100.00 | Tốt |
| DDOS attack-LOIC-UDP | 1,384 | 95.28 | 93.74 | 0.99 | 93.74 | 1.55 | 0.00 | 100.00 | Tốt |
| Benign | 1,960,000 | 98.68 | 98.66 | 0.00 | 98.82 | 0.02 | 5.81 | 99.95 | Tốt |
| DoS attacks-Slowloris | 3,620 | 99.99 | 99.82 | 0.14 | 99.81 | 0.17 | 0.00 | 100.00 | Tốt |
| DoS attacks-GoldenEye | 14,774 | 99.99 | 99.95 | 0.05 | 99.95 | 0.04 | 0.00 | 100.00 | Tốt |
| DDoS attacks-LOIC-HTTP | 205,417 | 99.97 | 99.95 | 0.00 | 99.95 | 0.01 | 0.00 | 100.00 | Tốt |
| SSH-Bruteforce | 41,828 | 100.00 | 99.99 | 0.01 | 99.99 | 0.01 | 0.01 | 99.99 | Tốt |
| Bot | 100,650 | 100.00 | 99.99 | 0.00 | 99.99 | 0.01 | 0.00 | 100.00 | Tốt |
| DoS attacks-Hulk | 155,042 | 100.00 | 100.00 | 0.00 | 99.99 | 0.00 | 0.00 | 100.00 | Tốt |
| DDOS attack-HOIC | 238,320 | 100.00 | 100.00 | 0.00 | 100.00 | 0.00 | 0.00 | 100.00 | Tốt |

Quy ước nhận xét: Train F1 < 90% là underfit (mô hình chưa khớp được lớp này ngay trên dữ liệu đã học); Train F1 – Val F1 > 5 điểm là overfit; còn lại là tốt.

## 3. Đường cong loss mở rộng tới 300 cây (fold 0)

Cấu hình giữ nguyên, chỉ kéo dài số cây để xem điều gì xảy ra sau mốc 100 cây đang dùng.

| Số cây | Train F1 | Val F1 | Val Accuracy | Val FPR | Val FNR |
|---|---|---|---|---|---|
| 10 | 71.04 | 72.29 | 97.60 | 0.014 | 7.256 |
| 25 | 82.47 | 82.96 | 97.85 | 0.169 | 6.128 |
| 50 | 86.99 | 85.69 | 97.89 | 0.215 | 5.907 |
| 75 | 87.65 | 86.26 | 97.91 | 0.216 | 5.835 |
| 100 | 87.78 | 86.31 | 97.91 | 0.231 | 5.800 |
| 150 | 87.87 | 86.36 | 97.91 | 0.246 | 5.755 |
| 200 | 88.01 | 86.28 | 97.91 | 0.259 | 5.724 |
| 250 | 87.92 | 86.30 | 97.91 | 0.263 | 5.715 |
| 300 | 87.96 | 86.25 | 97.91 | 0.268 | 5.701 |

**Đọc kết quả:** Loss validation còn giảm sau 100 cây (thấp nhất ở cây 300, thấp hơn mức ở 100 cây 3.70%): 100 cây hơi ít, mô hình còn có thể khớp thêm (underfit nhẹ theo số cây).

## 4. Learning curve (fold 0)

Huấn luyện cùng cấu hình trên một phần dữ liệu train của fold 0, đo trên cùng phần validation.

| Tỷ lệ dữ liệu | Số dòng train | Train F1 | Val F1 | Val Accuracy | Val FPR | Val FNR |
|---|---|---|---|---|---|---|
| 5% | 112,002 | 87.51 | 78.44 | 97.85 | 0.306 | 5.780 |
| 10% | 224,001 | 88.01 | 81.63 | 97.87 | 0.303 | 5.740 |
| 25% | 560,002 | 88.75 | 84.13 | 97.90 | 0.247 | 5.777 |
| 50% | 1,120,000 | 88.83 | 85.18 | 97.90 | 0.254 | 5.776 |
| 100% | 2,240,000 | 88.73 | 86.31 | 97.91 | 0.231 | 5.800 |

**Đọc kết quả:** Tăng dữ liệu từ 50% lên 100% làm val F1 thay đổi 1.12 điểm. Val F1 còn tăng rõ: thêm dữ liệu (nhất là lớp hiếm) có thể còn giúp. Khoảng cách train–val ở mức 100% là 2.43 điểm, khoảng cách còn rộng: có phần overfit hoặc lớp hiếm quá ít mẫu.

Cách đọc: hai đường cùng thấp và sát nhau là underfit; hai đường cách xa nhau và đường validation còn đi lên là overfit hoặc thiếu dữ liệu; hai đường cao và sát nhau là tốt.

## 5. Chia lại 80/20 với 5 seed (gộp train + test)

Giá trị: trung bình ± độ lệch chuẩn [khoảng tin cậy 95%], đơn vị %.

| Chỉ số | Test đầy đủ | Test sạch | Chính thức RQ1 |
|---|---|---|---|
| Accuracy | 97.90 ± 0.01 [±0.01] | 98.19 ± 0.01 [±0.02] | 97.91 |
| Macro Precision | 91.99 ± 0.89 [±1.10] | 90.29 ± 4.62 [±5.74] | 90.84 |
| Macro Recall | 84.46 ± 0.39 [±0.48] | 82.75 ± 3.70 [±4.59] | 83.99 |
| Macro F1 | 86.51 ± 0.43 [±0.53] | 85.17 ± 4.04 [±5.02] | 85.81 |
| FPR (báo động giả) | 0.243 ± 0.005 [±0.006] | 0.277 ± 0.004 [±0.005] | 0.232 |
| FNR (bỏ sót) | 5.79 ± 0.02 [±0.03] | 6.91 ± 0.07 [±0.08] | 5.75 |

Test sạch: bỏ các dòng test giống hệt một dòng train (trung bình 27.8% số dòng test).

**Đọc kết quả:** kết quả chính thức Macro F1 85.81% nằm ngoài khoảng các lần chia lại (86.09–87.01). Độ lệch chuẩn 0.43 điểm cho thấy cách chia ngẫu nhiên ảnh hưởng rất ít tới kết quả. Bỏ dòng trùng làm Macro F1 giảm 1.34 điểm: một phần điểm trên test đầy đủ đến từ các dòng mô hình đã thấy y hệt khi train.

Kiểm tra tái lập với lần chạy cũ (3_repeat_resplits.py, cùng seed):

| Seed | F1 cũ | F1 lần này | F1 sạch cũ | F1 sạch lần này |
|---|---|---|---|---|
| 1 | 86.09 | 86.09 | 78.19 | 83.78 |
| 2 | 86.92 | 86.92 | 78.32 | 83.91 |
| 3 | 86.23 | 86.23 | 79.84 | 79.84 |

## 6. Tóm tắt

- Lớp underfit (train F1 < 90%): Brute Force -Web, DoS attacks-SlowHTTPTest, FTP-BruteForce, Infilteration.
- Lớp overfit (train cao hơn val > 5 điểm): SQL Injection.
- Các lớp còn lại được học tốt và tổng quát hóa tốt.
- Mọi kết luận trên dựa trên cấu hình cố định của mô hình chính thức; mô hình đã lưu không bị thay đổi.
