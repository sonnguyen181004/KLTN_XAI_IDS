/* core.js — tiện ích dùng chung, điều hướng, nhãn demo */
const $=(q,p=document)=>p.querySelector(q), $$=(q,p=document)=>[...p.querySelectorAll(q)];
const HUB=window.HUB={mods:[],reg(fn){this.mods.push(fn)},boot(){
  initNav();initTip();$('#legend').innerHTML=Object.keys(BADGES).map(k=>badge(k,true)).join('');
  this.mods.forEach(fn=>{try{fn()}catch(e){console.error('module error',fn.name,e)}});
  $('#detailBtn').onclick=()=>{const all=$$('details.deep');const open=all.some(d=>!d.open);all.forEach(d=>d.open=open);$('#detailBtn').textContent=open?'Thu gọn chi tiết':'Mở tất cả chi tiết'};
  $('#printBtn').onclick=()=>{$$('details.deep').forEach(d=>d.open=true);window.print()};
}};

const BADGES={
  real:['Real Project Data','Số liệu thật từ kết quả dự án (RQ1/RQ2).'],
  interactive:['Interactive Explanation','Mô phỏng để giải thích khái niệm. Không phải kết quả nghiên cứu.'],
  proposed:['Proposed System','Kiến trúc/chức năng đề xuất, chưa chạy thật.'],
  prototype:['Current Prototype','Thành phần hiện đã chạy.'],
  unvalidated:['Not Yet Validated','Chưa có thực nghiệm chính thức.']
};
function badge(k,full){const b=BADGES[k];return `<span class="badge ${k}" ${full?`title="${b[1]}"`:''}>${b[0]}${full?` — ${b[1]}`:''}</span>`}
function head(title,badges){return `<div class="demo-head"><h3>${title}</h3><div>${(badges||[]).map(b=>badge(b)).join(' ')}</div></div>`}

/* số liệu */
const P=window.PROJECT;
const vi=(n,d=2)=>Number(n).toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d});
const vi0=n=>Number(n).toLocaleString('vi-VN');
const pct=(x,d=1)=>vi(x*100,d)+'%';
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
function rng(seed){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function gauss(r){let u=0,v=0;while(!u)u=r();while(!v)v=r();return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v)}
const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:0;
const std=a=>{if(a.length<2)return 0;const m=mean(a);return Math.sqrt(mean(a.map(x=>(x-m)**2)))};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* tên lớp */
const CLS=P.classes.map(c=>c.name);
const SHORT={'Benign':'Benign','Bot':'Bot','Brute Force -Web':'Brute Force Web','Brute Force -XSS':'Brute Force XSS','DDOS attack-HOIC':'DDoS HOIC','DDOS attack-LOIC-UDP':'DDoS LOIC-UDP','DDoS attacks-LOIC-HTTP':'DDoS LOIC-HTTP','DoS attacks-GoldenEye':'DoS GoldenEye','DoS attacks-Hulk':'DoS Hulk','DoS attacks-SlowHTTPTest':'DoS SlowHTTPTest','DoS attacks-Slowloris':'DoS Slowloris','FTP-BruteForce':'FTP Brute Force','Infilteration':'Infiltration','SQL Injection':'SQL Injection','SSH-Bruteforce':'SSH Brute Force'};
const cls=n=>P.classes.find(c=>c.name===n);

/* nav */
function initNav(){
  const links=$$('#nav a'), sections=$$('main section[id]');
  const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){links.forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id));const a=links.find(a=>a.hash==='#'+e.target.id);$('#crumb').textContent=a?a.textContent.replace(/^\d+\s*/,'').toUpperCase():''}}),{rootMargin:'-20% 0px -70%'});
  sections.forEach(s=>io.observe(s));
  $('#menuBtn').onclick=()=>$('.sidebar').classList.toggle('open');
  links.forEach(a=>a.addEventListener('click',()=>$('.sidebar').classList.remove('open')));
  const bar=$('#progressBar');addEventListener('scroll',()=>{const h=document.documentElement;bar.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight||1)*100)+'%'},{passive:true});
}
/* tooltip dùng data-tip */
function initTip(){const tip=$('#tip');
  document.addEventListener('mousemove',e=>{const t=e.target.closest&&e.target.closest('[data-tip]');if(!t){tip.style.display='none';return}tip.innerHTML=t.dataset.tip;tip.style.display='block';const w=tip.offsetWidth;tip.style.left=Math.min(innerWidth-w-8,e.clientX+14)+'px';tip.style.top=(e.clientY+16)+'px'});
  document.addEventListener('mouseleave',()=>tip.style.display='none');
}
/* segmented control helper */
function seg(root,onChange){$$('button',root).forEach(b=>b.onclick=()=>{$$('button',root).forEach(x=>x.classList.toggle('on',x===b));onChange(b)})}
function slider(id,label,min,max,val,step,fmt,help){return `<div class="ctl"><label for="${id}">${label}<output id="${id}_o">${fmt?fmt(val):val}</output></label><input id="${id}" type="range" min="${min}" max="${max}" step="${step}" value="${val}">${help?`<small>${help}</small>`:''}</div>`}
function bindSlider(id,fmt,cb){const el=$('#'+id);const f=()=>{$('#'+id+'_o').textContent=fmt?fmt(+el.value):el.value;cb(+el.value)};el.oninput=f;return f}
/* sparkline path */
function spark(vals,w=200,h=34,color='#ff7c43'){if(!vals.length)return'';const mx=Math.max(...vals,1e-9);const step=w/(vals.length-1||1);const d=vals.map((v,i)=>`${i?'L':'M'}${(i*step).toFixed(1)},${(h-3-v/mx*(h-6)).toFixed(1)}`).join(' ');return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><path d="${d}" fill="none" stroke="${color}" stroke-width="1.6"/></svg>`}
/* SVG helper */
function svg(w,h,inner,cls=''){return `<svg viewBox="0 0 ${w} ${h}" class="${cls}" xmlns="http://www.w3.org/2000/svg" role="img">${inner}</svg>`}
