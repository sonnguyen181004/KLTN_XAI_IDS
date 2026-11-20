/**
 * ml-concepts.js — Quản lý Khái niệm ML & XAI + Demo Mô phỏng SHAP Kéo co & Confusion Matrix
 */

// 1. SHAP Tug-of-War Interactive State
let shapState = {
  pps: 25000,
  stdDev: 2.5,
  synAck: 20,
  ipDisp: 0.1
};

// 2. Confusion Matrix Interactive State
let cmThreshold = 50;

function initMLConceptsSection() {
  initSHAPTugOfWar();
  initConfusionMatrixDemo();
}

// =============================================
// DEMO 1: SHAP FORCE PLOT TUG-OF-WAR DEMO
// =============================================
function initSHAPTugOfWar() {
  const ppsSlider = document.getElementById('shap-pps-slider');
  const stdDevSlider = document.getElementById('shap-std-slider');
  const synAckSlider = document.getElementById('shap-syn-slider');

  if (ppsSlider) {
    ppsSlider.addEventListener('input', (e) => {
      shapState.pps = parseInt(e.target.value);
      document.getElementById('shap-pps-val').textContent = `${shapState.pps.toLocaleString()} pps`;
      recalculateSHAP();
    });
  }

  if (stdDevSlider) {
    stdDevSlider.addEventListener('input', (e) => {
      shapState.stdDev = parseFloat(e.target.value);
      document.getElementById('shap-std-val').textContent = `${shapState.stdDev} B`;
      recalculateSHAP();
    });
  }

  if (synAckSlider) {
    synAckSlider.addEventListener('input', (e) => {
      shapState.synAck = parseFloat(e.target.value);
      document.getElementById('shap-syn-val').textContent = `${shapState.synAck} : 1`;
      recalculateSHAP();
    });
  }

  recalculateSHAP();
}

function recalculateSHAP() {
  // Base value: 0.10 (Bình thường)
  const baseValue = 0.10;
  
  // Calculate SHAP contributions
  let shapPPS = shapState.pps > 5000 ? Math.min(0.45, (shapState.pps / 50000) * 0.45) : -0.15;
  let shapStd = shapState.stdDev < 50 ? Math.min(0.35, (1 - shapState.stdDev / 50) * 0.35) : -0.20;
  let shapSyn = shapState.synAck > 3 ? Math.min(0.25, (shapState.synAck / 30) * 0.25) : -0.10;

  const totalScore = Math.min(0.99, Math.max(0.01, baseValue + shapPPS + shapStd + shapSyn));
  const isAttack = totalScore >= 0.50;

  // Update Score UI
  const scoreVal = document.getElementById('shap-total-score');
  const scoreBadge = document.getElementById('shap-result-badge');

  if (scoreVal) scoreVal.textContent = (totalScore * 100).toFixed(1) + '%';
  if (scoreBadge) {
    if (isAttack) {
      scoreBadge.textContent = '🔴 KẾT LUẬN SHAP: DDOS ATTACK';
      scoreBadge.className = 'sec-badge danger';
    } else {
      scoreBadge.textContent = '🟢 KẾT LUẬN SHAP: TRAFFIC BÌNH THƯỜNG';
      scoreBadge.className = 'sec-badge success';
    }
  }

  // Update Visual Arrows
  updateSHAPArrow('shap-bar-pps', shapPPS);
  updateSHAPArrow('shap-bar-std', shapStd);
  updateSHAPArrow('shap-bar-syn', shapSyn);

  // Live Explanation Update
  updateSHAPLiveExplanation(shapPPS, shapStd, shapSyn, totalScore, isAttack);
}

function updateSHAPArrow(barId, val) {
  const bar = document.getElementById(barId);
  if (!bar) return;

  const pct = Math.min(100, Math.abs(val) * 200);
  bar.style.width = `${pct}%`;

  if (val > 0) {
    bar.style.background = 'var(--red)';
    bar.textContent = `+${val.toFixed(2)} (Đẩy về DDoS)`;
  } else {
    bar.style.background = 'var(--green)';
    bar.textContent = `${val.toFixed(2)} (Kéo về Bình thường)`;
  }
}

function updateSHAPLiveExplanation(ppsVal, stdVal, synVal, totalScore, isAttack) {
  const explainTitle = document.getElementById('shap-explain-title');
  const explainText = document.getElementById('shap-explain-text');
  const explainPanel = document.getElementById('shap-explain-panel');
  if (!explainTitle || !explainText) return;

  let topFactor = 'Packet Rate';
  let topVal = ppsVal;
  if (stdVal > topVal) { topFactor = 'Độ lệch kích thước (StdDev)'; topVal = stdVal; }
  if (synVal > topVal) { topFactor = 'Tỷ lệ SYN/ACK'; topVal = synVal; }

  if (isAttack) {
    explainTitle.textContent = `🎯 SHAP Giải thích: Tấn công DDoS với độ tin cậy ${(totalScore * 100).toFixed(1)}%`;
    explainText.innerHTML = `Yếu tố đóng góp lớn nhất đẩy kết quả về hướng Tấn công là <strong>${topFactor}</strong> (cộng +${topVal.toFixed(2)} điểm SHAP). Thuật toán SHAP cho thấy các lực kéo màu ĐỎ đang áp đảo hoàn toàn các lực kéo màu XANH!`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card danger';
  } else {
    explainTitle.textContent = `🟢 SHAP Giải thích: Traffic Bình thường với độ an toàn ${((1 - totalScore) * 100).toFixed(1)}%`;
    explainText.innerHTML = `Các yếu tố màu XANH (kích thước biến thiên tự nhiên, Packet Rate thấp) đang kéo điểm số về mức an toàn. Điểm tổng hợp SHAP chỉ đạt ${(totalScore * 100).toFixed(1)}% (thấp hơn ngưỡng 50%).`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card success';
  }
}

// =============================================
// DEMO 2: CONFUSION MATRIX & METRICS SIMULATOR
// =============================================
function initConfusionMatrixDemo() {
  const slider = document.getElementById('cm-threshold-slider');
  const valText = document.getElementById('cm-threshold-val');

  if (slider) {
    slider.addEventListener('input', (e) => {
      cmThreshold = parseInt(e.target.value);
      if (valText) valText.textContent = `${cmThreshold}%`;
      recalculateConfusionMatrix();
    });
  }

  recalculateConfusionMatrix();
}

function recalculateConfusionMatrix() {
  // Out of 1000 sample packets (200 DDoS, 800 Normal)
  const totalDDoS = 200;
  const totalNormal = 800;

  // Higher threshold = stricter AI (fewer False Positives, but higher False Negatives)
  // Lower threshold = sensitive AI (fewer False Negatives, higher False Positives)
  let tp, fn, fp, tn;

  if (cmThreshold <= 30) {
    // Highly sensitive
    tp = 198; fn = 2;   // Bắt sạch DDoS (Recall ~99%)
    fp = 120; tn = 680; // Chặn nhầm nhiều (Precision thấp)
  } else if (cmThreshold <= 60) {
    // Balanced
    tp = 190; fn = 10;  // Recall 95%
    fp = 15;  tn = 785; // Precision 92.7%
  } else {
    // Stricter
    tp = 160; fn = 40;  // Bỏ sót 40 đợt DDoS (Recall 80%)
    fp = 3;   tn = 797; // Hầu như không chặn nhầm (Precision 98.1%)
  }

  const accuracy = (((tp + tn) / 1000) * 100).toFixed(1);
  const precision = (((tp) / (tp + fp)) * 100).toFixed(1);
  const recall = (((tp) / (tp + fn)) * 100).toFixed(1);
  const f1 = ((2 * (precision * recall) / (parseFloat(precision) + parseFloat(recall)))).toFixed(1);

  // Update Matrix Cells
  document.getElementById('cm-cell-tp').textContent = tp;
  document.getElementById('cm-cell-fn').textContent = fn;
  document.getElementById('cm-cell-fp').textContent = fp;
  document.getElementById('cm-cell-tn').textContent = tn;

  // Update Metrics UI
  document.getElementById('cm-metric-acc').textContent = `${accuracy}%`;
  document.getElementById('cm-metric-prec').textContent = `${precision}%`;
  document.getElementById('cm-metric-rec').textContent = `${recall}%`;
  document.getElementById('cm-metric-f1').textContent = `${f1}%`;

  // Update Dynamic Explanation
  updateCMLiveExplanation(tp, fn, fp, tn, precision, recall, f1);
}

function updateCMLiveExplanation(tp, fn, fp, tn, prec, rec, f1) {
  const explainTitle = document.getElementById('cm-explain-title');
  const explainText = document.getElementById('cm-explain-text');
  const explainPanel = document.getElementById('cm-explain-panel');
  if (!explainTitle || !explainText) return;

  if (cmThreshold <= 30) {
    explainTitle.textContent = `🟢 Chế độ Ưu tiên RECALL (Độ nhạy ${rec}%) — Chống Bỏ Sót DDoS`;
    explainText.innerHTML = `AI đang cài ở Ngưỡng nhạy thấp (${cmThreshold}%). Kết quả: Bắt được <strong>${tp}/${tp+fn} đợt DDoS</strong> (Recall = ${rec}%), chỉ bỏ sót ${fn} đợt. Tuy nhiên, cái giá phải trả là <strong>Chặn nhầm ${fp} khách hàng thật</strong> (False Positives). Thích hợp cho hệ thống Ngân hàng/Quốc phòng!`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card success';
  } else if (cmThreshold <= 60) {
    explainTitle.textContent = `🏆 Chế độ CÂN BẰNG F1-SCORE (${f1}%) — Điểm Cân Bằng Tối Ưu`;
    explainText.innerHTML = `AI đạt điểm F1-Score tối ưu <strong>${f1}%</strong>! Cân bằng hoàn hảo giữa việc phát hiện <strong>${tp} đợt DDoS (Recall ${rec}%)</strong> và chỉ chặn nhầm <strong>${fp} người dùng (Precision ${prec}%)</strong>. Đây là chỉ số chuẩn nhất để đánh giá hiệu năng hệ thống AI.`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card success';
  } else {
    explainTitle.textContent = `⚠️ Chế độ Ưu tiên PRECISION (${prec}%) — Nguy cơ BỎ SÓT DDoS!`;
    explainText.innerHTML = `AI cài ở Ngưỡng quá cao (${cmThreshold}%). Tuy hầu như không chặn nhầm người dùng nào (Chỉ chặn nhầm ${fp} người), nhưng AI đã <strong>BỎ SÓT ${fn} đợt tấn công DDoS (False Negatives)</strong>! Trong bảo mật, đây là điều cực kỳ nguy hiểm.`;
    if (explainPanel) explainPanel.className = 'live-explain-panel glass-card danger';
  }
}

document.addEventListener('DOMContentLoaded', initMLConceptsSection);
