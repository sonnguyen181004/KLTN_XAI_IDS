/**
 * Network Attack Map Demo
 * Educational simulation of a global DDoS attack map.
 */

function initNetworkMap() {
  const els = {
    canvas: document.getElementById('map-canvas'),
    ipCount: document.getElementById('map-ip-count'),
    pps: document.getElementById('map-pps'),
    bandwidth: document.getElementById('map-bandwidth'),
    countries: document.getElementById('map-countries'),
    countryList: document.getElementById('country-list'),
    btnStart: document.getElementById('btn-start-map'),
    btnReset: document.getElementById('btn-reset-map')
  };

  if (!els.canvas) return;

  const ctx = els.canvas.getContext('2d');
  
  // Trạng thái hệ thống
  let state = {
    isActive: false,
    startTime: 0,
    width: 0,
    height: 0,
    particles: [], // Hoạt ảnh các đường tấn công
    stats: {
      ips: 0,
      pps: 0,
      bw: 0
    },
    intervalId: null
  };

  // Danh sách các quốc gia tấn công
  const countryData = [
    { name: '🇨🇳 Trung Quốc', weight: 35, lat: 35, lng: 105 },
    { name: '🇷🇺 Nga', weight: 25, lat: 60, lng: 90 },
    { name: '🇺🇸 Hoa Kỳ', weight: 15, lat: 38, lng: -97 },
    { name: '🇧🇷 Brazil', weight: 10, lat: -10, lng: -55 },
    { name: '🇮🇳 Ấn Độ', weight: 8, lat: 20, lng: 77 },
    { name: '🇻🇳 Việt Nam', weight: 2, lat: 14, lng: 108 },
    { name: '🇩🇪 Đức', weight: 1, lat: 51, lng: 10 },
    { name: '🇬🇧 Anh', weight: 1, lat: 55, lng: -3 },
    { name: '🇰🇷 Hàn Quốc', weight: 1, lat: 36, lng: 127 },
    { name: '🇯🇵 Nhật Bản', weight: 1, lat: 36, lng: 138 },
    { name: '🇮🇷 Iran', weight: 1, lat: 32, lng: 53 }
  ];

  // Mục tiêu (Server giả định ở Châu Âu / Frankfurt)
  const target = { lat: 50, lng: 8 };

  // Hàm chuyển đổi Toạ độ địa lý (Lat, Lng) sang Toạ độ màn hình (x,y)
  function project(lat, lng) {
    // Chuyển đổi đơn giản Mercator-like
    const x = (lng + 180) * (state.width / 360);
    const latRad = lat * Math.PI / 180;
    const mercN = Math.log(Math.tan((Math.PI / 4) + (latRad / 2)));
    const y = (state.height / 2) - (state.width * mercN / (2 * Math.PI));
    return { x, y };
  }

  // Thay đổi kích thước Canvas
  function resizeCanvas() {
    const parent = els.canvas.parentElement;
    state.width = parent.clientWidth;
    state.height = parent.clientHeight || 400;
    els.canvas.width = state.width;
    els.canvas.height = state.height;
  }

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  // Tạo các điểm bản đồ tĩnh (Lục địa)
  function drawMapBackground() {
    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, state.width, state.height);

    // Vẽ lưới (Grid) Cyberpunk
    ctx.strokeStyle = 'rgba(0, 245, 255, 0.1)';
    ctx.lineWidth = 1;
    for (let x = 0; x < state.width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, state.height);
      ctx.stroke();
    }
    for (let y = 0; y < state.height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(state.width, y);
      ctx.stroke();
    }

    // Vẽ đường xích đạo giả
    ctx.strokeStyle = 'rgba(0, 245, 255, 0.2)';
    const eqY = project(0, 0).y;
    ctx.beginPath();
    ctx.moveTo(0, eqY);
    ctx.lineTo(state.width, eqY);
    ctx.stroke();
  }

  // Render danh sách quốc gia
  function renderCountryList() {
    if (!els.countryList) return;
    els.countryList.innerHTML = '';
    
    // Lấy top 5 quốc gia
    const topCountries = countryData.slice(0, 5);
    
    topCountries.forEach(country => {
      const div = document.createElement('div');
      div.className = 'mb-2';
      
      const header = document.createElement('div');
      header.className = 'flex justify-between text-xs mb-1';
      header.innerHTML = `<span>${country.name}</span><span class="text-red-400">${state.isActive ? (country.weight * state.stats.ips / 100).toFixed(0) : 0} IPs</span>`;
      
      const barBg = document.createElement('div');
      barBg.className = 'h-1.5 w-full bg-gray-800 rounded overflow-hidden';
      
      const barFill = document.createElement('div');
      barFill.className = 'h-full bg-red-500 transition-all duration-300';
      barFill.style.width = state.isActive ? `${country.weight}%` : '0%';
      barFill.style.boxShadow = '0 0 5px #ff003c';
      
      barBg.appendChild(barFill);
      div.appendChild(header);
      div.appendChild(barBg);
      
      els.countryList.appendChild(div);
    });
  }

  // Cập nhật số liệu thống kê
  function updateStats() {
    if (!state.isActive) return;
    
    const now = Date.now();
    const elapsed = (now - state.startTime) / 1000; // Giây
    
    // Tăng dần theo thời gian
    const progress = Math.min(1, elapsed / 15); // Max out sau 15 giây
    
    // Tính toán số liệu
    state.stats.ips = Math.floor(Math.random() * 5000 + progress * 45000); // Lên đến ~50k
    state.stats.pps = Math.floor(Math.random() * 200000 + progress * 1800000); // Lên đến ~2M
    state.stats.bw = (Math.random() * 0.2 + progress * 1.0).toFixed(2); // Lên đến 1.2 Gbps
    
    if (els.ipCount) els.ipCount.innerText = state.stats.ips.toLocaleString();
    if (els.pps) els.pps.innerText = (state.stats.pps / 1000000).toFixed(2) + ' M';
    if (els.bandwidth) els.bandwidth.innerText = state.stats.bw;
    if (els.countries) els.countries.innerText = state.stats.ips > 0 ? countryData.length : 0;
    
    renderCountryList();
  }

  // Hoạt ảnh
  function animate() {
    requestAnimationFrame(animate);
    
    // Fade effect cho vệt đuôi
    ctx.fillStyle = 'rgba(10, 10, 15, 0.2)';
    ctx.fillRect(0, 0, state.width, state.height);
    
    drawMapBackground();

    const targetPos = project(target.lat, target.lng);
    
    // Vẽ Server Mục tiêu (Blue)
    const pulseRadius = 5 + Math.sin(Date.now() / 200) * 3;
    ctx.beginPath();
    ctx.arc(targetPos.x, targetPos.y, pulseRadius, 0, Math.PI * 2);
    ctx.fillStyle = '#00f5ff';
    ctx.shadowBlur = 15;
    ctx.shadowColor = '#00f5ff';
    ctx.fill();
    ctx.shadowBlur = 0; // Reset
    
    // Vẽ các Nguồn tấn công (Red)
    countryData.forEach(country => {
      const pos = project(country.lat, country.lng);
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 3, 0, Math.PI * 2);
      ctx.fillStyle = state.isActive ? '#ff003c' : '#333';
      if (state.isActive) {
        ctx.shadowBlur = 10;
        ctx.shadowColor = '#ff003c';
      }
      ctx.fill();
      ctx.shadowBlur = 0;
    });

    if (state.isActive) {
      // Sinh particles
      if (Math.random() < 0.6) {
        // Chọn ngẫu nhiên nguồn
        const sourceCountry = countryData[Math.floor(Math.random() * countryData.length)];
        const sourcePos = project(sourceCountry.lat, sourceCountry.lng);
        
        state.particles.push({
          x: sourcePos.x,
          y: sourcePos.y,
          targetX: targetPos.x,
          targetY: targetPos.y,
          progress: 0,
          speed: 0.01 + Math.random() * 0.02,
          color: Math.random() > 0.8 ? '#ff8800' : '#ff003c'
        });
      }
    }

    // Vẽ và di chuyển Particles
    for (let i = state.particles.length - 1; i >= 0; i--) {
      let p = state.particles[i];
      p.progress += p.speed;
      
      if (p.progress >= 1) {
        state.particles.splice(i, 1);
        continue;
      }

      // Quỹ đạo hình cung Parabol (bezier)
      const ctrlX = (p.x + p.targetX) / 2;
      const ctrlY = (p.y + p.targetY) / 2 - 100; // Đẩy lên tạo vòng cung
      
      // Tính toạ độ hiện tại trên đường cong
      const t = p.progress;
      const invT = 1 - t;
      const currentX = invT * invT * p.x + 2 * invT * t * ctrlX + t * t * p.targetX;
      const currentY = invT * invT * p.y + 2 * invT * t * ctrlY + t * t * p.targetY;

      // Vẽ vệt tia
      ctx.beginPath();
      ctx.arc(currentX, currentY, 2, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowBlur = 5;
      ctx.shadowColor = p.color;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  // Điều khiển
  if (els.btnStart) {
    els.btnStart.addEventListener('click', () => {
      state.isActive = !state.isActive;
      
      if (state.isActive) {
        state.startTime = Date.now();
        els.btnStart.innerText = 'Dừng tấn công';
        els.btnStart.classList.replace('text-cyan-400', 'text-red-500');
        els.btnStart.classList.replace('border-cyan-400', 'border-red-500');
        state.intervalId = setInterval(updateStats, 500);
        if (typeof window.updateMapExplain === 'function') {
          window.updateMapExplain(true, state.stats.ips, state.stats.pps, state.stats.bw);
        }
      } else {
        els.btnStart.innerText = 'Bắt đầu';
        els.btnStart.classList.replace('text-red-500', 'text-cyan-400');
        els.btnStart.classList.replace('border-red-500', 'border-cyan-400');
        clearInterval(state.intervalId);
        if (typeof window.updateMapExplain === 'function') {
          window.updateMapExplain(false, 0, 0, 0);
        }
      }
    });
  }

  if (els.btnReset) {
    els.btnReset.addEventListener('click', () => {
      state.isActive = false;
      state.particles = [];
      state.stats = { ips: 0, pps: 0, bw: 0 };
      
      if (els.ipCount) els.ipCount.innerText = '0';
      if (els.pps) els.pps.innerText = '0';
      if (els.bandwidth) els.bandwidth.innerText = '0';
      if (els.countries) els.countries.innerText = '0';
      
      if (els.btnStart) {
        els.btnStart.innerText = 'Bắt đầu';
        els.btnStart.classList.replace('text-red-500', 'text-cyan-400');
        els.btnStart.classList.replace('border-red-500', 'border-cyan-400');
      }
      
      if (state.intervalId) clearInterval(state.intervalId);
      renderCountryList();
      if (typeof window.updateMapExplain === 'function') {
        window.updateMapExplain(false, 0, 0, 0);
      }
    });
  }

  // Bắt đầu ngay khi load
  renderCountryList();
  requestAnimationFrame(animate);
}

// Khởi tạo module
document.addEventListener('DOMContentLoaded', initNetworkMap);
initNetworkMap();
