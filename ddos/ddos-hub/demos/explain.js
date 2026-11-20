/**
 * explain.js — Hệ thống giải thích trực tiếp trong tất cả các demo
 * Cung cấp giải thích khái niệm thời gian thực cho 100% các Demo
 */

// =============================================
// 1. THÊM EXPLANATION PANEL VÀO SERVER SIM
// =============================================
function setupServerSimExplain() {
  const simSection = document.getElementById('server-sim');
  if (!simSection) return;
  
  const panel = document.createElement('div');
  panel.id = 'sim-explain-panel';
  panel.className = 'live-explain-panel glass-card';
  panel.innerHTML = `
    <div class="lep-icon" id="sim-lep-icon">💡</div>
    <div style="flex:1">
      <div class="lep-header">
        <div>
          <div class="lep-title" id="sim-lep-title">🟢 Server đang hoạt động bình thường</div>
          <div class="lep-text" id="sim-lep-text">Server nhận request từ người dùng thật và xử lý bình thường. CPU thấp, RAM ổn định. Thêm bot để xem điều gì xảy ra!</div>
        </div>
      </div>
      <div class="lep-details" id="sim-lep-details"></div>
      <div class="lep-concepts" style="margin-top:12px">
        <span class="lep-concept-label">🔗 Khái niệm liên quan:</span>
        <a class="lep-chip" href="#concepts">📦 Packet</a>
        <a class="lep-chip" href="#concepts">🚿 Bandwidth</a>
        <a class="lep-chip" href="#concepts">🔧 CPU Load</a>
      </div>
    </div>
  `;
  simSection.appendChild(panel);
}

window.updateSimExplain = function(bots, health, cpu, ram, firewall) {
  const panel = document.getElementById('sim-explain-panel');
  const titleEl = document.getElementById('sim-lep-title');
  const textEl = document.getElementById('sim-lep-text');
  const detailsEl = document.getElementById('sim-lep-details');
  const iconEl = document.getElementById('sim-lep-icon');
  if (!panel || !titleEl || !textEl) return;
  
  let title, text, icon, details = [], panelClass = '';
  
  if (bots === 0) {
    icon = '💡'; title = '🟢 Server đang hoạt động bình thường';
    text = 'Không có tấn công. Server xử lý requests từ người dùng thật một cách bình thường. Bandwidth, CPU, RAM đều ở mức thấp.';
    panelClass = '';
    details = [
      { label: 'Trạng thái', val: 'Requests thật từ người dùng được phục vụ ngay lập tức' },
      { label: 'CPU thấp?', val: 'CPU chỉ dùng để xử lý logic ứng dụng, không bị áp đảo' },
    ];
  } else if (bots < 10) {
    icon = '⚡'; title = '⚡ Phát hiện traffic bất thường nhẹ';
    text = `${bots} bot đang gửi requests. Server bắt đầu nhận thêm load. Đây là dấu hiệu sớm của tấn công — latency có thể tăng nhẹ.`;
    panelClass = '';
    details = [
      { label: 'Bot là gì?', val: 'Thiết bị bị nhiễm malware, bị kẻ xấu điều khiển để tấn công' },
      { label: 'CPU tăng vì?', val: 'Mỗi request đến đều cần CPU xử lý: đọc header, lookup DB, render response' },
    ];
  } else if (health > 60) {
    icon = '⚠️'; title = '⚠️ Tấn công đang leo thang — Server bị ảnh hưởng';
    text = `${bots} bot đang tấn công! CPU đạt ${cpu}%, bandwidth bị chiếm ${Math.min(bots*2, 100)}%. Người dùng thật bắt đầu thấy website chậm hơn.`;
    panelClass = 'warn';
    details = [
      { label: 'Bandwidth bị chiếm?', val: 'Bot gửi hàng ngàn packets/giây, chiếm đường ống internet của server' },
      { label: 'Người dùng thật?', val: 'Vẫn vào được nhưng latency cao hơn — phải chờ server xử lý hàng đợi dài' },
      { label: 'RAM tăng vì?', val: 'Mỗi kết nối đến server tốn một ít RAM để lưu trạng thái connection' },
    ];
  } else if (health > 20) {
    icon = '🚨'; title = '🚨 Server đang quá tải nghiêm trọng — DDoS đang hiệu quả!';
    text = `Server Health còn ${health}%. CPU đạt ${cpu}%. Hàng đợi request quá dài — người dùng thật nhận lỗi 503 Service Unavailable. Đây là mục tiêu của DDoS!`;
    panelClass = 'danger';
    details = [
      { label: 'Lỗi 503 là gì?', val: '"503 Service Unavailable" — Server từ chối request vì không đủ tài nguyên để xử lý' },
      { label: 'CPU 100%?', val: 'Khi CPU đầy, server không thể nhận request mới. Người dùng thật bị timeout' },
      { label: 'Giải pháp?', val: 'Bật Firewall để lọc traffic từ bot, hoặc dùng CDN để phân tán tải' },
    ];
  } else {
    icon = '💀'; title = '💀 SERVER SẮP SẬP — Tấn công DDoS thành công!';
    text = `Health chỉ còn ${health}%! Server gần như không phản hồi. Đây là mục tiêu cuối cùng của tấn công DDoS: làm dịch vụ hoàn toàn không sử dụng được.`;
    panelClass = 'danger';
    details = [
      { label: 'Hậu quả thực tế', val: 'Doanh nghiệp mất doanh thu, uy tín bị ảnh hưởng, khách hàng chuyển sang đối thủ' },
      { label: 'Chi phí downtime', val: 'Trung bình $22,000/phút cho doanh nghiệp lớn theo Ponemon Institute' },
      { label: 'Bật Firewall để', val: 'Lọc traffic bot, giảm tải, server có thể phục hồi dần dần' },
    ];
  }
  
  if (firewall && bots > 0) {
    icon = '🛡️'; title = '🛡️ Firewall đang HOẠT ĐỘNG — Chặn traffic tấn công!';
    text = 'Firewall đang phân tích và chặn packets từ các IP bot đã biết. Server đang phục hồi dần. Bandwidth và CPU giảm.';
    panelClass = 'success';
    details = [
      { label: 'Firewall làm gì?', val: 'Kiểm tra IP nguồn mỗi packet, chặn IP có hành vi bất thường (quá nhiều request/giây)' },
      { label: 'Rate Limiting?', val: 'Giới hạn số request/giây từ 1 IP — IP thường: OK, bot (hàng nghìn/giây): BỊ CHẶN' },
      { label: 'Hạn chế?', val: 'Bot có thể đổi IP liên tục (botnet lớn) để tránh bị chặn' },
    ];
  }
  
  panel.className = `live-explain-panel glass-card ${panelClass}`;
  if (iconEl) iconEl.textContent = icon;
  titleEl.textContent = title;
  textEl.textContent = text;
  
  if (detailsEl) {
    detailsEl.innerHTML = details.map(d => `
      <div class="lep-detail-item">
        <span class="ldi-label">${d.label}:</span>
        <span>${d.val}</span>
      </div>
    `).join('');
  }
};

// =============================================
// 2. NETWORK MAP EXPLANATION PANEL
// =============================================
function setupNetworkMapExplain() {
  const mapSection = document.getElementById('attack-map');
  if (!mapSection) return;

  const panel = document.createElement('div');
  panel.id = 'map-explain-panel';
  panel.className = 'live-explain-panel glass-card';
  panel.style.marginTop = '20px';
  panel.innerHTML = `
    <div class="lep-icon" id="map-lep-icon">🗺️</div>
    <div style="flex:1">
      <div class="lep-title" id="map-lep-title">💡 Bản đồ Tấn công Mạng toàn cầu</div>
      <div class="lep-text" id="map-lep-text">Nhấn nút "Bắt đầu tấn công" để kích hoạt mô phỏng bản đồ dòng chảy DDoS từ các quốc gia trên thế giới.</div>
      <div class="lep-concepts" style="margin-top:12px">
        <span class="lep-concept-label">🔗 Khái niệm liên quan:</span>
        <a class="lep-chip" href="#concepts">🤖 Botnet</a>
        <a class="lep-chip" href="#concepts">🌍 Anycast CDN</a>
        <a class="lep-chip" href="#concepts">🌐 IP Spoofing</a>
      </div>
    </div>
  `;
  mapSection.appendChild(panel);
}

window.updateMapExplain = function(isActive, ips, pps, bw) {
  const titleEl = document.getElementById('map-lep-title');
  const textEl = document.getElementById('map-lep-text');
  const iconEl = document.getElementById('map-lep-icon');
  const panel = document.getElementById('map-explain-panel');
  if (!panel || !titleEl || !textEl) return;

  if (!isActive) {
    if (iconEl) iconEl.textContent = '🗺️';
    titleEl.textContent = '💡 Trạng thái Mạng Yên bình';
    textEl.textContent = 'Chưa có đợt tấn công nào. Bấm nút "Bắt đầu tấn công" để xem hàng ngàn IP botnet từ Trung Quốc, Nga, Mỹ... xả băng thông vào server.';
    panel.className = 'live-explain-panel glass-card';
  } else {
    if (iconEl) iconEl.textContent = '💥';
    titleEl.textContent = `🚨 Đang diễn ra Tấn công Phân tán từ ${ips.toLocaleString()} IP Botnet!`;
    textEl.innerHTML = `Băng thông tấn công hiện tại đạt <strong>${bw} Gbps</strong> (${pps.toLocaleString()} packets/giây). Các tia sáng màu ĐỎ thể hiện luồng dữ liệu độc hại bay từ các quốc gia chứa Zombie IoT nhắm thẳng vào Server mục tiêu tại Châu Âu. Các hạ tầng lớn như Cloudflare dùng công nghệ <strong>BGP Anycast</strong> để chia nhỏ luồng traffic này ra 200+ server trên toàn cầu để tiêu biến đợt tấn công!`;
    panel.className = 'live-explain-panel glass-card danger';
  }
};

// =============================================
// 3. SYN FLOOD EXPLANATION PANEL
// =============================================
function setupSynFloodExplain() {
  const synSection = document.getElementById('syn-flood');
  if (!synSection) return;

  const panel = document.createElement('div');
  panel.id = 'syn-explain-panel';
  panel.className = 'live-explain-panel glass-card';
  panel.style.marginTop = '20px';
  panel.innerHTML = `
    <div class="lep-icon" id="syn-lep-icon">🧩</div>
    <div style="flex:1">
      <div class="lep-title" id="syn-lep-title">💡 Giải thích Cơ chế TCP 3-Way Handshake & SYN Flood</div>
      <div class="lep-text" id="syn-lep-text">Bình thường: Client gửi SYN -> Server đáp SYN-ACK -> Client đáp ACK (Hoàn thành Handshake). SYN Flood khai thác bằng cách gửi SYN xong trốn mất, khiến Server bị đầy Hàng đợi Half-open!</div>
      <div class="lep-concepts" style="margin-top:12px">
        <span class="lep-concept-label">🔗 Khái niệm liên quan:</span>
        <a class="lep-chip" href="#concepts">🤝 TCP Handshake</a>
        <a class="lep-chip" href="#concepts">🍪 SYN Cookie</a>
        <a class="lep-chip" href="#concepts">🚪 Connection Backlog</a>
      </div>
    </div>
  `;
  synSection.appendChild(panel);
}

window.updateSynExplain = function(valid, halfOpen, refused, synCookie, isAttacking) {
  const titleEl = document.getElementById('syn-lep-title');
  const textEl = document.getElementById('syn-lep-text');
  const iconEl = document.getElementById('syn-lep-icon');
  const panel = document.getElementById('syn-explain-panel');
  if (!panel || !titleEl || !textEl) return;

  if (synCookie) {
    if (iconEl) iconEl.textContent = '🛡️';
    titleEl.textContent = '🛡️ SYN Cookie đang BẬT — Chống SYN Flood Tuyệt đối!';
    textEl.textContent = 'Server không cấp phát bộ nhớ RAM cho kết nối cho đến khi nhận được gói ACK cuối cùng! Mã hash mã hóa trong Sequence Number giúp Server nhận biết kết nối hợp lệ mà BẢNG DUNG LƯỢNG KHÔNG BAO GIỜ BỊ ĐẦY.';
    panel.className = 'live-explain-panel glass-card success';
  } else if (isAttacking) {
    if (iconEl) iconEl.textContent = '🚨';
    titleEl.textContent = `🚨 SYN Flood đang diễn ra — Hàng đợi Half-open: ${halfOpen}/20`;
    textEl.textContent = `Botnet đang gửi liên tục gói SYN nhưng KHÔNG BAO GIỜ gửi lại ACK! Server bị ép giữ ${halfOpen} kết nối dở dang. Khi dung lượng đạt 20/20, người dùng hợp lệ bị TỪ CHỐI (Refused = ${refused}). Hãy BẬT SYN COOKIE để bảo vệ!`;
    panel.className = 'live-explain-panel glass-card danger';
  } else {
    if (iconEl) iconEl.textContent = '🤝';
    titleEl.textContent = '🟢 Kết nối Hợp lệ — TCP 3-Way Handshake Thành công';
    textEl.textContent = 'Client và Server hoàn thành đủ 3 bước SYN -> SYN-ACK -> ACK. Kết nối được thiết lập và tự động giải phóng tài nguyên sau khi truyền dữ liệu.';
    panel.className = 'live-explain-panel glass-card success';
  }
};

// =============================================
// 4. DEFENSE LAB EXPLANATION PANEL
// =============================================
function setupDefenseLabExplain() {
  const defSection = document.getElementById('defense-lab');
  if (!defSection) return;

  const panel = document.createElement('div');
  panel.id = 'def-explain-panel';
  panel.className = 'live-explain-panel glass-card';
  panel.style.marginTop = '20px';
  panel.innerHTML = `
    <div class="lep-icon" id="def-lep-icon">🛡️</div>
    <div style="flex:1">
      <div class="lep-title" id="def-lep-title">💡 Trò chơi Phòng thủ Chống DDoS</div>
      <div class="lep-text" id="def-lep-text">Kích hoạt 4 công cụ (Rate Limiter 60%, WAF 80%, CDN 70%, IP Blacklist 50%) đúng thời điểm để bảo vệ HP của Server trước các đợt tấn công!</div>
      <div class="lep-concepts" style="margin-top:12px">
        <span class="lep-concept-label">🔗 Khái niệm liên quan:</span>
        <a class="lep-chip" href="#concepts">🔥 Firewall & WAF</a>
        <a class="lep-chip" href="#concepts">🌍 Anycast CDN</a>
        <a class="lep-chip" href="#concepts">⏱️ Rate Limiting</a>
      </div>
    </div>
  `;
  defSection.appendChild(panel);
}

window.updateDefenseExplain = function(hp, wave, score, activeToolsText) {
  const titleEl = document.getElementById('def-lep-title');
  const textEl = document.getElementById('def-lep-text');
  const iconEl = document.getElementById('def-lep-icon');
  const panel = document.getElementById('def-explain-panel');
  if (!panel || !titleEl || !textEl) return;

  if (hp <= 0) {
    if (iconEl) iconEl.textContent = '💀';
    titleEl.textContent = `💀 GAME OVER — Server bị hạ gục ở Đợt #${wave}!`;
    textEl.textContent = `Server đã hết HP. Điểm của bạn: ${score}. Mẹo: Hãy kết hợp WAF và Rate Limiter cùng lúc khi sóng tấn công mạnh dội tới để nhân đôi tỷ lệ giảm damage!`;
    panel.className = 'live-explain-panel glass-card danger';
  } else if (activeToolsText) {
    if (iconEl) iconEl.textContent = '🛡️';
    titleEl.textContent = `🛡️ Công cụ đang kích hoạt: ${activeToolsText}`;
    textEl.textContent = `Lớp lá chắn đang hấp thụ phần lớn sát thương từ botnet! Server HP hiện tại: ${hp}%. Tiếp tục duy trì phòng thủ!`;
    panel.className = 'live-explain-panel glass-card success';
  } else {
    if (iconEl) iconEl.textContent = '⚡';
    titleEl.textContent = `⚔️ Đợt tấn công #${wave} đang diễn ra — HP Server: ${hp}%`;
    textEl.textContent = 'Mỗi giây trôi qua Server bị tổn hại HP do luồng botnet. Bấm nút kích hoạt các công cụ phòng thủ ở bên dưới!';
    panel.className = 'live-explain-panel glass-card warn';
  }
};

// =============================================
// 5. PACKET ANALYZER EXPLANATION & DETAIL
// =============================================
function setupPacketAnalyzerExplain() {
  const analyzerSection = document.getElementById('packet-analyzer');
  if (!analyzerSection) return;
  
  const detailPanel = document.createElement('div');
  detailPanel.id = 'packet-detail-panel';
  detailPanel.className = 'packet-detail-panel glass-card hidden';
  detailPanel.innerHTML = `
    <div class="pdp-head">
      <h4>🔍 Phân tích chi tiết Packet đã chọn</h4>
      <button onclick="document.getElementById('packet-detail-panel').classList.add('hidden')">✕ Đóng</button>
    </div>
    <div class="pdp-content" id="pdp-content">
      <div class="pdp-hint">👆 Click vào một dòng trong bảng packet để xem phân tích chi tiết từng trường...</div>
    </div>
  `;
  
  const explainPanel = document.createElement('div');
  explainPanel.id = 'analyzer-explain-panel';
  explainPanel.className = 'live-explain-panel glass-card';
  explainPanel.innerHTML = `
    <div class="lep-icon">🔬</div>
    <div style="flex:1">
      <div class="lep-title" id="ana-lep-title">💡 Phân tích luồng Packet</div>
      <div class="lep-text" id="ana-lep-text">Nhấn nút để bắt đầu quan sát luồng packets. <strong>Click vào từng dòng</strong> trong bảng để xem phân tích chi tiết từng trường của packet!</div>
      <div class="lep-concepts" style="margin-top:12px">
        <span class="lep-concept-label">🔗 Khái niệm:</span>
        <a class="lep-chip" href="#concepts">📦 Packet</a>
        <a class="lep-chip" href="#concepts">🚪 Port</a>
        <a class="lep-chip" href="#concepts">🤝 TCP/UDP</a>
        <a class="lep-chip" href="#concepts">🌐 IP Address</a>
      </div>
    </div>
  `;
  
  analyzerSection.appendChild(detailPanel);
  analyzerSection.appendChild(explainPanel);
  
  const stream = document.getElementById('packet-stream');
  if (stream) {
    stream.addEventListener('click', (e) => {
      const row = e.target.closest('.packet-row');
      if (!row) return;
      showPacketDetail(row);
    });
  }
}

function showPacketDetail(rowEl) {
  const cells = rowEl.querySelectorAll('span');
  if (cells.length < 6) return;
  
  const time = cells[0]?.textContent || '';
  const srcIP = cells[1]?.textContent || '';
  const dstIP = cells[2]?.textContent || '';
  const protocol = cells[3]?.textContent || '';
  const size = cells[4]?.textContent || '';
  const status = rowEl.classList.contains('blocked') ? 'blocked' : rowEl.classList.contains('suspicious') ? 'suspicious' : 'normal';
  
  const content = document.getElementById('pdp-content');
  if (!content) return;
  
  const protocolExplain = {
    'TCP SYN': 'TCP SYN = Cờ mở kết nối (👋 SYN). Client gửi SYN xin chào Server. Trong đợt tấn công này, botnet gửi SYN dội dập nhưng KHÔNG BAO GIỜ đáp ACK!',
    'TCP ACK': 'TCP ACK = Cờ xác nhận (🤝 ACK). Client báo cho Server là đã nhận dữ liệu an toàn. Luồng bắt tay hợp lệ.',
    'UDP 53': 'UDP Port 53 = Dịch vụ tra cứu tên miền DNS. Không cần bắt tay, dễ bị lợi dụng làm DNS Amplification.',
    'ICMP Echo': 'ICMP Echo = Gói tin Ping kiểm tra mạng. Nếu gửi hàng triệu gói Ping -> ICMP Smurf Flood.',
    'HTTP GET': 'HTTP GET / = Yêu cầu tải trang web. Kẻ tấn công gửi hàng triệu HTTP GET -> HTTP Flood.',
    'HTTP POST': 'HTTP POST = Gửi dữ liệu form/login lên server. Tốn nhiều CPU để xử lý DB.',
  };
  
  const statusInfo = {
    normal: { 
      label: 'BÌNH THƯỜNG', 
      cls: 'normal-explain', 
      risk: 'An toàn (Risk: 5%)',
      infectionReason: 'IP thuộc dải nhà mạng công cộng sạch. Thiết bị hợp lệ của người dùng thật, không phát hiện mã độc.',
      blockedReason: 'ĐƯỢC CHO QUA: Thực hiện đúng quy trình bắt tay TCP, kích thước payload hợp lệ (200–1500B), tần suất gửi bình thường.'
    },
    suspicious: { 
      label: 'KHẢ NGHI', 
      cls: 'suspicious-explain', 
      risk: 'Cảnh báo (Risk: 55%)',
      infectionReason: 'Thiết bị có dấu hiệu bị lây nhiễm malware nhẹ hoặc nằm trong dải mạng NAT có nhiều thiết bị phát traffic bất thường.',
      blockedReason: 'GHI NHẬN CẢNH BÁO: Tần suất gửi tăng đột biến hoặc kích thước gói nhỏ hơn bình thường. Hệ thống đưa vào danh sách theo dõi.'
    },
    blocked: { 
      label: 'BỊ CHẶN (ATTACK)', 
      cls: 'blocked-explain', 
      risk: 'Nguy hiểm (Risk: 99%)',
      infectionReason: 'Thiết bị nguồn (Camera IoT, Router WiFi, PC) đã bị lây nhiễm mã độc Mirai/Mozi. Kẻ tấn công chiếm quyền điều khiển từ xa qua máy chủ C2 (Command & Control), biến thiết bị thành botnet âm thầm xả traffic.',
      blockedReason: 'Firewall / Rate Limiter phát hiện 3 dấu hiệu tấn công:<br>' +
        '1. <strong>Bắt tay giả mạo (SYN Flood):</strong> Chỉ dội cờ <code>SYN</code> nhưng cố tình không trả lời <code>ACK</code> nhằm làm tràn hàng đợi kết nối.<br>' +
        '2. <strong>Kích thước rác (64 Bytes):</strong> Gói tin chỉ chứa Header tối thiểu, không có dữ liệu người dùng (Payload).<br>' +
        '3. <strong>Vượt ngưỡng Rate Limiter:</strong> Địa chỉ IP <code>' + srcIP + '</code> gửi tần suất quá cao (vượt ngưỡng an toàn).'
    },
  };
  
  const si = statusInfo[status];
  const protoExplainText = Object.entries(protocolExplain).find(([k]) => protocol.includes(k))?.[1] || 'Giao thức truyền dữ liệu mạng chuẩn.';
  
  content.innerHTML = `
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:10px; margin-bottom:16px;">
      <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; border:1px solid var(--border);">
        <span style="font-size:10px; color:var(--text-dim); font-weight:700; display:block;">⏰ THỜI GIAN ĐẾN</span>
        <span style="font-family:var(--font-mono); font-size:13px; color:var(--cyan);">${time}</span>
      </div>

      <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; border:1px solid var(--border);">
        <span style="font-size:10px; color:var(--text-dim); font-weight:700; display:block;">📤 IP NGUỒN (SENDER)</span>
        <span style="font-family:var(--font-mono); font-size:13px; color:var(--yellow);">${srcIP}</span>
      </div>

      <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; border:1px solid var(--border);">
        <span style="font-size:10px; color:var(--text-dim); font-weight:700; display:block;">📥 IP ĐÍCH (TARGET)</span>
        <span style="font-family:var(--font-mono); font-size:13px; color:var(--green);">${dstIP}</span>
      </div>

      <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; border:1px solid var(--border);">
        <span style="font-size:10px; color:var(--text-dim); font-weight:700; display:block;">🚦 ĐÁNH GIÁ RỦI RO</span>
        <span style="font-family:var(--font-mono); font-size:12px; font-weight:700; color:${status==='normal'?'var(--green)':status==='suspicious'?'var(--yellow)':'var(--red)'};">${si.risk}</span>
      </div>
    </div>

    <div class="pdp-field-row">
      <span class="pdp-field-name">📡 Giao thức (Layer 4/7)</span>
      <span class="pdp-field-val">${protocol}</span>
      <span class="pdp-field-explain">${protoExplainText}</span>
    </div>

    <div class="pdp-field-row">
      <span class="pdp-field-name">📏 Kích thước Gói (Size)</span>
      <span class="pdp-field-val">${size}</span>
      <span class="pdp-field-explain">Packet 64 bytes = Gói tin nhỏ chỉ chứa Header (Dấu hiệu Flood). Packet 200–1500 bytes = Dữ liệu người dùng thật.</span>
    </div>

    <!-- DEEP-DIVE INFECTION & BLOCK REASON BOXES -->
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:16px;">
      <div style="background:rgba(255,215,0,0.06); border:1px solid rgba(255,215,0,0.25); padding:14px; border-radius:var(--radius);">
        <h5 style="font-family:var(--font-title); font-size:12px; color:var(--yellow); margin-bottom:6px;">🦠 TẠI SAO IP NÀY BỊ NGUY CƠ NHIỄM MÃ ĐỘC?</h5>
        <div style="font-size:12px; color:var(--text-dim); line-height:1.6;">${si.infectionReason}</div>
      </div>

      <div style="background:${status==='blocked'?'rgba(255,0,60,0.08)':status==='suspicious'?'rgba(255,215,0,0.08)':'rgba(0,255,136,0.08)'}; border:1px solid ${status==='blocked'?'rgba(255,0,60,0.3)':status==='suspicious'?'rgba(255,215,0,0.3)':'rgba(0,255,136,0.3)'}; padding:14px; border-radius:var(--radius);">
        <h5 style="font-family:var(--font-title); font-size:12px; color:${status==='blocked'?'var(--red)':status==='suspicious'?'var(--yellow)':'var(--green)'}; margin-bottom:6px;">🚫 TẠI SAO HỆ THỐNG QUYẾT ĐỊNH CHẶN / XỬ LÝ?</h5>
        <div style="font-size:12px; color:var(--text-dim); line-height:1.6;">${si.blockedReason}</div>
      </div>
    </div>
  `;
  
  document.getElementById('packet-detail-panel').classList.remove('hidden');
  
  const anaTitle = document.getElementById('ana-lep-title');
  const anaText = document.getElementById('ana-lep-text');
  if (anaTitle && anaText) {
    anaTitle.textContent = `🔍 Đang phân tích: Packet ${si.label} từ ${srcIP}`;
    anaText.textContent = si.infectionReason.replace(/<[^>]*>/g, '');
    const panel = document.getElementById('analyzer-explain-panel');
    if (panel) panel.className = `live-explain-panel glass-card ${status === 'normal' ? 'success' : status === 'suspicious' ? 'warn' : 'danger'}`;
  }
}

window.updateAnalyzerExplain = function(mode) {
  const titleEl = document.getElementById('ana-lep-title');
  const textEl = document.getElementById('ana-lep-text');
  const panel = document.getElementById('analyzer-explain-panel');
  if (!titleEl || !textEl) return;
  
  if (mode === 'normal') {
    if (titleEl) titleEl.textContent = '🟢 Traffic bình thường — Phân tích packet hợp lệ';
    if (textEl) textEl.textContent = 'Đây là traffic bình thường từ người dùng thật. Packets có kích thước đa dạng (200-2000 bytes), IP nguồn từ nhiều vùng khác nhau, protocol đúng (HTTP GET/POST). Click vào packet để xem chi tiết từng trường!';
    if (panel) panel.className = 'live-explain-panel glass-card success';
  } else if (mode === 'attack') {
    if (titleEl) titleEl.textContent = '🔴 DDoS Attack! — Phân tích packet tấn công';
    if (textEl) textEl.textContent = 'Tấn công DDoS đang xảy ra! Chú ý: nhiều packet đến từ cùng subnet IP (botnet), kích thước nhỏ (64 bytes SYN), tần suất cực cao. Firewall chặn các packet này dựa trên pattern và rate limiting. Click vào packet để phân tích!';
    if (panel) panel.className = 'live-explain-panel glass-card danger';
  } else {
    if (titleEl) titleEl.textContent = '💡 Phân tích luồng Packet';
    if (textEl) textEl.textContent = 'Nhấn nút để bắt đầu quan sát luồng packets. Click vào từng dòng để xem phân tích chi tiết từng trường!';
    if (panel) panel.className = 'live-explain-panel glass-card';
  }
};

// =============================================
// INIT ALL EXPLANATION PANELS
// =============================================
document.addEventListener('DOMContentLoaded', () => {
  setupServerSimExplain();
  setupNetworkMapExplain();
  setupPacketAnalyzerExplain();
  setupSynFloodExplain();
  setupDefenseLabExplain();
});
