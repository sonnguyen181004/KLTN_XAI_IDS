// defense-lab.js
(function initDefenseLab() {
    // DOM elements
    const canvas = document.getElementById('defense-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const scoreDisplay = document.getElementById('defense-score');
    const timerDisplay = document.getElementById('defense-timer');
    const waveDisplay = document.getElementById('defense-wave');
    const hpBar = document.getElementById('defense-hp-bar');
    const hpText = document.getElementById('defense-hp-text');
    const logDiv = document.getElementById('defense-log');
    
    const startScreen = document.getElementById('defense-start-screen');
    const btnStart = document.getElementById('btn-start-defense');
    
    // Tools definition
    const tools = {
        rateLimiter: { btn: document.getElementById('btn-rate-limiter'), cd: document.getElementById('cd-rate-limiter'), duration: 5000, cooldown: 8000, reduction: 0.6, active: false, cdActive: false },
        waf: { btn: document.getElementById('btn-waf'), cd: document.getElementById('cd-waf'), duration: 5000, cooldown: 12000, reduction: 0.8, active: false, cdActive: false },
        cdn: { btn: document.getElementById('btn-cdn'), cd: document.getElementById('cd-cdn'), duration: 5000, cooldown: 15000, reduction: 0.7, active: false, cdActive: false },
        blacklist: { btn: document.getElementById('btn-blacklist'), cd: document.getElementById('cd-blacklist'), duration: 5000, cooldown: 5000, reduction: 0.5, active: false, cdActive: false }
    };
    
    // Game State
    let isPlaying = false;
    let hp = 100;
    let maxHp = 100;
    let score = 0;
    let wave = 1;
    let startTime = 0;
    let lastTime = 0;
    let waveTimer = 0;
    let particles = [];
    let explosions = [];
    let animationId;
    
    // Auto resize canvas to fit container
    function resizeCanvas() {
        if(canvas.parentElement) {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = 300;
        }
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
    
    // Helper to log events
    function addLog(msg, type='info') {
        if(!logDiv) return;
        const p = document.createElement('p');
        p.textContent = msg;
        p.style.color = type === 'warning' ? '#ff003c' : (type === 'success' ? '#00ff88' : '#00f5ff');
        p.style.margin = '2px 0';
        p.style.fontSize = '12px';
        p.style.fontFamily = 'monospace';
        logDiv.appendChild(p);
        logDiv.scrollTop = logDiv.scrollHeight;
    }
    
    function startGame() {
        if(startScreen) startScreen.classList.add('hidden');
        isPlaying = true;
        hp = maxHp;
        score = 0;
        wave = 1;
        startTime = Date.now();
        lastTime = startTime;
        waveTimer = 15000;
        particles = [];
        explosions = [];
        
        Object.values(tools).forEach(tool => {
            if(!tool.btn) return;
            tool.active = false;
            tool.cdActive = false;
            tool.btn.disabled = false;
            if(tool.cd) {
                tool.cd.style.transition = 'none';
                tool.cd.style.width = '0%';
            }
        });
        
        if(logDiv) logDiv.innerHTML = '';
        addLog('[ HỆ THỐNG PHÒNG THỦ KHỞI ĐỘNG ]', 'success');
        addLog('[ Đợt tấn công #1 bắt đầu! ]', 'warning');
        
        updateUI();
        if(animationId) cancelAnimationFrame(animationId);
        gameLoop();
    }
    
    function activateTool(toolName, logMsg) {
        const tool = tools[toolName];
        if (!tool || tool.cdActive) return;
        
        tool.active = true;
        tool.cdActive = true;
        if(tool.btn) tool.btn.disabled = true;
        addLog(logMsg, 'success');
        
        // Cooldown animation
        if(tool.cd) {
            tool.cd.style.transition = 'none';
            tool.cd.style.width = '100%';
            // force reflow
            void tool.cd.offsetWidth; 
            tool.cd.style.transition = `width ${tool.cooldown}ms linear`;
            tool.cd.style.width = '0%';
        }
        
        setTimeout(() => {
            tool.active = false;
        }, tool.duration);
        
        setTimeout(() => {
            tool.cdActive = false;
            if(tool.btn) tool.btn.disabled = false;
        }, tool.cooldown);
    }
    
    // Bind buttons
    if(tools.rateLimiter.btn) tools.rateLimiter.btn.addEventListener('click', () => activateTool('rateLimiter', '[ Rate Limiter kích hoạt — giảm 60% thiệt hại ]'));
    if(tools.waf.btn) tools.waf.btn.addEventListener('click', () => activateTool('waf', '[ WAF đang chặn traffic độc hại ]'));
    if(tools.cdn.btn) tools.cdn.btn.addEventListener('click', () => activateTool('cdn', '[ CDN Anycast kích hoạt — phân tán luồng tấn công ]'));
    if(tools.blacklist.btn) tools.blacklist.btn.addEventListener('click', () => activateTool('blacklist', '[ IP Blacklist kích hoạt — chặn các IP xấu ]'));
    
    if(btnStart) btnStart.addEventListener('click', startGame);
    
    function updateUI() {
        if(scoreDisplay) scoreDisplay.textContent = Math.floor(score);
        if(waveDisplay) waveDisplay.textContent = wave;
        if(hpText) hpText.textContent = `${Math.floor(hp)}/${maxHp}`;
        
        if(hpBar) {
            const hpPercent = Math.max(0, (hp / maxHp) * 100);
            hpBar.style.width = `${hpPercent}%`;
            
            if (hpPercent > 60) hpBar.style.background = '#00ff88';
            else if (hpPercent > 30) hpBar.style.background = '#ffd700';
            else hpBar.style.background = '#ff003c';
        }
        
        if (typeof window.updateDefenseExplain === 'function') {
            const activeToolsText = Object.keys(tools).filter(k => tools[k].active).join(', ');
            window.updateDefenseExplain(Math.floor(hp), wave, Math.floor(score), activeToolsText);
        }
        
        if(timerDisplay) {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const s = String(elapsed % 60).padStart(2, '0');
            timerDisplay.textContent = `${m}:${s}`;
        }
    }
    
    function drawServer() {
        const sX = canvas.width - 80;
        const sY = canvas.height / 2 - 40;
        
        // Server body
        ctx.fillStyle = '#1a1a24';
        ctx.strokeStyle = '#00f5ff';
        ctx.lineWidth = 2;
        ctx.fillRect(sX, sY, 60, 80);
        ctx.strokeRect(sX, sY, 60, 80);
        
        // blinking server lights
        const t = Date.now();
        ctx.fillStyle = t % 500 < 250 ? '#00ff88' : '#333';
        ctx.fillRect(sX + 10, sY + 10, 10, 10);
        ctx.fillStyle = t % 300 < 150 ? '#ff003c' : '#333';
        ctx.fillRect(sX + 10, sY + 30, 10, 10);
        ctx.fillStyle = t % 700 < 350 ? '#ffd700' : '#333';
        ctx.fillRect(sX + 10, sY + 50, 10, 10);
        
        // Shield effects stacking
        let shieldRadius = 60;
        
        if (tools.rateLimiter.active) { ctx.strokeStyle = '#00f5ff'; drawShield(sX+30, sY+40, shieldRadius); shieldRadius += 10; }
        if (tools.waf.active) { ctx.strokeStyle = '#00ff88'; drawShield(sX+30, sY+40, shieldRadius); shieldRadius += 10; }
        if (tools.cdn.active) { ctx.strokeStyle = '#ffd700'; drawShield(sX+30, sY+40, shieldRadius); shieldRadius += 10; }
        if (tools.blacklist.active) { ctx.strokeStyle = '#ff003c'; drawShield(sX+30, sY+40, shieldRadius); }
    }
    
    function drawShield(x, y, radius) {
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.lineWidth = 3;
        ctx.setLineDash([5, 5]);
        ctx.stroke();
        ctx.setLineDash([]); // reset
    }
    
    function spawnParticles(count) {
        for(let i=0; i<count; i++) {
            particles.push({
                x: -10,
                y: Math.random() * canvas.height,
                vx: 2 + Math.random() * 3 + wave * 0.5,
                vy: (Math.random() - 0.5) * 2,
                color: '#ff003c',
                size: 3 + Math.random() * 2
            });
        }
    }
    
    function gameLoop() {
        if (!isPlaying) return;
        
        const now = Date.now();
        const dt = now - lastTime;
        lastTime = now;
        
        // Damage Calculation
        let damagePerSec = 2 + (wave * 1);
        let reduction = 1;
        if (tools.rateLimiter.active) reduction *= (1 - tools.rateLimiter.reduction);
        if (tools.waf.active) reduction *= (1 - tools.waf.reduction);
        if (tools.cdn.active) reduction *= (1 - tools.cdn.reduction);
        if (tools.blacklist.active) reduction *= (1 - tools.blacklist.reduction);
        
        const actualDamage = damagePerSec * reduction;
        hp -= (actualDamage * (dt / 1000));
        
        // Warning log once
        if (hp <= 20 && !logDiv.innerHTML.includes('sắp sập')) {
            addLog('[ CẢNH BÁO: Server sắp sập! ]', 'warning');
        }
        
        // Game Over condition
        if (hp <= 0) {
            hp = 0;
            isPlaying = false;
            addLog('[ GAME OVER — Server đã bị hạ gục! ]', 'warning');
            updateUI();
            
            ctx.fillStyle = 'rgba(10, 10, 15, 0.8)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#ff003c';
            ctx.font = 'bold 30px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('GAME OVER', canvas.width/2, canvas.height/2 - 20);
            ctx.fillStyle = '#fff';
            ctx.font = '20px sans-serif';
            ctx.fillText(`Điểm cuối cùng: ${Math.floor(score)}`, canvas.width/2, canvas.height/2 + 20);
            
            if(startScreen) {
                startScreen.classList.remove('hidden');
                startScreen.innerHTML = `
                    <h3 style="color:#ff003c; margin-bottom: 10px;">Server Down!</h3>
                    <p style="margin-bottom: 20px;">Hệ thống đã quá tải trước làn sóng tấn công.</p>
                    <button id="btn-restart-defense" style="padding:10px 20px; background:#00f5ff; color:#0a0a0f; border:none; cursor:pointer; font-weight:bold; border-radius:4px;">Chơi Lại</button>
                `;
                document.getElementById('btn-restart-defense').addEventListener('click', startGame);
            }
            
            return;
        }
        
        // Scoring
        score += 5 * (dt / 1000);
        
        // Wave management
        waveTimer -= dt;
        if (waveTimer <= 0) {
            wave++;
            waveTimer = 15000;
            score += 50; // Bonus for surviving a wave
            addLog(`[ Đợt tấn công #${wave} bắt đầu! ]`, 'warning');
        }
        
        // Spawn bots
        if (Math.random() < 0.1 * wave) {
            spawnParticles(1 + Math.floor(wave / 2));
        }
        
        // Draw scene
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Wave text indicator
        if (waveTimer > 12000) { // Flash for first 3 seconds of wave
            ctx.fillStyle = `rgba(255, 0, 60, ${(waveTimer - 12000)/3000})`;
            ctx.font = 'bold 40px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(`WAVE ${wave}`, canvas.width/2, canvas.height/2);
        }
        
        drawServer();
        
        // Particle physics and collision
        const serverX = canvas.width - 80;
        const serverY = canvas.height / 2 - 40;
        const isShieldActive = tools.rateLimiter.active || tools.waf.active || tools.cdn.active || tools.blacklist.active;
        
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI*2);
            ctx.fill();
            
            // Hit detection with server boundary
            if (p.x > serverX - 20 && p.x < serverX + 80 && p.y > serverY - 20 && p.y < serverY + 100) {
                if (isShieldActive) {
                    // Blocked - bounce back and turn gray
                    p.vx = -p.vx;
                    p.color = '#555';
                } else {
                    // Hit - explode and remove
                    explosions.push({x: p.x, y: p.y, life: 1, maxLife: 20});
                    particles.splice(i, 1);
                }
            } else if (p.x > canvas.width || p.x < -20 || p.y < -20 || p.y > canvas.height + 20) {
                // Out of bounds
                particles.splice(i, 1);
            }
        }
        
        // Render explosions
        for (let i = explosions.length - 1; i >= 0; i--) {
            const e = explosions[i];
            e.life++;
            ctx.beginPath();
            ctx.arc(e.x, e.y, e.life, 0, Math.PI*2);
            ctx.strokeStyle = `rgba(255, 0, 60, ${1 - e.life/e.maxLife})`;
            ctx.stroke();
            if (e.life >= e.maxLife) explosions.splice(i, 1);
        }
        
        updateUI();
        animationId = requestAnimationFrame(gameLoop);
    }
    
})();
