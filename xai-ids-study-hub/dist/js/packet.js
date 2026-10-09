/* packet.js — Chương 01 (Packet → Flow) và Chương 02 (CICFlowMeter → feature) */

/* ===== Tính feature kiểu CICFlowMeter, dùng chung cho cả chương tấn công ===== */
HUB.computeFeatures=function(pk){
  const p=[...pk].sort((a,b)=>a.t-b.t); const n=p.length;
  const f=p.filter(x=>x.dir==='f'), b=p.filter(x=>x.dir==='b');
  const dur=n>1?p[n-1].t-p[0].t:0; // giây
  const iat=a=>{const r=[];for(let i=1;i<a.length;i++)r.push(a[i].t-a[i-1].t);return r};
  const I=iat(p),IF=iat(f),IB=iat(b);
  const lenF=f.map(x=>x.len),lenB=b.map(x=>x.len);
  const cnt=k=>p.filter(x=>x.flags&&x.flags.includes(k)).length;
  const total=lenF.reduce((s,x)=>s+x,0)+lenB.reduce((s,x)=>s+x,0);
  return {
    dur, nF:f.length, nB:b.length, lenF:lenF.reduce((s,x)=>s+x,0), lenB:lenB.reduce((s,x)=>s+x,0),
    pps:dur>0?n/dur:0, bps:dur>0?total/dur:0,
    iatMean:mean(I), iatStd:std(I), iatMax:I.length?Math.max(...I):0, iatMin:I.length?Math.min(...I):0,
    fIatMean:mean(IF), bIatMean:mean(IB),
    fLenMean:mean(lenF), bLenStd:std(lenB), pktLenMean:mean(p.map(x=>x.len)),
    syn:cnt('S'),fin:cnt('F'),rst:cnt('R'),psh:cnt('P'),ack:cnt('A'),n
  };
};

/* ===== Chương 01: Packet → Flow ===== */
(function(){
const SERVERS={
  dns:{name:'DNS 8.8.8.8',ip:'8.8.8.8',color:'#7c5cff',y:60},
  web:{name:'Web 203.0.113.10',ip:'203.0.113.10',color:'#16b8b6',y:140},
  api:{name:'API 203.0.113.20',ip:'203.0.113.20',color:'#ff7c43',y:220},
  cdn:{name:'CDN 198.51.100.7',ip:'198.51.100.7',color:'#6aa51a',y:300}
};
const CLIENT='192.168.1.10';
function build(endMode){
  const pk=[];let id=0;
  const add=(t,srv,dir,flags,len,info,sport,dport,proto)=>pk.push({id:id++,t,srv,dir,flags,len,info,sport,dport,proto:proto||'TCP'});
  // DNS (UDP)
  add(0,'dns','f','',60,'DNS truy vấn shop.example.vn',53211,53,'UDP');
  add(60,'dns','b','',92,'DNS trả lời 203.0.113.10',53211,53,'UDP');
  // Web TCP/HTTPS
  add(90,'web','f','S',60,'SYN',50122,443);add(140,'web','b','SA',60,'SYN-ACK',50122,443);add(150,'web','f','A',54,'ACK',50122,443);
  add(190,'web','f','PA',517,'TLS ClientHello',50122,443);add(260,'web','b','PA',1400,'TLS ServerHello + cert',50122,443);
  add(320,'web','f','PA',300,'GET /',50122,443);add(430,'web','b','PA',1400,'HTML (1)',50122,443);add(450,'web','b','PA',1400,'HTML (2)',50122,443);add(470,'web','f','A',54,'ACK',50122,443);
  // API
  add(520,'api','f','S',60,'SYN',50123,443);add(560,'api','b','SA',60,'SYN-ACK',50123,443);add(570,'api','f','A',54,'ACK',50123,443);
  add(610,'api','f','PA',420,'GET /api/products',50123,443);add(720,'api','b','PA',980,'JSON sản phẩm',50123,443);
  add(740,'api','f','FA',54,'FIN-ACK',50123,443);add(780,'api','b','FA',54,'FIN-ACK',50123,443);
  // CDN
  add(560,'cdn','f','S',60,'SYN',50124,443);add(610,'cdn','b','SA',60,'SYN-ACK',50124,443);add(620,'cdn','f','A',54,'ACK',50124,443);
  add(680,'cdn','f','PA',350,'GET /logo.png',50124,443);add(760,'cdn','b','PA',1400,'ảnh (1)',50124,443);add(780,'cdn','b','PA',1400,'ảnh (2)',50124,443);add(800,'cdn','b','PA',900,'ảnh (3)',50124,443);
  if(endMode==='fin'){add(900,'cdn','f','FA',54,'FIN-ACK',50124,443);add(940,'cdn','b','FA',54,'FIN-ACK',50124,443);}
  if(endMode==='rst'){add(900,'cdn','f','R',54,'RST',50124,443);}
  // Web kết thúc
  add(900,'web','f','FA',54,'FIN-ACK',50122,443);add(950,'web','b','FA',54,'FIN-ACK',50122,443);
  // Tracker bị từ chối -> RST (flow riêng, cổng khác)
  add(300,'api','f','S',60,'SYN tới tracker :8443',50130,8443);add(350,'api','b','R',54,'RST (cổng đóng)',50130,8443);
  return pk.sort((a,b)=>a.t-b.t).map((x,i)=>({...x,n:i+1}));
}
let pk=[],T=0,playing=false,last=0,state={group:true,end:'fin',off:new Set()};
const flowKey=p=>{const a=`${p.dir==='f'?CLIENT:SERVERS[p.srv].ip}:${p.dir==='f'?p.sport:p.dport}`,b=`${p.dir==='f'?SERVERS[p.srv].ip:CLIENT}:${p.dir==='f'?p.dport:p.sport}`;return p.proto+'|'+[a,b].sort().join('|')};
const FCOL=['#7c5cff','#16b8b6','#ff7c43','#6aa51a','#e5484d'];
function flows(){const m=new Map();pk.forEach(p=>{if(state.off.has(p.id))return;const k=flowKey(p);if(!m.has(k))m.set(k,{k,pkts:[],srv:p.srv,sport:p.sport,dport:p.dport,proto:p.proto});m.get(k).pkts.push(p)});
  return [...m.values()].map((f,i)=>{const l=f.pkts[f.pkts.length-1];const end=l.flags.includes('F')?'FIN':l.flags.includes('R')?'RST':'timeout';return {...f,end,col:FCOL[i%FCOL.length],bytes:f.pkts.reduce((s,x)=>s+x.len,0),dur:f.pkts[f.pkts.length-1].t-f.pkts[0].t}})}
function flowColorOf(p,fl){const f=fl.find(f=>f.pkts.includes(p));return f?f.col:'#9aa5b8'}

function render(){
  const fl=flows(); const Tmax=1100;
  const W=700,H=360,cx=90,sx=560;
  let g=`<rect width="${W}" height="${H}" fill="none"/>`;
  g+=`<g font-family="DM Mono,monospace" font-size="11"><rect x="${cx-62}" y="140" width="110" height="80" rx="12" fill="#10182a"/><text x="${cx-7}" y="172" fill="#fff" text-anchor="middle">Client</text><text x="${cx-7}" y="190" fill="#9aa5b8" text-anchor="middle" font-size="9">${CLIENT}</text>`;
  Object.entries(SERVERS).forEach(([k,s])=>{g+=`<line x1="${cx+48}" y1="180" x2="${sx}" y2="${s.y}" stroke="${s.color}" stroke-opacity=".25" stroke-width="2" stroke-dasharray="4 4"/><rect x="${sx}" y="${s.y-22}" width="130" height="44" rx="10" fill="#fff" stroke="${s.color}"/><text x="${sx+65}" y="${s.y-3}" text-anchor="middle" fill="#10182a">${s.name.split(' ')[0]}</text><text x="${sx+65}" y="${s.y+12}" text-anchor="middle" fill="#6b7686" font-size="9">${s.ip}</text>`});
  pk.forEach(p=>{if(state.off.has(p.id))return;const dur=260;const dt=T-p.t;if(dt<0||dt>dur)return;let u=dt/dur;const s=SERVERS[p.srv];const x0=cx+48,y0=180,x1=sx,y1=s.y;if(p.dir==='b')u=1-u;const x=x0+(x1-x0)*u,y=y0+(y1-y0)*u;const col=state.group?flowColorOf(p,fl):'#9aa5b8';g+=`<circle cx="${x}" cy="${y}" r="${5+Math.min(6,p.len/300)}" fill="${col}" stroke="#fff" stroke-width="1.5"/>`});
  g+='</g>';
  // thanh thời gian
  const pctT=T/Tmax;g+=`<rect x="20" y="${H-20}" width="${W-40}" height="4" rx="2" fill="#dfe2dc"/><rect x="20" y="${H-20}" width="${(W-40)*pctT}" height="4" rx="2" fill="#10182a"/>`;
  $('#pkSvg').innerHTML=g;
  // list
  $('#pkList').innerHTML=pk.map(p=>{const col=state.group?flowColorOf(p,fl):'#9aa5b8';const off=state.off.has(p.id);const seen=p.t<=T;
    const s=p.dir==='f'?`${CLIENT}:${p.sport}`:`${SERVERS[p.srv].ip}:${p.dport}`,d=p.dir==='f'?`${SERVERS[p.srv].ip}:${p.dport}`:`${CLIENT}:${p.sport}`;
    return `<div class="pk-row ${off?'off':''}" data-id="${p.id}" style="${seen||off?'':'opacity:.35'}" data-tip="<b>#${p.n}</b> ${p.proto} ${s} → ${d}<br>${p.info} · ${p.len} byte${p.flags?` · cờ ${p.flags}`:''}<br>Bấm để bật/tắt packet này"><span><i class="dot" style="background:${col}"></i></span><span>${p.t} ms</span><span>${p.dir==='f'?'→':'←'} ${esc(p.info)}</span><span>${p.flags||p.proto}</span></div>`}).join('');
  $$('#pkList .pk-row').forEach(r=>r.onclick=()=>{const id=+r.dataset.id;state.off.has(id)?state.off.delete(id):state.off.add(id);render()});
  // flows
  $('#pkFlows').innerHTML=state.group?fl.map(f=>`<div class="flowbox" style="border-left:4px solid ${f.col}"><h5>${f.proto} · ${f.pkts[0].dir==='f'?CLIENT+':'+f.sport:SERVERS[f.srv].ip+':'+f.dport} ↔ ${f.pkts[0].dir==='f'?SERVERS[f.srv].ip+':'+f.dport:CLIENT+':'+f.sport}</h5><small>${f.pkts.length} packet · ${f.bytes} byte · ${f.dur} ms · kết thúc: <b>${f.end==='timeout'?'timeout (không có FIN/RST)':f.end}</b></small></div>`).join(''):'<p class="note">Tắt “Gom theo 5-tuple”: bạn chỉ thấy một dòng packet lẫn lộn, chưa có khái niệm flow.</p>';
  $('#pkSummary').innerHTML=state.group?`<b>${pk.filter(p=>!state.off.has(p.id)).length}</b> packet → <b>${fl.length}</b> flow. Mỗi flow là một mẫu mô hình phải phân loại; ${fl.length} flow nghĩa là ${fl.length} lần dự đoán cho một lần mở trang.`:`<b>${pk.filter(p=>!state.off.has(p.id)).length}</b> packet rời rạc. Không có cách nào kết luận hành vi chỉ từ một packet.`;
  $('#pkT').value=T;$('#pkTo').textContent=Math.round(T)+' ms';
}
function tick(ts){if(!playing)return;const dt=ts-last;last=ts;T+=dt*(+$('#pkSpeed').value);if(T>=1100){T=1100;playing=false;$('#pkPlay').textContent='▶ Phát lại'}render();if(playing)requestAnimationFrame(tick)}
HUB.reg(function packetInit(){
  const root=$('#packetDemo');
  root.innerHTML=head('Demo · Một lần mở website tạo bao nhiêu flow?',['interactive'])+`
   <div class="toolbar"><button class="btn sm" id="pkPlay">▶ Phát</button>
    <label class="lbl">TỐC ĐỘ<select id="pkSpeed"><option value="0.25">0,25×</option><option value="0.5" selected>0,5×</option><option value="1">1×</option></select></label>
    <label class="toggle"><input type="checkbox" id="pkGroup" checked> Gom theo 5-tuple</label>
    <label class="lbl">KẾT THÚC FLOW CDN<span class="seg" id="pkEnd"><button class="on" data-e="fin">FIN</button><button data-e="rst">RST</button><button data-e="timeout">Timeout</button></span></label></div>
   <div class="pk-wrap"><div><div class="pk-stage"><svg id="pkSvg" viewBox="0 0 700 360"></svg></div>
     <div class="ctl"><label for="pkT">Thời gian<output id="pkTo">0 ms</output></label><input id="pkT" type="range" min="0" max="1100" step="5" value="0"></div>
     <p id="pkSummary" class="note good"></p></div>
    <div><div class="pk-list" id="pkList"></div></div></div>
   <h4>Các flow hình thành</h4><div id="pkFlows"></div>
   <p class="note">Bấm một dòng packet để tắt nó (ví dụ tắt packet FIN/RST) và xem flow kết thúc thế nào. Địa chỉ IP dùng dải tài liệu (TEST-NET), tất cả là dữ liệu minh họa.</p>`;
  pk=build('fin');
  $('#pkPlay').onclick=()=>{if(T>=1100)T=0;playing=!playing;last=performance.now();$('#pkPlay').textContent=playing?'⏸ Dừng':'▶ Phát';if(playing)requestAnimationFrame(tick)};
  $('#pkT').oninput=e=>{T=+e.target.value;playing=false;$('#pkPlay').textContent='▶ Phát';render()};
  $('#pkGroup').onchange=e=>{state.group=e.target.checked;render()};
  seg($('#pkEnd'),b=>{state.end=b.dataset.e;pk=build(state.end);state.off.clear();render()});
  T=700;render();
});
})();

/* ===== Chương 02: CICFlowMeter → feature ===== */
(function(){
const MAXT=6; // giây
let pk=[],unit='us',sel=-1,prev={};
const PRESETS={
 web:()=>[[0,'f',60,'S'],[.06,'b',60,'SA'],[.09,'f',54,'A'],[.2,'f',517,'PA'],[.35,'b',1400,'PA'],[.6,'f',300,'PA'],[.9,'b',1400,'PA'],[1.2,'b',1400,'PA'],[1.8,'f',54,'A'],[2.1,'b',900,'PA'],[2.4,'f',54,'FA'],[2.45,'b',54,'FA']],
 flood:()=>Array.from({length:30},(_,i)=>[i*.02,'f',66,i?'P':'S']).concat([[.6,'b',54,'A']]),
 slow:()=>[[0,'f',60,'S'],[.1,'b',60,'SA'],[.15,'f',54,'A'],[1.5,'f',60,'P'],[3,'f',58,'P'],[4.5,'f',59,'P'],[5.9,'f',58,'P']]
};
function load(name){pk=PRESETS[name]().map(([t,dir,len,flags])=>({t,dir,len,flags}));draw()}
function X(t){return 40+(t/MAXT)*820}
const FT=[
 ['dur','Flow Duration',f=>unit==='us'?vi0(Math.round(f.dur*1e6))+' µs':vi(f.dur,3)+' s','Thời gian từ packet đầu đến packet cuối.'],
 ['nF','Total Fwd Packets',f=>f.nF,'Số packet chiều đi (client → server).'],
 ['nB','Total Backward Packets',f=>f.nB,'Số packet chiều về.'],
 ['pps','Flow Packets/s',f=>vi(f.pps,2),'Tổng số packet chia cho thời lượng (giây). Flood: rất cao; slow: rất thấp.'],
 ['bps','Flow Bytes/s',f=>vi(f.bps,0),'Tổng byte chia cho thời lượng.'],
 ['iatMean','Flow IAT Mean',f=>unit==='us'?vi0(Math.round(f.iatMean*1e6))+' µs':vi(f.iatMean,4)+' s','Khoảng cách trung bình giữa hai packet liên tiếp.'],
 ['iatStd','Flow IAT Std',f=>unit==='us'?vi0(Math.round(f.iatStd*1e6))+' µs':vi(f.iatStd,4)+' s','Độ đều của nhịp: nhỏ = đều (máy), lớn = thất thường (người dùng/burst).'],
 ['iatMax','Flow IAT Max',f=>unit==='us'?vi0(Math.round(f.iatMax*1e6))+' µs':vi(f.iatMax,3)+' s','Khoảng lặng lâu nhất; slow attack có Max lớn.'],
 ['fIatMean','Fwd IAT Mean',f=>unit==='us'?vi0(Math.round(f.fIatMean*1e6))+' µs':vi(f.fIatMean,4)+' s','IAT trung bình chỉ xét chiều đi.'],
 ['bLenStd','Bwd Packet Length Std',f=>vi(f.bLenStd,1),'Độ lệch chuẩn kích thước packet chiều về.'],
 ['syn','SYN Flag Count',f=>f.syn,'Số packet có cờ SYN (mở kết nối).'],
 ['fin','FIN Flag Count',f=>f.fin,'Số packet có cờ FIN (đóng nhẹ nhàng).'],
 ['rst','RST Flag Count',f=>f.rst,'Số packet RST (ngắt đột ngột). Nhiều RST có thể là quét cổng, brute force hoặc lỗi kết nối.'],
 ['psh','PSH Flag Count',f=>f.psh,'Số packet có cờ PSH (đẩy dữ liệu lên ứng dụng).']
];
function draw(){
  const f=HUB.computeFeatures(pk);
  let g=`<rect x="0" y="0" width="900" height="250" fill="#10182a" rx="12"/>`;
  g+=`<line x1="40" x2="860" y1="125" y2="125" stroke="#3a4a66"/>`;
  for(let s=0;s<=MAXT;s++){g+=`<line x1="${X(s)}" x2="${X(s)}" y1="122" y2="128" stroke="#5f6c82"/><text x="${X(s)}" y="244" fill="#8e9ab0" font-size="10" font-family="DM Mono" text-anchor="middle">${s}s</text>`}
  g+=`<text x="46" y="20" fill="#29d3d1" font-size="10" font-family="DM Mono">FORWARD (client → server)</text><text x="46" y="238" fill="#b7f23d" font-size="10" font-family="DM Mono" dy="-14">BACKWARD (server → client)</text>`;
  pk.forEach((p,i)=>{const h=8+Math.min(90,p.len/1400*90);const up=p.dir==='f';const y1=up?125-h:125,y2=up?125:125+h;const col=up?'#29d3d1':'#b7f23d';
    g+=`<g class="pkt" data-i="${i}" style="cursor:ew-resize"><line x1="${X(p.t)}" x2="${X(p.t)}" y1="${y1}" y2="${y2}" stroke="${col}" stroke-width="${i===sel?5:3}" stroke-linecap="round"/><circle cx="${X(p.t)}" cy="${up?y1:y2}" r="${i===sel?7:5}" fill="${p.flags.includes('R')?'#ff7c43':col}" stroke="#10182a" stroke-width="2"/><title>${p.dir==='f'?'Fwd':'Bwd'} · ${p.len} byte · cờ ${p.flags||'-'} · t=${p.t.toFixed(2)}s</title></g>`});
  $('#ftSvg').innerHTML=g;
  $('#ftGrid').innerHTML=FT.map(([k,name,fmt,tip])=>{const v=fmt(f);const hl=prev[k]!==undefined&&prev[k]!==v;prev[k]=v;return `<div class="feat ${hl?'hl':''}" data-tip="${esc(tip)}"><small>${name}</small><b>${v}</b></div>`}).join('');
  const warn=unit==='s';
  $('#ftUnit').innerHTML=warn?`<div class="note warn"><b>Lỗi tương thích đơn vị (RQ3):</b> dữ liệu huấn luyện lưu thời gian theo µs, CICFlowMeter Python xuất theo giây. Flow này có Flow Duration = <b>${vi(f.dur,3)}</b> thay vì <b>${vi0(Math.round(f.dur*1e6))}</b>: mô hình sẽ thấy một flow “dài ${vi(f.dur,3)} µs”, tức nhanh hơn thật 1.000.000 lần. Schema Guard phải nhân ×10⁶ cho mọi feature thời gian trước khi dự đoán.</div>`:`<div class="note good">Đơn vị khớp dữ liệu huấn luyện (µs). Chuyển sang “giây” để xem lỗi tương thích.</div>`;
}
HUB.reg(function featureInit(){
  const root=$('#featureDemo');
  root.innerHTML=head('Demo · Kéo packet, xem feature đổi',['interactive'])+`
  <div class="toolbar"><label class="lbl">MẪU FLOW<span class="seg" id="ftPreset"><button class="on" data-p="web">Mở web bình thường</button><button data-p="flood">Flood</button><button data-p="slow">Slow attack</button></span></label>
   <label class="lbl">ĐƠN VỊ THỜI GIAN<span class="seg" id="ftUnitSeg"><button class="on" data-u="us">micro giây (dữ liệu huấn luyện)</button><button data-u="s">giây (CICFlowMeter Python)</button></span></label>
   <button class="btn sm alt" id="ftAddF">+ packet đi</button><button class="btn sm alt" id="ftAddB">+ packet về</button><button class="btn sm alt" id="ftAddR">+ RST</button><button class="btn sm alt" id="ftDel">− packet cuối</button></div>
  <div class="timeline"><svg id="ftSvg" viewBox="0 0 900 250"></svg></div>
  <p class="note">Kéo ngang một packet trên timeline để đổi thời điểm. Chiều cao thể hiện kích thước packet. Ô nào đổi giá trị sẽ viền cam.</p>
  <div class="feat-grid" id="ftGrid"></div><div id="ftUnit" class="mt"></div>`;
  seg($('#ftPreset'),b=>{prev={};load(b.dataset.p)});
  seg($('#ftUnitSeg'),b=>{unit=b.dataset.u;draw()});
  $('#ftAddF').onclick=()=>{const t=pk.length?Math.max(...pk.map(p=>p.t)):0;pk.push({t:Math.min(MAXT,t+.2),dir:'f',len:200,flags:'P'});draw()};
  $('#ftAddB').onclick=()=>{const t=pk.length?Math.max(...pk.map(p=>p.t)):0;pk.push({t:Math.min(MAXT,t+.2),dir:'b',len:800,flags:'P'});draw()};
  $('#ftAddR').onclick=()=>{const t=pk.length?Math.max(...pk.map(p=>p.t)):0;pk.push({t:Math.min(MAXT,t+.1),dir:'b',len:54,flags:'R'});draw()};
  $('#ftDel').onclick=()=>{pk.pop();draw()};
  // kéo thả
  const svgEl=$('#ftSvg');let drag=-1;
  const toT=e=>{const r=svgEl.getBoundingClientRect();const x=(e.clientX-r.left)/r.width*900;return clamp((x-40)/820*MAXT,0,MAXT)};
  svgEl.addEventListener('pointerdown',e=>{const g=e.target.closest('.pkt');if(!g)return;drag=+g.dataset.i;sel=drag;svgEl.setPointerCapture(e.pointerId);e.preventDefault()});
  svgEl.addEventListener('pointermove',e=>{if(drag<0)return;pk[drag].t=Math.round(toT(e)*100)/100;draw()});
  svgEl.addEventListener('pointerup',()=>{drag=-1;sel=-1;draw()});
  load('web');
});
})();
