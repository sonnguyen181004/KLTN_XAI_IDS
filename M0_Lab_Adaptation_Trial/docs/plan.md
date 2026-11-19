# Kế hoạch

1. Giữ nguyên M0. Nạp bản sao để huấn luyện tiếp, không ghi đè.
2. Kiểm tra extractor Java, trích xuất PCAP tấn công đã có, gán nhãn theo kịch bản đã xác minh.
3. Chia train/test theo lượt trước khi học. Loại chỉ có một lượt (LOIC) chỉ dùng để test.
4. Huấn luyện tiếp từ M0, thêm vòng boosting bằng flow tấn công lab thuộc tập train. Giữ 78 đặc trưng, thứ tự cột và encoder 15 lớp. Chưa thêm Benign.
5. Lưu tại `models/m0_continued_v1/`.
6. So trước và sau trên lượt giữ lại (đúng lớp, nhầm lớp, bỏ sót thành Benign) và trên test gốc (Benign chỉ để đánh giá).
7. Ghi cấu hình, số vòng, dữ liệu, kết quả. Không thay model mặc định trên dashboard. Không push khi chưa được yêu cầu.

## Quyết định đã chốt

- Cột cờ: bản chính đổi số đếm Java thành có hoặc không (min(số đếm, 1)) cho khớp train M0; bản đối chứng giữ số đếm. Người dùng đồng ý ngày 19/11/2026.
- Extractor: giữ nguyên upstream 98a5eba; chênh lệch packet đã giải thích bằng quy tắc vòng đời flow.
- Chia lượt: mức tải thấp vào train, mức cao vào test; SSH: Hydra train, Patator test.
- Huấn luyện tiếp: 20 vòng, tham số như M0, trọng số cân bằng theo lớp, không tuning.
- Lần 2 (người dùng đồng ý 19/11): trộn 200.001 dòng ôn lại từ train gốc (gồm Benign M0 đã học), `max_delta_step` = 1, trọng số lab mỗi lớp 5.000, mỗi dòng tối đa 50.
