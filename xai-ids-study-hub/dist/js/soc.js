/* soc.js — IDS–SOC pipeline, bảng cảnh báo, tiêm lỗi, điều tra theo IP (mô phỏng) */
HUB.reg(function soc(){
const STEPS=[
 ['Capture','tcpdump / pcap',4,'prototype'],
 ['CICFlowMeter','packet → flow',38,'prototype'],
 ['Schema Guard','kiểm tra 78 cột',2,'proposed'],
 ['XGBoost','15 lớp',6,'proposed'],
 ['TreeSHAP','giải thích',14,'proposed'],
 ['Alert','gom + ưu tiên',3,'proposed'],
 ['SOC','dashboard',0,'proposed']];
const FAULTS={
 none:{n:'Không lỗi',at:-1,msg:'Dữ liệu hợp lệ → toàn bộ pipeline chạy.'},
 missing:{n:'Thiếu feature',at:2,msg:'Schema Guard: thiếu 3/78 cột (Init Fwd Win Byts, …). Từ chối flow, ghi log, KHÔNG điền 0 âm thầm.'},
 order:{n:'Sai thứ tự cột',at:2,msg:'Schema Guard: cột đúng tên nhưng sai vị trí. Tự sắp xếp lại theo schema huấn luyện rồi đi tiếp (cảnh báo mức thấp).',recover:true},
 nan:{n:'Giá trị NaN',at:2,msg:'Schema Guard: Flow Byts/s = NaN. Với NaN/Infinity: loại flow khỏi dự đoán, đánh dấu “dữ liệu hỏng”.'},
 inf:{n:'Giá trị Infinity',at:2,msg:'Schema Guard: Flow Pkts/s = Infinity (chia cho thời lượng 0). Flow bị loại, gửi sang hàng đợi kiểm tra.'},
 unit:{n:'Sai đơn vị thời gian',at:2,msg:'Schema Guard: Flow Duration quá nhỏ so với phân phối huấn luyện (giây thay vì µs). Phát hiện lệch ×10⁶ → dừng, yêu cầu cấu hình lại CICFlowMeter.'},
 lowconf:{n:'Độ tin cậy thấp',at:3,msg:'XGBoost: xác suất cao nhất 0,41 < ngưỡng 0,60. Cảnh báo gắn nhãn “không chắc chắn”, chuyển analyst xem tay.',soft:true},
 shapfail:{n:'SHAP lỗi',at:4,msg:'TreeSHAP timeout. Vẫn phát cảnh báo nhưng ghi “chưa có giải thích”; không giả lập lý do.',soft:true}
};
let fault='none',run=0;
const pl=$('#socPipeline');
pl.innerHTML=`<div class="card"><div class="demo-head"><h3>Pipeline IDS–SOC</h3><div>${badge('prototype')} ${badge('proposed')} ${badge('unvalidated')}</div></div>
<div class="pipeline" id="plRow"></div><div id="plTotal" class="note"></div></div>`;
function drawPl(){
 const f=FAULTS[fault];let tot=0;
 $('#plRow').innerHTML=STEPS.map((s,i)=>{
  let cls='';if(f.at>=0){if(i===f.at)cls=f.soft||f.recover?'active':'fail';else if(i>f.at&&!f.soft&&!f.recover)cls='skip';}
  const ran=cls!=='skip'&&cls!=='fail';if(ran)tot+=s[2];
  return `${i?'<i>→</i>':''}<div class="${cls}"><b>${s[0]}</b><span>${s[1]}</span><em>${cls==='skip'?'—':cls==='fail'?'LỖI':s[2]+' ms'}</em></div>`}).join('');
 $('#plTotal').innerHTML=`Độ trễ minh họa cộng dồn: <b>${tot} ms</b> (số mô phỏng, <b>Not Yet Validated</b>).`;
}
/* alerts */
const attacks=P.classes.filter(c=>c.name!=='Benign'&&c.example);
const SEV={'Infilteration':'CAO','Bot':'CAO','SQL Injection':'CAO','SSH-Bruteforce':'TRUNG','FTP-BruteForce':'TRUNG'};
const alerts=attacks.slice(0,8).map((c,i)=>({c,ip:`172.31.${69+i%5}.${10+i*7}`,sev:SEV[c.name]||'TRUNG',t:`10:${String(12+i*3).padStart(2,'0')}`}));
let sel=0,verdicts={};
const sb=$('#socBoard');
function drawBoard(){
 const a=alerts[sel],ex=a.c.example,top=ex.shap.slice(0,6),mx=Math.max(...top.map(x=>Math.abs(x[1])));
 const open=alerts.length-Object.keys(verdicts).length;
 sb.innerHTML=`<div class="soc-top"><span>SOC DASHBOARD · MÔ PHỎNG</span><span>${badge('proposed')}</span></div>
 <div class="soc-kpis"><article><small>CẢNH BÁO MỞ</small><b>${open}</b><span>cần xử lý</span></article><article><small>ĐÃ KẾT LUẬN</small><b>${Object.keys(verdicts).length}</b><span>analyst</span></article><article><small>FALSE POSITIVE</small><b class="danger">${Object.values(verdicts).filter(v=>v==='fp').length}</b><span>đã loại</span></article><article><small>CẦN THÊM BẰNG CHỨNG</small><b>${Object.values(verdicts).filter(v=>v==='more').length}</b><span>chờ</span></article></div>
 <div class="soc-main"><div class="alert-list"><div class="soc-title">HÀNG ĐỢI CẢNH BÁO<span>${alerts.length}</span></div>
 ${alerts.map((x,i)=>`<div class="alert-row ${i===sel?'active':''}" data-i="${i}"><span class="severity">${x.sev}</span><div><b>${esc(SHORT[x.c.name]||x.c.name)}</b><small>${x.ip} · ${x.t}${verdicts[i]?' · ✔ '+({tp:'TP',fp:'FP',more:'cần thêm'})[verdicts[i]]:''}</small></div><output>${pct(x.c.example.prob,1)}</output></div>`).join('')}</div>
 <div class="investigation-content"><div class="alert-heading"><div><h3 style="color:#fff;margin:0">${esc(SHORT[a.c.name]||a.c.name)}</h3><small style="color:#8794ab">Nguồn ${a.ip} · flow #${ex.sample_id}</small></div><div class="confidence-ring">${Math.round(ex.prob*100)}%</div></div>
 <div class="flow-meta"><div><small>MỨC ƯU TIÊN</small><b>${a.sev}</b></div><div><small>Σ SHAP</small><b>${vi(ex.shapSum,2)}</b></div><div><small>LIME R² (flow)</small><b>${vi(ex.r2,2)}</b></div></div>
 <p style="color:#8794ab;font:9px var(--mono);margin:16px 0 4px">LÝ DO (TOP-6 SHAP, dữ liệu thật của 1 flow đại diện)</p>
 <div class="reason-list">${top.map(([f,v])=>`<div><span>${esc(f)}</span><i><em style="width:${Math.abs(v)/mx*100}%;background:${v<0?'var(--orange)':'var(--cyan-l)'}"></em></i><b>${v>0?'+':''}${vi(v,2)}</b></div>`).join('')}</div>
 <p style="color:#8794ab;font-size:11px">SHAP cho biết đặc trưng nào đẩy mô hình về lớp này, chưa phải bằng chứng nhân quả. Analyst vẫn phải kiểm tra.</p>
 <div class="verdicts">${[['tp','True positive'],['fp','False positive'],['more','Cần thêm bằng chứng']].map(([k,l])=>`<button data-v="${k}" class="${verdicts[sel]===k?'on':''}">${l}</button>`).join('')}</div></div></div>`;
 $$('.alert-row',sb).forEach(r=>r.onclick=()=>{sel=+r.dataset.i;drawBoard()});
 $$('.verdicts button',sb).forEach(b=>b.onclick=()=>{verdicts[sel]=b.dataset.v;drawBoard()});
}
/* fault */
const fd=$('#faultDemo');
fd.innerHTML=`${head('Tiêm lỗi: pipeline phản ứng thế nào?',['proposed','unvalidated'])}
<p class="note" style="margin-top:0">Chọn một lỗi dữ liệu và xem bước nào chặn nó. Nguyên tắc: <b>fail loudly</b>, không đưa dữ liệu hỏng vào mô hình.</p>
<div class="fault-grid" id="faultBtns">${Object.entries(FAULTS).map(([k,v])=>`<button data-k="${k}" class="${k===fault?'on':''}">${v.n}</button>`).join('')}</div>
<div class="sys-log" id="faultLog"></div>`;
function drawFault(){
 const f=FAULTS[fault];const L=[];
 STEPS.forEach((s,i)=>{if(f.at>=0&&i>f.at&&!f.soft&&!f.recover){L.push(`[skip] ${s[0]}`);return}
  if(i===f.at)L.push(`[${f.soft||f.recover?'warn':'FAIL'}] ${s[0]}: ${f.msg}`);else L.push(`[ ok ] ${s[0]} (${s[2]} ms)`)});
 $('#faultLog').textContent=L.join('\n');
 $$('#faultBtns button').forEach(b=>b.classList.toggle('on',b.dataset.k===fault));
 drawPl();
}
$$('#faultBtns button').forEach(b=>b.onclick=()=>{fault=b.dataset.k;drawFault()});
/* investigation */
const iv=$('#investDemo');
const r=rng(7);
const IPS=[['10.0.0.23','scan/brute force',[['SSH-Bruteforce',0.99,22],['SSH-Bruteforce',0.98,22],['SSH-Bruteforce',0.99,22],['SSH-Bruteforce',0.97,22],['Benign',0.9,22]],'tp'],
 ['10.0.0.57','trình duyệt bình thường',[['Infilteration',0.52,443],['Benign',0.95,443],['Benign',0.97,80],['Benign',0.93,443]],'fp'],
 ['10.0.0.91','khó kết luận',[['Infilteration',0.55,443],['Infilteration',0.61,8080],['Benign',0.7,443]],'more']];
let iSel=0,iAns={};
function drawInv(){
 const g=IPS[iSel];
 iv.innerHTML=`${head('Điều tra theo IP nguồn',['proposed','unvalidated'])}
 <p class="note" style="margin-top:0">Một flow lẻ ít khi đủ để kết luận. Analyst gom các flow theo <b>IP nguồn</b>, xem mẫu hình lặp lại rồi mới quyết định. Web này <b>không chặn IP thật</b>.</p>
 <div class="seg" id="ipTabs">${IPS.map((x,i)=>`<button class="${i===iSel?'on':''}" data-i="${i}">${x[0]}</button>`).join('')}</div>
 <table class="mt"><thead><tr><th>#</th><th>Dự đoán</th><th>Độ tin cậy</th><th>Cổng đích</th></tr></thead><tbody>${g[2].map((f,i)=>`<tr><td>${i+1}</td><td>${esc(SHORT[f[0]]||f[0])}</td><td>${pct(f[1],0)}</td><td>${f[2]}</td></tr>`).join('')}</tbody></table>
 <div class="verdicts" style="margin-top:12px">${[['tp','True positive'],['fp','False positive'],['more','Cần thêm bằng chứng']].map(([k,l])=>`<button data-v="${k}" class="${iAns[iSel]===k?'on':''}" style="color:var(--ink);border-color:var(--line)">${l}</button>`).join('')}</div>
 <p id="ivFb" class="note"></p>`;
 $$('#ipTabs button').forEach(b=>b.onclick=()=>{iSel=+b.dataset.i;drawInv()});
 $$('.verdicts button',iv).forEach(b=>b.onclick=()=>{iAns[iSel]=b.dataset.v;drawInv();
  const ok=b.dataset.v===g[3];$('#ivFb').innerHTML=(ok?'Hợp lý. ':'Chưa chắc. ')+({tp:'Nhiều flow cùng nhãn tấn công, cùng cổng dịch vụ, độ tin cậy cao → mẫu hình lặp lại, đáng tin.',fp:'Chỉ 1 flow nghi ngờ với độ tin cậy ~52%, còn lại là Benign. Infiltration là lớp khó (recall 16%) nên dễ báo nhầm.',more:'Độ tin cậy thấp, nhiều cổng khác nhau. Nên lấy thêm PCAP / log host trước khi kết luận.'})[g[3]]});
}
$('#plRow')&&0;
drawFault();drawBoard();drawInv();
});
