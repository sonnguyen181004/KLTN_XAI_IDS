# Đối chiếu đủ 78 đặc trưng

Sinh từ stage19; schema khớp không đồng nghĩa ngữ nghĩa tương thích. Trạng thái dựa trên fixture và source đã kiểm tra. Java master chỉ là tham chiếu hiện tại, chưa xác nhận đúng binary V3 đã tạo dataset 2018.

| # | Đặc trưng model | Cột Python | Nhận định | Bằng chứng/giới hạn |
|---|---|---|---|---|
| 1 | Dst Port | dst_port | checked_fixture_only | Giá trị/đổi đơn vị khớp fixture đơn giao thức; chưa chứng nhận toàn bộ flow segmentation. |
| 2 | Protocol | protocol | checked_fixture_only | Giá trị/đổi đơn vị khớp fixture đơn giao thức; chưa chứng nhận toàn bộ flow segmentation. |
| 3 | Flow Duration | flow_duration | checked_fixture_only | Giá trị/đổi đơn vị khớp fixture đơn giao thức; chưa chứng nhận toàn bộ flow segmentation. |
| 4 | Tot Fwd Pkts | tot_fwd_pkts | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 5 | Tot Bwd Pkts | tot_bwd_pkts | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 6 | TotLen Fwd Pkts | totlen_fwd_pkts | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 7 | TotLen Bwd Pkts | totlen_bwd_pkts | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 8 | Fwd Pkt Len Max | fwd_pkt_len_max | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 9 | Fwd Pkt Len Min | fwd_pkt_len_min | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 10 | Fwd Pkt Len Mean | fwd_pkt_len_mean | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 11 | Fwd Pkt Len Std | fwd_pkt_len_std | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 12 | Bwd Pkt Len Max | bwd_pkt_len_max | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 13 | Bwd Pkt Len Min | bwd_pkt_len_min | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 14 | Bwd Pkt Len Mean | bwd_pkt_len_mean | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 15 | Bwd Pkt Len Std | bwd_pkt_len_std | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 16 | Flow Byts/s | flow_byts_s | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 17 | Flow Pkts/s | flow_pkts_s | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 18 | Flow IAT Mean | flow_iat_mean | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 19 | Flow IAT Std | flow_iat_std | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 20 | Flow IAT Max | flow_iat_max | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 21 | Flow IAT Min | flow_iat_min | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 22 | Fwd IAT Tot | fwd_iat_tot | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 23 | Fwd IAT Mean | fwd_iat_mean | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 24 | Fwd IAT Std | fwd_iat_std | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 25 | Fwd IAT Max | fwd_iat_max | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 26 | Fwd IAT Min | fwd_iat_min | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 27 | Bwd IAT Tot | bwd_iat_tot | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 28 | Bwd IAT Mean | bwd_iat_mean | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 29 | Bwd IAT Std | bwd_iat_std | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 30 | Bwd IAT Max | bwd_iat_max | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 31 | Bwd IAT Min | bwd_iat_min | confirmed_extractor_defect | Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0). |
| 32 | Fwd PSH Flags | fwd_psh_flags | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 33 | Bwd PSH Flags | bwd_psh_flags | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 34 | Fwd URG Flags | fwd_urg_flags | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 35 | Bwd URG Flags | bwd_urg_flags | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 36 | Fwd Header Len | fwd_header_len | definition_mismatch_reference | Python dùng header IPv4; Java tham chiếu dùng header transport; fixture UDP/options phân biệt được. |
| 37 | Bwd Header Len | bwd_header_len | definition_mismatch_reference | Python dùng header IPv4; Java tham chiếu dùng header transport; fixture UDP/options phân biệt được. |
| 38 | Fwd Pkts/s | fwd_pkts_s | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 39 | Bwd Pkts/s | bwd_pkts_s | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 40 | Pkt Len Min | pkt_len_min | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 41 | Pkt Len Max | pkt_len_max | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 42 | Pkt Len Mean | pkt_len_mean | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 43 | Pkt Len Std | pkt_len_std | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 44 | Pkt Len Var | pkt_len_var | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 45 | FIN Flag Cnt | fin_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 46 | SYN Flag Cnt | syn_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 47 | RST Flag Cnt | rst_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 48 | PSH Flag Cnt | psh_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 49 | ACK Flag Cnt | ack_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 50 | URG Flag Cnt | urg_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 51 | CWE Flag Count | cwr_flag_count | confirmed_extractor_defect | Cột CWR sao chép Fwd URG Flags; fixture tách CWR/URG xác nhận sai. |
| 52 | ECE Flag Cnt | ece_flag_cnt | support_mismatch | Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu. |
| 53 | Down/Up Ratio | down_up_ratio | definition_mismatch_reference | Python chia số thực và chịu lặp gói đầu; train chỉ quan sát số nguyên; Java tham chiếu chia nguyên. |
| 54 | Pkt Size Avg | pkt_size_avg | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 55 | Fwd Seg Size Avg | fwd_seg_size_avg | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 56 | Bwd Seg Size Avg | bwd_seg_size_avg | definition_mismatch_reference | Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê. |
| 57 | Fwd Byts/b Avg | fwd_byts_b_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 58 | Fwd Pkts/b Avg | fwd_pkts_b_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 59 | Fwd Blk Rate Avg | fwd_blk_rate_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 60 | Bwd Byts/b Avg | bwd_byts_b_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 61 | Bwd Pkts/b Avg | bwd_pkts_b_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 62 | Bwd Blk Rate Avg | bwd_blk_rate_avg | support_mismatch | Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning. |
| 63 | Subflow Fwd Pkts | subflow_fwd_pkts | definition_unverified | Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train. |
| 64 | Subflow Fwd Byts | subflow_fwd_byts | definition_unverified | Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train. |
| 65 | Subflow Bwd Pkts | subflow_bwd_pkts | definition_unverified | Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train. |
| 66 | Subflow Bwd Byts | subflow_bwd_byts | definition_unverified | Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train. |
| 67 | Init Fwd Win Byts | init_fwd_win_byts | sentinel_mismatch | Train có -1; Python khởi tạo 0 khi thiếu chiều/TCP, dùng 0 làm điều kiện cập nhật lại window. |
| 68 | Init Bwd Win Byts | init_bwd_win_byts | sentinel_mismatch | Train có -1; Python khởi tạo 0 khi thiếu chiều/TCP, dùng 0 làm điều kiện cập nhật lại window. |
| 69 | Fwd Act Data Pkts | fwd_act_data_pkts | confirmed_extractor_defect | Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc. |
| 70 | Fwd Seg Size Min | fwd_seg_size_min | definition_mismatch_reference | Python dùng header IPv4; Java tham chiếu dùng header transport; fixture UDP/options phân biệt được. |
| 71 | Active Mean | active_mean | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 72 | Active Std | active_std | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 73 | Active Max | active_max | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 74 | Active Min | active_min | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 75 | Idle Mean | idle_mean | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 76 | Idle Std | idle_std | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 77 | Idle Max | idle_max | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
| 78 | Idle Min | idle_min | confirmed_extractor_defect | Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow. |
