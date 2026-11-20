# Tổng hợp M0: tình trạng, nguyên nhân, kế hoạch (cập nhật 20/11/2026)

Phạm vi: chỉ model M0 (XGBoost 15 lớp, RQ1) với bộ trích Java CICFlowMeter trong thư mục Java_CICFlowMeter_M0_Trial. Doc cũ về M1 và bộ trích Python viết trước đó đã được cập nhật ở đây.

## 1. Kết luận ngắn

M0 đạt gần 100% trên test set dataset và nhận tốt GoldenEye trong lab, nhưng bỏ sót SSH, Slowloris, LOIC lab, nhầm loại Hulk-Go, và báo tấn công cho 38,0% flow Wi-Fi thường. Đây là hiện tượng chênh lệch giữa benchmark offline và triển khai thực tế, không phải lỗi mã nguồn của pipeline.

## 2. Kết quả M0 (bộ trích Java)

| Kịch bản | Kết quả |
|---|---|
| HOIC, test set dataset | 59.580/59.580 đúng (100%) |
| LOIC-HTTP, test set dataset | 51.327/51.354 đúng (99,95%) |
| GoldenEye lab, mức đầu | 5.013/5.112 gán GoldenEye (98,06%) |
| GoldenEye lab, tăng tải | 7.173/7.606 (94,31%) |
| Hulk-Go lab, tăng tải (2.475 flow) | 5 Hulk (0,20%), 1.301 HOIC (52,6%), 719 GoldenEye (29,1%), 450 Benign (18,2%) |
| Slowloris lab (36 flow) | 0 Slowloris, 33 Benign (91,7%), 3 Hulk |
| LOIC-HTTP lab (52.641 flow) | 0 LOIC-HTTP, 22.323 Hulk (42,4%), 21.302 Benign (40,5%), 9.016 HOIC (17,1%) |
| SSH Hydra (ssbrute) | 5/5 flow cổng 22 là Benign |
| SSH Patator (ss2) | 3 flow chính đều Benign, 99,31 đến 99,45% |
| Wi-Fi do người dùng xác nhận là traffic thường (284 flow) | 108 flow bị báo tấn công (38,0%): 68 Hulk, 40 HOIC |

Giới hạn: các tỉ lệ lab là tỉ lệ nhãn dự đoán trùng tên công cụ, chưa phải recall hay FPR chuẩn, vì chưa có nhãn từng flow và flow nền còn lẫn trong PCAP. Số Wi-Fi dựa trên mô tả của người dùng.

## 3. Ba loại lỗi

Bỏ sót: SSH, Slowloris, LOIC lab, một phần Hulk-Go bị báo Benign.
Báo nhầm: 108/284 flow Wi-Fi thường. Với bản trích Python, 106/107 flow curl thường ở port 80 bị báo Hulk (99,07%).
Nhầm loại: Hulk-Go bị gán thành HOIC và GoldenEye.

## 4. Nguyên nhân và bằng chứng

Đã đo được:
1. Bộ trích Python và Java cho kết quả khác nhau trên cùng PCAP. Với HTTP-CPU025-02, Python gán Hulk cho 378/378 flow, Java gán Hulk cho 0/378, và 377/378 cặp flow ghép được bị đổi nhãn. Trên các cặp ghép, 62 đến 63/78 đặc trưng có ít nhất một giá trị khác, các cột độ dài gói lệch khoảng 54 đến 66 byte. Chưa xác định bản nào gần dataset hơn nếu thiếu nhãn từng flow.
2. Dấu vân tay môi trường: cửa sổ TCP khởi tạo của lab là 64240, còn train M0 lớp Hulk có giá trị 225 (149.577 mẫu), 26.883 (5.020 mẫu), 0 (445 mẫu), không có 64240. SHAP cho thấy Init Fwd Win Byts đẩy điểm HOIC trong nhiều ca.
3. Hành vi công cụ khác dataset: Hulk-Go dùng keep-alive, 285/323 stream có nhiều request, trung vị flow live 30 gói đi và 133.248 micro giây, khác Hulk train (trung vị 2 gói đi). Slowloris lab dài khoảng 19,5 đến 21 giây, train trung vị 106,3 giây. Hydra và Patator tạo ít flow chính, khác cấu hình dataset.
4. Cảnh báo trên Wi-Fi thường chịu ảnh hưởng của FIN Flag Cnt: 60/68 flow Hulk có FIN=2, 8 flow có FIN=1.

Đã loại trừ:
- Không có lỗi cơ học: đơn vị thời gian, ánh xạ 78 cột, thứ tự cột, NaN/Inf đều đúng.
- Sửa đếm PSH theo chiều không đủ để nhận SSH (M0 xác suất SSH vẫn khoảng 0,16 đến 0,20%).
- Đổi sang bộ trích Java loại bỏ kiểu lỗi "mọi flow port 80 thành Hulk" của bản Python nhưng không làm M0 nhận được SSH hay Slowloris.

Chưa kiểm chứng: Java đang dùng chưa chắc trùng bản đã tạo dataset 2018; chưa có cặp PCAP và CSV gốc của dataset để chứng nhận tương đương.

## 5. Kế hoạch M0_lab_v1 và chỉnh sửa đề xuất

Kế hoạch gốc: huấn luyện lại XGBoost bằng train gốc của M0 cộng flow tấn công lab (SSH, GoldenEye, Hulk-Go, Slowloris, LOIC-HTTP), gán nhãn theo kịch bản, chia theo lượt, giữ nguyên test gốc, không ghi đè M0.

Bốn chỉnh sửa cần có:
1. Thêm Benign lab: dùng flow nền không thuộc kịch bản trong PCAP, 284 flow Wi-Fi thường (giữ một phần làm test), T3 784 flow, và nên thu thêm 5 đến 10 phút Benign Kali sang Ubuntu. Không có Benign lab thì model có thể học "dấu vân tay lab là tấn công" và tăng báo nhầm.
2. Đối chứng dấu vân tay môi trường: huấn luyện thêm một nhánh bỏ nhóm đặc trưng môi trường rồi so sánh.
3. Số phiên không đủ cho một số lớp (SSH Patator 3 flow chính, Slowloris 36 flow, LOIC một lượt): ghi rõ lớp nào chỉ dùng để test, giới hạn số flow mỗi lượt, báo kết quả theo từng lượt.
4. Sửa extractor phải khớp quy ước train M0 (độ lệch chuẩn mẫu, Down/Up Ratio chia nguyên, cờ 0/1), không chỉ đúng ngữ nghĩa.

Phép kiểm tra báo nhầm bắt buộc: 284 flow Wi-Fi thường, mức nền hiện tại là 38,0%.

## 6. Gợi ý trình bày

Câu chuyện chính: M0 đạt 99,95 đến 100% trên dataset nhưng chỉ nhận một số tấn công lab và báo nhầm 38,0% traffic thường. Chuỗi bằng chứng: pipeline không lỗi, bộ trích khác nhau 62 đến 63/78 đặc trưng, môi trường và công cụ khác dataset. Thí nghiệm khắc phục: huấn luyện bổ sung dữ liệu lab kèm Benign lab, chia theo lượt. Nên nêu GoldenEye 94 đến 98% như điểm mạnh, các ca còn lại là giới hạn có số liệu.

Không nên khẳng định: bộ trích là nguyên nhân duy nhất; 38,0% là FPR chuẩn; kết quả lab tổng quát cho môi trường khác.

## 7. Tài liệu cần lưu ý

BaoCao_IDS_M1_M0.docx (viết 17/11) còn mục nói chưa có PCAP và chưa thử Java, nay đã lỗi thời. Bản gần nhất cho M0 là Java_CICFlowMeter_M0_Trial/bcao_tancon.docx (11 trang, 19 ảnh).
