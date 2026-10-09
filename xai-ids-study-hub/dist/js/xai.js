/* xai.js — Chương 08 SHAP, 09 LIME, 10 SHAP vs LIME, 11 Đánh giá, 12 Fingerprint & giới hạn */
const FEAT={
 'Dst Port':'Cổng đích. Gắn chặt với dịch vụ (80 web, 22 SSH, 21 FTP). Rất dễ trở thành “dấu vân tay” của môi trường dữ liệu.',
 'Protocol':'Giao thức tầng 4 (6 = TCP, 17 = UDP).',
 'Flow Duration':'Thời lượng flow. Slow attack dài, flood ngắn.',
 'Tot Fwd Pkts':'Tổng số packet chiều đi.','Tot Bwd Pkts':'Tổng số packet chiều về.',
 'TotLen Fwd Pkts':'Tổng byte chiều đi.','TotLen Bwd Pkts':'Tổng byte chiều về.',
 'Fwd Pkt Len Mean':'Kích thước trung bình packet chiều đi.','Bwd Pkt Len Mean':'Kích thước trung bình packet chiều về.',
 'Fwd Pkt Len Std':'Độ lệch chuẩn kích thước packet đi.','Bwd Pkt Len Std':'Độ lệch chuẩn kích thước packet về.',
 'Flow Byts/s':'Byte mỗi giây của flow.','Flow Pkts/s':'Packet mỗi giây của flow.','Fwd Pkts/s':'Packet mỗi giây chiều đi.','Bwd Pkts/s':'Packet mỗi giây chiều về.',
 'Flow IAT Mean':'Khoảng cách trung bình giữa hai packet liên tiếp.','Flow IAT Std':'Độ biến thiên khoảng cách giữa packet.','Flow IAT Max':'Khoảng lặng dài nhất.','Flow IAT Min':'Khoảng cách ngắn nhất.',
 'Fwd IAT Tot':'Tổng thời gian giữa các packet chiều đi.','Fwd IAT Mean':'IAT trung bình chiều đi.','Fwd IAT Std':'Độ biến thiên IAT chiều đi.','Fwd IAT Max':'IAT lớn nhất chiều đi.','Fwd IAT Min':'IAT nhỏ nhất chiều đi.',
 'Bwd IAT Mean':'IAT trung bình chiều về.','Bwd IAT Min':'IAT nhỏ nhất chiều về.',
 'FIN Flag Cnt':'Số cờ FIN: đóng kết nối nhẹ nhàng.','RST Flag Cnt':'Số cờ RST: ngắt đột ngột. Gắn với quét cổng, brute force, lỗi kết nối.','PSH Flag Cnt':'Số cờ PSH.','ACK Flag Cnt':'Số cờ ACK.','URG Flag Cnt':'Số cờ URG.','CWE Flag Count':'Cờ CWE.','Fwd URG Flags':'Cờ URG chiều đi.','Fwd PSH Flags':'Cờ PSH chiều đi.',
 'Init Fwd Win Byts':'Cửa sổ TCP ban đầu chiều đi. Phụ thuộc hệ điều hành/công cụ, dễ là fingerprint môi trường.','Init Bwd Win Byts':'Cửa sổ TCP ban đầu chiều về.',
 'Fwd Seg Size Min':'Kích thước segment nhỏ nhất chiều đi (MSS). Fingerprint môi trường điển hình.',
 'Fwd Act Data Pkts':'Số packet chiều đi có dữ liệu thật.','Fwd Header Len':'Tổng độ dài header chiều đi.','Pkt Len Mean':'Kích thước packet trung bình.','Pkt Len Std':'Độ lệch chuẩn kích thước packet.','Pkt Len Max':'Kích thước packet lớn nhất.','Pkt Len Var':'Phương sai kích thước packet.',
 'Idle Mean':'Thời gian nghỉ trung bình.','Idle Min':'Thời gian nghỉ ngắn nhất.','Idle Max':'Thời gian nghỉ dài nhất.','Subflow Fwd Pkts':'Packet chiều đi trong subflow.','Fwd Pkt Len Max':'Kích thước lớn nhất packet đi.','Fwd Pkt Len Min':'Kích thước nhỏ nhất packet đi.'
};
HUB.FEAT=FEAT;
const finfo=n=>FEAT[n]||'Một trong 78 flow feature của CICFlowMeter.';
const FPRINT=['Dst Port','Init Fwd Win Byts','Init Bwd Win Byts','Fwd Seg Size Min','Protocol'];

/* ---------- tính chỉ số so sánh ---------- */
function topK(list,k,key){return list.slice().sort((a,b)=>Math.abs(b[1])-Math.abs(a[1])).slice(0,k)}
function spearman(a,b){ // a,b: danh sách tên theo thứ hạng, chỉ lấy phần chung
  const com=a.filter(x=>b.includes(x));const n=com.length;if(n<2)return null;const ra=com.map(x=>a.filter(y=>com.includes(y)).indexOf(x)+1),rb=com.map(x=>b.filter(y=>com.includes(y)).indexOf(x)+1);
  const d2=ra.reduce((s,r,i)=>s+(r-rb[i])**2,0);return 1-6*d2/(n*(n*n-1))}
function compareLists(shap,lime,k){const s=topK(shap,k),l=topK(lime,k);const sn=s.map(x=>x[0]),ln=l.map(x=>x[0]);const com=sn.filter(x=>ln.includes(x));const uni=new Set([...sn,...ln]);
  const same=com.filter(n=>Math.sign(s.find(x=>x[0]===n)[1])===Math.sign(l.find(x=>x[0]===n)[1])).length;
  return{s,l,sn,ln,com,jac:com.length/uni.size,sp:spearman(sn,ln),sign:com.length?same/com.length:null,uni:uni.size}}

/* ---------- Shapley chính xác cho mô hình đồ chơi ---------- */
const TOY={names:['Flow Pkts/s','RST Cnt','Duration'],base:[3,2,4],f:(a,b,c)=>.5*a+.08*b*c+(a>5?1.2:0)-.3*c};
function toyShapley(x){const n=3,perms=[[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]];const phi=[0,0,0];
  perms.forEach(p=>{const cur=TOY.base.slice();let prev=TOY.f(...cur);p.forEach(i=>{cur[i]=x[i];const v=TOY.f(...cur);phi[i]+=(v-prev)/perms.length;prev=v})});return phi}

HUB.reg(function xaiInit(){
  const classOpts=sel=>CLS.map(n=>`<option value="${esc(n)}" ${n===sel?'selected':''}>${esc(SHORT[n]||n)}</option>`).join('');

  /* ===== 08 SHAP waterfall (flow thật) ===== */
  const sd=$('#shapDemo');
  sd.innerHTML=head('Demo · SHAP trên một flow thật của dự án',['real'])+`
   <div class="toolbar"><label class="lbl">LỚP DỰ ĐOÁN<select id="swCls">${classOpts('Bot')}</select></label>
    <label class="lbl">TOP-K<span class="seg" id="swK"><button data-k="3">3</button><button class="on" data-k="5">5</button><button data-k="10">10</button></span></label>
    <label class="lbl">THANG<span class="seg" id="swScale"><button class="on" data-s="lin">tuyến tính</button><button data-s="sqrt">√ (phóng to giá trị nhỏ)</button></span></label></div>
   <div id="swInfo" class="kv"></div><div class="wf-rows mt" id="swRows"></div><div class="wf-total" id="swTot"></div><p id="swNote" class="conclusion"></p>
   <p class="note">Bấm một dòng để tắt feature đó và xem tổng thay đổi. Đây là SHAP <b>raw margin</b> của lớp đã dự đoán, tính bằng TreeSHAP trên mô hình XGBoost thật; flow là flow có Local R² trung vị của lớp trong cohort ghép cặp.</p>`;
  let swK=5,swS='lin',swOff=new Set();
  const swDraw=()=>{const name=$('#swCls').value,c=cls(name),ex=c.example;if(!ex){return}
    const rows=topK(ex.shap,swK);const top10=ex.shap.reduce((s,x)=>s+x[1],0);
    const mx=Math.max(...rows.map(x=>Math.abs(x[1])),1e-9);const sc=v=>swS==='sqrt'?Math.sqrt(Math.abs(v)/mx):Math.abs(v)/mx;
    $('#swInfo').innerHTML=`<div><small>FLOW (sample_id)</small><b class="sm">#${ex.sample_id}</b></div><div><small>XÁC SUẤT DỰ ĐOÁN</small><b>${pct(ex.prob,2)}</b></div><div><small>TỔNG ĐÓNG GÓP 78 FEATURE</small><b>${ex.shapSum>0?'+':''}${vi(ex.shapSum,3)}</b></div><div><small>TOP-${swK} HIỆN CHỌN</small><b id="swSel">—</b></div>`;
    $('#swRows').innerHTML=rows.map(([n,v],i)=>{const off=swOff.has(n);const w=Math.max(1.5,sc(v)*48);return `<div class="wf-row ${off?'off':''}" data-n="${esc(n)}" data-tip="<b>${esc(n)}</b><br>${esc(finfo(n))}<br>SHAP = ${v>0?'+':''}${vi(v,4)} (${v>0?'đẩy điểm lên':'kéo điểm xuống'} cho lớp ${esc(SHORT[name])})"><span>${i+1}. ${esc(n)}</span><div class="track"><i style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:#4a5a78"></i><b class="seg-bar ${v>0?'pos':'neg'}" style="${v>0?`left:50%;width:${w}%`:`right:50%;width:${w}%`}"></b></div><output style="color:${v>0?'#29d3d1':'#ff9d73'}">${v>0?'+':''}${vi(v,3)}</output></div>`}).join('');
    const selSum=rows.filter(r=>!swOff.has(r[0])).reduce((s,x)=>s+x[1],0);$('#swSel').textContent=(selSum>0?'+':'')+vi(selSum,3);
    const rest=ex.shapSum-top10;
    $('#swTot').innerHTML=`<span>Σ Top-10 = ${vi(top10,3)} · 68 feature còn lại = ${vi(rest,3)}</span><span>raw margin = base value + ${vi(ex.shapSum,3)}</span>`;
    const lead=rows[0],share=Math.abs(lead[1])/rows.reduce((s,x)=>s+Math.abs(x[1]),0);
    $('#swNote').innerHTML=`Mô hình dự đoán <b>${esc(SHORT[name])}</b> với xác suất ${pct(ex.prob,1)}. Feature mạnh nhất là <b>${esc(lead[0])}</b> (${lead[1]>0?'+':''}${vi(lead[1],3)}), chiếm ${pct(share,0)} độ lớn của Top-${swK}. ${share>.6?'Một feature gánh phần lớn điểm: nên kiểm chứng xem đó là hành vi tấn công hay dấu vân tay môi trường.':'Điểm được chia khá đều giữa nhiều feature.'}`;
    $$('#swRows .wf-row').forEach(r=>r.onclick=()=>{const n=r.dataset.n;swOff.has(n)?swOff.delete(n):swOff.add(n);swDraw()});};
  $('#swCls').onchange=()=>{swOff.clear();swDraw()};seg($('#swK'),b=>{swK=+b.dataset.k;swDraw()});seg($('#swScale'),b=>{swS=b.dataset.s;swDraw()});swDraw();

  /* ===== Additivity (Shapley chính xác trên mô hình đồ chơi) ===== */
  const ad=$('#additivityDemo');
  ad.innerHTML=head('Demo · Additivity: base + Σ SHAP = đầu ra',['interactive'])+
   TOY.names.map((n,i)=>slider('ad'+i,n+` (flow trung bình = ${TOY.base[i]})`,0,10,[8,6,2][i],.5,v=>vi(v,1))).join('')+
   `<div class="add-eq" id="adEq"></div><button class="btn sm lime mt" id="adCheck">Kiểm tra additivity</button><div id="adOut" class="conclusion"></div>
   <p class="note">Mô hình đồ chơi 3 feature, SHAP tính <b>chính xác</b> bằng cách thử cả 6 thứ tự thêm feature. Trong dự án (run ${esc(P.global.runId||'')}): kiểm tra trên mẫu 300 flow của toàn bộ 700.000 flow test set, sai số tối đa <b>${esc(P.global.additivity||'')}</b> (cohort ${vi0(P.global.cohortN||1339)} flow: ${esc(P.global.additivityCohort||'')}), nghĩa là chỉ sai số số học dấu phẩy động.</p>`;
  const adCalc=()=>{const x=[0,1,2].map(i=>+$('#ad'+i).value);const phi=toyShapley(x);const base=TOY.f(...TOY.base),out=TOY.f(...x);
    $('#adEq').innerHTML=`<div class="box"><small>base value f(trung bình)</small>${vi(base,3)}</div><span class="op">+</span>`+phi.map((p,i)=>`<div class="box" style="border-color:${p>=0?'#29d3d1':'#ff7c43'}"><small>φ ${TOY.names[i]}</small>${p>=0?'+':''}${vi(p,3)}</div>`).join('<span class="op">+</span>')+`<span class="op">=?</span><div class="box"><small>f(x) đầu ra</small>${vi(out,3)}</div>`;$('#adOut').textContent='';};
  [0,1,2].forEach(i=>bindSlider('ad'+i,v=>vi(v,1),adCalc));adCalc();
  $('#adCheck').onclick=()=>{const x=[0,1,2].map(i=>+$('#ad'+i).value);const phi=toyShapley(x);const base=TOY.f(...TOY.base),out=TOY.f(...x);const sum=base+phi.reduce((s,p)=>s+p,0);
    $('#adOut').innerHTML=`Base ${vi(base,4)} + Σφ ${vi(phi.reduce((s,p)=>s+p,0),4)} = <b>${vi(sum,4)}</b> · f(x) = <b>${vi(out,4)}</b> · sai số = <b>${Math.abs(sum-out).toExponential(1)}</b> ⇒ cộng đủ.`};

  /* ===== local vs global ===== */
  const lg=$('#localGlobalDemo');
  lg.innerHTML=head('Demo · Local và Global',['real'])+`<div class="toolbar"><label class="lbl">LỚP<select id="lgCls">${classOpts('DoS attacks-Hulk')}</select></label></div><div class="grid2"><div><b>LOCAL · một flow</b><div id="lgL"></div></div><div><b>GLOBAL · cả lớp</b><div id="lgG"></div></div></div><p id="lgNote" class="conclusion"></p>`;
  const lgDraw=()=>{const c=cls($('#lgCls').value),ex=c.example;const mk=(arr,col)=>{const mx=Math.max(...arr.map(x=>Math.abs(x[1])),1e-9);return arr.map(([n,v])=>`<div class="bar-row" data-tip="${esc(finfo(n))}"><span>${esc(n)}</span><i class="bar-track"><em class="bar-fill ${v<0?'neg':''}" style="width:${Math.max(6,Math.abs(v)/mx*100)}%"></em></i><output>${v>0?'+':''}${vi(v,3)}</output></div>`).join('')};
    $('#lgL').innerHTML=mk(topK(ex.shap,5));$('#lgG').innerHTML=c.globalPos?mk(c.globalPos):'<p class="note">Benign không có SHAP toàn cục.</p>';
    const ln=topK(ex.shap,5).map(x=>x[0]),gn=(c.globalPos||[]).map(x=>x[0]);const com=ln.filter(x=>gn.includes(x));
    $('#lgNote').innerHTML=`Local trả lời “vì sao <i>flow này</i> bị dự đoán như vậy?”. Global trả lời “nhìn chung mô hình dựa vào feature nào cho lớp này?” (trung bình trên ${vi0(c.support)} flow). Hai bên trùng ${com.length}/5 feature. Một flow cụ thể không đại diện cho cả lớp.`};
  $('#lgCls').onchange=lgDraw;lgDraw();

  /* ===== 09 LIME neighborhood ===== */
  const ld=$('#limeDemo');
  ld.innerHTML=head('Demo · Vùng lân cận của LIME',['interactive'])+
   slider('lmX','Flow cần giải thích (vị trí x₀)',.5,9.5,5.5,.1,v=>vi(v,1))+slider('lmN','num_samples',30,2000,500,10)+slider('lmS','kernel_width (σ)',.3,6,1.5,.1,v=>vi(v,1),'Nhỏ = chỉ tin điểm rất gần; lớn = tin cả vùng rộng.')+
   `<div class="toolbar"><label class="toggle"><input type="checkbox" id="lmDisc"> discretize (rời rạc hóa)</label><button class="btn sm alt" id="lmSeed">Đổi seed</button><button class="btn sm lime" id="lmMulti">Chạy 10 seed</button></div>
   <div class="lime-plot"><svg id="lmSvg" viewBox="0 0 440 240"></svg></div><div class="kv mt" id="lmKv"></div><p id="lmNote" class="conclusion"></p>`;
  const bb=x=>.12+.3/(1+Math.exp(-(x-2.6)*7))+.25/(1+Math.exp(-(x-5.2)*9))+.28/(1+Math.exp(-(x-7.6)*8)); // đầu ra dạng bậc thang
  let lmSeed=3,multiRes=null;
  function lime(x0,N,sig,disc,seed){const r=rng(seed);const xs=[],ys=[],ws=[];for(let i=0;i<N;i++){let x=clamp(x0+gauss(r)*2.2,0,10);if(disc){x=(Math.floor(x/2.5)+.5)*2.5}xs.push(x);ys.push(bb(x));ws.push(Math.exp(-((x-x0)**2)/(sig*sig)))}
    const W=ws.reduce((s,w)=>s+w,0),mx=ws.reduce((s,w,i)=>s+w*xs[i],0)/W,my=ws.reduce((s,w,i)=>s+w*ys[i],0)/W;let sxy=0,sxx=0,syy=0;ws.forEach((w,i)=>{sxy+=w*(xs[i]-mx)*(ys[i]-my);sxx+=w*(xs[i]-mx)**2;syy+=w*(ys[i]-my)**2});
    const sl=sxx>1e-9?sxy/sxx:0,ic=my-sl*mx;let ssr=0;ws.forEach((w,i)=>ssr+=w*(ys[i]-(ic+sl*xs[i]))**2);const r2=syy>1e-12?1-ssr/syy:0;return{xs,ys,ws,sl,ic,r2}}
  const lmDraw=()=>{const x0=+$('#lmX').value,N=+$('#lmN').value,sig=+$('#lmS').value,disc=$('#lmDisc').checked;const L=lime(x0,N,sig,disc,lmSeed);
    const X=x=>20+x/10*400,Y=y=>220-y*190;let g=`<path d="${Array.from({length:101},(_,i)=>i/10).map((x,i)=>`${i?'L':'M'}${X(x)},${Y(bb(x))}`).join(' ')}" fill="none" stroke="#8e9ab0" stroke-width="1.5"/>`;
    L.xs.forEach((x,i)=>{g+=`<circle cx="${X(x)}" cy="${Y(L.ys[i])}" r="${1.2+L.ws[i]*3}" fill="#b7f23d" fill-opacity="${.15+L.ws[i]*.7}"/>`});
    g+=`<line x1="${X(0)}" y1="${Y(L.ic)}" x2="${X(10)}" y2="${Y(L.ic+L.sl*10)}" stroke="#29d3d1" stroke-width="2.4"/><line x1="${X(x0)}" x2="${X(x0)}" y1="20" y2="220" stroke="#ff7c43" stroke-dasharray="4 3"/><circle cx="${X(x0)}" cy="${Y(bb(x0))}" r="6" fill="#ff7c43" stroke="#fff" stroke-width="1.5"/>
    <text x="22" y="14" fill="#8e9ab0" font-size="9" font-family="DM Mono">xanh lá: mẫu lân cận (đậm = gần hơn, nặng hơn) · xanh lơ: đường LIME · cam: flow cần giải thích</text>`;
    $('#lmSvg').innerHTML=g;$('#lmKv').innerHTML=`<div><small>HỆ SỐ LIME (độ dốc)</small><b>${L.sl>=0?'+':''}${vi(L.sl,3)}</b></div><div><small>LOCAL R²</small><b style="color:${L.r2>=.3?'#b7f23d':'#ff9d73'}">${vi(L.r2,2)}</b></div><div><small>SEED</small><b>${lmSeed}</b></div>`;
    let t=`${L.r2>=.7?'Đường thẳng bám tốt quanh x₀: lời giải thích đáng tin.':L.r2>=.3?'Bám ở mức tạm được.':'<b>Local R² thấp:</b> đầu ra dạng bậc thang không khớp một đường thẳng, nên hệ số LIME chỉ là phép xấp xỉ kém.'}`;
    if(multiRes)t+=` Chạy 10 seed: hệ số từ ${vi(Math.min(...multiRes),3)} đến ${vi(Math.max(...multiRes),3)} (độ lệch chuẩn ${vi(std(multiRes),3)}): cùng flow, cùng mô hình mà lời giải thích dao động.`;
    $('#lmNote').innerHTML=t};
  ['lmX','lmN'].forEach(i=>bindSlider(i,i==='lmX'?v=>vi(v,1):null,()=>{multiRes=null;lmDraw()}));bindSlider('lmS',v=>vi(v,1),()=>{multiRes=null;lmDraw()});
  $('#lmDisc').onchange=()=>{multiRes=null;lmDraw()};$('#lmSeed').onclick=()=>{lmSeed=Math.floor(Math.random()*90)+1;multiRes=null;lmDraw()};
  $('#lmMulti').onclick=()=>{const x0=+$('#lmX').value,N=+$('#lmN').value,sig=+$('#lmS').value,disc=$('#lmDisc').checked;multiRes=Array.from({length:10},(_,i)=>lime(x0,N,sig,disc,i+1).sl);lmDraw()};
  lmDraw();

  /* ===== Local R² ===== */
  const rd=$('#r2Demo');
  rd.innerHTML=head('Demo · Local R² và dữ liệu thật',['interactive','real'])+slider('r2k','Độ “bậc thang” của mô hình (0 = trơn, 1 = như XGBoost)',0,1,.2,.05,v=>vi(v,2))+
   `<div class="grid2"><div class="lime-plot"><svg id="r2Svg" viewBox="0 0 220 150"></svg></div><div><div class="kv" id="r2Kv"></div></div></div><p id="r2Note" class="note"></p>
   <h4>Thực tế của dự án: ${vi0(P.global.r2n)} flow trong cohort <span class="badge real">Real</span></h4><div id="r2Hist"></div><p class="note">Median Local R² = <b>${vi(P.global.r2medAll,3)}</b>; chỉ <b>${vi(P.global.r2ge03*100,1)}%</b> flow đạt R² ≥ 0,3. Không nên đọc trọng số LIME mà bỏ qua Local R².</p>`;
  const r2Calc=()=>{const k=+$('#r2k').value;const f=x=>(1-k)*(0.1+0.08*x)+k*bb(x);const x0=5.2,sig=1.5;const r=rng(5),xs=[],ys=[],ws=[];for(let i=0;i<400;i++){const x=clamp(x0+gauss(r)*2.2,0,10);xs.push(x);ys.push(f(x));ws.push(Math.exp(-((x-x0)**2)/(sig*sig)))}
    const W=ws.reduce((s,w)=>s+w,0),mx=ws.reduce((s,w,i)=>s+w*xs[i],0)/W,my=ws.reduce((s,w,i)=>s+w*ys[i],0)/W;let sxy=0,sxx=0,syy=0;ws.forEach((w,i)=>{sxy+=w*(xs[i]-mx)*(ys[i]-my);sxx+=w*(xs[i]-mx)**2;syy+=w*(ys[i]-my)**2});const sl=sxy/sxx,ic=my-sl*mx;let ssr=0;ws.forEach((w,i)=>ssr+=w*(ys[i]-(ic+sl*xs[i]))**2);const r2=syy>1e-12?1-ssr/syy:1;
    const X=x=>10+x/10*200,Y=y=>140-y*125;let g=`<path d="${Array.from({length:81},(_,i)=>i/8).map((x,i)=>`${i?'L':'M'}${X(x)},${Y(f(x))}`).join(' ')}" fill="none" stroke="#10182a" stroke-width="1.8"/><line x1="${X(0)}" y1="${Y(ic)}" x2="${X(10)}" y2="${Y(ic+sl*10)}" stroke="#16b8b6" stroke-width="2"/><circle cx="${X(x0)}" cy="${Y(f(x0))}" r="4.5" fill="#ff7c43"/>`;
    $('#r2Svg').innerHTML=g;$('#r2Kv').innerHTML=`<div><small>LOCAL R²</small><b style="color:${r2>=.3?'#0f7d5a':'#b4232a'}">${vi(r2,2)}</b></div><div><small>ĐỌC KẾT QUẢ</small><b class="sm">${r2>=.7?'Tốt':r2>=.3?'Tạm được':'Kém'}</b></div>`;
    $('#r2Note').textContent=k<.3?'Mô hình gần như trơn nên một đường thẳng khớp tốt: R² cao.':k<.7?'Bắt đầu xuất hiện bậc thang: R² giảm.':'Giống XGBoost: các vùng phẳng rồi nhảy vọt, đường thẳng khó bám, R² thấp.'};
  bindSlider('r2k',v=>vi(v,2),r2Calc)();
  const hm=Math.max(...P.global.r2hist);$('#r2Hist').innerHTML=svg(440,110,P.global.r2hist.map((h,i)=>`<rect x="${20+i*40}" y="${90-h/hm*70}" width="34" height="${h/hm*70}" fill="${i<3?'#ff7c43':'#16b8b6'}" rx="3"/><text x="${37+i*40}" y="104" font-size="9" text-anchor="middle" font-family="DM Mono" fill="#6b7686">${vi(i/10,1)}</text><text x="${37+i*40}" y="${86-h/hm*70}" font-size="8" text-anchor="middle" font-family="DM Mono">${h}</text>`).join(''),'curve-svg');

  /* ===== 10 So sánh SHAP vs LIME ===== */
  const cp=$('#compareDemo');
  cp.innerHTML=head('Demo · SHAP và LIME trên cùng một flow thật',['real'])+`
   <div class="toolbar"><label class="lbl">LỚP<select id="cpCls">${classOpts('Bot')}</select></label><label class="lbl">TOP-K<span class="seg" id="cpK"><button data-k="3">3</button><button class="on" data-k="5">5</button><button data-k="10">10</button></span></label><button class="btn sm alt" id="cpAtk">Xem hoạt cảnh tấn công này</button></div>
   <div class="xai-bars"><div><h3>SHAP <small>raw margin · TreeSHAP</small></h3><div id="cpS"></div></div><div><h3>LIME <small>xác suất · surrogate Ridge</small></h3><div id="cpL"></div></div></div>
   <div class="metric-chips" id="cpChips"></div><p id="cpNote" class="conclusion"></p><p class="note" id="cpMacro"></p>
   <p class="note"><span class="tagpill both">xanh đậm</span> cả hai cùng chọn · <span class="tagpill shap">cyan</span> chỉ SHAP · <span class="tagpill lime">lime</span> chỉ LIME · ↑ đẩy lên · ↓ kéo xuống.</p>`;
  let cpK=5;
  const cpDraw=()=>{const name=$('#cpCls').value,c=cls(name),ex=c.example;const R=compareLists(ex.shap,ex.lime,cpK);
    const row=(arr,cmn,type,other)=>{const mx=Math.max(...arr.map(x=>Math.abs(x[1])),1e-9);return arr.map(([n,v])=>{const both=cmn.includes(n);return `<div class="bar-row ${both?'common':''}" data-tip="${esc(finfo(n))}"><span>${both?'<span class="tagpill both">'+esc(n)+'</span>':'<span class="tagpill '+type+'">'+esc(n)+'</span>'}</span><i class="bar-track"><em class="bar-fill ${type==='lime'?'lime':''} ${v<0?'neg':''}" style="width:${Math.max(6,Math.abs(v)/mx*100)}%"></em></i><output>${v>0?'↑':'↓'} ${vi(Math.abs(v),type==='lime'?4:3)}</output></div>`}).join('')};
    $('#cpS').innerHTML=row(R.s,R.com,'shap');$('#cpL').innerHTML=row(R.l,R.com,'lime');
    $('#cpChips').innerHTML=`<span>Jaccard@${cpK} <b>${vi(R.jac,3)}</b></span><span>Spearman <b>${R.sp==null?'— (chung < 2)':vi(R.sp,2)}</b></span><span>Đồng thuận dấu <b>${R.sign==null?'—':pct(R.sign,0)}</b></span><span>Local R² (LIME) <b>${vi(ex.r2,3)}</b></span>`;
    $('#cpNote').innerHTML=`SHAP và LIME trùng <b>${R.com.length}/${cpK}</b> feature. ${R.sign==null?'Không có feature chung nên không so được dấu.':`Trên ${R.com.length} feature chung, họ ${R.sign===1?'<b>đồng ý hoàn toàn</b> về hướng ảnh hưởng':R.sign>=.5?'đồng ý về hướng phần lớn':'<b>bất đồng</b> về hướng ảnh hưởng'}.`} ${ex.r2<.3?`LIME có Local R² = ${vi(ex.r2,3)} (thấp), nên kết quả đối chiếu cần đọc thận trọng.`:'Local R² ở mức khá cho một flow.'}`;
    const a=c.agree;$('#cpMacro').innerHTML=a?`Đây là <b>một flow</b>. Trung bình cả lớp ${esc(SHORT[name])} (${c.domainP5?c.domainP5.n:'?'} flow): Jaccard@5 = <b>${vi(a.jaccard_5_mean,3)}</b>, Spearman = ${a.spearman_5_mean==null?'—':vi(a.spearman_5_mean,2)}, đồng thuận dấu = ${a.signed_agreement_5_mean==null?'—':pct(a.signed_agreement_5_mean,0)}.`:''};
  $('#cpCls').onchange=cpDraw;seg($('#cpK'),b=>{cpK=+b.dataset.k;cpDraw()});$('#cpAtk').onclick=()=>{const n=$('#cpCls').value;HUB.openAttack(n==='Benign'?'Bot':n)};
  HUB.focusCompare=n=>{$('#cpCls').value=n;cpDraw()};cpDraw();

  /* Jaccard */
  const jd=$('#jaccardDemo');const POOL=['Dst Port','RST Flag','Bwd IAT','Flow Duration','Pkt Len','FIN Flag','Fwd URG','IAT Min'];const A=['Dst Port','RST Flag','Bwd IAT','Flow Duration','Pkt Len'];let B=['Dst Port','RST Flag','FIN Flag','Fwd URG','IAT Min'];
  jd.innerHTML=head('Jaccard',['interactive'])+`<p class="note" style="margin-top:0">SHAP Top-5 cố định. Bấm chip để đổi Top-5 của LIME (tối đa 5).</p><div class="seg" id="jPre" style="margin-bottom:8px"><button data-p="0">Không trùng</button><button data-p="1" class="on">Trùng một phần</button><button data-p="2">Trùng hoàn toàn</button></div><div id="jBody"></div>`;
  const jDraw=()=>{const inter=A.filter(x=>B.includes(x)),uni=[...new Set([...A,...B])];$('#jBody').innerHTML=`<p><b>SHAP:</b> ${A.map(x=>`<span class="tagpill ${B.includes(x)?'both':'shap'}">${x}</span>`).join('')}</p><p><b>LIME (bấm để đổi):</b><br>${POOL.map(x=>`<button class="tagpill ${B.includes(x)?(A.includes(x)?'both':'lime'):''}" data-x="${x}" style="border:1px dashed #b6bdc8;cursor:pointer">${x}</button>`).join('')}</p><div class="kv"><div><small>GIAO</small><b>${inter.length}</b></div><div><small>HỢP</small><b>${uni.length}</b></div><div><small>JACCARD</small><b>${vi(inter.length/uni.length,2)}</b></div></div><p class="note">Jaccard = |giao| / |hợp|. Chỉ nói hai phương pháp chọn <b>cùng tập</b> hay không, chưa nói thứ tự hay dấu.</p>`;
    $$('#jBody button[data-x]').forEach(b=>b.onclick=()=>{const x=b.dataset.x;if(B.includes(x))B=B.filter(y=>y!==x);else{B.push(x);if(B.length>5)B.shift()}jDraw()})};
  seg($('#jPre'),b=>{B=[['FIN Flag','Fwd URG','IAT Min','Dst Port','Flow Duration'].filter(x=>!A.includes(x)).concat(['FIN Flag','Fwd URG','IAT Min']).slice(0,3).concat(['x1','x2']).filter(x=>POOL.includes(x)),['Dst Port','RST Flag','FIN Flag','Fwd URG','IAT Min'],A.slice()][+b.dataset.p];if(+b.dataset.p===0)B=['FIN Flag','Fwd URG','IAT Min'];jDraw()});jDraw();

  /* Spearman */
  const sp=$('#spearmanDemo');sp.innerHTML=head('Spearman',['interactive'])+`<div class="seg" id="spPre" style="margin-bottom:8px"><button data-p="same">Cùng thứ tự</button><button data-p="mix" class="on">Lộn xộn</button><button data-p="rev">Đảo ngược</button></div><div id="spBody"></div>`;
  const NA=['Dst Port','RST Flag','Bwd IAT','Duration','Pkt Len'];let nb=['RST Flag','Dst Port','Duration','Pkt Len','Bwd IAT'];
  const spDraw=()=>{const rb=NA.map(x=>nb.indexOf(x)+1),n=5,d2=rb.reduce((s,r,i)=>s+(r-(i+1))**2,0),rho=1-6*d2/(n*(n*n-1));
    $('#spBody').innerHTML=`<div class="rank-grid"><div class="rank-col"><h5>SHAP (cố định)</h5>${NA.map((x,i)=>`<div class="rank-item" style="cursor:default"><span>${i+1}. ${x}</span></div>`).join('')}</div><div class="rank-col"><h5>LIME (bấm ↑ ↓)</h5>${nb.map((x,i)=>`<div class="rank-item"><span>${i+1}. ${x}</span><span><button data-i="${i}" data-d="-1" class="tagpill">↑</button><button data-i="${i}" data-d="1" class="tagpill">↓</button></span></div>`).join('')}</div></div><div class="kv mt"><div><small>Σd²</small><b>${d2}</b></div><div><small>SPEARMAN ρ</small><b>${vi(rho,2)}</b></div></div><p class="note">+1 cùng thứ tự · 0 không có quan hệ · −1 đảo ngược. Chỉ tính trên các feature <b>chung</b> của hai Top-k, và cần ít nhất 2 feature chung.</p>`;
    $$('#spBody button[data-i]').forEach(b=>b.onclick=()=>{const i=+b.dataset.i,j=i+ +b.dataset.d;if(j<0||j>4)return;[nb[i],nb[j]]=[nb[j],nb[i]];spDraw()})};
  seg($('#spPre'),b=>{nb=b.dataset.p==='same'?NA.slice():b.dataset.p==='rev'?NA.slice().reverse():['RST Flag','Dst Port','Duration','Pkt Len','Bwd IAT'];spDraw()});spDraw();

  /* Dấu */
  const sg=$('#signDemo');sg.innerHTML=head('Đồng thuận dấu',['interactive'])+slider('sgS','Giá trị SHAP (raw margin)',-2,2,1.4,.1,v=>(v>0?'+':'')+vi(v,1))+slider('sgL','Trọng số LIME (xác suất)',-.1,.1,.08,.01,v=>(v>0?'+':'')+vi(v,2))+`<div id="sgOut"></div><p class="note">SHAP tính trên <b>raw margin</b>, LIME trên <b>xác suất</b>: hai thang khác nhau nên <b>không so độ lớn</b>, chỉ so feature, thứ hạng và dấu.</p>`;
  const sgCalc=()=>{const s=+$('#sgS').value,l=+$('#sgL').value;const same=Math.sign(s)===Math.sign(l)&&s!==0&&l!==0;$('#sgOut').innerHTML=`<div class="kv"><div><small>SHAP</small><b style="color:${s>=0?'#16b8b6':'#ff7c43'}">${s>0?'↑':'↓'} ${vi(Math.abs(s),1)}</b></div><div><small>LIME</small><b style="color:${l>=0?'#6aa51a':'#ff7c43'}">${l>0?'↑':'↓'} ${vi(Math.abs(l),2)}</b></div><div><small>KẾT LUẬN</small><b class="sm" style="color:${same?'#0f7d5a':'#b4232a'}">${same?'Đồng thuận':'Bất đồng'}</b></div></div><p>${same?`Dù độ lớn khác hẳn (${vi(Math.abs(s),1)} vs ${vi(Math.abs(l),2)}), cả hai cùng nói feature này ${s>0?'làm tăng':'làm giảm'} dự đoán.`:'Hai phương pháp nói ngược hướng ảnh hưởng của feature này.'}</p>`};
  bindSlider('sgS',v=>(v>0?'+':'')+vi(v,1),sgCalc);bindSlider('sgL',v=>(v>0?'+':'')+vi(v,2),sgCalc);sgCalc();

  /* ===== 11 Đánh giá XAI ===== */
  const ev=$('#evalDemo');let et='domain';
  const barsByClass=(key1,key2,get,fmt,max)=>`<div class="cmp-head" style="grid-template-columns:150px 1fr 1fr"><span>LỚP</span><span>SHAP</span><span>LIME</span></div>`+P.classes.map(c=>{const v=get(c);if(!v)return'';return `<div class="cmp-row" style="grid-template-columns:150px 1fr 1fr"><span>${esc(SHORT[c.name])}</span><span class="bar"><i style="width:${v[0]/max*100}%;background:#16b8b6"></i></span><span class="bar"><i style="width:${v[1]/max*100}%;background:#b7d640"></i></span></div>`}).join('');
  const evDraw=()=>{
    if(et==='domain'){ev.innerHTML=head('Domain Precision@5 · dữ liệu thật + ví dụ',['real'])+`<div class="kv"><div><small>MACRO · SHAP</small><b>${vi(P.global.domain[0],3)}</b></div><div><small>MACRO · LIME</small><b>${vi(P.global.domain[1],3)}</b></div></div><div class="split mt"><div>${barsByClass('s','l',c=>c.domainP5&&[c.domainP5.shap,c.domainP5.lime],vi,.5)}</div><div><label class="lbl" style="font:9px DM Mono">VÍ DỤ MỘT FLOW<select id="evCls">${classOpts('DDoS attacks-LOIC-HTTP')}</select></label><div id="evEx"></div></div></div><p class="note">Đây là đối chiếu với <b>bảng tri thức miền</b> do nhóm dự án lập, <b>không phải</b> điểm chuyên gia SOC chấm. Thang thanh: 0 → 0,5.</p>`;
      const exDraw=()=>{const c=cls($('#evCls').value),ex=c.example,dom=c.domainSignals||[];const s5=topK(ex.shap,5).map(x=>x[0]),l5=topK(ex.lime,5).map(x=>x[0]);const hs=s5.filter(x=>dom.includes(x)).length,hl=l5.filter(x=>dom.includes(x)).length;
        $('#evEx').innerHTML=`<p><b>Tín hiệu miền kỳ vọng:</b><br>${dom.map(x=>`<span class="tagpill">${x}</span>`).join('')||'—'}</p><p><b>SHAP Top-5:</b><br>${s5.map(x=>`<span class="tagpill ${dom.includes(x)?'hit':'miss'}">${x} ${dom.includes(x)?'✓':'✗'}</span>`).join('')}</p><p><b>LIME Top-5:</b><br>${l5.map(x=>`<span class="tagpill ${dom.includes(x)?'hit':'miss'}">${x} ${dom.includes(x)?'✓':'✗'}</span>`).join('')}</p><div class="kv"><div><small>P@5 SHAP</small><b>${hs}/5 = ${vi(hs/5,1)}</b></div><div><small>P@5 LIME</small><b>${hl}/5 = ${vi(hl/5,1)}</b></div></div>`};
      $('#evCls').onchange=exDraw;exDraw()}
    if(et==='stab'){ev.innerHTML=head('Ổn định qua 10 seed',['real','interactive'])+`<div class="split"><div><b>Jaccard@5 trung bình giữa các lần chạy · dữ liệu thật</b><div class="mt">${P.classes.map(c=>`<div class="cmp-row" style="grid-template-columns:150px 1fr 50px"><span>${esc(SHORT[c.name])}</span><span class="bar"><i style="width:${c.stab*100}%;background:#16b8b6"></i></span><span class="n">${vi(c.stab,2)}</span></div>`).join('')}</div></div>
      <div><label class="lbl" style="font:9px DM Mono">MÔ PHỎNG 10 LẦN CHẠY LIME<select id="stCls">${classOpts('Bot')}</select></label><button class="btn sm lime" id="stRun" style="margin:8px 0">Chạy 10 seed</button><div id="stOut"></div></div></div><p class="note">Bên phải là <b>mô phỏng</b> dựa trên trọng số LIME của flow thật, thêm nhiễu hiệu chỉnh để Jaccard@5 giữa các lần khớp giá trị thật của lớp. Dùng để thấy hiện tượng: cùng flow, cùng mô hình, Top-5 vẫn đổi.</p>`;
      const run=()=>{const c=cls($('#stCls').value),ex=c.example,L=ex.lime;const base=L.map(x=>Math.abs(x[1]));const sc=Math.max(...base);const NS=10;
        const sim=s=>{const out=[];for(let sd=0;sd<NS;sd++){const r=rng(900+sd*13);out.push(L.map((x,i)=>[x[0],base[i]+gauss(r)*s*sc]).sort((a,b)=>b[1]-a[1]).slice(0,5).map(x=>x[0]))}return out};
        const jac=(a,b)=>a.filter(x=>b.includes(x)).length/new Set([...a,...b]).size;const avg=runs=>{let t=0,n=0;for(let i=0;i<NS;i++)for(let j=i+1;j<NS;j++){t+=jac(runs[i],runs[j]);n++}return t/n};
        let lo=0,hi=2;for(let k=0;k<14;k++){const mid=(lo+hi)/2;avg(sim(mid))>c.stab?lo=mid:hi=mid}const runs=sim((lo+hi)/2);const freq={};runs.flat().forEach(f=>freq[f]=(freq[f]||0)+1);
        $('#stOut').innerHTML=runs.map((r,i)=>`<div style="font-size:11px;margin:2px 0"><b>Seed ${i+1}:</b> ${r.map(x=>`<span class="tagpill">${x}</span>`).join('')}</div>`).join('')+`<h4>Tần suất xuất hiện trong Top-5</h4>`+Object.entries(freq).sort((a,b)=>b[1]-a[1]).map(([f,n])=>`<div class="cmp-row" style="grid-template-columns:140px 1fr 40px"><span>${esc(f)}</span><span class="bar"><i style="width:${n/NS*100}%;background:#b7d640"></i></span><span class="n">${n}/${NS}</span></div>`).join('')};
      $('#stRun').onclick=run;$('#stCls').onchange=run;run()}
    if(et==='rob'){ev.innerHTML=head('Chịu nhiễu ±1/5/10%',['real'])+`<div class="seg" id="rbN"><button class="on" data-n="1">±1%</button><button data-n="5">±5%</button><button data-n="10">±10%</button></div><div id="rbOut" class="mt"></div><p class="note">Phân biệt: <b>prediction robustness</b> (nhãn có đổi không) và <b>explanation robustness</b> (Top-5 có đổi không). Mô hình có thể giữ nguyên nhãn mà lời giải thích vẫn thay đổi. Nhiễu Gaussian áp lên <b>cả 78 đặc trưng</b> của toàn bộ ${vi0(P.global.cohortN||1339)} flow cohort, biên độ = % <b>độ lệch chuẩn toàn cục</b> (toàn train set) của mỗi đặc trưng. <b>Lưu ý quan trọng:</b> một số đặc trưng (Flow Duration, IAT...) có phân phối lệch dày do vài flow ngoại lai cực lớn, nên "nhiễu 1%" theo độ lệch chuẩn toàn cục có thể là một bước nhảy tuyệt đối RẤT LỚN so với giá trị thật của một flow bình thường — đây là lý do tỉ lệ đổi dự đoán ở đây cao hơn trực giác thông thường, một hạn chế của cách định nghĩa mức nhiễu (không phải lỗi tính toán).</p>`;
      const rb=n=>{const g=P.global.robust.find(x=>x[0]===+n);$('#rbOut').innerHTML=`<div class="kv"><div><small>JACCARD@5 TRƯỚC/SAU</small><b>${vi(g[1],3)}</b></div><div><small>TỈ LỆ ĐỔI DỰ ĐOÁN</small><b>${vi(g[2],1)}%</b></div></div><table class="mt"><thead><tr><th>Lớp</th><th class="num">Jaccard@5</th><th class="num">Đổi nhãn</th></tr></thead><tbody>${P.classes.map(c=>c.rob&&c.rob[n]?`<tr><td>${esc(SHORT[c.name])}</td><td class="num">${vi(c.rob[n][0],3)}</td><td class="num">${pct(c.rob[n][1],1)}</td></tr>`:'').join('')}</tbody></table>`};
      seg($('#rbN'),b=>rb(b.dataset.n));rb(1)}
    if(et==='faith'){
      ev.innerHTML=head('Faithfulness: xoá Top-k feature (đưa về giá trị nền), xác suất lớp dự đoán giảm bao nhiêu?',['real'])+`<div class="seg" id="fK"><button data-k="3">k = 3</button><button class="on" data-k="5">k = 5</button><button data-k="10">k = 10</button></div><div id="fOut" class="mt"></div><p class="note">Protocol (đổi so với bản trước): xoá Top-k feature được chọn, đặt về giá trị NỀN (trung vị toàn tập), đo mức giảm XÁC SUẤT (không phải margin) của lớp dự đoán, so với xoá k feature ngẫu nhiên — đo trên toàn bộ ${vi0(P.global.cohortN||1339)} flow cohort (coverage 100% ở mọi k, vì luôn có đủ 78 feature để chọn). Tỉ lệ thắng = % flow mà SHAP làm giảm xác suất nhiều hơn LIME (so trực tiếp từng flow).</p>`;
      const fk=k=>{const t=P.global.faithTable[k],w=P.global.faith[k];const mx=100;const bar=(l,v,c)=>`<div class="cmp-row" style="grid-template-columns:220px 1fr 60px"><span>${l}</span><span class="bar"><i style="width:${v/mx*100}%;background:${c}"></i></span><span class="n">${vi(v,1)}%</span></div>`;
        $('#fOut').innerHTML=`<div class="kv"><div><small>SHAP THẮNG LIME (so từng flow)</small><b>${vi(w[0],1)}%</b></div><div><small>LIME THẮNG SHAP</small><b>${vi(w[1],1)}%</b></div></div><h4>Mức giảm xác suất trung bình (điểm %)</h4>${bar('Xoá Top-'+k+' của SHAP',t[0],'#16b8b6')}${bar('Xoá '+k+' feature ngẫu nhiên (đối chứng)',t[1],'#9aa5b8')}${bar('Xoá Top-'+k+' của LIME',t[2],'#b7d640')}<p class="conclusion" style="color:#3d4659">Cả SHAP và LIME đều làm xác suất giảm nhiều hơn đối chứng ngẫu nhiên (faithfulness tốt hơn đoán mò), nhưng SHAP giảm mạnh hơn LIME rõ rệt ở mọi k, và khoảng cách này MỞ RỘNG khi k tăng.</p>`};
      seg($('#fK'),b=>fk(b.dataset.k));fk('5')}
  };
  seg($('#evalTabs'),b=>{et=b.dataset.t;evDraw()});evDraw();

  /* ===== 12 Fingerprint ===== */
  const fp=$('#fpDemo');
  const hits=P.classes.filter(c=>c.globalPos).map(c=>[c.name,c.globalPos.filter(x=>FPRINT.includes(x[0])).map(x=>x[0])]);const nHit=hits.filter(h=>h[1].length>0).length;
  fp.innerHTML=head('Demo · Mô hình nhìn hành vi hay nhìn “dấu vân tay” môi trường?',['interactive','unvalidated'])+`
   <div class="seg" id="fpEnv"><button class="on" data-e="2018">Môi trường CICIDS2018</button><button data-e="2026">Traffic thật 2026</button></div>
   <div class="ctl"><label for="fpPort">Dst Port</label><select id="fpPort"><option>80</option><option>443</option><option>8080</option><option>8443</option></select></div>
   <div class="ctl"><label for="fpWin">Init Fwd Win Byts</label><select id="fpWin"><option>8192</option><option>29200</option><option>64240</option></select></div>
   <div class="ctl"><label for="fpMss">Fwd Seg Size Min</label><select id="fpMss"><option>20</option><option>32</option><option>40</option></select></div>
   <div class="ctl"><label for="fpUnit">Đơn vị thời gian</label><select id="fpUnit"><option value="us">micro giây</option><option value="s">giây (chưa đổi)</option></select></div>
   <div class="ctl"><label>Hành vi thật của flow <output id="fpBeh_o">cao</output></label><input type="range" id="fpBeh" min="0" max="1" step=".1" value="1"><small>Flow thật sự là flood HTTP: tốc độ packet rất cao.</small></div>
   <div id="fpOut"></div>
   <p class="note warn">Mô hình đồ chơi này gán trọng số rất lớn cho các fingerprint để <b>mô phỏng hiện tượng</b>, không phải mô hình thật. Chưa chạy thí nghiệm đổi fingerprint trên XGBoost thật (Not Yet Validated).</p>
   <h4>Bằng chứng thật: fingerprint trong SHAP Top-5 toàn cục <span class="badge real">Real</span></h4>
   <p><b>${nHit}/14</b> lớp tấn công có ít nhất một fingerprint (${FPRINT.map(x=>`<code>${x}</code>`).join(', ')}) trong Top-5 SHAP toàn cục.</p>
   <div>${hits.map(([n,h])=>`<div style="font-size:12px;margin:3px 0"><b>${esc(SHORT[n])}</b> ${h.length?h.map(x=>`<span class="tagpill miss">${x}</span>`).join(''):'<span class="tagpill hit">không có</span>'}</div>`).join('')}</div>`;
  const fpCalc=()=>{const env=$('.seg#fpEnv .on').dataset.e,port=+$('#fpPort').value,win=+$('#fpWin').value,mss=+$('#fpMss').value,unit=$('#fpUnit').value,beh=+$('#fpBeh').value;
    const m=(port===80?3.6:0)+(win===8192?3.2:0)+(mss===20?1.4:0)+beh*1.6-4.2+(unit==='s'?-1.2*beh:0);const p=1/(1+Math.exp(-m));
    $('#fpOut').innerHTML=`<div class="kv"><div><small>DỰ ĐOÁN (ĐỒ CHƠI)</small><b>${p>.5?'DDoS-HOIC':'Benign'}</b></div><div><small>XÁC SUẤT</small><b>${pct(p>.5?p:1-p,1)}</b></div><div><small>MARGIN</small><b>${vi(m,2)}</b></div></div><p class="conclusion" style="color:#3d4659">${p>.5?`Đúng là flood và mô hình bắt được.`:`<b>Sai:</b> hành vi flood không đổi, nhưng ${port!==80?'cổng đích khác 80, ':''}${win!==8192?'cửa sổ TCP khác, ':''}${mss!==20?'MSS khác, ':''}${unit==='s'?'đơn vị thời gian sai, ':''}mô hình vẫn đổi lớp. Điều này cho thấy nó có thể đang dựa vào dấu vân tay môi trường thay vì bản chất hành vi.`}</p>`};
  seg($('#fpEnv'),b=>{const t=b.dataset.e==='2026';$('#fpPort').value=t?'8080':'80';$('#fpWin').value=t?'64240':'8192';$('#fpMss').value=t?'40':'20';$('#fpUnit').value=t?'s':'us';fpCalc()});
  ['fpPort','fpWin','fpMss','fpUnit'].forEach(i=>$('#'+i).onchange=fpCalc);bindSlider('fpBeh',v=>v>=.7?'cao':v>=.3?'vừa':'thấp',fpCalc)();

  /* Web attack limit */
  const wd=$('#webDemo');
  wd.innerHTML=head('Demo · Hai ống kính cùng một request',['interactive','real'])+`<div class="seg" id="wbSel"><button class="on" data-r="ben">Tìm kiếm bình thường</button><button data-r="sqli">SQL Injection</button><button data-r="xss">XSS</button></div><div class="grid2 mt"><div><b>HTTP payload (WAF/DPI thấy)</b><div class="payload" id="wbPay"></div><label class="toggle mt"><input type="checkbox" id="wbWaf"> Bật WAF/DPI</label><p id="wbWafOut" class="note"></p></div><div><b>Flow feature (mô hình thấy)</b><div id="wbFeat"></div></div></div><p class="note">SQL Injection: F1 ${pct(cls('SQL Injection').f1,1)} trên 17 flow test. XSS (Brute Force -XSS): F1 ${pct(cls('Brute Force -XSS').f1,1)} trên 46 flow. Ba request này tạo ra flow gần như giống nhau về hình dạng.</p>`;
  const REQ={ben:{p:'GET /search?q=<b>giay+the+thao</b> HTTP/1.1',g:()=>{const a=[[0,'f',60,'S'],[.03,'b',60,'SA'],[.04,'f',54,'A'],[.1,'f',430,'PA'],[.3,'b',1400,'PA'],[.33,'b',900,'PA'],[.4,'f',54,'A'],[.5,'f',54,'FA'],[.52,'b',54,'FA']];return a.map(([t,d,l,f])=>({t,dir:d,len:l,flags:f}))},waf:'Cho qua'},
   sqli:{p:"GET /product?id=1<mark> OR 1=1 --</mark> HTTP/1.1",g:GEN.sqli,waf:'<b>Chặn:</b> khớp mẫu SQL injection (điều kiện luôn đúng + chú thích).'},xss:{p:'GET /search?q=<mark>&lt;script&gt;alert(1)&lt;/script&gt;</mark> HTTP/1.1',g:GEN.xss,waf:'<b>Chặn:</b> thẻ &lt;script&gt; trong tham số.'}};
  const wbDraw=()=>{const k=$('#wbSel .on').dataset.r,r=REQ[k];$('#wbPay').innerHTML=r.p;const f=HUB.computeFeatures(r.g());
    $('#wbFeat').innerHTML=`<table><tbody><tr><td>Dst Port</td><td class="num">80</td></tr><tr><td>Flow Duration</td><td class="num">${vi(f.dur,2)} s</td></tr><tr><td>Tổng packet</td><td class="num">${f.n}</td></tr><tr><td>Fwd Pkt Len Mean</td><td class="num">${vi(f.fLenMean,0)}</td></tr><tr><td>Flow IAT Mean</td><td class="num">${vi(f.iatMean,3)} s</td></tr><tr><td>RST / FIN / PSH</td><td class="num">${f.rst} / ${f.fin} / ${f.psh}</td></tr></tbody></table>`;
    $('#wbWafOut').innerHTML=$('#wbWaf').checked?r.waf:'Bật WAF/DPI để xem payload có bị phát hiện không.'};
  seg($('#wbSel'),wbDraw);$('#wbWaf').onchange=wbDraw;wbDraw();
});
const GEN_REF=null;
