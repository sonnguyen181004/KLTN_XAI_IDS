/* metrics.js — Chương 06: Precision/Recall/F1, mất cân bằng, confusion matrix thật, FPR */
(function(){
const erf=x=>{const s=Math.sign(x);x=Math.abs(x);const t=1/(1+.3275911*x);const y=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-.284496736)*t+.254829592)*t*Math.exp(-x*x);return s*y};
const cdf=(x,m,s)=>.5*(1+erf((x-m)/(s*Math.SQRT2)));
HUB.reg(function metricsInit(){
  // ---- P/R/F1 + ngưỡng SOC
  const a=$('#prfDemo');
  a.innerHTML=head('Demo · Precision, Recall, F1 và ngưỡng cảnh báo',['interactive'])+`
   ${slider('thr','Ngưỡng cảnh báo (score ≥ ngưỡng thì báo Attack)',.05,.95,.5,.01,v=>vi(v,2),'Kéo để thấy đánh đổi: bắt nhiều tấn công hơn ⇄ nhiều cảnh báo giả hơn.')}
   <div id="thrPlot"></div>
   <div class="grid4 mt" style="grid-template-columns:repeat(4,1fr)">${[['TP','Tấn công, báo đúng',80],['FP','Benign, báo nhầm',10],['FN','Tấn công, bỏ sót',20],['TN','Benign, đúng',890]].map(([k,t,v])=>`<div class="ctl"><label for="n${k}">${k}</label><input type="number" id="n${k}" value="${v}" min="0" style="width:100%;padding:6px;border:1px solid var(--line);border-radius:8px"><small>${t}</small></div>`).join('')}</div>
   <div class="kv" id="prfKv"></div><p id="prfNote" class="note good"></p>
   <div class="payload" style="margin-top:10px">Precision = TP/(TP+FP)  ·  Recall = TP/(TP+FN)  ·  F1 = 2PR/(P+R)  ·  FPR = FP/(FP+TN)</div>`;
  const calc=()=>{const TP=+$('#nTP').value,FP=+$('#nFP').value,FN=+$('#nFN').value,TN=+$('#nTN').value;
    const P_=TP/(TP+FP||1),R=TP/(TP+FN||1),F=P_+R?2*P_*R/(P_+R):0,FPR=FP/(FP+TN||1),FNR=FN/(TP+FN||1),acc=(TP+TN)/(TP+FP+FN+TN||1);
    $('#prfKv').innerHTML=`<div><small>PRECISION</small><b>${pct(P_)}</b></div><div><small>RECALL</small><b>${pct(R)}</b></div><div><small>F1</small><b>${pct(F)}</b></div><div><small>FPR</small><b>${pct(FPR,2)}</b></div><div><small>FNR (BỎ SÓT)</small><b>${pct(FNR)}</b></div><div><small>ACCURACY</small><b>${pct(acc)}</b></div>`;
    $('#prfNote').innerHTML=`Analyst nhận <b>${TP+FP}</b> cảnh báo, trong đó <b>${FP}</b> là báo nhầm (${pct(1-P_,0)}). Còn <b>${FN}</b> tấn công không ai thấy. ${R<.7?'Recall thấp: nguy cơ bỏ sót.':P_<.7?'Precision thấp: analyst sẽ ngợp vì cảnh báo giả.':'Cân bằng tương đối.'}`};
  ['nTP','nFP','nFN','nTN'].forEach(i=>$('#'+i).oninput=calc);
  const thrRun=t=>{ // 100 tấn công ~ N(.7,.17), 900 benign ~ N(.3,.15)
    const TP=Math.round(100*(1-cdf(t,.7,.17))),FN=100-TP,FP=Math.round(900*(1-cdf(t,.3,.15))),TN=900-FP;
    $('#nTP').value=TP;$('#nFP').value=FP;$('#nFN').value=FN;$('#nTN').value=TN;calc();
    const W=420,H=120,xs=Array.from({length:101},(_,i)=>i/100);const pdf=(x,m,s)=>Math.exp(-(((x-m)/s)**2)/2)/(s*2.5066);
    const X=x=>10+x*(W-20),Y=(v,k)=>H-14-v*k*(H-30);
    const mk=(m,s,k)=>xs.map((x,i)=>`${i?'L':'M'}${X(x)},${Y(pdf(x,m,s),k)}`).join(' ');
    $('#thrPlot').innerHTML=svg(W,H,`<path d="${mk(.3,.15,.05*900/450)}" fill="#16b8b633" stroke="#16b8b6" stroke-width="2"/><path d="${mk(.7,.17,.05*100/450*2.5)}" fill="#ff7c4333" stroke="#ff7c43" stroke-width="2"/><line x1="${X(t)}" x2="${X(t)}" y1="6" y2="${H-14}" stroke="#10182a" stroke-width="2"/><text x="14" y="14" font-size="9" font-family="DM Mono" fill="#16b8b6">Benign (900)</text><text x="${W-90}" y="14" font-size="9" font-family="DM Mono" fill="#ff7c43">Attack (100)</text><text x="${X(t)+4}" y="${H-4}" font-size="9" font-family="DM Mono">ngưỡng ${vi(t,2)}</text>`,'curve-svg');};
  bindSlider('thr',v=>vi(v,2),thrRun)();

  // ---- mất cân bằng
  const b=$('#imbDemo');
  b.innerHTML=head('Demo · Accuracy 99% mà không bắt được tấn công nào',['interactive'])+`
   ${slider('imbA','Số tấn công trong 1.000 flow',1,200,10,1)}
   <div class="seg" id="imbMode"><button class="on" data-m="dummy">Mô hình “đoán tất cả Benign”</button><button data-m="real">Mô hình khá (Recall 80%, Precision 70%)</button></div>
   <div id="imbDots" class="imb-dots mt"></div><div class="kv mt" id="imbKv"></div><p id="imbNote" class="note"></p>`;
  let mode='dummy';
  const imb=()=>{const A=+$('#imbA').value,N=1000,B=N-A;
    $('#imbDots').innerHTML=Array.from({length:N},(_,i)=>`<i class="${i<A?'a':''}"></i>`).sort(()=>0).join('');
    let TP,FP,FN,TN;if(mode==='dummy'){TP=0;FP=0;FN=A;TN=B}else{TP=Math.round(A*.8);FN=A-TP;FP=Math.round(TP/.7-TP);TN=B-FP}
    const acc=(TP+TN)/N,R=TP/(A||1),Pp=TP/((TP+FP)||1),F1a=Pp+R?2*Pp*R/(Pp+R):0;
    const pB=TN/((TN+FN)||1),rB=TN/((TN+FP)||1),F1b=pB+rB?2*pB*rB/(pB+rB):0;const macro=(F1a+F1b)/2;
    $('#imbKv').innerHTML=`<div><small>ACCURACY</small><b>${pct(acc)}</b></div><div><small>RECALL ATTACK</small><b>${pct(R)}</b></div><div><small>F1 ATTACK</small><b>${pct(F1a)}</b></div><div><small>MACRO F1</small><b>${pct(macro)}</b></div>`;
    $('#imbNote').innerHTML=mode==='dummy'?`Tấn công chỉ chiếm ${pct(A/N)}. Đoán tất cả là Benign vẫn đúng <b>${pct(acc)}</b> nhưng <b>bỏ sót 100%</b> tấn công. Vì vậy dự án báo cáo <b>Macro F1</b> và xem <b>từng lớp</b>, không chỉ Accuracy.`:`Mô hình thật sự có ích có Macro F1 ${pct(macro)}, thấp hơn nhiều so với con số ${pct(acc)} của Accuracy: Accuracy bị lớp Benign “kéo” lên.`;
    $('#imbDots').innerHTML=Array.from({length:N},(_,i)=>`<i class="${i<A?'a':''}" ${i<A&&mode==='dummy'?'style="opacity:.55"':''}></i>`).join('');};
  seg($('#imbMode'),x=>{mode=x.dataset.m;imb()});bindSlider('imbA',null,imb)();

  // ---- confusion matrix thật
  const c=$('#cmDemo'),M=P.cm,K=P.classOrder;
  c.innerHTML=head('Confusion matrix thật của XGBoost (test 700.000 flow)',['real'])+`
   <div class="toolbar"><label class="lbl">HIỂN THỊ<span class="seg" id="cmMode"><button class="on" data-m="pct">% theo lớp thật (mỗi hàng = 100%)</button><button data-m="abs">Số flow</button></span></label></div>
   <div class="cm-wrap"><table class="cm" id="cmTable"></table></div>
   <div class="cm-info card mt" id="cmInfo">Bấm một ô hoặc một tên lớp để đọc.</div>
   <p class="note">Hàng = lớp thật, cột = lớp mô hình dự đoán. Đường chéo (đúng) màu xanh; ô lệch màu cam, càng đậm càng nhiều. Hai điểm yếu lớn: <b>Infilteration → Benign</b> và <b>SlowHTTPTest → FTP-BruteForce</b>.</p>`;
  let cmMode='pct';
  const drawCm=()=>{const short=K.map(k=>SHORT[k]||k);
    let h=`<tr><th></th>${short.map(s=>`<th>${esc(s)}</th>`).join('')}</tr>`;
    M.forEach((row,i)=>{const tot=row.reduce((s,x)=>s+x,0);h+=`<tr data-r="${i}"><td class="rl" data-r="${i}">${esc(short[i])}</td>`+row.map((v,j)=>{const f=v/tot;let bg;if(v===0)bg='#f4f6f1';else if(i===j)bg=`rgba(22,184,182,${.25+.75*f})`;else bg=`rgba(255,124,67,${Math.min(1,.28+Math.sqrt(f)*.9)})`;
      return `<td class="c" data-r="${i}" data-c="${j}" style="background:${bg};color:${v===0?'#c9cfc8':(i===j&&f<.5?'#10182a':'#fff')}" data-tip="<b>${esc(K[i])}</b> → dự đoán <b>${esc(K[j])}</b><br>${vi0(v)} flow (${pct(f,2)} của lớp thật)">${v===0?'·':cmMode==='abs'?(v>=1000?Math.round(v/1000)+'k':v):(f>=.995?'100':(f*100).toFixed(f<.1?1:0))}</td>`}).join('')+'</tr>'});
    $('#cmTable').innerHTML=h;
    $$('#cmTable td.c').forEach(td=>td.onclick=()=>{const i=+td.dataset.r,j=+td.dataset.c,v=M[i][j],tot=M[i].reduce((s,x)=>s+x,0);
      $('#cmInfo').innerHTML=i===j?`<b>${esc(K[i])}</b>: ${vi0(v)}/${vi0(tot)} flow được dự đoán đúng (Recall ${pct(v/tot,2)}).`:`<b>${esc(K[i])} → ${esc(K[j])}</b>: ${vi0(v)} flow (${pct(v/tot,2)} của lớp thật bị nhầm sang ${esc(K[j])}).`});
    $$('#cmTable td.rl').forEach(td=>td.onclick=()=>{const i=+td.dataset.r,cl=P.classes[i];const conf=M[i].map((v,j)=>[v,j]).filter(([v,j])=>j!==i&&v>0).sort((a,b)=>b[0]-a[0]).slice(0,3);
      $$('#cmTable tr').forEach(r=>r.classList.toggle('hi',+r.dataset.r===i));
      $('#cmInfo').innerHTML=`<b>${esc(K[i])}</b> · Precision ${pct(cl.precision,2)} · Recall ${pct(cl.recall,2)} · F1 ${pct(cl.f1,2)} · ${vi0(cl.support)} flow test.<br>${conf.length?'Hay bị nhầm sang: '+conf.map(([v,j])=>`<span class="tagpill miss">${esc(SHORT[K[j]]||K[j])} · ${vi0(v)}</span>`).join(''):'Hầu như không bị nhầm.'}`})};
  drawCm();seg($('#cmMode'),x=>{cmMode=x.dataset.m;drawCm()});

  // ---- 5,7481% vs 0,2324%
  const f=$('#fprDemo');
  const ben=K.indexOf('Benign');const benTot=M[ben].reduce((s,x)=>s+x,0);const fp=benTot-M[ben][ben];
  let missed=0,attTot=0;M.forEach((row,i)=>{if(i===ben)return;const tot=row.reduce((s,x)=>s+x,0);attTot+=tot;missed+=row[ben]});
  f.innerHTML=head('Hai con số dễ nhầm: 0,2324% và 5,7481%',['real'])+`
   <div class="grid2"><div class="card" style="background:#f4fbf7"><div class="card-label">BÁO ĐỘNG GIẢ THẬT (FPR TRÊN BENIGN)</div><h3 style="font-size:36px;color:#0f7d5a">${pct(fp/benTot,4)}</h3><p>${vi0(fp)} flow Benign bị báo là tấn công / ${vi0(benTot)} flow Benign.</p></div>
   <div class="card" style="background:#fff5f0"><div class="card-label">TỈ LỆ BỎ SÓT (TẤN CÔNG BỊ ĐOÁN LÀ BENIGN)</div><h3 style="font-size:36px;color:#b4232a">${pct(missed/attTot,4)}</h3><p>${vi0(missed)} flow tấn công bị đoán là Benign / ${vi0(attTot)} flow tấn công. Trong bảng RQ1 cũ con số này bị ghi nhầm là “FPR”.</p></div></div>
   <p class="note warn">Khi hội đồng hỏi “tỉ lệ báo động giả là bao nhiêu?”, trả lời <b>0,2324%</b> trên Benign. Nhưng cũng nên nói thẳng: <b>${pct(missed/attTot,2)}</b> tấn công bị bỏ sót, phần lớn là Infilteration (${vi0(M[K.indexOf('Infilteration')][ben])} flow).</p>`;
});
})();
