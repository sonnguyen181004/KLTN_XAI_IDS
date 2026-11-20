// quiz.js
(function initQuiz() {
    // Quiz data
    const questions = [
        {
            q: "DDoS là viết tắt của?",
            options: [
                { text: "Direct Denial of Service", correct: false },
                { text: "Distributed Denial of Service", correct: true },
                { text: "Data Destruction on Server", correct: false },
                { text: "Digital Disruption of Systems", correct: false }
            ],
            explanation: "DDoS = Distributed Denial of Service — Từ chối Dịch vụ Phân tán"
        },
        {
            q: "Botnet là gì?",
            options: [
                { text: "Một loại phần mềm diệt virus", correct: false },
                { text: "Mạng lưới máy tính bị nhiễm malware và bị điều khiển từ xa", correct: true },
                { text: "Công cụ bảo mật mạng", correct: false },
                { text: "Giao thức truyền dữ liệu", correct: false }
            ],
            explanation: "Botnet là mạng các thiết bị bị kiểm soát (zombie) mà chủ nhân không hay biết"
        },
        {
            q: "Điểm khác biệt chính giữa DoS và DDoS là gì?",
            options: [
                { text: "DoS dùng nhiều máy, DDoS dùng 1 máy", correct: false },
                { text: "DoS tấn công database, DDoS tấn công network", correct: false },
                { text: "DoS dùng 1 máy, DDoS dùng nhiều máy phân tán", correct: true },
                { text: "Không có sự khác biệt", correct: false }
            ],
            explanation: "Distributed = Phân tán — DDoS dùng hàng nghìn máy từ nhiều nơi"
        },
        {
            q: "SYN Flood khai thác điểm yếu của giao thức nào?",
            options: [
                { text: "UDP", correct: false },
                { text: "HTTP", correct: false },
                { text: "TCP 3-way Handshake", correct: true },
                { text: "DNS", correct: false }
            ],
            explanation: "SYN Flood gửi SYN không hoàn thành handshake, khiến server giữ half-open connections"
        },
        {
            q: "DNS Amplification có hệ số khuếch đại lên đến bao nhiêu?",
            options: [
                { text: "5x", correct: false },
                { text: "20x", correct: false },
                { text: "70x", correct: true },
                { text: "200x", correct: false }
            ],
            explanation: "DNS Amplification gửi 50 bytes, nhận về 3500 bytes — khuếch đại ~70 lần!"
        },
        {
            q: "Công cụ nào sau đây KHÔNG giúp phòng thủ DDoS?",
            options: [
                { text: "WAF (Web Application Firewall)", correct: false },
                { text: "CDN với Anycast routing", correct: false },
                { text: "Tăng dung lượng RAM server", correct: true },
                { text: "Rate Limiting", correct: false }
            ],
            explanation: "Tăng RAM không giúp ích nhiều khi băng thông và CPU bị cạn kiệt hoàn toàn"
        },
        {
            q: "Cuộc tấn công DDoS lớn nhất trong lịch sử (tính đến 2023) nhắm vào ai?",
            options: [
                { text: "Facebook", correct: false },
                { text: "Amazon AWS", correct: false },
                { text: "Google (2022)", correct: true },
                { text: "GitHub", correct: false }
            ],
            explanation: "Google 2022: 46 triệu requests/giây — kỷ lục thế giới chưa bị phá vỡ"
        },
        {
            q: "Slowloris là loại tấn công ở layer nào của mô hình OSI?",
            options: [
                { text: "Layer 3 — Mạng", correct: false },
                { text: "Layer 4 — Vận chuyển", correct: false },
                { text: "Layer 7 — Ứng dụng", correct: true },
                { text: "Layer 2 — Data Link", correct: false }
            ],
            explanation: "Slowloris gửi HTTP headers rất chậm — hoạt động ở Layer 7 Application"
        },
        {
            q: "SYN Cookie giúp chống SYN Flood như thế nào?",
            options: [
                { text: "Chặn tất cả kết nối TCP", correct: false },
                { text: "Server không cấp phát bộ nhớ cho kết nối cho đến khi nhận được ACK", correct: true },
                { text: "Giới hạn tốc độ download", correct: false },
                { text: "Mã hóa tất cả packets", correct: false }
            ],
            explanation: "SYN Cookie encode thông tin vào sequence number, tránh tốn RAM cho half-open connections"
        },
        {
            q: "Mirai Botnet năm 2016 chủ yếu lây nhiễm loại thiết bị nào?",
            options: [
                { text: "Máy tính cá nhân", correct: false },
                { text: "Điện thoại Android", correct: false },
                { text: "Thiết bị IoT (camera IP, router)", correct: true },
                { text: "Máy chủ web", correct: false }
            ],
            explanation: "Mirai khai thác mật khẩu mặc định của camera IP và router, tạo botnet 600,000 thiết bị"
        }
    ];

    // DOM elements
    const startScreen = document.getElementById('quiz-start-screen');
    const gameScreen = document.getElementById('quiz-game');
    const resultScreen = document.getElementById('quiz-result');
    
    const btnStart = document.getElementById('btn-start-quiz');
    const btnRetry = document.getElementById('btn-retry-quiz');
    const btnNext = document.getElementById('btn-next-q');
    
    const progressFill = document.getElementById('quiz-progress');
    const qNumText = document.getElementById('quiz-qnum');
    const scoreText = document.getElementById('quiz-score-display');
    const questionText = document.getElementById('quiz-question');
    const optionsContainer = document.getElementById('quiz-options');
    const feedbackDiv = document.getElementById('quiz-feedback');
    
    // State
    let currentQuestions = [];
    let currentQIndex = 0;
    let score = 0;
    let answered = false;
    
    // Utility function to shuffle an array
    function shuffle(array) {
        let currentIndex = array.length, randomIndex;
        while (currentIndex !== 0) {
            randomIndex = Math.floor(Math.random() * currentIndex);
            currentIndex--;
            [array[currentIndex], array[randomIndex]] = [array[randomIndex], array[currentIndex]];
        }
        return array;
    }
    
    function startQuiz() {
        if(startScreen) startScreen.classList.add('hidden');
        if(resultScreen) resultScreen.classList.add('hidden');
        if(gameScreen) gameScreen.classList.remove('hidden');
        
        // Deep copy and shuffle questions and their options
        currentQuestions = shuffle([...questions]).map(q => ({
            ...q,
            options: shuffle([...q.options])
        }));
        
        currentQIndex = 0;
        score = 0;
        showQuestion();
    }
    
    function showQuestion() {
        answered = false;
        const q = currentQuestions[currentQIndex];
        
        if(qNumText) qNumText.textContent = `Câu ${currentQIndex + 1}/${currentQuestions.length}`;
        if(scoreText) scoreText.textContent = `Điểm: ${score}`;
        if(progressFill) progressFill.style.width = `${((currentQIndex) / currentQuestions.length) * 100}%`;
        
        if(questionText) questionText.textContent = q.q;
        if(optionsContainer) optionsContainer.innerHTML = '';
        if(feedbackDiv) feedbackDiv.classList.add('hidden');
        if(btnNext) btnNext.classList.add('hidden');
        
        q.options.forEach((opt, idx) => {
            const btn = document.createElement('button');
            btn.className = 'quiz-option-btn';
            btn.textContent = `${String.fromCharCode(65 + idx)}) ${opt.text}`;
            
            // Inline styling for fallback (should ideally be in CSS)
            btn.style.display = 'block';
            btn.style.width = '100%';
            btn.style.padding = '12px';
            btn.style.margin = '8px 0';
            btn.style.background = '#1a1a24';
            btn.style.color = '#fff';
            btn.style.border = '1px solid #00f5ff';
            btn.style.borderRadius = '4px';
            btn.style.cursor = 'pointer';
            btn.style.textAlign = 'left';
            btn.style.transition = 'all 0.3s';
            btn.style.fontFamily = 'inherit';
            btn.style.fontSize = '16px';
            
            // Hover effects handled mostly in JS if CSS is missing
            btn.onmouseover = () => { if(!answered) btn.style.boxShadow = '0 0 10px #00f5ff'; };
            btn.onmouseout = () => { if(!answered) btn.style.boxShadow = 'none'; };
            
            btn.addEventListener('click', () => selectOption(btn, opt, q));
            if(optionsContainer) optionsContainer.appendChild(btn);
        });
    }
    
    function selectOption(btn, opt, q) {
        if (answered) return;
        answered = true;
        
        const allBtns = optionsContainer.querySelectorAll('button');
        
        if (opt.correct) {
            btn.style.background = '#00ff88';
            btn.style.color = '#0a0a0f';
            btn.style.borderColor = '#00ff88';
            score += 10;
        } else {
            btn.style.background = '#ff003c';
            btn.style.color = '#fff';
            btn.style.borderColor = '#ff003c';
            
            // Highlight the correct answer
            allBtns.forEach(b => {
                const bText = b.textContent.substring(3); // Remove "A) "
                const correctOpt = q.options.find(o => o.text === bText && o.correct);
                if (correctOpt) {
                    b.style.background = '#00ff88';
                    b.style.color = '#0a0a0f';
                    b.style.borderColor = '#00ff88';
                }
            });
        }
        
        if(scoreText) scoreText.textContent = `Điểm: ${score}`;
        
        if(feedbackDiv) {
            feedbackDiv.textContent = `Giải thích: ${q.explanation}`;
            feedbackDiv.classList.remove('hidden');
            feedbackDiv.style.marginTop = '15px';
            feedbackDiv.style.padding = '12px';
            feedbackDiv.style.background = 'rgba(0, 245, 255, 0.1)';
            feedbackDiv.style.borderLeft = '4px solid #00f5ff';
            feedbackDiv.style.color = '#e0e0e0';
            feedbackDiv.style.borderRadius = '2px';
        }
        
        if(btnNext) btnNext.classList.remove('hidden');
    }
    
    function nextQuestion() {
        currentQIndex++;
        if (currentQIndex < currentQuestions.length) {
            showQuestion();
        } else {
            showResult();
        }
    }
    
    function showResult() {
        if(gameScreen) gameScreen.classList.add('hidden');
        if(resultScreen) resultScreen.classList.remove('hidden');
        if(progressFill) progressFill.style.width = '100%';
        
        const qrIcon = document.getElementById('qr-icon');
        const qrTitle = document.getElementById('qr-title');
        const qrScore = document.getElementById('qr-score');
        const qrBadge = document.getElementById('qr-badge');
        const qrMessage = document.getElementById('qr-message');
        
        if(qrScore) qrScore.textContent = `${score}/100`;
        
        if (score >= 80) {
            if(qrIcon) qrIcon.textContent = '🏆';
            if(qrTitle) qrTitle.textContent = 'Xuất sắc!';
            if(qrBadge) {
                qrBadge.textContent = '🥇 Chuyên gia DDoS';
                qrBadge.style.color = '#ffd700';
            }
            if(qrMessage) qrMessage.textContent = 'Bạn đã nắm rất rõ kiến thức về DDoS và cách phòng chống!';
            fireConfetti();
        } else if (score >= 50) {
            if(qrIcon) qrIcon.textContent = '👏';
            if(qrTitle) qrTitle.textContent = 'Làm tốt lắm!';
            if(qrBadge) {
                qrBadge.textContent = '🥈 Học viên trung cấp';
                qrBadge.style.color = '#c0c0c0';
            }
            if(qrMessage) qrMessage.textContent = 'Kiến thức của bạn khá vững, nhưng hãy ôn lại một số khái niệm nhé.';
        } else {
            if(qrIcon) qrIcon.textContent = '📚';
            if(qrTitle) qrTitle.textContent = 'Cần cố gắng thêm';
            if(qrBadge) {
                qrBadge.textContent = '🥉 Người mới bắt đầu';
                qrBadge.style.color = '#cd7f32';
            }
            if(qrMessage) qrMessage.textContent = 'Đừng nản lòng! Hãy đọc lại các bài học và thử lại sau nhé.';
        }
    }
    
    function fireConfetti() {
        for(let i=0; i<50; i++) {
            const conf = document.createElement('div');
            conf.style.position = 'fixed';
            conf.style.width = '10px';
            conf.style.height = '10px';
            conf.style.backgroundColor = ['#00f5ff', '#ff003c', '#00ff88', '#ffd700'][Math.floor(Math.random()*4)];
            conf.style.left = Math.random() * 100 + 'vw';
            conf.style.top = '-20px';
            conf.style.zIndex = '9999';
            conf.style.pointerEvents = 'none';
            document.body.appendChild(conf);
            
            const duration = Math.random() * 2 + 2;
            conf.animate([
                { transform: 'translate3d(0,0,0) rotate(0deg)', opacity: 1 },
                { transform: `translate3d(${Math.random()*200 - 100}px, 100vh, 0) rotate(${Math.random()*360}deg)`, opacity: 0 }
            ], {
                duration: duration * 1000,
                easing: 'cubic-bezier(.37,0,.63,1)'
            }).onfinish = () => conf.remove();
        }
    }
    
    // Event listeners
    if (btnStart) btnStart.addEventListener('click', startQuiz);
    if (btnNext) btnNext.addEventListener('click', nextQuestion);
    if (btnRetry) btnRetry.addEventListener('click', startQuiz);
})();
