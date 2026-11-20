# DDoS Learning Hub — Tài liệu Dự án toàn diện

> **Mục đích file này:** Cung cấp toàn bộ kiến thức, kiến trúc, cấu trúc code và hướng dẫn mở rộng của dự án để AI hoặc Developer có thể đọc qua và hiểu 100% ngữ cảnh dự án ngay lập tức.

---

## 1. Tổng quan dự án

- **Tên dự án:** DDoS Learning Hub
- **Mục tiêu:** Website học thuật trực quan giải thích tấn công DDoS (Distributed Denial of Service) bằng tiếng Việt với 8 demo mô phỏng tương tác thời gian thực, 100% demo có hệ thống Live Explanation giải thích thời gian thực, bảng 11 khái niệm cơ bản mạng (bao gồm thẻ IDS), Khung Chuyên sâu IDS (NIDS vs HIDS, Signature vs Anomaly & Lý do làm XAI-IDS), Sơ đồ Giải phẫu Chi tiết Gói tin Mạng 4 Lớp (Ethernet, IP Header, TCP Header + 4 TCP Flags `SYN/ACK/FIN/RST`, Payload), Bảng Soi chi tiết Packet đã chọn (chứa 2 Khung Chuyên sâu: Nguyên nhân IP bị lây nhiễm botnet & Lý do Hệ thống quyết định chặn), Khung Điều khiển SYN Flood tinh gọn tích hợp Thanh Dung lượng Hàng đợi `0/20`, bảng 10 khái niệm Machine Learning & XAI (đi kèm Khung Chuyên sâu Giải thích SHAP & LIME + Bảng so sánh 5 tiêu chí đối kháng), hồ sơ 4 tấn công thực tế, bảng so sánh công cụ phòng thủ Defense Trade-offs, và sơ đồ quy trình kiến trúc 5 bước của Hệ thống XAI-IDS.
- **Đối tượng:** Sinh viên CNTT, học viên An toàn thông tin, lập trình viên, nghiên cứu sinh bảo mật mạng.
- **Ngôn ngữ giao diện:** 100% tiếng Việt chuẩn văn phong học thuật, màu sắc phát sáng chuẩn Cyberpunk tương phản cao (High Contrast Neon Glow).
- **Triết lý thiết kế:** Dark Cyberpunk (xanh cyan neon `#00f5ff`, đỏ `#ff003c`, vàng `#ffd700`, xanh lá `#00ff88` trên nền tối `#0a0a0f`).

---

## 2. Tech Stack & Kiến trúc

- **HTML5:** Cấu trúc Single Page Application (SPA) không load lại trang.
- **CSS3:** Vanilla CSS thuần (không dùng Tailwind/Bootstrap), CSS Variables cho Design System, CSS Grid & Flexbox, Keyframe animations.
- **JavaScript:** ES6+ Vanilla JS (không dùng framework như React/Vue).
- **Canvas API:** HTML5 Canvas 2D render hiệu ứng hạt nền, bản đồ tấn công, packet stream và game mini.
- **Font chữ:** Google Fonts (`Orbitron` cho tiêu đề cyberpunk, `Inter` cho body text, `JetBrains Mono` cho thông số/code).
- **Không dùng backend/build tools:** Chạy trực tiếp từ file `index.html` trong trình duyệt.

---

## 3. Cấu trúc Thư mục

```
ddos-hub/
├── index.html          # File HTML chính chứa cấu trúc tất cả 14 sections (~1,970 dòng)
├── style.css           # Toàn bộ styling, cyberpunk theme (~1,600 dòng)
├── main.js             # Logic khởi tạo, background particles, sidebar scroll, counter animation
├── netlify.toml        # File cấu hình deploy tự động trên Netlify
├── PROJECT.md          # [File này] Tài liệu dự án cho AI & Developer
└── demos/
    ├── concepts.js         # Xử lý accordion mở/đóng và bộ lọc cho 11 thẻ khái niệm mạng (có IDS)
    ├── explain.js          # Hệ thống giải thích trực tiếp (Live Explanation Panels cho 100% Demos + PDP Inspector Grid)
    ├── server-sim.js       # Demo 1: Mô phỏng sức khỏe Server khi bị Botnet đánh
    ├── network-map.js      # Demo 2: Bản đồ tấn công DDoS toàn cầu trên Canvas + Live Map Explain Panel
    ├── packet-analyzer.js  # Demo 3: Phân tích luồng Gói tin (Packet Stream) real-time + Visual Packet Anatomy Guide (4 Layers)
    ├── syn-flood.js        # Demo 4: Mô phỏng cơ chế TCP 3-way Handshake & SYN Flood + Live SYN Explain Panel
    ├── defense-lab.js      # Demo 5: Game tương tác phòng thủ DDoS + Live Defense Explain Panel & Trade-offs Matrix
    ├── case-studies.js     # Hồ sơ 4 vụ tấn công kinh điển (Mirai, GitHub, Google, Spamhaus) + Modal phân tích
    ├── ai-detection.js     # Demo 6: Mô phỏng AI / Machine Learning phân loại DDoS real-time + Click-to-Inspect Packet
    ├── ml-concepts.js      # Demo 7 & 8: Mô phỏng Mũi tên Kéo co SHAP Force Plot & Ma trận Nhầm lẫn Confusion Matrix + Khung Chuyên sâu IDS & SHAP/LIME + Bảng so sánh đối kháng 5 tiêu chí
    └── quiz.js             # Bài kiểm tra 10 câu trắc nghiệm (ngẫu nhiên câu hỏi & đáp án)
```

---

## 4. Tối ưu Giao diện SYN Flood (Loại bỏ Bảng Kết nối)

1. **Loại bỏ Hoàn toàn Bảng Kết nối Server:**
   - Xóa bỏ khối thẻ `.conn-table-card` khỏi giao diện SYN Flood theo yêu cầu.
   - Chuyển thanh **Dung lượng Hàng đợi `0/20`** trực tiếp vào ô **Bảng Thông số Điều khiển** giúp giao diện gọn gàng, rộng rãi và tập trung 100% vào animation Canvas trực quan.

---

*Tài liệu được cập nhật ngày 2026-08-28 cho hệ thống DDoS Learning Hub.*
