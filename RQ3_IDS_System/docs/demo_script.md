# Kịch bản demo hệ thống IDS giải thích được (RQ3)

Dành cho người trình bày. Số liệu "mong đợi" lấy từ lần chạy thử ngày 20/10/2026 trên DB tạm với model thật. Mục nào ghi **chưa chạy thử** thì chưa có số đo, hãy chạy trước một lần.

## 0. Chuẩn bị (làm trước, không làm trên sân khấu)

DB demo đã reset trống ngày 20/10/2026 (bản sao lưu: `backups/before_reset_20261020_094428_demo_script/`). Mở 2 terminal tại thư mục `RQ3_IDS_System`:

```
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
python -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501
```

Mở `http://127.0.0.1:8501/`. Tắt: đóng tab trình duyệt trước, rồi nhấn Ctrl+C một lần.

Câu cần tránh: "độ chính xác của hệ thống", "tỷ lệ báo nhầm" (FPR). Lý do: traffic thật không có nhãn xác nhận; số cảnh báo chỉ là tỷ lệ cảnh báo.

## 1. Trạng thái hệ thống và màn hình trống

- **Thao tác:** mở trang, chưa nạp gì.
- **Thấy:** thanh trạng thái (API hoạt động, Model đã nạp 15 lớp, Capture chưa bật điều khiển, Hàng đợi SHAP 0/200). Thông báo "Không có flow khớp bộ lọc".
- **Nói:** luồng là flow hoàn tất → dự đoán → cảnh báo → SHAP chạy nền; LIME chỉ chạy khi người dùng yêu cầu.

## 2. Nạp CSV mẫu 15 lớp có nhãn

- **Dữ liệu:** `data/test_samples/test_sample100_15classes_with_label.csv` (105 flow, 7 flow mỗi lớp).
- **Thao tác:** tab «Nạp CSV / PCAP» → «CSV đặc trưng» → chọn file → «Gửi CSV vào /predict» (không tick «Đổi giây → micro giây»). Mất khoảng 1 phút.
- **Mong đợi:** 105 flow, 16 Benign, 89 cảnh báo, SHAP xong 89/89, nhánh A 43 và B 46 (dấu hiệu môi trường 43, lớp hiếm 4).
- **Nói thật về chất lượng:** chạy offline model trên đúng file này đạt khoảng 81,9% khớp nhãn. Các nhầm lẫn điển hình: Infilteration → Benign (5), SlowHTTPTest → FTP-BruteForce (5), Brute Force -Web → Benign (4), SQL Injection → Brute Force -Web (3). Đây là mẫu demo, không phải đánh giá chính thức; bảng nhãn thật của hệ thống không hiện nhãn này.

## 3. Giám sát và bộ lọc

- **Thấy:** thẻ số liệu (tổng, Benign, cảnh báo, SHAP), biểu đồ flow theo phút, phân bố nhãn, bảng flow tô màu.
- **Thao tác lọc (thanh bên):** Nhãn = `Bot`; tick «Chỉ cảnh báo»; Nhánh = «B · cần xem lại»; Nguồn = `csv_upload`.
- **Nói:** tỷ lệ cảnh báo (≈ 85% ở mẫu này vì mẫu cố ý nhiều tấn công) không phải FPR. Bảng giữ flow đang chọn khi tự làm mới 5 giây; tick «Tạm dừng tự làm mới» nếu cần đứng yên.

## 4. Chi tiết flow và SHAP

- **Case nên chọn:** một cảnh báo `Bot` (nhánh A).
- **Thấy:** nhãn, xác suất lớp thắng, «Vì sao nghi ngờ» (2 đặc trưng đẩy mạnh nhất, nói bằng lời), tab «SHAP tự động» (đỏ đẩy lên, xanh kéo xuống), «Đọc từng đặc trưng bằng lời», tab «Xác suất các lớp».
- **Nói:** SHAP ở thang raw margin, không phải phần trăm xác suất.

## 5. Nhánh A/B (phần cốt lõi, các case)

| Case | Lọc | Mong đợi | Ý nghĩa để nói |
|---|---|---|---|
| A bình thường | Nhãn `FTP-BruteForce` (11 flow, cả 11 là A) hoặc `Bot` (7/7 A) | Thẻ xanh «Giải thích bình thường» | Top-5 SHAP không nghiêng về đặc trưng nhạy môi trường, lớp đủ mẫu train |
| B do dấu hiệu môi trường | Nhãn `DoS attacks-Hulk` (7/7 B), `DDOS attack-HOIC` (7/7 B), `DoS attacks-Slowloris` (7/7 B), `SSH-Bruteforce` (7/7 B) | Thẻ cam, chip «Dấu hiệu môi trường: BẬT» | Model dựa nhiều vào đặc điểm mạng lab. Đây là giả thuyết, chưa kiểm chứng |
| B do lớp hiếm | Nhãn `SQL Injection` (4 flow B, 4 dấu hiệu lớp hiếm) | Chip «Dấu hiệu lớp hiếm: BẬT · 70 mẫu train» | Lớp chỉ có 70 mẫu train, dưới ngưỡng 100 |
| Cùng lớp, nhánh khác | Nhãn `Brute Force -Web` (A 2, B 4) hoặc `Brute Force -XSS` (A 2, B 5) | Mỗi flow tự ra nhánh theo SHAP của chính nó | Nhánh là thuộc tính của từng flow, không phải của lớp |

- **Thao tác cho mỗi case:** mở «Nhánh này được quyết định thế nào?» (4 bước với số thật), rồi «A/B là gì? Vì sao hệ thống có nhánh này?» (bảng 4 đặc trưng, độ quan trọng đo từ model, cột «Phản ánh môi trường lab?» = chưa kiểm chứng). Trong tab SHAP, đặc trưng có ⚠ là đặc trưng nhạy môi trường.
- **Câu bắt buộc nói:** nhánh B không có nghĩa là báo nhầm; nhánh A không có nghĩa là đúng; nhánh chỉ đổi cách hiển thị.

## 6. LIME theo yêu cầu (3 kết quả khác nhau)

Chọn đúng cảnh báo rồi bấm «Yêu cầu / kiểm tra lại LIME». Số dưới đây từ lần chạy thử:

| Case | Kết quả |
|---|---|
| `FTP-BruteForce` (nhánh A) | Hợp lệ, độ khớp R² 0,96 |
| `DoS attacks-GoldenEye` (nhánh B) | Hợp lệ, R² 0,97 |
| `DDOS attack-HOIC` hoặc `Bot` | Hợp lệ nhưng R² thấp (0,45), Jaccard@5 0,11: nói rõ đây là giải thích xấp xỉ yếu |
| `Brute Force -XSS` (một flow nhánh A) | «Không đủ tin cậy» (insufficient_neighborhood), không hiện R² |

- **Nói:** hệ thống ghi «Không đủ tin cậy» thay vì hiện kết quả sai. Chú thích trên nút LIME nêu số lần hợp lệ/đã chạy theo từng nguồn, lấy từ DB. Với traffic thật (realtime, PCAP) LIME thường không đủ tin cậy; SHAP vẫn dùng được.
- Jaccard@5 thấp cho thấy SHAP và LIME thường chọn Top-5 khác nhau, vì thế Agreement không được dùng làm tiêu chí nhánh.

## 7. Gợi ý «FIN + có dữ liệu» (báo nhầm Hulk)

- **Dữ liệu:** `data/samples/sample_hulk_fin_data.json` (flow Hulk có FIN do model báo trên traffic duyệt web thật). Không có nút nạp JSON, dùng PowerShell:

```
$body = Get-Content data\samples\sample_hulk_fin_data.json -Raw
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/predict?capture_run_id=demo-fin&run_name=Demo%20FIN" -ContentType "application/json" -Body $body
```

- **Thao tác:** «Làm mới ngay», chọn lượt «Demo FIN», mở flow Hulk.
- **Mong đợi:** nhãn Hulk, khung vàng «Gợi ý có thể báo nhầm» với số đếm lấy từ train (445/445 flow Hulk, 0 Benign; 9.815 flow Benign đóng FIN đều không gửi dữ liệu), nhánh B.
- **Nói:** đây là gợi ý, không phải kết luận; ngưỡng nằm trong `config.yaml`, số đếm tính trực tiếp từ file train.
- **Đối chiếu:** `sample_benign.json` cho Benign, không có cảnh báo; `sample_attack.json` cho một tấn công.

## 8. Lọc theo IP nguồn/đích và khoảng giờ (chuẩn bị cho demo tấn công)

- **Dữ liệu:** CSV có cột `src_ip` (ví dụ `data/live_phone_01.csv`, nạp với tick «Đổi giây → micro giây» và chọn múi giờ `+07:00`). **Chưa chạy thử** với file này.
- **Thao tác:** nhập một IP lấy từ cột «Nguồn» vào «IP nguồn»; chọn «Khoảng thời gian nhận» = «Tùy chọn (từ – đến)».
- **Nói:** lọc theo giờ API nhận flow, không phải giờ gói đầu tiên (lệch tới vài chục giây đến 90 giây); IP nguồn là bên gửi gói đầu của flow.

## 9. Phát lại PCAP

- **Dữ liệu:** `data/dashboard_uploaded_replay.pcap` hoặc `data/stage13_synthetic.pcap`.
- **Thao tác:** tab «PCAP đã ghi», chọn file, bấm gửi. Test tự động Stage14 đã kiểm bước này; **chưa chạy thử riêng cho kịch bản demo**.
- **Nói:** PCAP qua cùng bộ trích đặc trưng và cùng đường `/predict` như realtime.

## 10. Realtime thật (làm sau cùng, cần mạng và quyền)

- **Điều kiện:** đặt cùng `IDS_CAPTURE_CONTROL_TOKEN` (≥ 32 ký tự) cho API và dashboard rồi khởi động lại; cần Npcap và chạy với quyền phù hợp. Chi tiết: tab «Realtime», `docs/dashboard_usage.md`.
- **Thao tác:** bắt đầu bắt Wi-Fi, duyệt web 2–3 phút, dừng để ghi nốt.
- **Mong đợi (từ các lần đo trước, không phải cam kết):** flow đầu tiên xuất hiện sau tối đa 90 giây; đa số Benign; một phần cảnh báo Hulk nhánh B kèm gợi ý FIN. Tỷ lệ cảnh báo đo được từ 8% (20 phút) đến 23% (4 phút).
- **Nói:** đây là báo nhầm do lệch môi trường train–thực tế, không có nhãn thật nên không tính được FPR; hướng khắc phục là kế hoạch demo tấn công (E0–E4).

## 11. Khả năng dùng khi trình bày

- Tự làm mới 5 giây không làm mờ giao diện; nút «Tạm dừng tự làm mới» để đứng yên.
- Thu gọn «Dung lượng lưu trữ» (chỉ theo dõi, không tự xóa) và «Nhóm cảnh báo» (gom theo cặp IP/cổng/lớp, cửa sổ 5 phút) khi cần nói về vận hành.

## Thứ tự gợi ý (20 phút)

1 → 2 → 3 → 4 → 5 → 6 → 7, sau đó 8–10 tùy thời gian và điều kiện máy.
