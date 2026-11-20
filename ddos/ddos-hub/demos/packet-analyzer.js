// C:\Users\LOQ\Downloads\SELF_KLTN\ddos-hub\demos\packet-analyzer.js

/**
 * Trình phân tích luồng gói tin (Packet Stream Analyzer)
 * Mô phỏng phân tích và phân loại các gói tin mạng theo thời gian thực.
 */

const PacketAnalyzer = (function() {
    // Các phần tử DOM
    let elStream, elTotal, elNormal, elSuspicious, elBlocked;
    let btnFilterAll, btnFilterNormal, btnFilterSuspicious, btnFilterBlocked;
    let btnNormalTraffic, btnAttackTraffic, btnReset;
    
    // Trạng thái hệ thống
    let state = {
        total: 0,
        normal: 0,
        suspicious: 0,
        blocked: 0,
        mode: 'idle', // 'idle', 'normal', 'attack'
        filter: 'all', // 'all', 'normal', 'suspicious', 'blocked'
        intervalId: null,
        attackIntensityLevel: 0,
        intensityIntervalId: null,
        maxRows: 200,
        packetCount: 0 // để tăng tự động
    };

    // Dữ liệu mẫu
    const normalIPs = ['103.21.144.', '27.64.12.', '118.70.55.', '14.161.42.'];
    const attackIPs = ['192.168.1.', '10.0.0.', '172.16.5.'];
    const protocols = ['TCP SYN', 'TCP ACK', 'UDP 53', 'HTTP GET /', 'HTTP POST /api', 'ICMP Echo'];

    // Hàm khởi tạo
    function init() {
        elStream = document.getElementById('packet-stream');
        elTotal = document.getElementById('total-packets');
        elNormal = document.getElementById('normal-packets');
        elSuspicious = document.getElementById('suspicious-packets');
        elBlocked = document.getElementById('blocked-packets');
        
        btnFilterAll = document.getElementById('filter-all');
        btnFilterNormal = document.getElementById('filter-normal');
        btnFilterSuspicious = document.getElementById('filter-suspicious');
        btnFilterBlocked = document.getElementById('filter-blocked');
        
        btnNormalTraffic = document.getElementById('btn-normal-traffic');
        btnAttackTraffic = document.getElementById('btn-attack-traffic');
        btnReset = document.getElementById('btn-reset-analyzer');

        if (!elStream) return; // Không có DOM thì bỏ qua

        bindEvents();
        updateUI();
    }

    // Gắn sự kiện
    function bindEvents() {
        btnFilterAll.addEventListener('click', () => setFilter('all'));
        btnFilterNormal.addEventListener('click', () => setFilter('normal'));
        btnFilterSuspicious.addEventListener('click', () => setFilter('suspicious'));
        btnFilterBlocked.addEventListener('click', () => setFilter('blocked'));

        btnNormalTraffic.addEventListener('click', () => startTraffic('normal'));
        btnAttackTraffic.addEventListener('click', () => startTraffic('attack'));
        btnReset.addEventListener('click', resetAnalyzer);
    }

    // Cập nhật giao diện
    function updateUI() {
        if(elTotal) elTotal.textContent = state.total;
        if(elNormal) elNormal.textContent = state.normal;
        if(elSuspicious) elSuspicious.textContent = state.suspicious;
        if(elBlocked) elBlocked.textContent = state.blocked;

        // Cập nhật nút bộ lọc
        [btnFilterAll, btnFilterNormal, btnFilterSuspicious, btnFilterBlocked].forEach(btn => {
            if(btn) btn.classList.remove('active');
        });
        
        if (state.filter === 'all' && btnFilterAll) btnFilterAll.classList.add('active');
        if (state.filter === 'normal' && btnFilterNormal) btnFilterNormal.classList.add('active');
        if (state.filter === 'suspicious' && btnFilterSuspicious) btnFilterSuspicious.classList.add('active');
        if (state.filter === 'blocked' && btnFilterBlocked) btnFilterBlocked.classList.add('active');

        // Lọc stream hiển thị
        if (elStream) {
            elStream.className = state.filter !== 'all' ? `filter-${state.filter}` : '';
        }
    }

    // Thiết lập bộ lọc
    function setFilter(filterType) {
        state.filter = filterType;
        updateUI();
    }

    // Sinh số ngẫu nhiên
    function randomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    // Lấy IP ngẫu nhiên
    function getRandomIP(type) {
        let prefixList = type === 'attack' ? attackIPs : normalIPs;
        let prefix = prefixList[randomInt(0, prefixList.length - 1)];
        let suffix = type === 'attack' ? randomInt(1, 50) : randomInt(2, 254);
        return prefix + suffix;
    }

    // Sinh gói tin
    function generatePacket(mode) {
        let type, sourceIP, protocol, size, statusText;
        let rand = Math.random();

        if (mode === 'normal') {
            // Normal mode: 70% normal, 30% suspicious
            if (rand < 0.7) {
                type = 'normal';
                size = randomInt(200, 2000) + ' B';
            } else {
                type = 'suspicious';
                size = randomInt(64, 128) + ' B';
            }
            sourceIP = getRandomIP('normal');
        } else {
            // Attack mode: 10% normal, 20% suspicious, 70% blocked
            if (rand < 0.1) {
                type = 'normal';
                size = randomInt(200, 2000) + ' B';
                sourceIP = getRandomIP('normal');
            } else if (rand < 0.3) {
                type = 'suspicious';
                size = randomInt(64, 128) + ' B';
                sourceIP = getRandomIP('normal');
            } else {
                type = 'blocked';
                size = '64 B'; // Thường là SYN flood
                sourceIP = getRandomIP('attack');
            }
        }

        protocol = protocols[randomInt(0, protocols.length - 1)];
        if (type === 'blocked') protocol = 'TCP SYN'; // Force SYN cho block
        
        switch(type) {
            case 'normal': statusText = '✅ Bình thường'; state.normal++; break;
            case 'suspicious': statusText = '⚠️ Khả nghi'; state.suspicious++; break;
            case 'blocked': statusText = '🚫 Bị chặn'; state.blocked++; break;
        }
        
        state.total++;

        // Tạo phần tử DOM
        const row = document.createElement('div');
        row.className = `packet-row ${type}`;
        
        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}`;

        row.innerHTML = `
            <span>${timeStr}</span>
            <span>${sourceIP}</span>
            <span>10.0.0.1</span>
            <span>${protocol}</span>
            <span>${size}</span>
            <span class="pkt-status">${statusText}</span>
        `;

        if (elStream) {
            elStream.appendChild(row);
            
            // Xóa phần tử cũ nếu vượt quá giới hạn
            if (elStream.children.length > state.maxRows) {
                elStream.removeChild(elStream.firstChild);
            }
            
            // Tự động cuộn xuống dưới cùng
            elStream.scrollTop = elStream.scrollHeight;
        }

        updateUI();
    }

    // Bắt đầu sinh luồng
    function startTraffic(mode) {
        stopTraffic();
        state.mode = mode;
        state.attackIntensityLevel = 1;

        if (typeof window.updateAnalyzerExplain === 'function') {
            window.updateAnalyzerExplain(mode);
        }

        const loop = () => {
            if (state.mode === 'normal') {
                // ~1 packet mỗi 1.2s - 1.8s (dễ đọc, dễ click)
                generatePacket('normal');
                state.intervalId = setTimeout(loop, randomInt(1200, 1800));
            } else if (state.mode === 'attack') {
                // Tấn công: ~1 packet mỗi 350ms - 500ms (vừa đủ mượt, vừa dễ bấm)
                generatePacket('attack');
                state.intervalId = setTimeout(loop, randomInt(350, 500));
            }
        };

        loop();

        if (mode === 'attack') {
            state.intensityIntervalId = setInterval(() => {
                state.attackIntensityLevel++;
            }, 3000); // Tăng cường độ mỗi 3 giây
        }
    }

    // Dừng luồng
    function stopTraffic() {
        state.mode = 'idle';
        if (state.intervalId) clearTimeout(state.intervalId);
        if (state.intensityIntervalId) clearInterval(state.intensityIntervalId);
    }

    // Đặt lại trình phân tích
    function resetAnalyzer() {
        stopTraffic();
        state = {
            ...state,
            total: 0,
            normal: 0,
            suspicious: 0,
            blocked: 0,
            mode: 'idle',
            attackIntensityLevel: 0
        };
        if (elStream) elStream.innerHTML = '';
        updateUI();
    }

    return {
        init: init
    };
})();

// Tự động khởi tạo khi load xong
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', PacketAnalyzer.init);
} else {
    PacketAnalyzer.init();
}

function initPacketAnalyzer() {
    PacketAnalyzer.init();
}
window.initPacketAnalyzer = initPacketAnalyzer;
