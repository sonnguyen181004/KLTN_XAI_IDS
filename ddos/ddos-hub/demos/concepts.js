/**
 * concepts.js — Xử lý thẻ khái niệm có thể mở/đóng
 */

// Toggle expand/collapse concept card
function toggleConcept(headerEl) {
  const card = headerEl.closest('.cc-card');
  const isOpen = card.classList.contains('open');
  
  // Close all others
  document.querySelectorAll('.cc-card.open').forEach(c => {
    if (c !== card) c.classList.remove('open');
  });
  
  // Toggle current
  card.classList.toggle('open', !isOpen);
  
  // Scroll into view if opening
  if (!isOpen) {
    setTimeout(() => {
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 300);
  }
}

// Category filter
function initConceptFilter() {
  const filterBtns = document.querySelectorAll('.cf-btn');
  const cards = document.querySelectorAll('.cc-card');
  
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      const cat = btn.dataset.cf;
      cards.forEach(card => {
        card.classList.remove('open'); // Close all on filter
        if (cat === 'all' || card.dataset.cat === cat) {
          card.classList.remove('cc-hidden');
        } else {
          card.classList.add('cc-hidden');
        }
      });
    });
  });
}

// Auto-open first card as example
function initConceptsSection() {
  initConceptFilter();
  
  // Open first card after a small delay to attract attention
  setTimeout(() => {
    const firstCard = document.querySelector('.cc-card');
    if (firstCard) {
      // Only auto-open if concepts section is in view
      const obs = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          firstCard.classList.add('open');
          obs.disconnect();
        }
      }, { threshold: 0.5 });
      const section = document.getElementById('concepts');
      if (section) obs.observe(section);
    }
  }, 500);
}

document.addEventListener('DOMContentLoaded', initConceptsSection);
