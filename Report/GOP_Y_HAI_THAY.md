# Góp ý của hai thầy về đề tài

Nguồn: ghi chú buổi góp ý, đã sắp xếp lại. Chưa sửa mã nguồn hay báo cáo theo các ý này.

## 1. Các ý thầy nói

| # | Ý của thầy | Nghĩa là gì |
|---|---|---|
| 1 | SHAP có 5 đặc trưng nổi bật, LIME chỉ 1 | Hai phương pháp tính ảnh hưởng khác nhau nên kết quả khác nhau. LIME vẫn dùng các đặc trưng khác, chỉ là trọng số nhỏ hơn. Cần giải thích được khi bị hỏi. |
| 2 | Không so sánh thuật toán để chọn cái tốt nhất | Phải chạy nhiều dữ liệu, nhiều trường hợp mới kết luận được cái nào tốt hơn. Chọn XGBoost rồi train, test, đưa vào ứng dụng thực tế. |
| 3 | Phải có hệ thống xâm nhập rồi mới làm phát hiện xâm nhập | Cần máy tấn công, máy nạn nhân và máy IDS. Có thêm máy IDS thì mới gọi là "hệ thống". |
| 4 | Tấn công nằm ngoài dataset thì lấy đâu ra | Tự tạo tình huống tấn công (chạy công cụ tấn công, kể cả tấn công do AI sinh ra), thu traffic thật, tăng độ khó dần. |
| 5 | IDS phát hiện và trả kết quả thì học máy mới "chạy" | Không cần chèn bước T3 để xác định đúng hay sai. Trọng tâm là IDS phát hiện, rồi XAI giải thích. |
| 6 | XGBoost chỉ phát hiện, XAI giải thích "tại sao" và "tấn công như thế nào" | SHAP cho thấy kiểu tấn công trong mô hình hệ thống. Không cần giải thích kết quả của XGBoost. |
| 7 | Sơ đồ phải là sơ đồ hệ thống, không phải flow các bước phần mềm | Vẽ kiến trúc: máy tấn công, mạng, bộ thu thập, trích đặc trưng, XGBoost nằm ở đâu và vai trò gì, rồi XAI và cảnh báo. |
| 8 | So sánh dữ liệu thực tế với dữ liệu có sẵn thì hay hơn | Đây là đóng góp nên giữ, đặt sau khi hệ thống chạy được. |

## 2. Cần cải thiện

1. Đổi scope: "xây dựng và đánh giá hệ thống IDS có giải thích", không còn là "so sánh thuật toán".
2. Bỏ hoặc hạ cấp phần so sánh thuật toán. Giữ một câu giải thích vì sao dùng XGBoost, hoặc đưa xuống phụ lục.
3. Dựng lab thật: máy tấn công, máy nạn nhân, máy IDS (bắt gói tin, trích đặc trưng, XGBoost, cảnh báo).
4. Tạo tấn công ngoài dataset, chạy nhiều lần, nhiều kịch bản, tăng độ khó dần. Phần này thay cho việc chèn T3.
5. Chuyển XAI sang giải thích hành vi tấn công: tấn công khác lưu lượng bình thường ở đặc trưng nào và diễn ra thế nào. Thêm đoạn giải thích vì sao SHAP và LIME khác nhau.
6. Vẽ lại sơ đồ kiến trúc hệ thống, ghi rõ XGBoost là bộ phát hiện, SHAP/LIME là bộ giải thích.
7. Giữ phần so sánh dữ liệu thực tế với dataset có sẵn.

## 3. Khung RQ đề xuất

- RQ1: Hệ thống IDS (lab tấn công, IDS, XGBoost) có phát hiện được tấn công thật không?
- RQ2: Mô hình train trên dataset có sẵn so với train trên dữ liệu thực tế tự thu thập khác nhau thế nào?
- RQ3: XAI có giải thích được vì sao và như thế nào một luồng bị coi là tấn công không?

## 4. Cần hỏi lại thầy

- "rough base" và "rough chạy AI tấn công" trong ghi chú chưa rõ. Có thể là "ground truth", "baseline" hoặc "red team".
- Hai thầy muốn mức độ nào cho phần dựng lab: giả lập trên máy ảo hay mạng vật lý.

## 5. Việc tiếp theo

- Đối chiếu `ids-lab/`, `ddos/`, `RQ3_IDS_System/` với khung trên để biết đã có gì, còn thiếu gì.
- Vẽ sơ đồ kiến trúc hệ thống.
- Viết lại scope và RQ trong báo cáo.
