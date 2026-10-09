/* models.js — Chương 03 (cây), 04 (Bagging vs Boosting), 05 (RF, XGBoost, siêu tham số) */

/* ===== bộ dựng cây hồi quy dùng chung (CART + công thức Gain của XGBoost) ===== */
const ML={};
ML.truth=x=>Math.sin(1.3*x);
ML.data=function(seed,n,noise,outliers){const r=rng(seed);const X=[],Y=[];for(let i=0;i<n;i++){const x=r()*10;let y=ML.truth(x)+gauss(r)*noise;if(outliers&&r()<.1)y+=(r()<.5?-1:1)*1.6;X.push(x);Y.push(y)}return{X,Y}};
ML.GRID=Array.from({length:160},(_,i)=>i/159*10);
ML.tree=function(X,R,idx,depth,o){
  // idx: chỉ số đã sắp theo X
  const n=idx.length;let G=0;for(const i of idx)G+=R[i];const H=n,lam=o.lambda||0;
  const leaf=()=>({w:G/(H+lam),leaf:1});
  if(depth>=o.depth||n<2*(o.minLeaf||1))return leaf();
  let best=null,GL=0;
  for(let k=1;k<n;k++){GL+=R[idx[k-1]];if(X[idx[k]]===X[idx[k-1]])continue;const nl=k,nr=n-k;if(nl<(o.minLeaf||1)||nr<(o.minLeaf||1))continue;const HL=nl,HR=nr;if(HL<(o.mcw||0)||HR<(o.mcw||0))continue;const GR=G-GL;
    const gain=.5*(GL*GL/(HL+lam)+GR*GR/(HR+lam)-G*G/(H+lam))-(o.gamma||0);if(gain>1e-12&&(!best||gain>best.gain))best={gain,k,t:(X[idx[k]]+X[idx[k-1]])/2}}
  if(!best)return leaf();
  return{t:best.t,l:ML.tree(X,R,idx.slice(0,best.k),depth+1,o),r:ML.tree(X,R,idx.slice(best.k),depth+1,o)};
};
ML.pred=(t,x)=>{while(!t.leaf)t=x<t.t?t.l:t.r;return t.w};
ML.leaves=t=>t.leaf?1:ML.leaves(t.l)+ML.leaves(t.r);
ML.sorted=(X,ids)=>ids.slice().sort((a,b)=>X[a]-X[b]);
ML.mse=(f,X,Y)=>mean(X.map((x,i)=>(f(x)-Y[i])**2));
ML.single=(d,o)=>{const idx=ML.sorted(d.X,d.X.map((_,i)=>i));const t=ML.tree(d.X,d.Y,idx,0,o);return{f:x=>ML.pred(t,x),leaves:ML.leaves(t)}};
ML.rf=(d,o)=>{const r=rng(o.seed||7);const n=d.X.length;const m=Math.max(2,Math.round(n*(o.frac||1)));const trees=[];
  for(let b=0;b<o.trees;b++){const ids=Array.from({length:m},()=>Math.floor(r()*n));trees.push(ML.tree(d.X,d.Y,ML.sorted(d.X,ids),0,o))}
  let lv=0;trees.forEach(t=>lv+=ML.leaves(t));
  const f=(x,k)=>{let s=0;const K=k||trees.length;for(let i=0;i<K;i++)s+=ML.pred(trees[i],x);return s/K};
  return{f,trees,leaves:lv};};
ML.xgb=(d,o)=>{const r=rng(o.seed||11);const n=d.X.length;const base=mean(d.Y);const F=new Array(n).fill(base);const trees=[];
  for(let m=0;m<o.rounds;m++){const R=d.Y.map((y,i)=>y-F[i]);let ids=Array.from({length:n},(_,i)=>i);if((o.subsample||1)<1)ids=ids.filter(()=>r()<o.subsample);if(ids.length<4)ids=Array.from({length:n},(_,i)=>i);
    const t=ML.tree(d.X,R,ML.sorted(d.X,ids),0,o);trees.push(t);for(let i=0;i<n;i++)F[i]+=o.eta*ML.pred(t,d.X[i])}
  const f=(x,k)=>{let s=base;const K=k===undefined?trees.length:k;for(let i=0;i<K;i++)s+=o.eta*ML.pred(trees[i],x);return s};
  let lv=0;trees.forEach(t=>lv+=ML.leaves(t));return{f,trees,leaves:lv};};

function curveSvg(opts){ // opts:{train,val,series:[{ys,color,w,dash}],w,h,title}
  const W=opts.w||320,H=opts.h||200,m=14;const X=x=>m+x/10*(W-2*m),Y=y=>H-m-(y+2)/4*(H-2*m);
  let g=`<rect width="${W}" height="${H}" fill="none"/>`;
  g+=`<path d="${ML.GRID.map((x,i)=>`${i?'L':'M'}${X(x).toFixed(1)},${Y(ML.truth(x)).toFixed(1)}`).join(' ')}" fill="none" stroke="#9aa5b8" stroke-width="1.2" stroke-dasharray="3 3"/>`;
  (opts.series||[]).forEach(s=>{g+=`<path d="${ML.GRID.map((x,i)=>`${i?'L':'M'}${X(x).toFixed(1)},${Y(clamp(s.f(x),-2,2)).toFixed(1)}`).join(' ')}" fill="none" stroke="${s.color}" stroke-width="${s.w||2}" ${s.dash?`stroke-dasharray="${s.dash}"`:''} stroke-linejoin="round"/>`});
  if(opts.train)opts.train.X.forEach((x,i)=>{g+=`<circle cx="${X(x).toFixed(1)}" cy="${Y(clamp(opts.train.Y[i],-2,2)).toFixed(1)}" r="2.6" fill="${opts.pt||'#ff7c43'}" fill-opacity=".75"/>`});
  return svg(W,H,g,'curve-svg');
}

/* ===== Chương 03: cây minh họa + bias/variance ===== */
HUB.reg(function mlInit(){
  // --- cây quyết định minh họa
  const t=$('#treeDemo');
  t.innerHTML=head('Demo · Một flow đi qua cây thế nào?',['interactive'])+`
   ${slider('tPps','Flow Packets/s',0,1000,680,10,v=>v+' pkt/s')}${slider('tRst','RST Flag Count',0,30,14,1)}
   <svg id="treeSvg" viewBox="0 0 420 250" class="tree-svg"></svg><p id="treeOut" class="note good"></p>
   <p class="note">Đây là <b>cây minh họa</b> với ngưỡng ví dụ, không phải cấu trúc của mô hình thật (XGBoost thật có 1.500 cây, mỗi cây sâu tối đa 8 tầng).</p>`;
  const nodes=(pps,rst)=>{
    const a=pps>500,b=rst>10;const on=(c)=>c?'#ff7c43':'#c9cfc8';
    let g=`<g font-family="DM Mono,monospace" font-size="11" text-anchor="middle">`;
    const box=(x,y,w,txt,act,fill)=>`<rect x="${x-w/2}" y="${y}" width="${w}" height="34" rx="9" fill="${act?fill:'#f4f6f1'}" stroke="${act?'#10182a':'#c9cfc8'}" stroke-width="${act?2:1}"/><text x="${x}" y="${y+21}" fill="${act?'#10182a':'#8a93a3'}">${txt}</text>`;
    g+=`<line x1="210" y1="44" x2="110" y2="92" stroke="${on(!a)}" stroke-width="${!a?3:1.5}"/><line x1="210" y1="44" x2="310" y2="92" stroke="${on(a)}" stroke-width="${a?3:1.5}"/>`;
    g+=`<line x1="310" y1="126" x2="250" y2="170" stroke="${on(a&&!b)}" stroke-width="${a&&!b?3:1.5}"/><line x1="310" y1="126" x2="370" y2="170" stroke="${on(a&&b)}" stroke-width="${a&&b?3:1.5}"/>`;
    g+=box(210,10,190,'Flow Pkts/s > 500 ?',true,'#ffe3d3')+`<text x="150" y="72" fill="#6b7686" font-size="9">Không</text><text x="285" y="72" fill="#6b7686" font-size="9">Có</text>`;
    g+=box(110,92,120,'Benign',!a,'#dcf7ec')+box(310,92,160,'RST Cnt > 10 ?',a,'#ffe3d3');
    g+=`<text x="262" y="154" fill="#6b7686" font-size="9">Không</text><text x="350" y="154" fill="#6b7686" font-size="9">Có</text>`;
    g+=box(250,170,110,'Cần xem xét',a&&!b,'#fff0d6')+box(370,170,100,'Attack',a&&b,'#ffd9d9');
    return g+'</g>';};
  const upd=()=>{const pps=+$('#tPps').value,rst=+$('#tRst').value;$('#treeSvg').innerHTML=nodes(pps,rst);const res=pps<=500?'Benign':rst>10?'Attack':'Cần xem xét';$('#treeOut').textContent=`Flow ${pps} pkt/s, RST = ${rst} → ${res}. Mô hình chỉ cần vài câu hỏi “lớn hơn ngưỡng?” để chia flow vào lớp.`};
  bindSlider('tPps',v=>v+' pkt/s',upd);bindSlider('tRst',null,upd);upd();

  // --- bias / variance
  const o=$('#overfitDemo');
  o.innerHTML=head('Demo · Quá đơn giản hay quá phức tạp?',['interactive'])+`
   ${slider('ovDepth','Độ sâu cây (max_depth)',1,12,3,1)}
   <label class="toggle"><input type="checkbox" id="ovOut"> Thêm nhiễu/outlier vào nhãn</label>
   <div id="ovPlot"></div><div class="kv mt" id="ovKv"></div><div id="ovErr"></div><p id="ovNote" class="note"></p>`;
  const ovRun=()=>{
    const out=$('#ovOut').checked;const tr=ML.data(3,45,.35,out),va=ML.data(99,200,.35,false);const d=+$('#ovDepth').value;
    const m=ML.single(tr,{depth:d,minLeaf:1});
    $('#ovPlot').innerHTML=curveSvg({train:tr,series:[{f:m.f,color:'#10182a'}],w:420,h:210});
    const errs=[];for(let k=1;k<=12;k++){const mm=ML.single(tr,{depth:k,minLeaf:1});errs.push([ML.mse(mm.f,tr.X,tr.Y),ML.mse(mm.f,va.X,va.Y)])}
    const mx=Math.max(...errs.flat());const W=420,H=110;const x=i=>20+i/11*(W-40),y=v=>H-14-v/mx*(H-30);
    let g=`<path d="${errs.map((e,i)=>`${i?'L':'M'}${x(i)},${y(e[0])}`).join(' ')}" fill="none" stroke="#16b8b6" stroke-width="2"/><path d="${errs.map((e,i)=>`${i?'L':'M'}${x(i)},${y(e[1])}`).join(' ')}" fill="none" stroke="#e5484d" stroke-width="2"/><circle cx="${x(d-1)}" cy="${y(errs[d-1][0])}" r="5" fill="#16b8b6"/><circle cx="${x(d-1)}" cy="${y(errs[d-1][1])}" r="5" fill="#e5484d"/><text x="22" y="12" font-size="10" font-family="DM Mono" fill="#16b8b6">train</text><text x="60" y="12" font-size="10" font-family="DM Mono" fill="#e5484d">validation</text>`;
    for(let k=1;k<=12;k++)g+=`<text x="${x(k-1)}" y="${H-1}" font-size="8" text-anchor="middle" fill="#6b7686" font-family="DM Mono">${k}</text>`;
    $('#ovErr').innerHTML=svg(W,H,g,'curve-svg');
    $('#ovKv').innerHTML=`<div><small>TRAIN MSE</small><b>${vi(errs[d-1][0],3)}</b></div><div><small>VALIDATION MSE</small><b>${vi(errs[d-1][1],3)}</b></div><div><small>SỐ LÁ</small><b>${m.leaves}</b></div>`;
    const gap=errs[d-1][1]-errs[d-1][0];
    $('#ovNote').innerHTML=d<=2?'<b>Underfit (bias cao):</b> cây quá nông, cả train và validation đều sai nhiều.':gap>.12?'<b>Overfit (variance cao):</b> cây ôm theo từng điểm nhiễu, train rất thấp nhưng validation tệ hơn.':'<b>Vùng cân bằng:</b> train và validation đều thấp, khoảng cách nhỏ.';
  };
  bindSlider('ovDepth',null,ovRun);$('#ovOut').onchange=ovRun;ovRun();
});

/* ===== Chương 04: Bagging vs Boosting ===== */
HUB.reg(function ensembleInit(){
  const r=$('#ensembleDemo');
  r.innerHTML=head('Demo · Cùng một dữ liệu nhiễu, ba cách học',['interactive'])+`
   <div class="grid3">
    <div>${slider('enB','Bagging · số cây B',1,120,25,1)}</div>
    <div>${slider('enM','Boosting · số vòng M',1,150,40,1)}</div>
    <div>${slider('enE','Boosting · learning rate η',.02,1,.3,.02,v=>vi(v,2))}</div></div>
   <div class="toolbar"><label class="toggle"><input type="checkbox" id="enOut"> Thêm nhãn nhiễu (10% outlier)</label><button class="btn sm lime" id="enPlay">▶ Boosting từng vòng</button><button class="btn sm alt" id="enSeed">Đổi mẫu dữ liệu</button></div>
   <div class="fit-grid"><div><div id="enSingle"></div><b>Một cây sâu</b><br><small id="enSingleI"></small></div><div><div id="enBag"></div><b>Bagging (trung bình B cây sâu)</b><br><small id="enBagI"></small></div><div><div id="enBoost"></div><b>Boosting (cộng M cây nông)</b><br><small id="enBoostI"></small></div></div>
   <p class="note">Chấm cam: dữ liệu huấn luyện. Nét đứt xám: hàm thật. Nét đậm: dự đoán. MSE tính so với <b>hàm thật</b> (càng thấp càng tốt). Bagging làm đường cong <b>mượt</b> hơn một cây (giảm variance). Boosting dần <b>bám</b> hàm thật; nếu quá nhiều vòng hoặc η lớn, nó bắt đầu học cả nhiễu.</p>`;
  let seed=5;
  const run=()=>{
    const B=+$('#enB').value,M=+$('#enM').value,eta=+$('#enE').value,out=$('#enOut').checked;
    const d=ML.data(seed,60,.35,out);const tm=x=>ML.truth(x);
    const mt=g=>mean(ML.GRID.map(x=>(g(x)-tm(x))**2));
    const s=ML.single(d,{depth:12,minLeaf:1});
    const bg=ML.rf(d,{trees:B,depth:12,minLeaf:1,frac:1,seed:seed+1});
    const bs=ML.xgb(d,{rounds:M,depth:2,eta,lambda:1,gamma:0,seed:seed+2});
    $('#enSingle').innerHTML=curveSvg({train:d,series:[{f:s.f,color:'#e5484d'}]});$('#enSingleI').textContent=`MSE so với hàm thật: ${vi(mt(s.f),3)}`;
    $('#enBag').innerHTML=curveSvg({train:d,series:[{f:bg.f,color:'#29d3d1'}]});$('#enBagI').textContent=`B = ${B} · MSE: ${vi(mt(bg.f),3)}`;
    $('#enBoost').innerHTML=curveSvg({train:d,series:[{f:bs.f,color:'#b7f23d'}]});$('#enBoostI').textContent=`M = ${M}, η = ${vi(eta,2)} · MSE: ${vi(mt(bs.f),3)}`;
  };
  const f1=bindSlider('enB',null,run),f2=bindSlider('enM',null,run),f3=bindSlider('enE',v=>vi(v,2),run);
  $('#enOut').onchange=run;$('#enSeed').onclick=()=>{seed=Math.floor(Math.random()*1e5);run()};
  let timer=null;$('#enPlay').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('#enPlay').textContent='▶ Boosting từng vòng';return}
    $('#enM').value=1;f2();$('#enPlay').textContent='⏸ Dừng';timer=setInterval(()=>{const el=$('#enM');if(+el.value>=+el.max){clearInterval(timer);timer=null;$('#enPlay').textContent='▶ Boosting từng vòng';return}el.value=+el.value+2;f2()},120)};
  run();
});

/* ===== Chương 05: bỏ phiếu vs cộng điểm, phòng siêu tham số, Gain ===== */
HUB.reg(function modelsInit(){
  // --- vote vs boosting
  const v=$('#voteDemo');
  v.innerHTML=head('Demo · Cùng một flow, hai cách ra quyết định',['interactive'])+`
   <div class="toolbar"><label class="lbl">LOẠI FLOW<span class="seg" id="vtCase"><button class="on" data-c="clear">Rõ ràng là tấn công</button><button data-c="mid">Mập mờ</button><button data-c="ben">Rõ ràng là Benign</button></span></label><button class="btn sm lime" id="vtPlay">▶ Chạy</button></div>
   <div class="grid2"><div><b>Random Forest · 25 cây bỏ phiếu</b><div id="vtVotes" class="imb-dots" style="grid-template-columns:repeat(13,1fr);max-width:360px;margin:10px 0"></div><output id="vtRf" class="note good"></output></div>
   <div><b>XGBoost · cộng điểm qua các vòng</b><svg id="vtXgb" viewBox="0 0 360 150" class="curve-svg"></svg><output id="vtXo" class="note good"></output>${slider('vtRound','Số vòng đã cộng',0,10,10,1)}</div></div>
   <p class="note">Rút gọn còn 2 lớp (Attack vs Benign) cho dễ nhìn. Mô hình thật có 15 lớp: mỗi vòng cộng điểm cho cả 15 lớp rồi softmax. Giá trị ở đây là minh họa.</p>`;
  let cs='clear';const cases={clear:{p:.88,m:[.9,.8,1.1,.7,.6,.5,.4,.3,.25,.2],base:-.4},mid:{p:.55,m:[.5,-.4,.6,-.3,.4,-.2,.3,.1,-.1,.2],base:0},ben:{p:.1,m:[-.8,-.6,-.5,-.4,-.3,-.2,-.2,-.1,-.1,-.05],base:.5}};
  const runV=(anim)=>{const c=cases[cs],r=rng(21);const votes=Array.from({length:25},()=>r()<c.p);
    $('#vtVotes').innerHTML=votes.map(a=>`<i class="${a?'a':''}" style="aspect-ratio:1"></i>`).join('');const na=votes.filter(Boolean).length;
    $('#vtRf').textContent=`${na}/25 phiếu Attack → ${na>12?'Attack':'Benign'} (xác suất ≈ ${vi(na/25,2)})`;
    const k=+$('#vtRound').value;let s=c.base;const steps=[s];for(let i=0;i<k;i++){s+=c.m[i];steps.push(s)}
    let g='';const W=360,H=150;const bw=(W-40)/11;steps.forEach((m,i)=>{const h=Math.abs(m)*34;const y=m>=0?75-h:75;g+=`<rect x="${20+i*bw}" y="${y}" width="${bw-4}" height="${Math.max(2,h)}" rx="3" fill="${i===0?'#9aa5b8':(c.m[i-1]>=0?'#16b8b6':'#ff7c43')}"/>`});
    g+=`<line x1="14" x2="${W-6}" y1="75" y2="75" stroke="#9aa5b8"/><text x="16" y="12" font-size="9" font-family="DM Mono" fill="#6b7686">cột 0 = dự đoán nền; mỗi cột sau = một cây sửa thêm</text>`;
    $('#vtXgb').innerHTML=g;const prob=1/(1+Math.exp(-s));
    $('#vtXo').textContent=`Tổng margin ${vi(s,2)} → xác suất Attack ${vi(prob,2)} (softmax/sigmoid) → ${prob>.5?'Attack':'Benign'}`;};
  seg($('#vtCase'),b=>{cs=b.dataset.c;$('#vtRound').value=0;$('#vtRound_o').textContent=0;runV();$('#vtPlay').click()});
  bindSlider('vtRound',null,runV);
  $('#vtPlay').onclick=()=>{let k=0;$('#vtRound').value=0;const iv=setInterval(()=>{k++;$('#vtRound').value=k;$('#vtRound_o').textContent=k;runV();if(k>=10)clearInterval(iv)},260)};
  runV();

  // --- phòng siêu tham số
  const L=$('#paramLab');
  const XP=[['rounds','n_estimators',1,200,100,1,'Số vòng boosting. Nhiều vòng: học kỹ hơn nhưng càng về sau càng dễ học nhiễu.'],['depth','max_depth',1,10,4,1,'Độ sâu mỗi cây. Sâu = học tương tác phức tạp, dễ overfit.'],['eta','learning_rate',.02,1,.1,.02,'Mức đóng góp của mỗi cây (η). Nhỏ = cẩn trọng, cần nhiều vòng hơn.'],['subsample','subsample',.3,1,.8,.05,'Tỉ lệ dòng dùng cho mỗi cây. <1 tạo ngẫu nhiên, giảm overfit.'],['lambda','reg_lambda (λ)',0,20,1,.5,'Phạt L2 trên điểm lá. Lớn = lá nhỏ lại, mô hình mượt hơn.'],['gamma','gamma (γ)',0,1.5,0,.05,'Gain tối thiểu để được tách. Lớn = cây bị cắt tỉa.'],['mcw','min_child_weight',1,12,1,1,'Tổng hessian tối thiểu ở nút con; ở bài toán này ≈ số mẫu tối thiểu.']];
  const RP=[['trees','n_estimators',1,200,100,1,'Số cây trong rừng. Nhiều cây: ổn định hơn, không overfit thêm.'],['depth','max_depth',1,16,12,1,'Độ sâu tối đa mỗi cây.'],['minLeaf','min_samples_leaf',1,15,1,1,'Số mẫu tối thiểu ở lá. Tăng = mượt hơn, giảm overfit.'],['frac','max_samples (bootstrap)',.3,1,1,.05,'Tỉ lệ mẫu rút cho mỗi cây.']];
  L.innerHTML=head('Phòng lab siêu tham số · thí nghiệm thật trên dữ liệu 1 chiều',['interactive'])+`
   <div class="split"><div><div class="seg" id="plModel"><button class="on" data-m="xgb">XGBoost</button><button data-m="rf">Random Forest</button></div><div id="plCtl"></div></div>
   <div><div id="plCurve"></div><div class="kv mt" id="plKv"></div><div id="plErr" class="mt"></div><p id="plAdvice" class="note"></p></div></div>
   <div class="project-config mt"><span class="card-label">CẤU HÌNH XGBOOST CỦA DỰ ÁN</span> ${badge('real')}<br><code>n_estimators=100 · max_depth=8 · learning_rate=0.08 · tree_method=hist · objective=multi:softprob · 15 lớp</code></div>
   <h4>Các siêu tham số khác cần biết</h4><div class="gloss" id="plDict"></div>
   <p class="note">Mỗi lần kéo là một lần huấn luyện thật (mô hình tự viết) trên 45 điểm train và 200 điểm validation. Đây là <b>thí nghiệm minh họa</b> để thấy xu hướng, không phải kết quả của dự án.</p>`;
  let pm='xgb';
  const DICT={xgb:[['colsample_bytree','Tỉ lệ feature lấy cho mỗi cây; tạo đa dạng, chống overfit.'],['reg_alpha','Phạt L1 trên điểm lá, có thể đưa lá về 0.'],['tree_method','hist: gom giá trị vào histogram để dựng cây nhanh trên dữ liệu lớn (dự án dùng hist).'],['objective / num_class','multi:softprob: mỗi vòng xây K cây (K = 15 lớp) rồi softmax.'],['early_stopping_rounds','Dừng khi validation không cải thiện sau N vòng.'],['sample_weight','Trọng số mẫu để xử lý mất cân bằng lớp.']],rf:[['max_features','Số feature xét ở mỗi lần chia (mặc định sqrt(p) ≈ 9 với 78 feature): tạo sự đa dạng giữa các cây.'],['bootstrap','Có rút mẫu có hoàn lại cho từng cây không (nền tảng của bagging).'],['criterion','gini hoặc entropy: hàm đo chất lượng một lần chia.'],['class_weight','Tăng trọng số lớp hiếm khi mất cân bằng.'],['oob_score','Dùng mẫu out-of-bag để ước lượng lỗi mà không cần validation.'],['n_jobs','Số luồng CPU; các cây độc lập nên chạy song song được.']]};
  const trD=ML.data(3,45,.35,false),vaD=ML.data(99,200,.35,false);
  function draw(){
    const defs=pm==='xgb'?XP:RP;const vals={};defs.forEach(d=>vals[d[0]]=+$('#pl_'+d[0]).value);
    let model,stage;
    if(pm==='xgb'){model=ML.xgb(trD,{rounds:vals.rounds,depth:vals.depth,eta:vals.eta,subsample:vals.subsample,lambda:vals.lambda,gamma:vals.gamma,mcw:vals.mcw,seed:4});
      stage=Array.from({length:vals.rounds},(_,k)=>[ML.mse(x=>model.f(x,k+1),trD.X,trD.Y),ML.mse(x=>model.f(x,k+1),vaD.X,vaD.Y)]);}
    else{model=ML.rf(trD,{trees:vals.trees,depth:vals.depth,minLeaf:vals.minLeaf,frac:vals.frac,seed:4});
      const step=Math.max(1,Math.floor(vals.trees/60));stage=[];for(let k=1;k<=vals.trees;k+=step)stage.push([ML.mse(x=>model.f(x,k),trD.X,trD.Y),ML.mse(x=>model.f(x,k),vaD.X,vaD.Y)]);}
    $('#plCurve').innerHTML=curveSvg({train:trD,series:[{f:x=>model.f(x),color:'#10182a'}],w:420,h:210});
    const tr=ML.mse(model.f,trD.X,trD.Y),va=ML.mse(model.f,vaD.X,vaD.Y);
    $('#plKv').innerHTML=`<div><small>TRAIN MSE</small><b>${vi(tr,3)}</b></div><div><small>VALIDATION MSE</small><b>${vi(va,3)}</b></div><div><small>TỔNG SỐ LÁ</small><b>${model.leaves}</b></div><div><small>CHI PHÍ ~ SỐ LÁ</small><b class="sm">${model.leaves>800?'cao':model.leaves>250?'vừa':'thấp'}</b></div>`;
    const W=420,H=120,mx=Math.max(...stage.flat());const x=i=>20+i/(Math.max(1,stage.length-1))*(W-40),y=v=>H-16-v/mx*(H-34);
    let bi=0;stage.forEach((s,i)=>{if(s[1]<stage[bi][1])bi=i});
    let g=`<path d="${stage.map((s,i)=>`${i?'L':'M'}${x(i)},${y(s[0])}`).join(' ')}" fill="none" stroke="#16b8b6" stroke-width="2"/><path d="${stage.map((s,i)=>`${i?'L':'M'}${x(i)},${y(s[1])}`).join(' ')}" fill="none" stroke="#e5484d" stroke-width="2"/><line x1="${x(bi)}" x2="${x(bi)}" y1="14" y2="${H-16}" stroke="#7c5cff" stroke-dasharray="3 3"/><text x="${Math.min(W-130,x(bi)+4)}" y="24" font-size="9" font-family="DM Mono" fill="#7c5cff">validation tốt nhất${pm==='xgb'?' (early stopping)':''}</text><text x="22" y="${H-3}" font-size="9" font-family="DM Mono" fill="#6b7686">${pm==='xgb'?'vòng boosting':'số cây'} →  <tspan fill="#16b8b6">train</tspan>  <tspan fill="#e5484d">validation</tspan></text>`;
    $('#plErr').innerHTML=svg(W,H,g,'curve-svg');
    const bestK=pm==='xgb'?bi+1:null;
    let adv='';
    if(pm==='xgb'){adv=va-tr>.1?`<b>Overfit:</b> validation (${vi(va,3)}) cao hơn train (${vi(tr,3)}). Thử giảm max_depth/learning_rate, tăng reg_lambda/gamma hoặc dừng sớm ở vòng ${bestK}.`:`<b>Ổn:</b> khoảng cách train–validation nhỏ. Validation tốt nhất ở vòng ${bestK}${bestK<vals.rounds*.8?`, nên dùng early stopping thay vì chạy hết ${vals.rounds} vòng`:''}.`}
    else adv=vals.depth>=10&&vals.minLeaf===1?'<b>Mỗi cây rất sâu</b> nhưng nhờ trung bình nhiều cây, validation vẫn ổn. Thử giảm số cây xuống 1–3 để thấy variance trở lại.':'<b>Cây vừa phải:</b> tăng min_samples_leaf làm đường mượt hơn nhưng có thể underfit.';
    $('#plAdvice').innerHTML=adv;
  }
  function build(){const defs=pm==='xgb'?XP:RP;$('#plCtl').innerHTML=defs.map(d=>slider('pl_'+d[0],d[1],d[2],d[3],d[4],d[5],d[5]<1?(x=>vi(x,2)):null,d[6])).join('');
    defs.forEach(d=>bindSlider('pl_'+d[0],d[5]<1?(x=>vi(x,2)):null,draw));$('#plDict').innerHTML=DICT[pm].map(([a,b])=>`<article><b>${a}</b><p>${b}</p></article>`).join('');draw()}
  seg($('#plModel'),b=>{pm=b.dataset.m;build()});build();

  // --- Gain calculator
  const G=$('#gainDemo');
  G.innerHTML=head('Demo · Máy tính Gain của XGBoost: khi nào nên tách nút?',['interactive'])+`
   <div class="grid2"><div>${slider('gGL','G_L (tổng gradient nút trái)',-20,20,-8,1)}${slider('gHL','H_L (tổng hessian nút trái)',1,30,10,1)}${slider('gGR','G_R (nút phải)',-20,20,9,1)}${slider('gHR','H_R',1,30,12,1)}${slider('gLam','λ (reg_lambda)',0,10,1,.5,x=>vi(x,1))}${slider('gGam','γ (gamma)',0,5,0.5,.1,x=>vi(x,1))}</div>
   <div><div class="kv" id="gKv"></div><p id="gOut" class="note good"></p><div class="payload" id="gFormula"></div></div></div>
   <p class="note">Mỗi nút có điểm tối ưu <code>w* = −G/(H+λ)</code>. Gain = chất lượng hai nút con − chất lượng nút cha − γ. Gain &gt; 0 mới tách. Tăng λ hoặc γ làm cây khó tách hơn, tức <b>regularization</b>.</p>`;
  const gcalc=()=>{const gl=+$('#gGL').value,hl=+$('#gHL').value,gr=+$('#gGR').value,hr=+$('#gHR').value,lam=+$('#gLam').value,gam=+$('#gGam').value;
    const sc=(g,h)=>g*g/(h+lam);const gain=.5*(sc(gl,hl)+sc(gr,hr)-sc(gl+gr,hl+hr))-gam;
    $('#gKv').innerHTML=`<div><small>w* TRÁI</small><b>${vi(-gl/(hl+lam),3)}</b></div><div><small>w* PHẢI</small><b>${vi(-gr/(hr+lam),3)}</b></div><div><small>w* NÚT CHA</small><b>${vi(-(gl+gr)/(hl+hr+lam),3)}</b></div><div><small>GAIN</small><b style="color:${gain>0?'#0f7d5a':'#b4232a'}">${vi(gain,3)}</b></div>`;
    $('#gOut').innerHTML=gain>0?`Gain = ${vi(gain,3)} &gt; 0 ⇒ <b>tách nút</b>. Hai bên kéo điểm về hai hướng khác nhau đủ nhiều để vượt qua γ = ${vi(gam,1)}.`:`Gain = ${vi(gain,3)} ≤ 0 ⇒ <b>không tách</b> (cắt tỉa). Hai bên quá giống nhau hoặc γ/λ quá lớn so với lợi ích.`;
    $('#gFormula').textContent=`Gain = ½·[ ${vi(sc(gl,hl),2)} + ${vi(sc(gr,hr),2)} − ${vi(sc(gl+gr,hl+hr),2)} ] − ${vi(gam,1)} = ${vi(gain,3)}`;};
  ['gGL','gHL','gGR','gHR'].forEach(i=>bindSlider(i,null,gcalc));['gLam','gGam'].forEach(i=>bindSlider(i,x=>vi(x,1),gcalc));gcalc();
});
