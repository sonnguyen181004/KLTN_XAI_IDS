# Tiến độ

| Bước | Trạng thái | Bằng chứng |
|---|---|---|
| 1. Kiểm kê M0 và PCAP | Xong 19/11 | `manifests/pcaps.csv`, `results/extraction_audit/inventory.json` |
| 2. Extractor Java | Xong 19/11: chênh packet giải thích đủ, cột cờ khác quy ước | `results/extraction_audit/packet_accounting.json`, `flag_convention.json` |
| 3. Gán nhãn, chia lượt | Xong 19/11 | `manifests/splits.csv`, `results/extraction_audit/rejected_flows.csv` (0 dòng) |
| 4. Huấn luyện tiếp v1 | Xong 19/11 | `configs/continue_v1.yaml`, `models/*/training_info.json` (không trong git) |
| 5. Đánh giá | Xong 19/11: v1 không dùng được, Benign test gốc bị báo tấn công toàn bộ | `results/adaptation/` |
| 6. Phương án tiếp | Chờ người dùng chọn | `docs/findings.md` mục 5 |
