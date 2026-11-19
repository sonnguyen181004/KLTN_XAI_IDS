# Kết quả thử nghiệm huấn luyện tiếp M0 (19/11/2026)

## 1. Kiểm kê

Chín PCAP khớp mã băm với audit ngày 18/11 (`manifests/pcaps.csv`). M0: 15 lớp, 100 vòng, max_depth 8, eta 0.08, hist, seed 42. Thứ tự 78 đặc trưng của model khớp `train_set.parquet`. Môi trường: Python 3.14.7, XGBoost 3.4.1, scikit-learn 1.9.1, pandas 3.0.6.

## 2. Extractor Java (profile M0, upstream 98a5eba)

Chênh lệch packet giữa PCAP và flow được giải thích đầy đủ. Mô phỏng lại máy trạng thái `FlowGenerator.addPacket` trên bảng packet TShark cho đúng số flow và số packet theo từng cặp IP:cổng ở cả 9 PCAP (0 cặp lệch, `results/extraction_audit/packet_accounting.json`). Packet bị thiếu do hai quy tắc của extractor:

- FIN đầu tiên từ phía nhận đóng flow ngay (điều kiện trong mã là `getBwdFINFlags() + getBwdFINFlags() == 2`). Packet ACK cuối của phía gửi mở một flow mới có 1 packet, và flow 1 packet còn mở ở cuối file không được ghi. Ví dụ GoldenEye mức 1: 1.547 packet, Hulk-Go mức 2: 2.471 packet.
- FIN lặp lại ở cùng chiều bị bỏ (Hydra 1, GoldenEye mức 2: 4, LOIC 38).

Đây là quy ước vòng đời flow của bản Java này, không phải mất gói khi capture và không phải lỗi tính đặc trưng. Không sửa extractor trong đợt này, vì chưa xác minh được quy ước của extractor tạo dataset gốc.

Cột cờ khác quy ước (`results/extraction_audit/flag_convention.json`): train M0 chỉ có 0 hoặc 1 ở 12 cột cờ, Java ghi số đếm. M0 chỉ tách các cột cờ ở ngưỡng 1, nên đổi số đếm thành min(số đếm, 1) không đổi dự đoán nào của M0 trên 55.121 flow lab (sai khác xác suất lớn nhất 0). Bản chính dùng quy ước này, bản đối chứng giữ số đếm. Trong train gốc `Fwd PSH Flags` trùng `SYN Flag Cnt` và `RST Flag Cnt` gần trùng `ECE Flag Cnt`; Java lab không có quan hệ này. Chưa xử lý.

## 3. Gán nhãn và chia lượt

Flow TCP giữa Kali 192.168.11.133 và Ubuntu 192.168.11.134 trên cổng đích của lượt được gán nhãn kịch bản. Các PCAP HTTP không có request curl hoặc wget. 0 flow bị loại vì giá trị không hữu hạn. Chia theo lượt (`manifests/splits.csv`): lượt mức tải thấp vào train, lượt còn lại vào test; LOIC chỉ có một lượt nên chỉ dùng để test. Hai lượt không chồng thời gian, không PCAP nào trùng nội dung.

Train lab: GoldenEye 5.112, Hulk-Go 343, Slowloris 16, SSH 5 flow. Trọng số cân bằng theo lớp.

## 4. Huấn luyện tiếp

Thêm 20 vòng vào 100 vòng của M0, chỉ bằng flow tấn công lab, không có Benign (`configs/continue_v1.yaml`).

## 5. Kết quả

Lượt lab giữ lại (số flow đúng lớp trên tổng):

| Lượt test | M0 | v1 (cờ 0/1) | v1 cờ đếm |
|---|---:|---:|---:|
| GoldenEye mức 2 | 7.173/7.606 | 6.754/7.606 | 6.769/7.606 |
| Hulk-Go mức 2 | 5/2.475 | 2.416/2.475 | 2.418/2.475 |
| Slowloris mức 2 | 0/36 | 36/36 | 36/36 |
| SSH Patator | 1/4 | 4/4 | 4/4 |
| LOIC-HTTP (không có trong train) | 0/52.641 | 0/52.641 | 0/52.641 |

Tập test gốc (700.000 flow):

| | M0 | v1 | v1 cờ đếm |
|---|---:|---:|---:|
| Accuracy | 97,91% | 1,85% | 1,85% |
| Benign bị báo tấn công | 1.139/490.000 | 490.000/490.000 | 490.000/490.000 |
| Tấn công bị đoán Benign | 12.071/210.000 | 0/210.000 | 0/210.000 |

Kết luận: số đúng lớp trên lab tăng không phải cải thiện. Hai bản huấn luyện tiếp gán nhãn tấn công cho toàn bộ Benign của test gốc. Chỉ sau vòng 101, không còn mẫu Benign nào giữ nhãn Benign (kiểm trên 20.000 Benign lấy ngẫu nhiên).

Nguyên nhân đo được: không có mẫu Benign nào trong lượt huấn luyện tiếp, nên mọi lá của lớp Benign ở 20 cây mới đều âm hoặc bằng 0 (nhỏ nhất −11,9). Các lớp lab nhận lá dương tới +109,5, vì M0 cho các flow này xác suất gần 0 nên bước Newton không bị chặn. Cây mới áp dụng cho mọi đầu vào, không chỉ flow lab.

Thử đường tắt trên Benign của test gốc cho kết quả bão hòa (490.000/490.000 ở cả hai phép thử), nên chưa đo được riêng ảnh hưởng của `Init Fwd Win Byts` hay số đếm cờ. M0 với `Init Fwd Win Byts` = 64.240 báo 14.401/490.000.

Các số trên là phép đo trên các lượt đã ghi, không chứng minh khả năng nhận diện realtime. Chưa có Benign lab nên chưa đo được báo nhầm trong môi trường Kali và Ubuntu.

## 6. Lần 2 (v2): thêm dữ liệu ôn lại từ train gốc và chặn bước cập nhật

Cấu hình chốt trước khi chạy (`configs/continue_v2.yaml`): 20 vòng thêm; 200.001 dòng lấy từ train gốc theo đúng tỷ lệ 15 lớp (gồm Benign mà M0 đã học, không có Benign lab); flow tấn công lab thuộc lượt train với tổng trọng số mỗi lớp 5.000 và trọng số một dòng không quá 50; `max_delta_step` = 1. Không thử cấu hình khác theo kết quả test.

Lượt lab giữ lại (số flow đúng lớp trên tổng):

| Lượt test | M0 | v2 |
|---|---:|---:|
| GoldenEye mức 2 | 7.173/7.606 | 7.252/7.606 |
| Hulk-Go mức 2 | 5/2.475 | 280/2.475 |
| Slowloris mức 2 | 0/36 | 0/36 |
| SSH Patator | 1/4 | 0/4 |
| LOIC-HTTP (không có trong train) | 0/52.641 | 0/52.641 |

Hulk-Go mức 2 với v2: 175 flow thành Benign, 2.020 thành lớp tấn công khác (1.175 HOIC, 845 GoldenEye). Slowloris và SSH không đổi so với M0, kể cả trên chính lượt train (Slowloris mức 1: 0/16; Hydra: 0/5).

Tập test gốc (700.000 flow):

| | M0 | v2 |
|---|---:|---:|
| Accuracy | 97,91% | 97,90% |
| Benign bị báo tấn công | 1.139/490.000 | 1.225/490.000 |
| Tấn công bị đoán Benign | 12.071/210.000 | 12.001/210.000 |
| Dự đoán khác M0 | | 368 |

Thử đường tắt trên Benign của test gốc: đặt `Init Fwd Win Byts` = 64.240 thì M0 báo 14.401/490.000, v2 báo 14.476/490.000; đổi cờ 1 thành 2 thì M0 1.139, v2 1.225. v2 không tạo thêm phụ thuộc đáng kể vào hai yếu tố này.

Kết luận lần 2: v2 giữ được hành vi của M0 trên test gốc (thêm 86 Benign bị báo nhầm trên 490.000) nhưng học được ít từ lab. Cải thiện duy nhất trên lượt độc lập là Hulk-Go mức 2 (5 lên 280 trên 2.475). Slowloris (16 flow train) và SSH (5 flow train) quá ít mẫu để thay đổi quyết định khi trộn với 200.001 dòng ôn lại và bước cập nhật bị chặn. Đây là kết quả của một cấu hình; chưa đủ để nói huấn luyện tiếp không hiệu quả nói chung. Muốn kết luận cần thêm lượt lab cho mỗi loại (nhất là SSH và Slowloris) và một tập validation riêng để chọn mức trọng số, không chọn theo test.
