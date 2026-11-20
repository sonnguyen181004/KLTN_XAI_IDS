/**
 * Server Health Simulator Demo
 * Educational simulation of server load during a DDoS attack.
 */

function initServerSim() {
  // Trạng thái ứng dụng
  let state = {
    bots: 0,
    health: 100,
    firewall: false,
    intervalId: null,
    isDown: false,
    packets: [], // Cho hoạt ảnh canvas
    lastFrameTime: 0
  };

  // Các Element DOM
  const els = {
    server: document.getElementById('sim-server'),
    healthBar: document.getElementById('server-health-bar'),
    healthValue: document.getElementById('server-health-value'),
    statusLabel: document.getElementById('server-status-label'),
    statusText: document.getElementById('server-status-text'),
    rps: document.getElementById('server-rps'),
    bandwidth: document.getElementById('server-bandwidth'),
    cpu: document.getElementById('server-cpu'),
    ram: document.getElementById('server-ram'),
    botCount: document.getElementById('bot-count'),
    cpuBar: document.getElementById('cpu-bar'),
    ramBar: document.getElementById('ram-bar'),
    bwBar: document.getElementById('bw-bar'),
    cpuPct: document.getElementById('cpu-pct'),
    ramPct: document.getElementById('ram-pct'),
    bwPct: document.getElementById('bw-pct'),
    log: document.getElementById('server-log'),
    smoke: document.getElementById('server-smoke'),
    fire: document.getElementById('server-fire'),
    indPwr: document.getElementById('ind-pwr'),
    indNet: document.getElementById('ind-net'),
    indHdd: document.getElementById('ind-hdd'),
    canvas: document.getElementById('packet-canvas'),
    btnAddBot: document.getElementById('btn-add-bot'),
    btnAddBots: document.getElementById('btn-add-bots'),
    btnFlood: document.getElementById('btn-flood'),
    btnFirewall: document.getElementById('btn-firewall'),
    btnReset: document.getElementById('btn-reset-server'),
    fwLabel: document.getElementById('fw-label')
  };

  let ctx = null;
  if (els.canvas) {
    ctx = els.canvas.getContext('2d');
    els.canvas.width = 300;
    els.canvas.height = 160;
  }

  // Hàm thêm log
  function addLog(msg, isWarning = false) {
    if (!els.log) return;
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;
    const logLine = document.createElement('div');
    logLine.className = 'log-line text-xs font-mono ' + (isWarning ? 'text-red-500' : 'text-cyan-400');
    logLine.innerText = `[${timeStr}] ${msg}`;
    els.log.prepend(logLine);
    
    // Giới hạn số dòng log
    while (els.log.children.length > 20) {
      els.log.removeChild(els.log.lastChild);
    }
  }

  // Cập nhật giao diện
  function updateUI() {
    if (!els.server) return;

    // Tính toán tài nguyên
    let baseRPS = 10;
    let baseBW = 0.5;
    let baseCPU = 5;
    let baseRAM = 15;

    let botRPS = state.bots * 50;
    let botBW = state.bots * 2;
    let botCPU = state.bots * 3;
    let botRAM = state.bots * 2;

    if (state.firewall) {
      botRPS *= 0.3; // Giảm 70% sát thương
      botBW *= 0.3;
      botCPU *= 0.3;
      botRAM *= 0.3;
    }

    let rps = baseRPS + botRPS;
    let bw = baseBW + botBW;
    let cpu = Math.min(100, baseCPU + botCPU);
    let ram = Math.min(100, baseRAM + botRAM);

    // Render thông số
    if (els.botCount) els.botCount.innerText = state.bots;
    if (els.rps) els.rps.innerText = rps.toFixed(0);
    if (els.bandwidth) els.bandwidth.innerText = bw.toFixed(1);
    if (els.cpu) els.cpu.innerText = cpu.toFixed(1);
    if (els.ram) els.ram.innerText = ram.toFixed(1);

    if (els.cpuBar) els.cpuBar.style.width = cpu + '%';
    if (els.cpuPct) els.cpuPct.innerText = cpu.toFixed(1) + '%';
    if (els.ramBar) els.ramBar.style.width = ram + '%';
    if (els.ramPct) els.ramPct.innerText = ram.toFixed(1) + '%';
    if (els.bwBar) els.bwBar.style.width = Math.min(100, bw) + '%'; // Max 100MB/s cho thanh biểu đồ
    if (els.bwPct) els.bwPct.innerText = bw.toFixed(1) + ' MB/s';

    // Cập nhật Health
    if (els.healthValue) els.healthValue.innerText = state.health.toFixed(1) + '%';
    if (els.healthBar) {
      els.healthBar.style.width = state.health + '%';
      
      // Đổi màu
      if (state.health > 70) els.healthBar.style.backgroundColor = '#00ff88'; // green
      else if (state.health > 40) els.healthBar.style.backgroundColor = '#ffd700'; // yellow
      else if (state.health > 15) els.healthBar.style.backgroundColor = '#ff8800'; // orange
      else els.healthBar.style.backgroundColor = '#ff003c'; // red
    }

    // Cập nhật Status
    let status = 'ONLINE';
    let statusClass = 'text-green-400';
    
    if (state.health <= 0) {
      status = 'DOWN';
      statusClass = 'text-red-600 font-bold';
      state.isDown = true;
    } else if (state.health <= 15) {
      status = 'OVERLOADED';
      statusClass = 'text-red-500';
    } else if (state.health <= 40) {
      status = 'DEGRADED';
      statusClass = 'text-yellow-400';
    }

    if (els.statusLabel) {
      els.statusLabel.innerText = status;
      els.statusLabel.className = statusClass;
    }
    if (els.statusText) {
      els.statusText.innerText = status;
      els.statusText.className = statusClass;
    }

    // Hiệu ứng Server
    if (els.smoke) els.smoke.classList.toggle('hidden', state.health > 40);
    if (els.fire) els.fire.classList.toggle('hidden', state.health > 15);
    
    if (state.health <= 30 && state.health > 0) {
      els.server.classList.add('server-shaking');
    } else {
      els.server.classList.remove('server-shaking');
    }

    if (state.health <= 0) {
      els.server.classList.add('server-critical');
    } else {
      els.server.classList.remove('server-critical');
    }

    // Nhấp nháy indicator khi có bot
    if (state.bots > 0 && state.health > 0) {
      if (els.indNet) els.indNet.style.backgroundColor = Math.random() > 0.5 ? '#ff003c' : '#333';
      if (els.indHdd) els.indHdd.style.backgroundColor = Math.random() > 0.3 ? '#ff003c' : '#333';
    } else {
      if (els.indNet) els.indNet.style.backgroundColor = '#00ff88';
      if (els.indHdd) els.indHdd.style.backgroundColor = '#00ff88';
    }

    // Trạng thái nút bấm
    if (state.isDown) {
      if (els.btnAddBot) els.btnAddBot.disabled = true;
      if (els.btnAddBots) els.btnAddBots.disabled = true;
      if (els.btnFlood) els.btnFlood.disabled = true;
      if (!els.log.innerHTML.includes('SERVER NGỪNG HOẠT ĐỘNG')) {
        addLog('[ SERVER NGỪNG HOẠT ĐỘNG! ]', true);
      }
    } else {
      if (els.btnAddBot) els.btnAddBot.disabled = false;
      if (els.btnAddBots) els.btnAddBots.disabled = false;
      if (els.btnFlood) els.btnFlood.disabled = false;
    }
  }

  // Cập nhật State theo thời gian
  function tick() {
    if (state.isDown) return;

    if (state.bots > 0) {
      let damage = state.bots * 0.1;
      if (state.firewall) damage *= 0.3;
      
      state.health = Math.max(0, state.health - damage);
      
      // Log cảnh báo ngẫu nhiên
      if (state.health < 40 && Math.random() < 0.1) {
        addLog('[ CẢNH BÁO: Tải server rất cao! ]', true);
      }
      if ((state.bots * 3) > 80 && Math.random() < 0.1) {
        addLog('[ CẢNH BÁO: CPU vượt 80% ]', true);
      }
    } else if (state.health < 100) {
      // Phục hồi
      state.health = Math.min(100, state.health + 0.5);
    }

    updateUI();
    
    let botCPU = state.bots * 3;
    let botRAM = state.bots * 2;
    if (state.firewall) {
      botCPU *= 0.3;
      botRAM *= 0.3;
    }
    let cpu = Math.min(100, 5 + botCPU).toFixed(1);
    let ram = Math.min(100, 15 + botRAM).toFixed(1);
    if (typeof window.updateSimExplain === 'function') {
      window.updateSimExplain(state.bots, state.health.toFixed(1), cpu, ram, state.firewall);
    }
  }

  // Animation Canvas Packets
  function drawPackets(timestamp) {
    if (!ctx) return;
    requestAnimationFrame(drawPackets);
    
    ctx.clearRect(0, 0, els.canvas.width, els.canvas.height);
    
    if (state.isDown) return; // Không vẽ khi sập

    // Spawn packets
    let spawnRate = state.bots > 0 ? (state.bots / 10) + 1 : 0.5;
    if (Math.random() < spawnRate * 0.5) {
      let isAttack = state.bots > 0 && Math.random() < (state.bots / (state.bots + 5));
      state.packets.push({
        x: 0,
        y: Math.random() * els.canvas.height,
        speed: (Math.random() * 2 + 1) * (state.bots > 0 ? 2 : 1),
        color: isAttack ? '#ff003c' : '#00ff88',
        size: isAttack ? 3 : 2
      });
    }

    // Update and draw
    for (let i = state.packets.length - 1; i >= 0; i--) {
      let p = state.packets[i];
      p.x += p.speed;
      
      // Xử lý tường lửa (chặn gói màu đỏ ở giữa)
      if (state.firewall && p.color === '#ff003c' && p.x > els.canvas.width / 2) {
        // Hiệu ứng chặn (nhỏ lại rồi biến mất)
        p.size *= 0.8;
        if (p.size < 0.5) {
          state.packets.splice(i, 1);
          continue;
        }
      }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.fill();

      // Xóa gói ra khỏi màn hình
      if (p.x > els.canvas.width) {
        state.packets.splice(i, 1);
      }
    }

    // Vẽ vạch tường lửa
    if (state.firewall) {
      ctx.fillStyle = 'rgba(0, 245, 255, 0.3)';
      ctx.fillRect(els.canvas.width / 2, 0, 5, els.canvas.height);
      ctx.fillStyle = '#00f5ff';
      ctx.fillRect(els.canvas.width / 2 + 1, 0, 3, els.canvas.height);
    }
  }

  // Thêm Bot
  function addBots(amount) {
    if (state.isDown) return;
    state.bots += amount;
    addLog(`[ +${amount} bot đã tham gia tấn công ]`);
    updateUI();
  }

  // Lắng nghe sự kiện
  if (els.btnAddBot) els.btnAddBot.addEventListener('click', () => addBots(1));
  if (els.btnAddBots) els.btnAddBots.addEventListener('click', () => addBots(10));
  if (els.btnFlood) els.btnFlood.addEventListener('click', () => addBots(100));
  
  if (els.btnFirewall) {
    els.btnFirewall.addEventListener('click', () => {
      state.firewall = !state.firewall;
      if (els.fwLabel) {
        els.fwLabel.innerText = state.firewall ? 'FIREWALL: BẬT' : 'FIREWALL: TẮT';
      }
      els.btnFirewall.style.borderColor = state.firewall ? '#00f5ff' : '';
      els.btnFirewall.style.backgroundColor = state.firewall ? 'rgba(0, 245, 255, 0.2)' : '';
      
      if (state.firewall) {
        addLog('[ Firewall đã được kích hoạt ]');
      } else {
        addLog('[ Firewall đã bị tắt ]', true);
      }
      updateUI();
    });
  }

  if (els.btnReset) {
    els.btnReset.addEventListener('click', () => {
      state.bots = 0;
      state.health = 100;
      state.firewall = false;
      state.isDown = false;
      state.packets = [];
      if (els.log) els.log.innerHTML = '';
      if (els.fwLabel) els.fwLabel.innerText = 'FIREWALL: TẮT';
      if (els.btnFirewall) {
        els.btnFirewall.style.borderColor = '';
        els.btnFirewall.style.backgroundColor = '';
      }
      addLog('[ Server đã được khởi động lại ]');
      updateUI();
    });
  }

  // Khởi chạy
  addLog('[ Server đang khởi động... ]');
  addLog('[ Server sẵn sàng tại cổng 8080 ]');
  state.intervalId = setInterval(tick, 500);
  requestAnimationFrame(drawPackets);
  updateUI();
}

// Khởi tạo module
document.addEventListener('DOMContentLoaded', initServerSim);
initServerSim();
