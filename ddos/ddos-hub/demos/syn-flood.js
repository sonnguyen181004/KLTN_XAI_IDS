// C:\Users\LOQ\Downloads\SELF_KLTN\ddos-hub\demos\syn-flood.js

/**
 * Trình mô phỏng tấn công SYN Flood
 * Hiển thị trực quan cạn kiệt tài nguyên Server và cơ chế bảo vệ SYN Cookie.
 */

const SynFloodDemo = (function() {
    let canvas, ctx;
    let elValid, elHalfOpen, elRefused, elSynCookieStatus, elConnectionTable, elCapacityFill, elCapacityText;
    let btnNormalConn, btnSynFloodStart, btnSynCookie, btnReset;

    let state = {
        valid: 0,
        halfOpen: 0,
        refused: 0,
        synCookieEnabled: false,
        isAttacking: false,
        maxConnections: 20,
        connections: [], // Lưu trữ các kết nối hiện tại
        packets: [],     // Dữ liệu cho animation canvas
        lastTime: 0,
        attackIntervalId: null,
        nextId: 1
    };

    function init() {
        canvas = document.getElementById('syn-canvas');
        elValid = document.getElementById('valid-connections');
        elHalfOpen = document.getElementById('half-open-connections');
        elRefused = document.getElementById('refused-connections');
        elSynCookieStatus = document.getElementById('syn-cookie-status');
        elConnectionTable = document.getElementById('connection-table');
        elCapacityFill = document.getElementById('capacity-fill');
        elCapacityText = document.getElementById('capacity-text');

        btnNormalConn = document.getElementById('btn-normal-conn');
        btnSynFloodStart = document.getElementById('btn-syn-flood-start');
        btnSynCookie = document.getElementById('btn-syn-cookie');
        btnReset = document.getElementById('btn-reset-syn');

        if (!canvas) return;

        ctx = canvas.getContext('2d');
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        bindEvents();
        updateUI();
        requestAnimationFrame(render);
    }

    function resizeCanvas() {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = 300;
    }

    function bindEvents() {
        btnNormalConn.addEventListener('click', addNormalConnection);
        btnSynFloodStart.addEventListener('click', toggleSynFlood);
        btnSynCookie.addEventListener('click', toggleSynCookie);
        btnReset.addEventListener('click', resetDemo);
    }

    function addNormalConnection() {
        let connId = state.nextId++;
        let ip = `192.168.1.${Math.floor(Math.random() * 254) + 1}`;
        let port = Math.floor(Math.random() * 10000) + 1024;
        
        let conn = {
            id: connId,
            ip: ip,
            port: port,
            type: 'normal', // normal, attack
            status: 'syn_sent', // syn_sent, syn_rcvd, established, refused
            timeRemaining: 2000 // thời gian xử lý giả lập (ms)
        };

        processConnection(conn);
    }

    function addAttackConnection() {
        let connId = state.nextId++;
        let ip = `10.0.0.${Math.floor(Math.random() * 254) + 1}`;
        let port = Math.floor(Math.random() * 10000) + 1024;

        let conn = {
            id: connId,
            ip: ip,
            port: port,
            type: 'attack',
            status: 'syn_sent',
            timeRemaining: 10000 // Giữ kết nối lâu hơn do không có ACK
        };

        processConnection(conn);
    }

    function processConnection(conn) {
        // Animation gói tin SYN
        state.packets.push({
            x: 50, y: 150 + (Math.random() * 40 - 20),
            tx: canvas.width - 50, ty: 150,
            progress: 0,
            type: 'syn',
            color: conn.type === 'normal' ? '#00ff88' : '#ff003c',
            connId: conn.id,
            parentConn: conn
        });
    }

    function onPacketArrival(packet) {
        let conn = packet.parentConn;
        
        if (packet.type === 'syn') {
            let spaceAvailable = state.connections.length < state.maxConnections;
            
            if (state.synCookieEnabled) {
                // SYN Cookie: không lưu trạng thái (half-open) trên server
                if (conn.type === 'normal') {
                    // Trả về SYN-ACK
                    state.packets.push({
                        x: canvas.width - 50, y: 150,
                        tx: 50, ty: 150 + (Math.random() * 40 - 20),
                        progress: 0,
                        type: 'syn_ack',
                        color: '#ffd700',
                        parentConn: conn
                    });
                }
                // Nếu attack (giả lập IP giả, không gửi ACK lại) thì không làm gì thêm
            } else {
                // Không có SYN Cookie: Lưu trạng thái
                if (spaceAvailable) {
                    conn.status = 'syn_rcvd';
                    state.connections.push(conn);
                    state.halfOpen++;
                    
                    // Trả về SYN-ACK
                    state.packets.push({
                        x: canvas.width - 50, y: 150,
                        tx: 50, ty: 150 + (Math.random() * 40 - 20),
                        progress: 0,
                        type: 'syn_ack',
                        color: '#ffd700',
                        parentConn: conn
                    });
                    updateUI();
                } else {
                    // Refused
                    conn.status = 'refused';
                    state.refused++;
                    updateUI();
                }
            }
        } else if (packet.type === 'syn_ack') {
            if (conn.type === 'normal') {
                // Trả về ACK (chỉ connection normal mới trả về ACK)
                state.packets.push({
                    x: 50, y: 150,
                    tx: canvas.width - 50, ty: 150,
                    progress: 0,
                    type: 'ack',
                    color: '#00f5ff',
                    parentConn: conn
                });
            }
        } else if (packet.type === 'ack') {
            // Server nhận ACK
            if (state.synCookieEnabled) {
                // Tái tạo kết nối từ Cookie, bây giờ mới lưu vào bảng
                let spaceAvailable = state.connections.length < state.maxConnections;
                if (spaceAvailable) {
                    conn.status = 'established';
                    state.connections.push(conn);
                    state.valid++;
                } else {
                    state.refused++;
                }
            } else {
                // Tìm connection trong bảng và cập nhật status
                let existingConn = state.connections.find(c => c.id === conn.id);
                if (existingConn && existingConn.status === 'syn_rcvd') {
                    existingConn.status = 'established';
                    state.halfOpen--;
                    state.valid++;
                }
            }
            updateUI();
        }
    }

    function toggleSynFlood() {
        state.isAttacking = !state.isAttacking;
        if (state.isAttacking) {
            btnSynFloodStart.textContent = "Dừng SYN Flood";
            btnSynFloodStart.classList.add('active');
            // Bắt đầu tạo liên tục
            state.attackIntervalId = setInterval(addAttackConnection, 100); // 10 conn / sec
        } else {
            btnSynFloodStart.textContent = "Bắt đầu SYN Flood";
            btnSynFloodStart.classList.remove('active');
            clearInterval(state.attackIntervalId);
        }
    }

    function toggleSynCookie() {
        state.synCookieEnabled = !state.synCookieEnabled;
        if (state.synCookieEnabled) {
            btnSynCookie.classList.add('active');
            if(elSynCookieStatus) elSynCookieStatus.textContent = "Bật (Bảo vệ bộ nhớ)";
            if(elSynCookieStatus) elSynCookieStatus.style.color = "#00ff88";
        } else {
            btnSynCookie.classList.remove('active');
            if(elSynCookieStatus) elSynCookieStatus.textContent = "Tắt";
            if(elSynCookieStatus) elSynCookieStatus.style.color = "#ff003c";
        }
    }

    function resetDemo() {
        if (state.isAttacking) toggleSynFlood();
        state.valid = 0;
        state.halfOpen = 0;
        state.refused = 0;
        state.connections = [];
        state.packets = [];
        updateUI();
    }

    function updateUI() {
        if (elValid) elValid.textContent = state.valid;
        if (elHalfOpen) elHalfOpen.textContent = state.halfOpen;
        if (elRefused) elRefused.textContent = state.refused;

        let connCount = state.connections.length;
        if (elCapacityText) elCapacityText.textContent = `${connCount} / ${state.maxConnections}`;
        
        if (elCapacityFill) {
            let percent = (connCount / state.maxConnections) * 100;
            elCapacityFill.style.width = `${percent}%`;
            elCapacityFill.style.backgroundColor = percent > 80 ? '#ff003c' : (percent > 50 ? '#ffd700' : '#00ff88');
        }

        renderConnectionTable();
        if (typeof window.updateSynExplain === 'function') {
            window.updateSynExplain(state.valid, state.halfOpen, state.refused, state.synCookieEnabled, state.isAttacking);
        }
    }

    function renderConnectionTable() {
        if (!elConnectionTable) return;
        elConnectionTable.innerHTML = '';
        
        state.connections.forEach(conn => {
            let row = document.createElement('div');
            let statusClass = '';
            let statusText = '';
            
            if (conn.status === 'syn_rcvd') {
                statusClass = 'half-open';
                statusText = 'SYN-RCVD';
            } else if (conn.status === 'established') {
                statusClass = 'established';
                statusText = 'ESTABLISHED';
            } else if (conn.status === 'refused') {
                statusClass = 'refused';
                statusText = 'REFUSED';
            }
            
            row.className = `ct-row ${statusClass}`;
            row.innerHTML = `
                <span class="ctr-ip">${conn.ip}</span>
                <span class="ctr-port">${conn.port}</span>
                <span class="ctr-status">${statusText}</span>
                <span class="ctr-age">${(conn.timeRemaining / 1000).toFixed(1)}s</span>
            `;
            elConnectionTable.appendChild(row);
        });
    }

    function render(timestamp) {
        let dt = timestamp - state.lastTime;
        if (dt > 100) dt = 16; // Chống lag nhảy cóc
        state.lastTime = timestamp;

        if (!ctx) return;

        // Xóa canvas
        ctx.fillStyle = '#0a0a0f';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Vẽ nodes
        ctx.fillStyle = '#222';
        ctx.strokeStyle = '#00f5ff';
        ctx.lineWidth = 2;
        
        // Client
        ctx.fillRect(10, 100, 60, 100);
        ctx.strokeRect(10, 100, 60, 100);
        ctx.fillStyle = '#fff';
        ctx.font = '12px sans-serif';
        ctx.fillText('Client', 20, 150);

        // Server
        ctx.fillStyle = '#222';
        ctx.fillRect(canvas.width - 70, 100, 60, 100);
        ctx.strokeRect(canvas.width - 70, 100, 60, 100);
        ctx.fillStyle = '#fff';
        ctx.fillText('Server', canvas.width - 60, 150);

        // Cập nhật packets
        for (let i = state.packets.length - 1; i >= 0; i--) {
            let p = state.packets[i];
            p.progress += dt * 0.001; // Thời gian bay ~ 1s

            if (p.progress >= 1) {
                onPacketArrival(p);
                state.packets.splice(i, 1);
            } else {
                let curX = p.x + (p.tx - p.x) * p.progress;
                let curY = p.y + (p.ty - p.y) * p.progress;
                
                ctx.beginPath();
                ctx.arc(curX, curY, 4, 0, Math.PI * 2);
                ctx.fillStyle = p.color;
                ctx.fill();
                
                // Trail
                ctx.beginPath();
                ctx.moveTo(curX, curY);
                ctx.lineTo(curX - (p.tx - p.x) * 0.05, curY - (p.ty - p.y) * 0.05);
                ctx.strokeStyle = p.color;
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        }

        // Cập nhật connections (giảm thời gian)
        let needsUpdate = false;
        for (let i = state.connections.length - 1; i >= 0; i--) {
            let conn = state.connections[i];
            conn.timeRemaining -= dt;
            if (conn.timeRemaining <= 0) {
                if (conn.status === 'syn_rcvd') state.halfOpen--;
                if (conn.status === 'established') state.valid--;
                state.connections.splice(i, 1);
                needsUpdate = true;
            }
        }
        
        if (needsUpdate || state.connections.length > 0) {
            updateUI(); // Cập nhật lại thời gian còn lại
        }

        requestAnimationFrame(render);
    }

    return {
        init: init
    };
})();

// Tự động khởi tạo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', SynFloodDemo.init);
} else {
    SynFloodDemo.init();
}

function initSynFlood() {
    SynFloodDemo.init();
}
window.initSynFlood = initSynFlood;
