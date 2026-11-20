/**
 * ai-detection.js — Demo Tương tác AI / Machine Learning phát hiện DDoS
 * Giúp người học hiểu cách AI trích xuất đặc trưng và phân loại traffic thời gian thực
 */

let aiState = {
  isRunning: false,
  model: 'rf', // Default 'rf': Random Forest
  threshold: 85, // Confidence threshold %
  totalAnalyzed: 0,
  truePositives: 0,   // AI phát hiện ĐÚNG DDoS
  trueNegatives: 0,   // AI phát hiện ĐÚNG Traffic bình thường
  falsePositives: 0,  // AI CHẶN NHẦM người dùng thật
  falseNegatives: 0,  // AI BỎ SÓT DDoS
  intervalId: null
};

// 1. Giải thích khái niệm AI cơ bản
const AI_CONCEPTS_EXPLAIN = {
  dt: {
    name: "Cây quyết định (Decision Tree)",
    analogy: "🌳 <strong>Hình dung đơn giản:</strong> Giống như sơ đồ cây câu hỏi Yes/No: 'Số packet > 5000/s?' -> Yes -> 'Kích thước packet = 64B?' -> Yes -> 💥 KẾT LUẬN: DDOS!",
    speed: "⚡ Nhanh cực kỳ (0.2 ms)",
    accuracy: "🎯 Khá (88-92%)",
    desc: "Thuật toán kiểm tra từng điều kiện theo thứ tự. Rất dễ hiểu nhưng dễ bị qua mặt nếu hacker thay đổi chiêu thức."
  },
  rf: {
    name: "Rừng ngẫu nhiên (Random Forest)",
    analogy: "🌲 <strong>Hình dung đơn giản:</strong> Cho 50 Cây quyết định cùng phân tích độc lập rồi 'bỏ phiếu biểu quyết'. Hầu hết cây bảo DDoS thì kết luận là DDoS!",
    speed: "⚡ Trung bình (1.5 ms)",
    accuracy: "🎯 Rất cao (96-98%)",
    desc: "Kết hợp hàng chục cây quyết định. Giúp giảm thiểu tối đa việc chặn nhầm người dùng thật."
  },
  dnn: {
    name: "Mạng Nơ-ron Sâu (Deep Learning DNN)",
    analogy: "🧠 <strong>Hình dung đơn giản:</strong> Mô phỏng não người với nhiều lớp nơ-ron liên kết. Có khả năng tự phát hiện ra các pattern tấn công mới tinh mà chưa từng thấy trước đây!",
    speed: "⚡ Chậm hơn (5.0 ms)",
    accuracy: "🎯 Cực cao (99.2%)",
    desc: "Mô hình AI học sâu mạnh mẽ nhất. Đòi hỏi phần cứng mạnh để xử lý hàng triệu packet/giây."
  }
};

function initAIDetectionDemo() {
  const btnStart = document.getElementById('btn-start-ai');
  const btnReset = document.getElementById('btn-reset-ai');
  const selectModel = document.getElementById('ai-model-select');
  const sliderThreshold = document.getElementById('ai-threshold-slider');
  const valThreshold = document.getElementById('ai-threshold-val');

  if (selectModel) {
    aiState.model = selectModel.value;
    selectModel.addEventListener('change', (e) => {
      aiState.model = e.target.value;
      updateAIModelInfo();
    });
  }

  if (sliderThreshold) {
    aiState.threshold = parseInt(sliderThreshold.value);
    if (valThreshold) valThreshold.textContent = `${aiState.threshold}%`;
    sliderThreshold.addEventListener('input', (e) => {
      aiState.threshold = parseInt(e.target.value);
      if (valThreshold) valThreshold.textContent = `${aiState.threshold}%`;
    });
  }

  if (btnStart) btnStart.onclick = window.toggleAISimulation;
  if (btnReset) btnReset.onclick = window.resetAISimulation;

  updateAIModelInfo();
}

window.toggleAISimulation = function() {
  if (aiState.isRunning) {
    stopAISimulation();
  } else {
    startAISimulation();
  }
};

window.resetAISimulation = function() {
  stopAISimulation();
  resetAIStats();
};

function updateAIModelInfo() {
  const infoBox = document.getElementById('ai-model-info-box');
  const info = AI_CONCEPTS_EXPLAIN[aiState.model] || AI_CONCEPTS_EXPLAIN['rf'];
  if (!infoBox || !info) return;

  infoBox.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <strong style="color:var(--cyan); font-size:14px;">🤖 ${info.name}</strong>
      <span style="font-size:11px; color:var(--text-dim); font-family:var(--font-mono);">${info.speed} | ${info.accuracy}</span>
    </div>
    <div class="cc-analogy-box" style="margin: 6px 0 10px 0; padding:10px;">
      <span class="cab-icon" style="font-size:20px;">💡</span>
      <div style="font-size:12px;">${info.analogy}</div>
    </div>
    <p style="font-size:12px; color:var(--text-dim); margin:0;">${info.desc}</p>
  `;
}

function startAISimulation() {
  aiState.isRunning = true;
  const btnStart = document.getElementById('btn-start-ai');
  if (btnStart) {
    btnStart.textContent = '⏹️ Dừng AI Phân Tích';
    btnStart.style.background = 'var(--red)';
    btnStart.style.color = '#fff';
  }

  processNextAIPacketBatch();
  if (aiState.intervalId) clearInterval(aiState.intervalId);
  aiState.intervalId = setInterval(processNextAIPacketBatch, 600);
}

function stopAISimulation() {
  aiState.isRunning = false;
  if (aiState.intervalId) clearInterval(aiState.intervalId);
  const btnStart = document.getElementById('btn-start-ai');
  if (btnStart) {
    btnStart.textContent = '▶️ Bắt đầu AI Phân Tích Traffic';
    btnStart.style.background = '';
    btnStart.style.color = '';
  }
}

function resetAIStats() {
  aiState.totalAnalyzed = 0;
  aiState.truePositives = 0;
  aiState.trueNegatives = 0;
  aiState.falsePositives = 0;
  aiState.falseNegatives = 0;

  updateAIDashboardUI();

  const stream = document.getElementById('ai-stream-list');
  if (stream) stream.innerHTML = '<div class="pdp-hint">Chưa có dữ liệu. Nhấn "Bắt đầu AI Phân Tích" để kích hoạt mô hình...</div>';

  const detailPanel = document.getElementById('ai-packet-detail-panel');
  if (detailPanel) detailPanel.classList.add('hidden');

  const explainTitle = document.getElementById('ai-live-explain-title');
  const explainText = document.getElementById('ai-live-explain-text');
  const explainPanel = document.getElementById('ai-live-explain-panel');
  if (explainTitle) explainTitle.textContent = '💡 Giải thích nguyên lý AI phát hiện DDoS';
  if (explainText) explainText.textContent = 'Mô hình AI đang ở trạng thái chờ. Nhấn bắt đầu để AI trích xuất 4 đặc trưng (Packet Rate, Entropy, SYN/ACK Ratio, IP Subnet) và đưa ra quyết định.';
  if (explainPanel) explainPanel.className = 'live-explain-panel glass-card';
}

function processNextAIPacketBatch() {
  const isActualAttack = Math.random() < 0.45;
  let pps, sizeStdDev, synAckRatio, ipDispersion;

  if (isActualAttack) {
    pps = Math.floor(20000 + Math.random() * 50000);
    sizeStdDev = (Math.random() * 5).toFixed(1);
    synAckRatio = (15 + Math.random() * 35).toFixed(1);
    ipDispersion = (0.05 + Math.random() * 0.15).toFixed(2);
  } else {
    pps = Math.floor(100 + Math.random() * 1500);
    sizeStdDev = (150 + Math.random() * 400).toFixed(1);
    synAckRatio = (0.9 + Math.random() * 0.3).toFixed(1);
    ipDispersion = (0.85 + Math.random() * 0.15).toFixed(2);
  }

  let aiConfidence = 0;
  if (aiState.model === 'dt') {
    if (pps > 10000 && sizeStdDev < 20) aiConfidence = 92;
    else if (synAckRatio > 5) aiConfidence = 85;
    else aiConfidence = 15;
  } else if (aiState.model === 'rf') {
    let score = 0;
    if (pps > 15000) score += 35;
    if (sizeStdDev < 30) score += 30;
    if (synAckRatio > 8) score += 25;
    if (ipDispersion < 0.3) score += 10;
    aiConfidence = Math.min(99, Math.max(5, score + Math.floor(Math.random() * 6)));
  } else {
    let score = 0;
    if (pps > 10000) score += 40;
    if (sizeStdDev < 40) score += 35;
    if (synAckRatio > 6) score += 20;
    aiConfidence = isActualAttack ? (94 + Math.floor(Math.random() * 6)) : (3 + Math.floor(Math.random() * 8));
  }

  const aiPredictsAttack = aiConfidence >= aiState.threshold;

  aiState.totalAnalyzed++;
  if (isActualAttack && aiPredictsAttack) aiState.truePositives++;
  else if (!isActualAttack && !aiPredictsAttack) aiState.trueNegatives++;
  else if (!isActualAttack && aiPredictsAttack) aiState.falsePositives++;
  else if (isActualAttack && !aiPredictsAttack) aiState.falseNegatives++;

  const packetObj = {
    isActualAttack,
    aiPredictsAttack,
    confidence: aiConfidence,
    pps,
    sizeStdDev,
    synAckRatio,
    ipDispersion,
    time: new Date().toLocaleTimeString('vi-VN')
  };

  addAIPacketToStream(packetObj);
  updateAIDashboardUI();
  updateAILiveExplanation(isActualAttack, aiPredictsAttack, aiConfidence, pps, sizeStdDev, synAckRatio);
}

function addAIPacketToStream(pkt) {
  const stream = document.getElementById('ai-stream-list');
  if (!stream) return;

  if (stream.querySelector('.pdp-hint')) stream.innerHTML = '';

  const row = document.createElement('div');
  let statusClass = '';
  let statusBadge = '';

  if (pkt.aiPredictsAttack && pkt.isActualAttack) {
    statusClass = 'ai-row-blocked';
    statusBadge = `🚫 Bị AI Chặn (${pkt.confidence}% Tin cậy)`;
  } else if (!pkt.aiPredictsAttack && !pkt.isActualAttack) {
    statusClass = 'ai-row-passed';
    statusBadge = `✅ Cho Qua (${100 - pkt.confidence}% Bình thường)`;
  } else if (pkt.aiPredictsAttack && !pkt.isActualAttack) {
    statusClass = 'ai-row-fp';
    statusBadge = `⚠️ DƯƠNG TÍNH GIẢ (Chặn nhầm người dùng!)`;
  } else {
    statusClass = 'ai-row-fn';
    statusBadge = `💥 ÂM TÍNH GIẢ (Bỏ sót đợt tấn công!)`;
  }

  row.className = `ai-packet-row ${statusClass}`;
  row.style.cursor = 'pointer';
  row.innerHTML = `
    <div style="display:flex; justify-content:space-between; font-weight:700; margin-bottom:4px;">
      <span>${statusBadge}</span>
      <span style="font-family:var(--font-mono); font-size:11px;">Thực tế: ${pkt.isActualAttack ? '🔴 Tấn công' : '🟢 Người dùng thật'}</span>
    </div>
    <div class="ai-feature-chips">
      <span class="ai-chip">📊 Rate: ${pkt.pps.toLocaleString()} pps</span>
      <span class="ai-chip">📏 StdDev Size: ${pkt.sizeStdDev}B</span>
      <span class="ai-chip">🔄 SYN/ACK: ${pkt.synAckRatio}</span>
      <span class="ai-chip">🌐 Subnet: ${pkt.ipDispersion}</span>
    </div>
  `;

  // Attach click listener for deep inspection
  row.addEventListener('click', () => {
    inspectAIPacketDetail(pkt);
  });

  stream.insertBefore(row, stream.firstChild);

  while (stream.children.length > 20) {
    stream.removeChild(stream.lastChild);
  }
}

// 🔬 SOÌ CHI TIẾT KHI CLICK VÀO ROW
function inspectAIPacketDetail(pkt) {
  const panel = document.getElementById('ai-packet-detail-panel');
  const content = document.getElementById('ai-pdp-content');
  if (!panel || !content) return;

  const modelName = AI_CONCEPTS_EXPLAIN[aiState.model]?.name || 'AI Model';

  let decisionExplain = '';
  if (pkt.aiPredictsAttack && pkt.isActualAttack) {
    decisionExplain = `<div class="pdp-explain-box blocked-explain">
      <strong>🎯 KẾT LUẬN AI: PHÁT HIỆN ĐÚNG DDOS (True Positive)</strong><br>
      Mô hình <em>${modelName}</em> đánh giá độ tin cậy tấn công là <strong>${pkt.confidence}%</strong> (vượt ngưỡng threshold ${aiState.threshold}%). AI đã quyết định <strong>CHẶN NGAY</strong>. Hạ tầng được bảo vệ an toàn!
    </div>`;
  } else if (!pkt.aiPredictsAttack && !pkt.isActualAttack) {
    decisionExplain = `<div class="pdp-explain-box normal-explain">
      <strong>✅ KẾT LUẬN AI: XÁC NHẬN TRAFFIC BÌNH THƯỜNG (True Negative)</strong><br>
      Mô hình <em>${modelName}</em> đánh giá độ tin cậy tấn công chỉ có <strong>${pkt.confidence}%</strong> (thấp hơn threshold ${aiState.threshold}%). AI quyết định <strong>CHO PHÉP TRUY CẬP</strong>. Người dùng thật lướt web mượt mà.
    </div>`;
  } else if (pkt.aiPredictsAttack && !pkt.isActualAttack) {
    decisionExplain = `<div class="pdp-explain-box suspicious-explain">
      <strong>⚠️ KẾT LUẬN AI: CHẶN NHẦM NGƯỜI DÙNG THẬT (False Positive - Dương tính giả)</strong><br>
      Mô hình <em>${modelName}</em> đánh giá nhầm điểm tin cậy ${pkt.confidence}% $\\ge$ threshold ${aiState.threshold}%. Hậu quả: Khách hàng thật bị sập web! <em>Khắc phục: Tăng ngưỡng Confidence Threshold lên cao hơn hoặc chuyển sang mô hình Random Forest / DNN.</em>
    </div>`;
  } else {
    decisionExplain = `<div class="pdp-explain-box suspicious-explain">
      <strong>💥 KẾT LUẬN AI: BỎ SÓT ĐỢT TẤN CÔNG (False Negative - Âm tính giả)</strong><br>
      Mô hình <em>${modelName}</em> đánh giá điểm tin cậy ${pkt.confidence}% thấp hơn threshold ${aiState.threshold}%. Hậu quả: DDoS lọt qua bảo vệ! <em>Khắc phục: Giảm ngưỡng Threshold xuống hoặc dùng mô hình học sâu DNN.</em>
    </div>`;
  }

  content.innerHTML = `
    <div class="pdp-field-row">
      <span class="pdp-field-name">📊 Packet Rate (PPS)</span>
      <span class="pdp-field-val">${pkt.pps.toLocaleString()} pps</span>
      <span class="pdp-field-explain">Chuẩn bình thường: &lt;2,000 pps | Tấn công: &gt;20,000 pps. AI dùng con số này để đo mật độ dội bom.</span>
    </div>
    <div class="pdp-field-row">
      <span class="pdp-field-name">📏 StdDev Size (Độ lệch)</span>
      <span class="pdp-field-val">${pkt.sizeStdDev} Bytes</span>
      <span class="pdp-field-explain">Chuẩn bình thường: &gt;150B (kích thước biến thiên tự nhiên) | Tấn công SYN/UDP: &approx;0B (gói tin bị botnet sinh ra giống hệt nhau).</span>
    </div>
    <div class="pdp-field-row">
      <span class="pdp-field-name">🔄 SYN/ACK Ratio</span>
      <span class="pdp-field-val">${pkt.synAckRatio} : 1</span>
      <span class="pdp-field-explain">Chuẩn bình thường: ~1:1 (bắt tay 3 bước sòng phẳng) | Tấn công SYN Flood: &gt;15:1 (gửi SYN xong rồi bỏ trốn).</span>
    </div>
    <div class="pdp-field-row">
      <span class="pdp-field-name">🌐 IP Subnet Dispersion</span>
      <span class="pdp-field-val">${pkt.ipDispersion}</span>
      <span class="pdp-field-explain">Chuẩn bình thường: &gt;0.85 (từ khắp nơi trên toàn cầu) | Tấn công: &lt;0.20 (tập trung từ vài dãy IP botnet bị điều khiển).</span>
    </div>
    <div class="pdp-field-row">
      <span class="pdp-field-name">🤖 Thuật toán & Ngưỡng</span>
      <span class="pdp-field-val">${modelName} (Ngưỡng ${aiState.threshold}%)</span>
      <span class="pdp-field-explain">Điểm tin cậy dự đoán: <strong>${pkt.confidence}%</strong>. Nếu $\\ge ${aiState.threshold}\\%$ $\\rightarrow$ Chặn!</span>
    </div>
    ${decisionExplain}
  `;

  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function updateAIDashboardUI() {
  const elTotal = document.getElementById('ai-stat-total');
  const elTp = document.getElementById('ai-stat-tp');
  const elFp = document.getElementById('ai-stat-fp');
  const elAcc = document.getElementById('ai-stat-acc');

  if (elTotal) elTotal.textContent = aiState.totalAnalyzed;
  if (elTp) elTp.textContent = aiState.truePositives;
  if (elFp) elFp.textContent = aiState.falsePositives;

  if (elAcc) {
    if (aiState.totalAnalyzed === 0) {
      elAcc.textContent = '0%';
    } else {
      const correct = aiState.truePositives + aiState.trueNegatives;
      const accPct = ((correct / aiState.totalAnalyzed) * 100).toFixed(1);
      elAcc.textContent = `${accPct}%`;
    }
  }
}

function updateAILiveExplanation(isActualAttack, aiPredictsAttack, confidence, pps, stdDev, synAck) {
  const explainTitle = document.getElementById('ai-live-explain-title');
  const explainText = document.getElementById('ai-live-explain-text');
  const explainPanel = document.getElementById('ai-live-explain-panel');
  if (!explainTitle || !explainText) return;

  if (aiPredictsAttack && isActualAttack) {
    explainTitle.textContent = `🎯 AI phát hiện chính xác Tấn công DDoS (${confidence}% độ tin cậy)`;
    explainText.textContent = `Thuật toán phát hiện Packet Rate tăng vọt (${pps.toLocaleString()} pps) kết hợp với kích thước gói tin gần như không đổi (StdDev = ${stdDev}B) và tỷ lệ SYN/ACK = ${synAck}. Click vào dòng packet bên trên để soi chi tiết!`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card danger';
  } else if (aiPredictsAttack && !isActualAttack) {
    explainTitle.textContent = `⚠️ CẢNH BÁO: Dương tính giả (False Positive) — Chặn nhầm!`;
    explainText.textContent = `AI đã chặn nhầm một người dùng hợp lệ! Nguyên nhân: Ngưỡng tin cậy (Threshold) hiện tại đang đặt ở ${aiState.threshold}%, khiến mô hình quá nhạy cảm. Click vào dòng packet bên trên để soi chi tiết lý do chặn nhầm!`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card warn';
  } else if (!aiPredictsAttack && isActualAttack) {
    explainTitle.textContent = `💥 CẢNH BÁO: Âm tính giả (False Negative) — Bỏ sót tấn công!`;
    explainText.textContent = `Đợt tấn công đã lọt qua mắt AI! Nguyên nhân: Ngưỡng Threshold quá cao (${aiState.threshold}%) hoặc mô hình Decision Tree đơn giản chưa đủ nhạy. Hãy thử đổi sang mô hình Random Forest hoặc Deep Learning!`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card warn';
  } else {
    explainTitle.textContent = `🟢 Traffic hợp lệ — AI cho phép lưu thông`;
    explainText.textContent = `Traffic có tần suất bình thường (${pps.toLocaleString()} pps), kích thước gói tin biến thiên tự nhiên (${stdDev}B) đúng chuẩn người dùng gõ web. AI xác nhận an toàn.`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card success';
  }
}

// Auto init on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAIDetectionDemo);
} else {
  initAIDetectionDemo();
}
