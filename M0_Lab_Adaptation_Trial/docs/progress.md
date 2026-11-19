# Tiến độ

| Bước | Trạng thái | Bằng chứng |
|---|---|---|
| 1. Kiểm kê M0 và PCAP | Xong 19/11 | `manifests/pcaps.csv`, `results/extraction_audit/inventory.json` |
| 2. Extractor Java | Xong 19/11: chênh packet giải thích đủ, cột cờ khác quy ước | `results/extraction_audit/packet_accounting.json`, `flag_convention.json` |
| 3. Gán nhãn, chia lượt | Xong 19/11 | `manifests/splits.csv`, `results/extraction_audit/rejected_flows.csv` (0 dòng) |
| 4. Huấn luyện tiếp v1 | Xong 19/11 | `configs/continue_v1.yaml`, `models/*/training_info.json` (không trong git) |
| 5. Đánh giá | Xong 19/11: v1 không dùng được, Benign test gốc bị báo tấn công toàn bộ | `results/adaptation/` |
| 6. Lần 2 (v2): ôn lại train gốc, chặn bước cập nhật | Xong 19/11: giữ được test gốc, học ít từ lab (Hulk-Go 5 lên 280/2.475; Slowloris, SSH không đổi) | `configs/continue_v2.yaml`, `results/adaptation/`, `docs/findings.md` mục 6 |
| 7. Tiếp theo | Cần thêm lượt lab SSH, Slowloris, LOIC và tập validation riêng | |
