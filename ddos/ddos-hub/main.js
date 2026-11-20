/**
 * DDoS Learning Hub — main.js
 * Xử lý: Particles, Sidebar, Navigation, Scroll, Hero Animation,
 *         Card Flip, Layer Filter, Counters, Hero Visual
 */

// =============================================
// PARTICLES CANVAS
// =============================================
(function initParticles() {
  const canvas = document.getElementById('particles-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let particles = [];
  let W, H;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  function createParticle() {
    return {
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      size: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.5 + 0.1,
      color: Math.random() > 0.7 ? '#ff003c' : '#00f5ff'
    };
  }

  for (let i = 0; i < 120; i++) particles.push(createParticle());

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // Draw connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(0, 245, 255, ${0.04 * (1 - dist / 120)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }

    // Draw particles
    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color.replace(')', `, ${p.alpha})`).replace('rgb', 'rgba').replace('#00f5ff', 'rgba(0,245,255,').replace('#ff003c', 'rgba(255,0,60,');
      // simpler approach:
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;
      ctx.fill();
      ctx.globalAlpha = 1;
    });

    requestAnimationFrame(draw);
  }
  draw();
})();

// =============================================
// SIDEBAR & NAVIGATION
// =============================================
(function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const menuBtn = document.getElementById('menu-toggle');
  const progressFill = document.getElementById('scroll-progress');
  const progressPct = document.getElementById('progress-pct');
  const navItems = document.querySelectorAll('.nav-item');

  // Mobile menu toggle
  if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
    // Close sidebar when clicking outside
    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) &&
          e.target !== menuBtn) {
        sidebar.classList.remove('open');
      }
    });
  }

  // Scroll progress
  function updateScrollProgress() {
    const scrollTop = window.scrollY;
    const docHeight = document.body.scrollHeight - window.innerHeight;
    const pct = docHeight > 0 ? Math.round((scrollTop / docHeight) * 100) : 0;
    if (progressFill) progressFill.style.width = pct + '%';
    if (progressPct) progressPct.textContent = pct + '%';
  }

  // Active section tracking
  const sections = document.querySelectorAll('.section');
  function updateActiveNav() {
    let current = '';
    sections.forEach(section => {
      const rect = section.getBoundingClientRect();
      if (rect.top <= 100 && rect.bottom >= 100) {
        current = section.id;
      }
    });
    navItems.forEach(item => {
      item.classList.toggle('active', item.dataset.section === current);
    });
  }

  window.addEventListener('scroll', () => {
    updateScrollProgress();
    updateActiveNav();
  }, { passive: true });

  // Smooth scroll on nav click
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      const href = link.getAttribute('href');
      if (href && href.startsWith('#')) {
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth' });
          sidebar.classList.remove('open');
        }
      }
    });
  });
})();

// =============================================
// HERO SECTION ANIMATION
// =============================================
(function initHero() {
  // Create bot nodes
  const botsContainer = document.getElementById('hero-bots');
  if (botsContainer) {
    const botEmojis = ['💻', '📱', '🖥️', '📺', '📷', '🔌'];
    for (let i = 0; i < 6; i++) {
      const node = document.createElement('div');
      node.className = 'hero-bot-node';
      node.textContent = botEmojis[i % botEmojis.length];
      node.style.animationDelay = `${i * 0.25}s`;
      botsContainer.appendChild(node);
    }
  }

  // Animate server status changes
  const heroServer = document.getElementById('hero-server');
  const srvStatus = document.getElementById('hero-srv-status');
  const heroFire = document.getElementById('hero-fire');
  const lights = [
    document.getElementById('hl-1'),
    document.getElementById('hl-2'),
    document.getElementById('hl-3')
  ];

  let phase = 0;
  const phases = [
    { label: '🟢 ONLINE', border: '#00f5ff', shadow: '0 0 20px rgba(0,245,255,0.5)', lightClass: 'green', fireVisible: false },
    { label: '🟡 DEGRADED', border: '#ffd700', shadow: '0 0 20px rgba(255,215,0,0.5)', lightClass: 'yellow', fireVisible: false },
    { label: '🔴 OVERLOADED', border: '#ff6600', shadow: '0 0 20px rgba(255,102,0,0.5)', lightClass: 'red', fireVisible: false },
    { label: '💀 SERVER DOWN', border: '#ff003c', shadow: '0 0 30px rgba(255,0,60,0.7)', lightClass: 'red', fireVisible: true },
  ];

  function animateHeroServer() {
    const p = phases[phase];
    if (heroServer) {
      heroServer.style.borderColor = p.border;
      heroServer.style.boxShadow = p.shadow;
    }
    if (srvStatus) srvStatus.textContent = p.label;
    if (heroFire) heroFire.classList.toggle('hidden', !p.fireVisible);
    lights.forEach(light => {
      if (light) {
        light.className = `hlight ${p.lightClass}`;
      }
    });
    phase = (phase + 1) % phases.length;
  }

  setInterval(animateHeroServer, 2000);

  // Animate hero stat counters
  document.querySelectorAll('.hstat-num').forEach(el => {
    const target = parseInt(el.dataset.to) || 0;
    let current = 0;
    const step = Math.max(1, Math.floor(target / 20));
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 50);
  });
})();

// =============================================
// CARD FLIP — DDoS Types
// =============================================
(function initCardFlip() {
  const cards = document.querySelectorAll('.type-card');
  cards.forEach(card => {
    card.addEventListener('click', () => {
      card.classList.toggle('flipped');
    });
  });
})();

// =============================================
// LAYER FILTER — DDoS Types
// =============================================
(function initLayerFilter() {
  const filterBtns = document.querySelectorAll('.lf-btn');
  const typeCards = document.querySelectorAll('.type-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const layer = btn.dataset.layer;
      typeCards.forEach(card => {
        card.classList.remove('hidden-card');
        card.classList.remove('flipped');
        if (layer !== 'all' && card.dataset.layer !== layer) {
          card.classList.add('hidden-card');
        }
      });
    });
  });
})();

// =============================================
// DANGER BARS — Types Cards
// =============================================
(function initDangerBars() {
  document.querySelectorAll('.danger-bar').forEach(bar => {
    const level = parseInt(bar.dataset.level) || 0;
    bar.innerHTML = '';
    for (let i = 1; i <= 5; i++) {
      const dot = document.createElement('span');
      dot.style.cssText = `
        display:inline-block; width:12px; height:8px;
        border-radius:2px; margin-right:2px;
        background: ${i <= level ? (level >= 5 ? '#ff003c' : level >= 4 ? '#ff6600' : '#ffd700') : 'rgba(255,255,255,0.1)'};
        ${i <= level ? `box-shadow: 0 0 4px ${level >= 5 ? '#ff003c' : level >= 4 ? '#ff6600' : '#ffd700'};` : ''}
        transition: all 0.3s ease;
      `;
      bar.appendChild(dot);
    }
  });
})();

// =============================================
// ANIMATED COUNTERS — History Section
// =============================================
(function initCounters() {
  const counterMap = {
    'ctr-rps': { target: 46000000, suffix: '' },
    'ctr-tbps': { target: 2300, suffix: ' Gbps' },
    'ctr-bots': { target: 600000, suffix: '' },
    'ctr-amp': { target: 51000, suffix: 'x' }
  };

  function formatNum(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
    return n.toString();
  }

  let countersStarted = false;

  function startCounters() {
    if (countersStarted) return;
    countersStarted = true;

    Object.entries(counterMap).forEach(([id, config]) => {
      const el = document.getElementById(id);
      if (!el) return;
      let current = 0;
      const duration = 2500;
      const startTime = performance.now();

      function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out
        const eased = 1 - Math.pow(1 - progress, 3);
        current = Math.round(config.target * eased);
        el.textContent = formatNum(current) + (config.suffix || '');
        if (progress < 1) requestAnimationFrame(update);
      }
      requestAnimationFrame(update);
    });
  }

  // Intersection Observer to start counters when visible
  const historySection = document.getElementById('history');
  if (historySection) {
    const obs = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        startCounters();
        obs.disconnect();
      }
    }, { threshold: 0.3 });
    obs.observe(historySection);
  }
})();

// =============================================
// SCROLL REVEAL ANIMATIONS
// =============================================
(function initScrollReveal() {
  const style = document.createElement('style');
  style.textContent = `
    .reveal { opacity: 0; transform: translateY(30px); transition: opacity 0.7s ease, transform 0.7s ease; }
    .reveal.visible { opacity: 1; transform: translateY(0); }
    .reveal-left { opacity: 0; transform: translateX(-30px); transition: opacity 0.7s ease, transform 0.7s ease; }
    .reveal-left.visible { opacity: 1; transform: translateX(0); }
    .reveal-right { opacity: 0; transform: translateX(30px); transition: opacity 0.7s ease, transform 0.7s ease; }
    .reveal-right.visible { opacity: 1; transform: translateX(0); }
  `;
  document.head.appendChild(style);

  // Add reveal class to elements
  document.querySelectorAll('.ts-item, .ht-item, .type-card, .counter-box, .bv-note').forEach((el, i) => {
    el.classList.add('reveal');
    el.style.transitionDelay = `${(i % 4) * 0.1}s`;
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -60px 0px' });

  document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach(el => observer.observe(el));
})();

// =============================================
// INIT ALL DEMOS
// =============================================
window.addEventListener('DOMContentLoaded', () => {
  if (typeof initConceptsSection === 'function') initConceptsSection();
  if (typeof initServerSim === 'function') initServerSim();
  if (typeof initNetworkMap === 'function') initNetworkMap();
  if (typeof initPacketAnalyzer === 'function') initPacketAnalyzer();
  if (typeof initSynFlood === 'function') initSynFlood();
  if (typeof initDefenseLab === 'function') initDefenseLab();
  if (typeof initAIDetectionDemo === 'function') initAIDetectionDemo();
  if (typeof initMLConceptsSection === 'function') initMLConceptsSection();
  if (typeof initQuiz === 'function') initQuiz();
});

// =============================================
// TOOLTIP HELPER
// =============================================
(function initTooltips() {
  const tooltipStyle = document.createElement('style');
  tooltipStyle.textContent = `
    [data-tip] { position: relative; }
    [data-tip]::after {
      content: attr(data-tip);
      position: absolute; bottom: calc(100% + 8px); left: 50%;
      transform: translateX(-50%);
      background: rgba(0,0,0,0.9); color: #e0e0f0;
      padding: 6px 12px; border-radius: 6px;
      font-size: 12px; white-space: nowrap; pointer-events: none;
      opacity: 0; transition: opacity 0.2s;
      border: 1px solid rgba(0,245,255,0.2); z-index: 1000;
    }
    [data-tip]:hover::after { opacity: 1; }
  `;
  document.head.appendChild(tooltipStyle);
})();

// =============================================
// KEYBOARD SHORTCUTS
// =============================================
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.getElementById('sidebar')?.classList.remove('open');
    document.querySelectorAll('.type-card.flipped').forEach(c => c.classList.remove('flipped'));
  }
});

// =============================================
// CONSOLE EASTER EGG
// =============================================
console.log('%c⚡ DDoS Learning Hub', 'font-family: monospace; font-size: 20px; color: #00f5ff; font-weight: bold;');
console.log('%c🛡️ Trang web này chỉ dành cho mục đích giáo dục.', 'color: #00ff88; font-size: 13px;');
console.log('%c⚠️ Tấn công DDoS là bất hợp pháp! Học để bảo vệ, không học để tấn công.', 'color: #ffd700; font-size: 12px;');

// =============================================
// SCROLL PROGRESS BAR
// =============================================
(function initScrollProgress() {
  const bar = document.getElementById('scroll-progress-bar');
  if (!bar) return;
  window.addEventListener('scroll', () => {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    bar.style.width = pct + '%';
  }, { passive: true });
})();

// =============================================
// BACK TO TOP BUTTON
// =============================================
(function initBackToTop() {
  const btn = document.getElementById('back-to-top');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    if (window.scrollY > 400) {
      btn.classList.add('visible');
    } else {
      btn.classList.remove('visible');
    }
  }, { passive: true });
  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();

// =============================================
// SCROLL REVEAL — IntersectionObserver
// =============================================
(function initScrollReveal() {
  // 1. Gắn class reveal + stagger delay cho cards trong mỗi section
  document.querySelectorAll('.section').forEach(section => {
    // Section header: slide từ trái
    const header = section.querySelector('.section-header');
    if (header) header.classList.add('reveal-left');

    // Tất cả glass-card trong section: fade-in staggered
    const cards = section.querySelectorAll('.glass-card, .cc-card, .type-card, .demo-block');
    cards.forEach((card, i) => {
      if (!card.classList.contains('reveal') && !card.classList.contains('reveal-left') && !card.classList.contains('reveal-right')) {
        card.classList.add('reveal');
        const delay = Math.min(i % 6 + 1, 6);
        card.classList.add(`delay-${delay}`);
      }
    });

    // Tiêu đề section (h2.sec-title): neon flash
    const secTitle = section.querySelector('.sec-title');
    if (secTitle) secTitle.dataset.neonFlash = '1';
  });

  // 2. Observer cho reveal + reveal-left + reveal-right
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target); // chỉ chạy 1 lần
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach(el => {
    revealObserver.observe(el);
  });

  // 3. Observer cho neon flash trên sec-title
  const flashObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && entry.target.dataset.neonFlash) {
        entry.target.classList.add('flash-in');
        flashObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('[data-neon-flash]').forEach(el => {
    flashObserver.observe(el);
  });
})();
