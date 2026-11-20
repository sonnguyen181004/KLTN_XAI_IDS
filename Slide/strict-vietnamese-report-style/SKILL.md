---
name: strict-vietnamese-report-style
description: Viết mới, biên tập hoặc kiểm tra report và đoạn văn tiếng Việt theo văn phong trực tiếp, cụ thể, có căn cứ; loại bỏ dấu vết chatbot, sáo ngữ, cấu trúc công thức và ký hiệu định dạng không phù hợp. Dùng khi người dùng yêu cầu văn bản tiếng Việt tự nhiên, nghiêm túc hoặc muốn kiểm tra các dấu hiệu thường gắn với nội dung AI. Không dùng để cam kết vượt qua công cụ phát hiện AI hoặc che giấu hành vi gian lận.
---

# Văn phong báo cáo tiếng Việt nghiêm ngặt

## Mục tiêu bắt buộc

Tạo văn bản có nội dung cụ thể, mạch lập luận rõ, giọng văn phù hợp người dùng và không còn dấu vết của câu trả lời chatbot. Không được tuyên bố văn bản là do con người viết, không thể bị nhận diện, hoặc chắc chắn vượt qua công cụ phát hiện AI.

## Quy trình

1. Xác định mục đích, người đọc, độ dài, ngôi xưng và dữ liệu người dùng cung cấp. Không tự bịa trải nghiệm, số liệu, nguồn, tác giả, khảo sát hoặc kết quả nghiên cứu.
2. Nếu người dùng cung cấp bản nháp, giữ nguyên ý và thông tin có căn cứ. Chỉ thay đổi nội dung khi họ yêu cầu.
3. Soạn câu trực tiếp, ưu tiên chủ thể và hành động cụ thể. Mỗi đoạn phải có một nhiệm vụ rõ ràng trong lập luận.
4. Đọc toàn bộ [danh mục kiểm soát](references/strict-rules.md) trước khi viết hoặc biên tập. Áp dụng các lệnh cấm, giới hạn và ngoại lệ ở đó.
5. Sau khi soạn, tự kiểm tra theo ba lượt: tính đúng và đủ; ngôn ngữ và lập luận; ký hiệu và định dạng.
6. Với văn bản dài hơn 150 từ, lưu bản nháp tạm và chạy `python scripts/lint_vietnamese_report.py <file>`. Sửa tất cả lỗi mức `ERROR`. Xem từng cảnh báo `WARN` trong ngữ cảnh và sửa nếu không thuộc ngoại lệ.
7. Chỉ giao phần văn bản người dùng yêu cầu. Không thêm lời dẫn kiểu trợ lý, nhận xét về quá trình viết hoặc câu mời người dùng hỏi tiếp, trừ khi người dùng yêu cầu giải thích.

## Tiêu chuẩn đạt

Văn bản chỉ được coi là hoàn tất khi thỏa mãn tất cả điều kiện sau:

- Không có câu giao tiếp của chatbot, chỗ giữ nội dung, cú pháp Markdown bị lộ, emoji trang trí, mũi tên hoặc dấu gạch ngang dài.
- Không có câu sáo rỗng chỉ làm đầy độ dài. Mọi nhận định quan trọng phải được giải thích, minh họa, định nghĩa hoặc gắn với bằng chứng đã có.
- Không lặp lại cùng một ý bằng cách đổi từ.
- Không dùng cấu trúc ba phần, hai mặt hoặc kết luận cân bằng một cách máy móc nếu nội dung không đòi hỏi.
- Không tạo trích dẫn hay số liệu giả. Khi thiếu dữ liệu cần thiết, nói rõ giới hạn bằng một câu ngắn hoặc dùng chỗ trống chỉ khi người dùng yêu cầu mẫu.
- Không có lỗi `ERROR` từ bộ kiểm tra. Cảnh báo còn lại phải thuộc ngoại lệ có lý do rõ ràng.

## Ngoại lệ

Không được làm sai kiến thức hoặc phá hỏng quy ước chuyên môn chỉ để tuân thủ hình thức. Giữ ký hiệu bắt buộc trong công thức, mã nguồn, URL, trích dẫn nguyên văn, tên chính thức, tiêu chuẩn kỹ thuật và tài liệu tham khảo. Tách các phần này khỏi văn xuôi nếu có thể. Không tự ý sửa lời trích dẫn của nguồn.
