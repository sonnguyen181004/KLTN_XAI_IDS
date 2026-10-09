/* study.js — flashcard, quiz, ngân hàng câu hỏi, thuật ngữ, hình báo cáo */
HUB.reg(function study(){
const CARDS=[
 ['Flow','Chuỗi packet cùng 5-tuple (IP nguồn/đích, cổng nguồn/đích, giao thức) trong một khoảng thời gian. Là đơn vị mà mô hình phân loại.'],
 ['CICFlowMeter','Công cụ gom packet thành flow và tính 78 đặc trưng thống kê (duration, IAT, độ dài packet, cờ TCP…).'],
 ['Precision','TP / (TP + FP). Trong các cảnh báo đã bắn, bao nhiêu là thật.'],
 ['Recall','TP / (TP + FN). Trong các tấn công thật, bắt được bao nhiêu.'],
 ['F1','Trung bình điều hòa của Precision và Recall. Phạt mạnh khi một trong hai thấp.'],
 ['Bagging','Huấn luyện nhiều cây độc lập trên mẫu bootstrap rồi bỏ phiếu/trung bình → giảm variance (Random Forest).'],
 ['Boosting','Xây cây tuần tự, mỗi cây sửa sai số của các cây trước → giảm bias (XGBoost).'],
 ['XGBoost: số cây','Với phân loại K lớp, mỗi vòng boosting sinh K cây. 100 vòng × 15 lớp = 1500 cây.'],
 ['Gain (XGBoost)','½[G_L²/(H_L+λ) + G_R²/(H_R+λ) − (G_L+G_R)²/(H_L+H_R+λ)] − γ. Chia nếu Gain > 0.'],
 ['SHAP','Chia giá trị dự đoán thành đóng góp của từng feature theo Shapley value. Cộng lại = dự đoán − base value.'],
 ['LIME','Xấp xỉ mô hình quanh một điểm bằng mô hình tuyến tính có trọng số trên các mẫu nhiễu loạn lân cận.'],
 ['Local R² (LIME)','Mức độ mô hình tuyến tính cục bộ khớp với mô hình thật. R² thấp → giải thích LIME kém tin cậy.'],
 ['Jaccard@k','|A∩B| / |A∪B| giữa top-k feature của SHAP và LIME. Đo mức trùng tập.'],
 ['Spearman','Tương quan thứ hạng giữa hai bảng xếp hạng feature.'],
 ['Faithfulness','Xóa/che các feature được giải thích là quan trọng thì dự đoán có giảm thật không.'],
 ['Stability','Chạy lại giải thích (đổi seed) thì top feature có giữ nguyên không.'],
 ['Dataset fingerprint','Feature (Dst Port, Init Fwd Win Byts…) tách lớp nhờ đặc điểm môi trường thu thập, không nhờ hành vi tấn công. Rủi ro khi triển khai sang mạng khác.'],
 ['Domain Precision@5','Tỷ lệ top-5 feature trùng bảng tri thức chuyên gia. Là đối chiếu bảng, chưa phải đánh giá chuyên gia SOC.']];
let ci=0;
const fl=$('#flashDemo');
function drawFc(){
 const c=CARDS[ci];
 fl.innerHTML=`${head('Flashcard',['interactive'])}<div class="fc-wrap"><div class="fc" id="fc" tabindex="0" role="button" aria-label="Lật thẻ"><div class="front"><small>THUẬT NGỮ ${ci+1}/${CARDS.length}</small><h3>${esc(c[0])}</h3><small style="margin-top:14px">Bấm để lật</small></div><div class="back"><small>GIẢI THÍCH</small><p>${esc(c[1])}</p></div></div></div>
 <div class="verdicts" style="margin-top:14px"><button class="btn sm alt" id="fcP">← Trước</button><button class="btn sm alt" id="fcR">Ngẫu nhiên</button><button class="btn sm" id="fcN">Sau →</button></div>`;
 const f=$('#fc');f.onclick=()=>f.classList.toggle('flip');f.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();f.classList.toggle('flip')}};
 $('#fcP').onclick=()=>{ci=(ci+CARDS.length-1)%CARDS.length;drawFc()};
 $('#fcN').onclick=()=>{ci=(ci+1)%CARDS.length;drawFc()};
 $('#fcR').onclick=()=>{ci=Math.floor(Math.random()*CARDS.length);drawFc()};
}
/* quiz */
const QZ=[
 ['Một IDS bỏ sót nhiều tấn công. Chỉ số nào thấp?',['Precision','Recall','Accuracy trên Benign'],1,'Recall = TP/(TP+FN); bỏ sót làm FN tăng.'],
 ['XGBoost 15 lớp, 100 vòng boosting có bao nhiêu cây?',['100','115','1500'],2,'Mỗi vòng sinh K=15 cây (một cây cho mỗi lớp).'],
 ['Random Forest chủ yếu giảm…',['Bias','Variance','Số feature'],1,'Bagging trung bình nhiều cây độc lập → giảm variance.'],
 ['Boosting khác bagging ở chỗ…',['Cây xây tuần tự, sửa sai cây trước','Cây xây song song độc lập','Không dùng cây'],0,'Boosting là tuần tự, mỗi cây fit phần dư/gradient.'],
 ['SHAP có tính chất additivity nghĩa là…',['Top-5 luôn trùng LIME','Tổng đóng góp = dự đoán − base value','Chạy nhanh hơn LIME'],1,'Local accuracy: base + Σφ = f(x).'],
 ['LIME có R² cục bộ 0,16. Nên…',['Tin hoàn toàn','Dè dặt với giải thích đó','Tăng learning rate'],1,'Surrogate tuyến tính khớp kém → giải thích kém tin cậy.'],
 ['Jaccard@5 giữa SHAP và LIME thấp cho thấy…',['Một trong hai sai chắc chắn','Hai phương pháp chọn tập feature khác nhau','Mô hình overfit'],1,'Không biết cái nào đúng; cần faithfulness/domain để đánh giá thêm.'],
 ['Dst Port nổi lên là feature quan trọng nhất. Rủi ro?',['Không có','Dấu vân tay môi trường, khó khái quát','Mô hình quá đơn giản'],1,'Port gắn với dịch vụ/kịch bản thu thập dữ liệu.'],
 ['Tỉ lệ 5,7481% trong bảng cũ thật ra là…',['FPR của Benign','Tỉ lệ tấn công bị đoán là Benign','Lỗi cú pháp'],1,'FPR thật trên Benign là 0,2324%.']];
let qi=0,score=0,done=false;
const qd=$('#quizDemo');
function drawQ(){
 if(qi>=QZ.length){qd.innerHTML=`${head('Quiz nhanh',['interactive'])}<h3>Kết quả: ${score}/${QZ.length}</h3><p class="note">${score>=QZ.length-1?'Rất tốt.':'Xem lại các chương liên quan trong ngân hàng câu hỏi.'}</p><button class="btn sm" id="qR">Làm lại</button>`;$('#qR').onclick=()=>{qi=0;score=0;drawQ()};return}
 const q=QZ[qi];done=false;
 qd.innerHTML=`${head('Quiz nhanh',['interactive'])}<small class="note">Câu ${qi+1}/${QZ.length}</small><h4 style="margin:6px 0 10px">${esc(q[0])}</h4>${q[1].map((o,i)=>`<button class="qa-opt" data-i="${i}">${esc(o)}</button>`).join('')}<p class="note" id="qExp"></p><button class="btn sm" id="qN" style="display:none">Câu tiếp →</button>`;
 $$('.qa-opt',qd).forEach(b=>b.onclick=()=>{if(done)return;done=true;const i=+b.dataset.i;if(i===q[2])score++;
  $$('.qa-opt',qd).forEach(x=>{x.classList.toggle('ok',+x.dataset.i===q[2]);if(x===b&&i!==q[2])x.classList.add('bad')});
  $('#qExp').textContent=q[3];$('#qN').style.display='inline-flex'});
 $('#qN').onclick=()=>{qi++;drawQ()};
}
/* question bank */
const QB=[
 ['Vì sao chọn XGBoost?','Dữ liệu dạng bảng, mất cân bằng, nhiều feature thống kê. Gradient boosting trên cây cho độ chính xác cao, TreeSHAP tính nhanh và chính xác. Kết quả: macro-F1 cao trên 700.000 flow test.','Chương Decision Tree / XGBoost'],
 ['XGBoost khác Random Forest thế nào?','RF: bagging, cây độc lập, giảm variance. XGBoost: boosting, cây tuần tự sửa sai, có regularization (λ, γ), learning rate η. Đề tài dùng 100 vòng, depth 8, lr 0,08, hist, multi:softprob.','Chương Bagging vs Boosting'],
 ['Vì sao không chỉ dùng Accuracy?','Benign chiếm 490.000/700.000 flow. Đoán toàn Benign đã đạt accuracy cao. Cần precision/recall/F1 theo từng lớp.','Chương Precision/Recall/F1, Imbalance'],
 ['Lớp nào yếu nhất và vì sao?','Infiltration (recall ~16%, 12.026 flow bị đoán Benign) và SlowHTTPTest (1.082 flow bị đoán FTP). Hành vi giống lưu lượng thường hoặc giống lớp khác.','Chương Confusion matrix, Attack demo'],
 ['SHAP và LIME khác nhau ra sao?','SHAP: dựa Shapley, cộng lại bằng dự đoán, TreeSHAP chính xác cho cây. LIME: surrogate tuyến tính cục bộ, phụ thuộc kernel width, số mẫu, seed.','Chương SHAP vs LIME'],
 ['Vì sao SHAP và LIME ít trùng nhau?','Jaccard@5 trung bình thấp. Hai phương pháp định nghĩa “quan trọng” khác nhau; LIME còn bị nhiễu (R² thấp, seed). Không thể kết luận cái nào đúng chỉ từ độ trùng.','Chương Agreement'],
 ['Làm sao biết giải thích đáng tin?','Dùng nhiều tiêu chí: faithfulness (xóa feature thì dự đoán đổi?), stability (đổi seed), robustness (nhiễu), domain Precision@5. Không tiêu chí nào đủ một mình.','Chương Evaluation'],
 ['Dst Port là fingerprint nghĩa là gì?','Mô hình có thể học “cổng X thuộc lớp Y” do cách thu thập dataset. Sang mạng khác, tín hiệu này có thể sai. Cần đánh giá chéo dataset (chưa làm: Not Yet Validated).','Chương Dataset Fingerprint'],
 ['Hạn chế với tấn công web (XSS, SQLi)?','Flow feature chỉ thấy thống kê, không thấy payload. Cần lớp phân tích HTTP/WAF bổ sung.','Chương Web attack limits'],
 ['Đề tài đã chạy thật phần nào?','Prototype: bắt packet → CSV flow. Đề xuất: Schema Guard, dự đoán online, SHAP real-time, dashboard SOC. Độ trễ end-to-end chưa đo.','Chương IDS–SOC'],
 ['Lệch đơn vị thời gian là gì?','CICFlowMeter bản Python xuất giây, dữ liệu huấn luyện dùng µs. Nếu không chuyển đổi, Flow Duration/IAT lệch ×10⁶ và dự đoán sai.','Chương Pipeline fault'],
 ['Đóng góp chính của đề tài?','Đánh giá giải thích IDS bằng nhiều thước đo trên số liệu thật, chỉ ra điểm yếu (SHAP/LIME lệch, fingerprint), và đề xuất kiến trúc IDS–SOC có giải thích.','Tổng quan']];
$('#qbank').innerHTML=QB.map(q=>`<details><summary>${esc(q[0])}</summary><p>${esc(q[1])}</p><p><span class="tagpill">${esc(q[2])}</span></p></details>`).join('');
/* glossary */
const G=Object.entries(HUB.FEAT||{}).map(([k,v])=>[k,v]);
CARDS.forEach(c=>G.push(c));
function drawG(){
 const t=($('#glossSearch').value||'').toLowerCase().trim();
 const L=G.filter(g=>!t||g[0].toLowerCase().includes(t)||g[1].toLowerCase().includes(t));
 $('#gloss').innerHTML=L.length?L.map(g=>`<article><b>${esc(g[0])}</b><p>${esc(g[1])}</p></article>`).join(''):'<p class="note">Không có kết quả.</p>';
}
$('#glossSearch').oninput=drawG;
/* figures — mỗi hình kèm phân tích ngắn, dễ hiểu, số liệu thật của run hiện tại */
const FIG_FILE={workflow:'workflow',confusion:'confusion-matrix',agreement:'agreement',signed:'shap-lime-signed',stability:'stability',faithfulness:'faithfulness'};
const FIG_CAPTION={
  workflow:'Sơ đồ toàn bộ quy trình dự án: từ packet mạng → flow → 78 feature → model XGBoost → giải thích SHAP/LIME → (đề xuất) cảnh báo SOC. Dùng để định hướng: đang đọc demo nào thì đang ở bước nào trong sơ đồ này.',
  confusion:`Ma trận nhầm lẫn của XGBoost trên 700.000 flow test (không đổi so với RQ1). Đường chéo sáng = dự đoán đúng. Nhìn CỘT/HÀNG của Infilteration, SlowHTTPTest, SQL Injection để thấy các lớp này bị nhầm đi đâu nhiều nhất — đây là 3 lớp cần đọc kết quả giải thích (SHAP/LIME) cẩn trọng hơn vì model hay sai ở đây.`,
  agreement:`Jaccard, Spearman (toàn bộ 78 feature) và đồng thuận dấu giữa SHAP và LIME theo k, so với đường đứt nét (ngẫu nhiên). Đọc nhanh: cột xanh dương (Jaccard) luôn CAO HƠN đường ngẫu nhiên nhiều lần → hai phương pháp không chọn feature một cách độc lập ngẫu nhiên, nhưng mức trùng tuyệt đối còn thấp (dưới 25%). Đường Spearman không đổi theo k vì tính trên toàn bộ 78 feature, không chỉ Top-k.`,
  signed:`Spearman (toàn bộ 78 feature) giữa SHAP và LIME, tách riêng theo từng lớp tấn công. Thanh dài = hai phương pháp đồng thuận MẠNH cho lớp đó; thanh ngắn (gần 0) = hai phương pháp "nhìn" ra lý do khác nhau nhiều cho lớp đó, nên đọc riêng từng explainer khi gặp các lớp này. KHÔNG có lớp nào bị âm (khác một phiên bản tính sai đã sửa khi chạy lại dự án).`,
  stability:`Phân bố độ ổn định của LIME: chạy lại giải thích 10 lần (10 seed ngẫu nhiên khác nhau) trên CÙNG một flow, đo Jaccard@5 giữa các lần. Cột càng lệch về bên PHẢI (gần 1.0) thì LIME càng ổn định; cột lệch trái nghĩa là Top-5 "nhảy" nhiều giữa các lần chạy dù không đổi gì cả — đây là rủi ro thật khi dùng LIME để ra quyết định mà không chạy kiểm tra nhiều lần. SHAP (TreeSHAP) không có trong hình này vì nó luôn cho kết quả giống tuyệt đối 100% (không có yếu tố ngẫu nhiên).`,
  faithfulness:`Hai đường: Deletion (xoá dần Top-k feature quan trọng nhất, đo xác suất dự đoán GIẢM bao nhiêu) và Insertion (chỉ thêm lại Top-k từ giá trị nền, đo xác suất PHỤC HỒI bao nhiêu). Đường SHAP (xanh dương) nằm TRÊN đường LIME ở cả hai biểu đồ và ở mọi k → Top-k của SHAP "nặng" hơn về mặt quyết định của model so với Top-k của LIME. Đường xám (ngẫu nhiên) luôn ở dưới cùng, xác nhận cả hai phương pháp đều có giá trị giải thích thật.`,
};
seg($('#figTabs'),b=>{const f=b.dataset.f;$('#figImg').src='assets/'+FIG_FILE[f]+'.png';$('#figCaption').innerHTML=`<b>Phân tích:</b> ${FIG_CAPTION[f]}`});
$('#figCaption').innerHTML=`<b>Phân tích:</b> ${FIG_CAPTION.workflow}`;
drawFc();drawQ();drawG();
});
