/**
 * case-studies.js — Quản lý Hồ sơ Tấn công Thực tế & Modal Giải thích
 */

const CASE_STUDIES_DATA = {
  mirai: {
    title: "Mirai Botnet (2016)",
    badge: "🤖 IoT Botnet",
    badgeCls: "danger",
    subtitle: "Thảm họa 600,000 thiết bị IoT đánh sập hạ tầng DNS Bắc Mỹ",
    stats: [
      { label: "Quy mô Botnet", val: "600,000+ thiết bị" },
      { label: "Băng thông đỉnh", val: "1.2 Tbps" },
      { label: "Mục tiêu", val: "Dyn DNS Service" },
      { label: "Thiệt hại", val: "Twitter, Netflix, Reddit sập" }
    ],
    analogy: "🏡 <strong>Ví dụ đời thực:</strong> Hãy hình dung 600,000 chiếc khóa cửa thông minh gia đình bị bẻ khóa vì chủ nhà để mật khẩu mặc định (admin/123456). Kẻ trộm không ăn trộm đồ, mà biến tất cả các ổ khóa này thành tay sai đồng loạt gọi điện dội bom vào tổng đài điện thoại quốc gia khiến tổng đài liệt hoàn toàn!",
    concepts: [
      { term: "IoT (Internet of Things)", desc: "Các thiết bị thông minh kết nối internet như Camera IP, Router Wi-Fi, Đầu ghi hình DVR. Chúng thường ít được bảo mật." },
      { term: "Default Credentials", desc: "Tên đăng nhập & mật khẩu mặc định từ nhà sản xuất (ví dụ: admin/admin, root/123456). Mirai chỉ thử 62 cặp mật khẩu này là lây nhiễm thành công 600,000 thiết bị." },
      { term: "C2 Server (Command & Control)", desc: "Máy chủ chỉ huy của Hacker. Khi lây nhiễm xong, các thiết bị IoT biến thành 'Zombie' âm thầm chờ lệnh tấn công từ C2 Server." }
    ],
    timeline: [
      "Quét tự động toàn mạng Internet tìm các cổng Telnet (port 23/2323) mở.",
      "Thử 62 cặp tài khoản mặc định -> Lây nhiễm mã độc Mirai vào bộ nhớ RAM của thiết bị IoT.",
      "Nhận lệnh từ C2 Server -> Đồng loạt xả luồng SYN Flood và UDP Flood nhắm vào Dyn DNS.",
      "Dyn DNS ngưng hoạt động -> Hàng triệu người dùng gõ twitter.com hay netflix.com không thể phân giải ra IP."
    ],
    takeaway: "🔒 <strong>Bài học:</strong> Luôn đổi mật khẩu mặc định của thiết bị IoT và chặn các cổng quản trị không cần thiết (như Telnet) từ Internet."
  },

  github: {
    title: "GitHub Memcached Attack (2018)",
    badge: "💥 Amplification (Khuếch đại)",
    badgeCls: "warn",
    subtitle: "Cuộc tấn công khuếch đại kỷ lục 1.35 Tbps không cần Botnet",
    stats: [
      { label: "Băng thông đỉnh", val: "1.35 Tbps" },
      { label: "Hệ số khuếch đại", val: "51,000 lần (51,000x)" },
      { label: "Packet/giây", val: "126.9 triệu PPS" },
      { label: "Thời gian khắc phục", val: "10 phút" }
    ],
    analogy: "📮 <strong>Ví dụ đời thực:</strong> Bạn gửi 1 bưu thiếp nhẹ 10g đến thư viện với địa chỉ người gửi giả là nhà nạn nhân, yêu cầu gửi lại toàn bộ sách bách khoa toàn thư. Thư viện gửi 500kg sách về nhà nạn nhân. Kẻ tấn công chỉ tốn 10g lực nhưng nạn nhân hứng chịu 500kg!",
    concepts: [
      { term: "Memcached", desc: "Hệ thống bộ nhớ đệm (caching) dữ liệu cực nhanh chạy ở port 11211. Mặc định nó cho phép gửi truy vấn qua UDP mà không cần xác thực." },
      { term: "UDP Reflector Attack", desc: "Tấn công dội ngược: Gửi request với IP nguồn bị giả mạo (IP nạn nhân) đến các server trung gian (Reflector). Server trung gian sẽ dội toàn bộ câu trả lời về nạn nhân." },
      { term: "Amplification Ratio (Hệ số khuếch đại)", desc: "Tỷ lệ giữa kích thước gói tin phản hồi và gói tin truy vấn. Memcached có hệ số kỷ lục lên đến 51,000x (gửi 15 bytes nhận 750,000 bytes)." }
    ],
    timeline: [
      "Hacker tìm kiếm hàng ngàn Server Memcached mở port 11211 UDP công khai trên Internet.",
      "Gửi gói tin request nhỏ vài chục bytes chứa lệnh 'stats' với IP nguồn giả là IP của GitHub.",
      "Các Server Memcached gửi lại các gói tin trả lời khổng lồ đập thẳng vào hạ tầng GitHub.",
      "Akamai Prolexic tự động phát hiện, kích hoạt BGP Anycast phân tán 1.35 Tbps traffic và cứu GitHub sau 10 phút."
    ],
    takeaway: "🛡️ <strong>Bài học:</strong> Không bao giờ mở các dịch vụ nội bộ (như Memcached, Redis) ra Internet công khai mà không có Firewall bảo vệ."
  },

  google: {
    title: "Google HTTP/2 Rapid Reset (2023)",
    badge: "⚡ Layer 7 Application",
    badgeCls: "danger",
    subtitle: "Tấn công kỷ lục thế giới 398 Triệu Requests/giây khai thác HTTP/2",
    stats: [
      { label: "Tốc độ đỉnh", val: "398 Triệu RPS" },
      { label: "Giao thức bị khai thác", val: "HTTP/2 Stream Reset" },
      { label: "So sánh", val: "Gấp 7.5 lần kỷ lục cũ" },
      { label: "Trạng thái Google", val: "Vẫn hoạt động ổn định" }
    ],
    analogy: "🍔 <strong>Ví dụ đời thực:</strong> Bạn đến quầy ăn nhanh gọi 100 phần ăn, nhưng ngay khi thu ngân vừa ghi đơn (chưa kịp làm xong), bạn lập tức hủy đơn rồi lại gọi 100 phần mới liên tục. Thu ngân bị vắt cạn sức xử lý yêu cầu hủy đơn mà không bán được phần ăn nào!",
    concepts: [
      { term: "HTTP/2 Stream Multiplexing", desc: "Tính năng cho phép truyền nhiều yêu cầu (requests) song song trên cùng 1 kết nối TCP duy nhất giúp tải web nhanh hơn." },
      { term: "RST_STREAM Frame", desc: "Khung tín hiệu trong HTTP/2 dùng để hủy một request ngay lập tức nếu client không cần nữa." },
      { term: "Rapid Reset Vulnerability (CVE-2023-44487)", desc: "Kẻ tấn công gửi liên tục request + lệnh hủy RST_STREAM. Server tốn chi phí CPU xử lý việc mở/hủy request nhưng kết nối TCP không bao giờ bị đóng." }
    ],
    timeline: [
      "Hacker mở một số lượng kết nối TCP vừa phải đến hạ tầng Google Cloud.",
      "Gửi hàng triệu stream HTTP/2 request và lập tức gửi khung RST_STREAM để hủy.",
      "Server phải làm việc hết công suất để khởi tạo và hủy stream mà không kịp giải phóng tài nguyên CPU.",
      "Hạ tầng Cloud Armor của Google tự động phát hiện pattern bất thường ở tầng giao thức và cân bằng tải tiêu biến đợt tấn công."
    ],
    takeaway: "⚙️ <strong>Bài học:</strong> Giới hạn số lượng RST_STREAM được phép trên mỗi kết nối HTTP/2 để tránh bị vắt cạn tài nguyên CPU."
  },

  spamhaus: {
    title: "Spamhaus DNS Amplification (2013)",
    badge: "🌐 Network Infrastructure",
    badgeCls: "warn",
    subtitle: "Cuộc tấn công 300 Gbps suýt làm chậm mạng Internet toàn cầu",
    stats: [
      { label: "Băng thông đỉnh", val: "300 Gbps" },
      { label: "Loại tấn công", val: "DNS Open Resolver Amplification" },
      { label: "Tác động rộng", val: "Chậm mạng Internet Châu Âu" },
      { label: "Hệ số khuếch đại", val: "~70x" }
    ],
    analogy: "📞 <strong>Ví dụ đời thực:</strong> Bạn nhờ 10,000 người lạ gọi điện hỏi tổng đài danh bạ điện thoại với cú pháp: 'Hãy đọc cho tôi toàn bộ danh bạ thành phố'. Nhưng bạn đưa số điện thoại của nạn nhân làm số gọi đến. 10,000 người trả lời cùng lúc khiến máy nạn nhân nghẽn sóng hoàn toàn!",
    concepts: [
      { term: "DNS Open Resolver", desc: "Máy chủ DNS được cấu hình hớ hênh, cho phép bất kỳ ai trên Internet gửi truy vấn và nhận phản hồi." },
      { term: "EDNS0 (Extension Mechanisms for DNS)", desc: "Chuẩn DNS mở rộng cho phép gói tin trả lời DNS có kích thước lớn (lên đến 4096 bytes thay vì 512 bytes truyền thống)." },
      { term: "Tier-1 Network Congestion", desc: "Khi băng thông tấn công quá lớn (300 Gbps năm 2013 là con số khổng lồ), các tuyến cáp quang trục chính của Internet bị quá tải, gây chậm mạng toàn vùng." }
    ],
    timeline: [
      "Spamhaus đưa Cyberbunker vào danh sách đen chống Spam.",
      "Cyberbunker phối hợp gửi hàng ngàn truy vấn DNS `ANY .` với IP nguồn giả mạo là IP Spamhaus đến các DNS Open Resolvers.",
      "Các máy chủ DNS trả về các câu trả lời dung lượng lớn gấp 70 lần đập thẳng vào Spamhaus.",
      "Traffic tràn ra các hạ tầng trao đổi Internet (IXP) ở London và Amsterdam gây ảnh hưởng dây chuyền."
    ],
    takeaway: "🌐 <strong>Bài học:</strong> Cấu hình đóng tính năng Open Recursion trên máy chủ DNS nội bộ để không bị kẻ xấu lợi dụng làm điểm dội cầu."
  }
};

function openCaseStudyModal(caseKey) {
  const data = CASE_STUDIES_DATA[caseKey];
  if (!data) return;

  let modal = document.getElementById('case-study-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'case-study-modal';
    modal.className = 'cs-modal-overlay';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="cs-modal-card glass-card">
      <div class="cs-modal-header">
        <div>
          <span class="sec-badge ${data.badgeCls}">${data.badge}</span>
          <h2 class="cs-modal-title">${data.title}</h2>
          <p class="cs-modal-sub">${data.subtitle}</p>
        </div>
        <button class="cs-modal-close" onclick="closeCaseStudyModal()">✕</button>
      </div>

      <div class="cs-modal-body">
        <!-- Stats Grid -->
        <div class="cs-stats-grid">
          ${data.stats.map(s => `
            <div class="cs-stat-item">
              <span class="cs-stat-label">${s.label}</span>
              <span class="cs-stat-val">${s.val}</span>
            </div>
          `).join('')}
        </div>

        <!-- Analogy Box -->
        <div class="cc-analogy-box" style="margin: 16px 0;">
          <span class="cab-icon">💡</span>
          <div>${data.analogy}</div>
        </div>

        <!-- Concepts Detail -->
        <div class="cs-section-block">
          <h4 class="cs-block-title">🧠 Thuật ngữ & Khái niệm cốt lõi cần nhớ</h4>
          <div class="cs-concepts-list">
            ${data.concepts.map(c => `
              <div class="cs-concept-item">
                <span class="cs-ci-term">🔹 ${c.term}:</span>
                <span class="cs-ci-desc">${c.desc}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Timeline -->
        <div class="cs-section-block">
          <h4 class="cs-block-title">⏱️ Diễn biến từng bước của đợt tấn công</h4>
          <ol class="cs-timeline-list">
            ${data.timeline.map(t => `<li>${t}</li>`).join('')}
          </ol>
        </div>

        <!-- Takeaways -->
        <div class="cs-takeaway-box">
          ${data.takeaway}
        </div>
      </div>
    </div>
  `;

  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeCaseStudyModal() {
  const modal = document.getElementById('case-study-modal');
  if (modal) modal.classList.remove('active');
  document.body.style.overflow = '';
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeCaseStudyModal();
});
