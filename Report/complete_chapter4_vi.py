"""Complete Chapter 4 using the independently rechecked project artifacts."""
from pathlib import Path
import json,csv,re
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import build_chapter4_vi as base

R=Path(__file__).resolve().parent; A=R/'chapter4_assets'
v=json.loads((A/'verification.json').read_text(encoding='utf-8'))
s=json.loads((A/'supplement.json').read_text(encoding='utf-8'))
pc=json.loads((A/'pcap_recheck.json').read_text(encoding='utf-8'))
tests=json.loads((A/'rq3_test_results.json').read_text(encoding='utf-8'))
assert v['rq1']['confusion_equal_saved'] and all(t['exit_code']==0 for t in tests)
base.main(); d=Document(base.OUTPUT)
for para in d.paragraphs:
    if para.text.startswith('Chương này báo cáo kết quả'):
        para.text=para.text.replace('RQ1 đánh giá phân loại trên CSE-CIC-IDS2018.','RQ1 thử siêu tham số và so sánh Random Forest với XGBoost trên CSE-CIC-IDS2018, sau đó chọn mô hình triển khai.')
d.tables[0].cell(1,1).text='Train 2.800.000 flow, test 700.000 flow, 78 đặc trưng, 15 lớp. Tinh chỉnh Random Forest và XGBoost, so sánh và chọn XGBoost cho các bước sau.'
d.tables[0].cell(1,2).text='Kết quả thử tham số, so sánh hai mô hình và đánh giá mô hình triển khai.'
for row in d.tables[0].rows:
    for cell in row.cells:
        for para in cell.paragraphs:
            for run in para.runs:run.font.size=Pt(11)
def p(t): return base.paragraph(d,t)
def h(t): d.add_heading(t,3)
def section(t): d.add_heading(t,2)
def fmt(x,n=2): return f'{x:,.{n}f}'.replace(',','X').replace('.',',').replace('X','.')
def table(caption,headers,rows,widths=None):
    caption=re.sub(r'^Bảng 4\.\d+[a-z]?\.',f'Bảng 4.{len(d.tables)+1}.',caption)
    c=d.add_paragraph(caption);c.alignment=1;c.paragraph_format.keep_with_next=True
    t=d.add_table(rows=1,cols=len(headers));t.autofit=False
    ws=widths or [6.5/len(headers)]*len(headers)
    for col,w in zip(t.columns,ws):col.width=Inches(w)
    for i,values in enumerate([headers]+list(rows)):
        cells=t.rows[0].cells if i==0 else t.add_row().cells
        for cell,value,w in zip(cells,values,ws):
            cell.width=Inches(w);cell.text=str(value);base.set_cell_border(cell);base.set_cell_padding(cell)
            if i==0:base.set_cell_fill(cell,'DCEAF5')
            for para in cell.paragraphs:
                para.paragraph_format.space_after=Pt(3)
                if i==0:para.paragraph_format.keep_with_next=True
                for run in para.runs:run.font.size=Pt(10);run.bold=i==0
        pr=t.rows[i]._tr.get_or_add_trPr(); pr.append(OxmlElement('w:cantSplit'))
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
def fig(name,caption,width=6.2):
    caption=re.sub(r'^Hình 4\.\d+\.',f'Hình 4.{len(d.inline_shapes)+1}.',caption)
    para=d.add_paragraph();para.alignment=1;para.paragraph_format.keep_with_next=True
    para.add_run().add_picture(str(A/name),width=Inches(width))
    cap=d.add_paragraph(caption);cap.alignment=1
    for run in cap.runs:run.font.size=Pt(11)

section('4.2 Kết quả chuẩn bị và kiểm tra dữ liệu')
p('Dữ liệu được kiểm tra trực tiếp từ hai tệp train_set.parquet và test_set.parquet của dự án. Lần đối chứng ngày 28/10/2026 xác nhận tập train có 2.800.000 dòng, tập test có 700.000 dòng, cùng 78 đặc trưng đầu vào và 15 nhãn. Không phát hiện giá trị NaN hoặc vô hạn trong các cột đặc trưng của hai tệp. Kết quả này xác nhận trạng thái của dữ liệu đã xử lý, không xác nhận lại toàn bộ quy trình làm sạch từ dữ liệu gốc [1].')
p('Benign chiếm 70% ở cả hai tập. Phân bố các lớp tấn công không cân bằng. Trong tập test, SQL Injection chỉ có 17 flow, Brute Force -XSS có 46 flow, trong khi DDOS attack-HOIC có 59.580 flow. Vì vậy, accuracy tổng thể được trình bày cùng macro F1 và kết quả từng lớp. Tên Infilteration được giữ đúng như bộ mã hóa nhãn của dự án để tránh nhầm giữa tên hiển thị và mã lớp.')
fig('class_distribution.png','Hình 4.1. Phân bố 15 lớp trong hai tệp dữ liệu đã kiểm tra. Trục số flow dùng thang logarit.')
h('4.2.1 Trùng lặp giữa tập huấn luyện và tập kiểm tra')
p('Phép đối chiếu băm toàn bộ 78 đặc trưng, không đưa chỉ số dòng và nhãn vào khóa, tìm thấy 194.149 dòng test có vector đặc trưng xuất hiện trong train, tương đương 27,7356% tập test. Con số này khớp kiểm tra đã lưu của RQ2. Đây là số dòng test trùng đặc trưng, không phải số cặp trùng hoặc số mẫu có cùng nhãn. Kết quả trên tập test vì thế chưa đại diện cho một tập đánh giá độc lập hoàn toàn.')
h('4.2.2 Quy ước đặc trưng và phạm vi tái lập')
p('Các cột FIN Flag Cnt, SYN Flag Cnt, RST Flag Cnt, PSH Flag Cnt, ACK Flag Cnt, URG Flag Cnt và ECE Flag Cnt trong train đều có giá trị nhỏ nhất 0 và lớn nhất 1. Ngược lại, bộ trích xuất PCAP có thể ghi nhận nhiều gói mang cùng cờ trong một flow. Trùng tên cột và đủ 78 cột chưa bảo đảm hai nguồn có cùng ý nghĩa thống kê. Trong phạm vi lần đối chứng này, mô hình, dữ liệu và quy tắc chuẩn hóa hiện hành được giữ nguyên. Không tự ép các cột đếm về nhị phân để làm thay đổi kết quả báo cáo.')

section('4.3 Kết quả phát hiện xâm nhập')
p('RQ1 được thực hiện theo trình tự xây dựng mô hình ban đầu, thử các siêu tham số của Random Forest và XGBoost, so sánh kết quả, rồi chọn mô hình để chuyển sang RQ2 và RQ3. Vì vậy, kết quả của mô hình đang chạy phải được đọc cùng quá trình lựa chọn, thay vì trình bày như một thí nghiệm XGBoost riêng lẻ [2, 7].')
h('4.3.1 Thử siêu tham số của hai mô hình')
p('Báo cáo Random Forest gốc ghi nhận mô hình ban đầu có 50 cây, độ sâu tối đa 20, min_samples_split bằng 10 và min_samples_leaf bằng 4. RandomizedSearchCV thử sáu tổ hợp với ba fold, tổng cộng 18 lần fit, chấm theo macro F1. Tập tuning gồm khoảng 400.000 mẫu lấy từ train và bổ sung các mẫu lớp hiếm từ chính train. Theo báo cáo này, test không tham gia tuning. Cấu hình được chọn có 80 cây, độ sâu 28, min_samples_split bằng 5, min_samples_leaf bằng 2, max_features là sqrt và class_weight là balanced_subsample. Macro F1 trung bình cross-validation ghi nhận là 0,8464, không phải F1 trên test [7].')
table('Bảng 4.2. Không gian thử siêu tham số của Random Forest',['Tham số','Giá trị đã thử'],[['n_estimators','30, 50, 80'],['max_depth','12, 20, 28'],['min_samples_split','5, 10'],['min_samples_leaf','2, 4'],['max_features','sqrt'],['class_weight','None hoặc balanced_subsample']],[2.7,3.8])
p('Với XGBoost, bảng kết quả lưu bảy cấu hình kết hợp độ sâu cây và tốc độ học. Mã huấn luyện cuối dùng 100 vòng tăng cường, phương pháp hist và seed 42. Bảng sau được đối chiếu trực tiếp với CSV kết quả quét tham số, không phải chạy lại bảy lượt huấn luyện trong lần biên soạn này.')
with (R.parent/'RQ1_Model_Training_xboost/results/bang_1_ket_qua_quet_tham_so_thuc_te.csv').open(encoding='utf-8-sig') as stream:tuning=list(csv.DictReader(stream))
table('Bảng 4.2. Kết quả quét cấu hình XGBoost đã lưu',['Cấu hình','Thời gian s','Macro P %','Macro F1 %','FNR %'],[[x['Cấu hình'],fmt(float(x['Thời gian (s)'])),fmt(float(x['Test Prec (%) [Sub-1.1]'])),fmt(float(x['Test F1 (%) [Sub-1.1]'])),fmt(float(next(val for key,val in x.items() if key.startswith('FNR'))),4)] for x in tuning],[2.1,1.05,1.1,1.1,1.15])
p('Bảng quét có macro F1 cao nhất 85,95% tại độ sâu 12 và tốc độ học 0,08. Cấu hình độ sâu 8 và tốc độ học 0,10 đạt 85,94%. Tuy nhiên, script huấn luyện cuối và tệp mô hình sử dụng độ sâu 8, tốc độ học 0,08, đạt 85,81%. Các tài liệu cũ mô tả đây là lựa chọn cân bằng, nhưng chưa có quy tắc định lượng đủ rõ để tái lập quyết định chọn cấu hình này thay vì hai cấu hình F1 cao hơn. Vì vậy, báo cáo gọi đây là cấu hình được triển khai, không gọi là cấu hình có F1 cao nhất trong bảng quét. Cột cuối là FNR trên tấn công, không phải FPR trên Benign.')
h('4.3.2 So sánh Random Forest và XGBoost để chọn mô hình')
table('Bảng 4.2. So sánh kết quả được ghi nhận trên tập test',['Chỉ số','RF ban đầu','RF tinh chỉnh','XGBoost triển khai'],[['Accuracy %','86,12','93,17','97,9076'],['Macro precision %','71,17','78,65','90,8358'],['Macro recall %','87,74','86,02','83,9950'],['Macro F1 %','73,17','80,81','85,8058'],['Nguồn đối chứng','Báo cáo RF gốc','Báo cáo RF gốc','Chạy lại đủ 700.000 flow']],[1.85,1.45,1.45,1.75])
p('So với Random Forest tinh chỉnh trong báo cáo gốc, XGBoost triển khai cao hơn khoảng 5,00 điểm phần trăm macro F1 và 12,19 điểm phần trăm macro precision, nhưng thấp hơn khoảng 2,03 điểm phần trăm macro recall. Kết quả này giải thích việc dự án chọn XGBoost cho bước giải thích và triển khai, đồng thời cho thấy có đánh đổi giữa các chỉ số. Không kết luận XGBoost hơn Random Forest ở mọi tiêu chí.')
p('Tệp rf_tuned.pkl và các dự đoán RF gốc chưa có trong workspace hiện tại. Số liệu RF được đối chiếu giữa tài liệu tổng hợp RF và báo cáo so sánh, chưa chạy lại suy luận RF. Bảng quét XGBoost được kiểm tra về nội dung và thứ hạng, còn mô hình XGBoost cuối được chạy lại trên toàn bộ test. Các mức bằng chứng này được tách rõ. Quy trình tuning RF theo báo cáo dùng cross-validation, trong khi mã tuning XGBoost chấm trên test, nên đây chưa phải so sánh hai thuật toán dưới cùng một quy trình lựa chọn tham số.')
p('Mô hình XGBoost đã lưu của RQ1 được nạp lại và dự đoán trên toàn bộ 700.000 flow test. Ma trận nhầm lẫn mới khớp toàn bộ các ô với confusion_matrix_values.csv. Mô hình có 100 vòng tăng cường và 1.500 cây trong cấu hình đa lớp, không phải tổng cộng 100 cây. Mã băm của tệp mô hình bắt đầu bằng 52eb5a671ee82109 [1, 2].')
q=v['rq1']
table('Bảng 4.2. Chỉ số phân loại tính lại trên toàn bộ tập test',['Chỉ số','Kết quả'],[
('Accuracy',fmt(q['accuracy']*100,4)+'%'),('Macro precision',fmt(q['macro']['precision']*100,4)+'%'),('Macro recall',fmt(q['macro']['recall']*100,4)+'%'),('Macro F1',fmt(q['macro']['f1-score']*100,4)+'%'),('FPR trên Benign',fmt(q['FPR']*100,4)+'%'),('FNR trên các lớp tấn công',fmt(q['FNR']*100,4)+'%')],[3.7,2.8])
h('4.3.3 Kết quả theo từng lớp của mô hình triển khai')
rows=[]
for label,metric in q['metrics'].items():
    if label in ['accuracy','macro avg','weighted avg']:continue
    rows.append([label,fmt(metric['support'],0),fmt(metric['precision']*100),fmt(metric['recall']*100),fmt(metric['f1-score']*100)])
table('Bảng 4.3. Kết quả phân loại theo nhãn thật',['Lớp','Số flow','Precision %','Recall %','F1 %'],rows,[2.55,.75,1.1,1.05,1.05])
p('Hulk đạt recall 99,9974% trong tập test, nhưng Infilteration chỉ đạt 15,9832% và SlowHTTPTest đạt 37,6369%. Sự chênh lệch này cho thấy accuracy 97,9076% không phản ánh đồng đều năng lực nhận diện 15 lớp. Kết quả rất cao của Hulk trong miền dữ liệu 2018 cũng không chứng minh mô hình phân biệt được Hulk với traffic duyệt web ngoài miền huấn luyện.')
fig('confusion_matrix.png','Hình 4.2. Ma trận nhầm lẫn được chuẩn hóa theo nhãn thật. Số trong ô là phần trăm, chỉ ghi ô từ 1% trở lên.')
h('4.3.4 Tách báo nhầm và bỏ sót')
table('Bảng 4.4. Đối soát nhị phân, quy ước tấn công là lớp dương',['Nhãn thật','Dự đoán Benign','Dự đoán tấn công'],[['Benign',fmt(q['TN'],0),fmt(q['FP'],0)],['Tấn công',fmt(q['FN'],0),fmt(q['TP'],0)]],[2.2,2.15,2.15])
p('Có 1.139 flow Benign bị dự đoán thành một lớp tấn công trên tổng 490.000 flow Benign. FPR được tính bằng 1.139 chia 490.000, đạt 0,2324%. Có 12.071 flow tấn công bị dự đoán thành Benign trên tổng 210.000 flow tấn công, cho FNR 5,7481%. Nhầm giữa hai lớp tấn công làm giảm kết quả phân loại đa lớp nhưng không được cộng vào FPR trên Benign.')
p('Mã quét siêu tham số XGBoost sử dụng macro F1 của chính tập test để xếp hạng cấu hình. Cùng với trùng lặp đặc trưng giữa train và test, điều này giới hạn cách diễn giải kết quả. Các chỉ số trên mô tả mô hình đã triển khai trong quy trình hiện có, chưa phải ước lượng khách quan trên một tập ngoài hoàn toàn chưa tham gia lựa chọn mô hình. FPR chính xác của Random Forest chưa được đối soát lại bằng dự đoán hoặc ma trận gốc nên không dùng để kết luận chênh lệch báo nhầm giữa hai mô hình.')

section('4.4 Kết quả đánh giá SHAP và LIME')
p('Tập đánh giá giải thích gồm 1.339 flow cố định của RQ2. Đối chiếu dự đoán mới xác nhận toàn bộ tập này thuộc nhóm được mô hình dự đoán đúng. Do đó, các kết quả ở mục này phản ánh chất lượng giải thích trên tập mẫu đó, không đại diện cho mọi dự đoán sai hoặc mọi flow ngoài miền. SHAP và LIME giải thích cùng mô hình đã dùng ở mục 4.3 [1, 3].')
h('4.4.1 Tái lập đóng góp SHAP và hệ số LIME')
p('SHAP được tính lại cho đủ 1.339 flow với TreeExplainer. Sai khác tuyệt đối lớn nhất so với đóng góp đã lưu là 4,72 × 10⁻⁷. Sai số cộng tính lớn nhất giữa tổng đóng góp cùng giá trị nền và điểm thô của mô hình là 1,335 × 10⁻⁵. Kiểm tra cộng tính xác nhận cách phân rã đầu ra trong phạm vi sai số số học. Nó không chứng minh nhãn dự đoán đúng về mặt an ninh.')
p('LIME được chạy lại với 1.000 mẫu nhiễu, kernel width 3,312, nền 2.000 mẫu train chọn bằng seed 42, giữ đủ 78 đặc trưng và không chia khoảng liên tục. Seed từng flow được khôi phục theo mã RQ2. Sai khác lớn nhất của hệ số so với kết quả đã lưu nhỏ hơn 10⁻¹⁶, còn sai khác R² nhỏ hơn 1,12 × 10⁻¹⁶. Kết quả cho thấy thí nghiệm này tái lập được với cấu hình đã khóa, không có nghĩa LIME luôn ổn định khi đổi seed hoặc đổi nguồn dữ liệu.')
table('Bảng 4.5. Kết quả kiểm tra giải thích trên tập 1.339 flow',['Chỉ tiêu','Giá trị'],[
('R² LIME trung bình',fmt(v['rq2']['lime_mean_r2'],4)),('R² LIME trung vị',fmt(v['rq2']['lime_median_r2'],4)),('Số flow đạt R² từ 0,3',f"{v['rq2']['lime_pass_count']} / 1.339"),('Tỷ lệ đạt ngưỡng R²',fmt(v['rq2']['lime_pass_fraction']*100,2)+'%'),('Jaccard top-5 SHAP với LIME',fmt(v['rq2']['jaccard5_rerun_mean'],4))],[4,2.5])
fig('lime_agreement.png','Hình 4.3. Phân bố R² LIME và mức giao nhau của tập đặc trưng SHAP, LIME. R² và Jaccard đo hai khía cạnh khác nhau.')
h('4.4.2 Mức đồng thuận và độ ổn định')
p('Jaccard top-5 trung bình bằng 0,1414, cho thấy hai phương pháp thường chọn các tập đặc trưng khác nhau. Không thể kết luận phương pháp nào đúng chỉ từ mức đồng thuận này. SHAP phân rã điểm thô của mô hình, còn LIME khớp mô hình cục bộ trên các điểm nhiễu với trọng số khoảng cách. Giá trị và dấu đóng góp phải được đọc theo lớp đang giải thích, không so trực tiếp như hai tỷ lệ xác suất.')
with (R.parent/'RQ2/runs/20261009/gd7_agreement/rq2_1_agreement_overall.csv').open(encoding='utf-8-sig') as stream:ag=next(x for x in csv.DictReader(stream) if x['k']=='5')
table('Bảng 4.5. Các chỉ số đồng thuận tại top-5 và trên toàn bộ đặc trưng',['Chỉ số','Giá trị','Cách đọc'],[
('Jaccard top-5',fmt(float(ag['jaccard_mean']),4),'Mức giao nhau giữa hai tập 5 đặc trưng.'),
('Spearman trên hợp top-5',fmt(float(ag['spearman_topk_union_mean']),4),'Tương quan thứ hạng trên các đặc trưng thuộc ít nhất một top-5.'),
('Kendall trên hợp top-5',fmt(float(ag['kendall_tau_topk_union_mean']),4),'Mức nhất quán của các cặp thứ hạng trong tập hợp trên.'),
('Spearman toàn bộ 78',fmt(float(ag['spearman_full78_mean']),4),'Tương quan thứ hạng khi xét tất cả đặc trưng.'),
('Kendall toàn bộ 78',fmt(float(ag['kendall_full78_mean']),4),'Đồng thuận thứ hạng theo cặp trên tất cả đặc trưng.'),
('RBO top-5',fmt(float(ag['rbo_mean']),4),'Mức trùng thứ hạng, nhấn mạnh vị trí đầu danh sách.'),
('Đồng thuận dấu top-5',fmt(float(ag['sign_agreement_mean']),4),'Tỷ lệ cùng dấu trên phần giao, không phải trên toàn bộ 78 cột.'),
('Jaccard theo nhóm',fmt(float(ag['jaccard_group_mean']),4),'Đồng thuận sau khi gom đặc trưng cùng nhóm thống kê.')],[2.25,.8,3.45])
p('Jaccard top-5 có khoảng tin cậy bootstrap 95% từ 0,1368 đến 0,1460 theo kết quả đã lưu. Đường cơ sở ngẫu nhiên đạt trung bình 0,0359, thấp hơn mức quan sát khoảng 3,94 lần. Như vậy, đồng thuận cao hơn ngẫu nhiên nhưng vẫn thấp về giá trị tuyệt đối. Spearman trên hợp top-5 âm trong khi tương quan trên toàn bộ 78 đặc trưng dương nhẹ. Hai số này dùng hai tập đặc trưng khác nhau nên không mâu thuẫn. Các trung bình được tính lại từ bảng từng flow, còn khoảng tin cậy và mô phỏng ngẫu nhiên được đối chiếu với kết quả RQ2 đã lưu.')
p('Tỷ lệ LIME đạt R² từ 0,3 cũng khác nhau giữa các lớp. Trong tập mẫu đã lưu, Benign và Slowloris chỉ có 23 trong 100 flow đạt ngưỡng, trong khi Hulk có 100 trong 100 flow đạt. Vì vậy, tỷ lệ chung 85,96% không có nghĩa mọi lớp đều có chất lượng giải thích như nhau. R² đo mức khớp của mô hình cục bộ với đầu ra mô hình gốc trên các mẫu nhiễu, không đo độ chính xác phát hiện tấn công.')
revision=json.loads((A/'revision_rq2/recheck.json').read_text(encoding='utf-8'))
st=json.loads((A/'revision_rq2/gd9_stability_robustness/rq2_2_stability_summary.json').read_text(encoding='utf-8'))
p(f"Lần kiểm tra bổ sung chạy lại LIME trên đủ 1.339 flow với 10 seed. Jaccard top-5 trung bình giữa các cặp seed đạt {fmt(st['lime_mean_pairwise_jaccard5'],4)}, trung vị {fmt(st['lime_median_pairwise_jaccard5'],4)}. SHAP giữ nguyên top-5 trên {fmt(st['shap_jaccard5_rerun']*100,2)}% flow khi tính lại cùng mô hình và đầu vào. Khả năng tái lập với seed cố định khác với độ ổn định khi thay seed. Kết quả cho thấy LIME có biến động do lấy mẫu dù chạy lại đúng seed vẫn tái lập.")
h('4.4.3 Độ ổn định khi thay đổi đầu vào và số mẫu LIME')
with (A/'revision_rq2/gd9_stability_robustness/rq2_2_noise_robustness.csv').open(encoding='utf-8-sig') as stream:noise=list(csv.DictReader(stream))
table('Bảng 4.5. Jaccard top-5 khi thêm nhiễu đầu vào',['Mức nhiễu theo độ lệch chuẩn train','SHAP','LIME'],[[fmt(float(x['sigma_fraction'])*100,0)+'%',fmt(float(x['shap_mean_jaccard5']),4),fmt(float(x['lime_mean_jaccard5']),4)] for x in noise],[3.9,1.3,1.3])
p('Phép thử được chạy lại trên 1.339 flow với nhiễu Gaussian ở mức 1%, 5% và 10% độ lệch chuẩn từng đặc trưng, sau đó cắt về khoảng giá trị train. Cả hai phương pháp vẫn giải thích lớp dự đoán ban đầu để đo thay đổi của giải thích. Mức giao nhau top-5 giảm khi nhiễu tăng, đặc biệt với LIME. SHAP tái lập khi đầu vào giữ nguyên không có nghĩa SHAP bất biến khi đầu vào thay đổi. Vector nhiễu cũng chưa chắc tương ứng với một flow mạng hợp lệ, nên phép thử này đo độ nhạy của giải thích chứ không đo khả năng chống tấn công né tránh.')
fig('revision_rq2/gd9_stability_robustness/figures/noise_robustness.png','Hình 4.4. Mức giao nhau của top-5 khi thay đổi đầu vào. Mức nhiễu tính theo độ lệch chuẩn đặc trưng trên train.',5.5)
with (A/'revision_rq2/gd9_stability_robustness/rq2_2_lime_convergence.csv').open(encoding='utf-8-sig') as stream:conv=list(csv.DictReader(stream))
table('Bảng 4.5. R² LIME khi thay số mẫu nhiễu trên 150 flow kiểm tra',['Số mẫu nhiễu','R² trung vị','R² trung bình','Thời gian lượt chạy s'],[[x['num_samples'],fmt(float(x['median_r2']),4),fmt(float(x['mean_r2']),4),fmt(float(x['total_time_sec']),2)] for x in conv],[1.5,1.6,1.6,1.8])
p('Tăng số mẫu từ 500 lên 10.000 không làm R² tăng trong phép thử đã khóa kernel và cách sinh nhiễu này. Thêm nhiều mẫu chỉ có ích khi các mẫu mô tả được vùng cần giải thích. Không thể chữa mọi trường hợp LIME yếu bằng cách tăng số mẫu hoặc tự tăng kernel. Kết quả trên 150 flow kiểm tra cũng không được thay thế cho kết quả trên tập 1.339 flow có cách lấy mẫu khác.')
h('4.4.4 Độ trung thực theo phép thay thế đặc trưng')
p('Phép thử thay thế lần lượt từ 1 đến 10 đặc trưng quan trọng được chạy lại trên đủ 1.339 flow. Ba giá trị nền gồm trung vị toàn train, trung bình toàn train và trung vị Benign. Đối chứng chọn đặc trưng ngẫu nhiên dùng seed 42. Sai khác lớn nhất của các giá trị tổng hợp so với bảng cũ nhỏ hơn 3 × 10⁻⁸.')
with (A/'faithfulness_rerun.csv').open(encoding='utf-8') as stream:fr=list(csv.DictReader(stream))
names={'global_median':'Trung vị train','global_mean':'Trung bình train','benign_median':'Trung vị Benign'}
table('Bảng 4.6. Mức giảm xác suất trung bình khi thay thế đặc trưng',['Giá trị nền','SHAP','LIME','Ngẫu nhiên'],[[names[b]]+[fmt(float(next(x for x in fr if x['baseline']==b and x['method']==m)['comprehensiveness_auc']),4) for m in ['SHAP','LIME','Random']] for b in names],[2.7,1.25,1.25,1.3])
fig('faithfulness.png','Hình 4.4. Đối chứng thay thế đặc trưng với ba giá trị nền. Trục tung là mức giảm xác suất trung bình theo k từ 1 đến 10.')
p('SHAP tạo mức giảm xác suất lớn hơn LIME và đối chứng ngẫu nhiên ở cả ba nền trong phép thử này. Điều đó hỗ trợ nhận định rằng nhóm đặc trưng SHAP chọn tác động mạnh hơn đến đầu ra mô hình dưới phép thay thế đã định nghĩa. Cột được mã nguồn đặt tên AUC thực tế tính trung bình các giá trị tại 10 mức k, không phải ROC-AUC. Thay thế các cột riêng lẻ cũng có thể tạo vector không tương ứng với flow mạng hợp lệ, nên kết quả không được diễn giải như tác động nhân quả của một cuộc tấn công.')
table('Bảng 4.6. Xác suất lớp được phục hồi khi chỉ giữ các đặc trưng đầu',['Giá trị nền','SHAP','LIME','Ngẫu nhiên'],[[names[b]]+[fmt(float(next(x for x in fr if x['baseline']==b and x['method']==m)['sufficiency_auc']),4) for m in ['SHAP','LIME','Random']] for b in names],[2.7,1.25,1.25,1.3])
p('Phép chèn đặc trưng bắt đầu từ vector nền rồi khôi phục lần lượt các đặc trưng quan trọng. Giá trị trong bảng là xác suất lớp được phục hồi, trung bình theo k từ 1 đến 10, nên giá trị lớn hơn thể hiện phục hồi đầu ra tốt hơn trong cách định nghĩa của dự án. Đây không phải độ chênh xác suất cần tối thiểu hóa như một số định nghĩa sufficiency khác. Kết quả phụ thuộc giá trị nền và phải đọc cùng giới hạn vector thay thế có thể không hợp lệ.')
p('Đối chiếu thêm bảng kiểm định đã lưu tại k bằng 5 cho thấy SHAP tạo mức giảm xác suất lớn hơn LIME trên khoảng 77,97% đến 79,99% flow tùy nền. Kiểm định Wilcoxon ghép cặp có p nhỏ hơn 10⁻¹⁴⁰ trong cả ba trường hợp. Mức khác biệt thống kê áp dụng cho tập mẫu và phép thay thế đang xét, không chứng minh ưu thế trên mọi dữ liệu hoặc quan hệ nhân quả. Các phép kiểm định này được đọc từ kết quả RQ2 gốc, còn đường thay thế và chèn đặc trưng đã được tính lại trong lần đối chứng.')
h('4.4.5 Cách đọc và giới hạn giải thích')
p('SHAP dương làm tăng điểm thô của lớp đang xét so với nền, SHAP âm làm giảm điểm đó. Giá trị 5,86 không có nghĩa là tăng xác suất 5,86% và không chứng minh đặc trưng là dấu hiệu tấn công. LIME chỉ được trình bày như giải thích cục bộ khi vùng mẫu nhiễu có đủ thông tin. Một R² cao trên vùng mẫu suy biến vẫn có thể gây hiểu nhầm. Vì thế, RQ3 kiểm tra thêm cỡ mẫu hữu hiệu và trạng thái hệ số trước khi cho người dùng đọc kết quả.')
p('Tập phân tích lỗi bổ sung của RQ2 có 151 flow dự đoán sai. Kết quả đã lưu cho Jaccard top-5 trung bình 0,1611, cao hơn mức 0,1414 trên tập dự đoán đúng. Điều này minh họa rằng đồng thuận giữa SHAP và LIME không chứng nhận dự đoán đúng. Phân tích này được đối chiếu từ báo cáo lỗi gốc, không chạy lại giải thích của 151 flow trong lần sửa. Không suy ra khác biệt thống kê giữa hai nhóm có cách lấy mẫu và phân bố lớp khác nhau.')

section('4.5 Kết quả triển khai nguyên mẫu IDS')
p('Nguyên mẫu triển khai chuỗi xử lý từ dữ liệu flow đến dự đoán, lưu kết quả và giải thích. Mô hình RQ1 được giữ nguyên. Tầng chuẩn hóa kiểm tra thứ tự 78 đặc trưng trước khi gọi mô hình. FastAPI cung cấp dịch vụ dự đoán và truy vấn. SQLite lưu lịch sử flow, dự đoán, cảnh báo và thông tin giải thích. Streamlit hiển thị kết quả và gửi yêu cầu điều khiển [4].')
table('Bảng 4.7. Các đường dữ liệu và chức năng đã kiểm tra',['Đường xử lý','Chức năng','Bằng chứng lần chạy lại'],[
('CSV','Nhận dòng đặc trưng, chuẩn hóa và gửi dự đoán.','Stage14 kiểm tra tải CSV, chọn lượt và không gửi trùng khi làm mới.'),
('PCAP','Trích gói thành flow, chuyển đơn vị và đưa vào cùng mô hình.','Stage14 kiểm tra qua UI. Stage21 phát lại hai PCAP và đối soát gói.'),
('Realtime','Capture ghi CSV, feeder theo dõi và gọi API.','Kiểm thử lifecycle, feeder và nhật ký Wi-Fi 20 phút được đối soát riêng.'),
('Giải thích','SHAP chạy nền cho cảnh báo. LIME chạy khi được yêu cầu.','Stage14 kiểm tra SHAP bất đồng bộ và nút LIME. Stage15 kiểm tra suy biến.'),
('Start và Stop','API sở hữu trạng thái, giám sát worker và chặn phiên trùng.','Stage36 dùng tiến trình thật với NIC giả lập. Stage37 kiểm tra quyền và UI.')],[1,2.6,2.9])
h('4.5.1 Thông tin hiển thị và hỗ trợ đọc flow')
p('Dashboard hiển thị nguồn dữ liệu, lượt xử lý, thời gian, địa chỉ nguồn và đích khi có, nhãn dự đoán, xác suất lớp được chọn và trạng thái giải thích. Khi chọn một flow, người dùng xem phân bố xác suất các lớp, SHAP, LIME, đặc trưng đầu vào và thông tin đối chứng. Bộ lọc địa chỉ nguồn, khoảng thời gian, phân trang và giữ lựa chọn khi làm mới đã qua kiểm thử AppTest. Đây là kiểm thử giao diện bằng chương trình, chưa thay thế đánh giá mức dễ sử dụng với người dùng độc lập.')
p('Nhánh cảnh báo liên quan đặc trưng môi trường là lớp thông tin bổ sung. Cờ này không thay đổi nhãn mô hình và không xác nhận một cảnh báo là báo nhầm. Khi nguồn CSV không có metadata IP, hệ thống phải thể hiện thiếu thông tin thay vì tự suy ra IP từ vector đặc trưng. Các giá trị xác suất mô hình cũng không được trình bày như xác suất đã xác minh có tấn công.')
h('4.5.2 Phạm vi của hệ thống')
p('Hệ thống là nguyên mẫu IDS dựa trên đặc trưng flow mạng. Việc chạy cảm biến trên máy cá nhân không biến hệ thống thành EDR, vì dữ liệu đang xử lý không phải nhật ký tiến trình, tệp hoặc hành vi hệ điều hành. Hệ thống có thể cung cấp cảnh báo cho hoạt động giám sát của SOC, nhưng chưa phải nền tảng SOC hoặc SIEM đầy đủ. Mô hình hiện tại dự đoán theo từng flow và chưa mô hình hóa đầy đủ quan hệ giữa nhiều kết nối trong một chiến dịch tấn công.')

section('4.6 Kiểm thử hệ thống và hiệu năng vận hành')
p('Kiểm thử RQ3 được tổ chức theo ba nguồn CSV, PCAP và realtime, sau đó kiểm tra các tình huống lỗi và quản lý tiến trình. Các phép thử dùng cơ sở dữ liệu và dịch vụ cô lập, không reset lịch sử đang sử dụng. Lần kiểm tra bổ sung có bắt Wi-Fi thật trong 30 giây. Lượt ngắn này được tách khỏi nhật ký 20 phút trước đó và không dùng để kết luận ổn định dài hạn [1, 4].')
table('Bảng 4.8. Kiểm thử hồi quy thực hiện ngày 28/10/2026',['Nhóm kiểm thử','Phạm vi','Kết quả'],[
('Stage26','Vòng đời flow và đối soát gói bằng dữ liệu tổng hợp.','22 kiểm thử đạt'),('Stage27','Feeder, xác nhận nhận dữ liệu, checkpoint và giới hạn hàng đợi.','8 kiểm thử đạt'),('Stage29','Giới hạn buffer và xử lý cấu hình không hợp lệ.','6 kiểm thử đạt'),('Stage15','LIME bình thường, suy biến, hệ số bằng 0 và tái lập đồng thời.','Các xác nhận đạt'),('Stage14','API với mô hình thật, CSV, PCAP và Streamlit AppTest.','Các xác nhận đạt'),('Stage36','Supervisor và tiến trình worker với NIC giả lập.','7 kiểm thử đạt'),('Stage37','Quyền điều khiển, nút bắt, dừng và làm mới UI.','5 kiểm thử đạt')],[1.05,4.05,1.4])
h('4.6.1 Kiểm thử nhập CSV và phát lại PCAP')
p('Đường CSV được kiểm tra qua Dashboard và feeder. Stage14 xác nhận tải CSV tạo dự đoán, gắn đúng lượt, giữ metadata và không gửi lại các dòng chỉ vì làm mới giao diện. Kiểm thử feeder bổ sung xác nhận xử lý phản hồi không hợp lệ, checkpoint và yêu cầu lặp. Dữ liệu này là đầu vào kiểm thử chức năng, không phải tập mới dùng để tính accuracy hoặc FPR.')
p('Đường PCAP được kiểm tra cả thao tác nhập qua Dashboard và phát lại độc lập hai tệp gốc. Kết quả project-v3 cho test.pcapng có 511 gói và 38 flow, tesst2.pcapng có 637 gói và 61 flow. Hai lần trích xuất cùng cấu hình tạo CSV giống nhau theo byte. Mỗi flow tiếp tục đi qua chuẩn hóa, dự đoán và giải thích. Phân bố nhãn cùng ca LIME không đạt được trình bày riêng ở mục 4.7 để không đánh đồng kiểm thử pipeline với đánh giá độ chính xác.')
h('4.6.2 Kiểm thử realtime mới bằng Wi-Fi thật')
rt=json.loads((A/'realtime_revision_20261028.json').read_text(encoding='utf-8'))
assert rt['status']=='passed' and rt['isolated_api_stopped']
table('Bảng 4.8. Kiểm thử realtime ngày 28/10/2026',['Nội dung','Kết quả'],[
('Thời gian ở trạng thái đang bắt',fmt(rt['running_seconds'],3)+' giây'),('Thời gian dừng và xử lý nốt',fmt(rt['stop_drain_seconds'],3)+' giây'),('Gói đã nhận và xuất',str(rt['packet_counters']['accepted_packets'])),('Flow CSV, API và feeder xác nhận',str(rt['api_flows'])),('SHAP đã xử lý, bị bỏ',f"{rt['queue']['n_processed']} đã xử lý, {rt['queue']['n_dropped']} bị bỏ"),('Đỉnh gói trong buffer',str(rt['packet_counters']['peak_buffered_packets'])),('Start, Stop và làm mới qua AppTest','Đạt'),('API và worker thử nghiệm','Đã dừng')],[3.8,2.7])
p('Phép thử dùng card Wi-Fi thật, API và mô hình thật. Nút Bắt đầu, Dừng và làm mới được thao tác bằng Streamlit AppTest, không phải kiểm tra thủ công trên trình duyệt. Bộ đếm xác nhận 2.645 gói được chấp nhận và xuất, 70 flow xuất hiện trong CSV và API. Ba tác vụ SHAP được xử lý, không có tác vụ bị bỏ và không chạm cap. Kết quả xác nhận đường realtime hoạt động trong lượt ngắn đã quan sát, chưa đo FPR và chưa chứng nhận tải cao.')
p('Trong 30 giây đang bắt, nhật ký mới ghi nhận bảy dòng đã được feeder xác nhận. Khi dừng, hệ thống xuất các flow còn mở rồi feeder xử lý nốt, làm tổng số tăng lên 70. Điều này giải thích vì sao người dùng có thể thấy ít flow khi vừa bật capture dù vẫn đang lướt web. Hệ thống dự đoán khi có flow được xuất, không dự đoán ngay sau từng gói tin.')
h('4.6.3 Đối soát lượt Wi-Fi 20 phút đã lưu')
live=s['historical_live']
p('Nhật ký live_20min_ht3_retry_20261018.json ghi nhận lượt Wi-Fi ngày 18/10/2026. Quá trình capture chạy 1.202,61 giây, với cap thử nghiệm 50.000 gói đang lưu trong buffer và 64 MiB byte gói. Đây là phân tích lại nhật ký của lượt chạy trước, không phải kết quả bắt mạng mới ngày 28/10/2026. Cấu hình mặc định hiện hành trong mã lifecycle là 80.000 gói và 96 MiB. Không dùng nhật ký 50.000 gói để tuyên bố đã nghiệm thu cấu hình mặc định mới.')
table('Bảng 4.9. Đối soát số lượng trong lượt Wi-Fi đã lưu',['Đại lượng','Kết quả'],[
('Gói được capture chấp nhận',fmt(live['accepted_packets'],0)),('Gói đã xuất và tổng gói trong CSV',fmt(live['exported_packets'],0)),('Flow CSV và flow API',fmt(live['api_flows'],0)),('Tác vụ SHAP đã xử lý',str(live['queue']['n_processed'])),('Tác vụ SHAP bị bỏ',str(live['queue']['n_dropped'])),('Đỉnh buffer gói',f"{fmt(live['buffer_counters']['peak_buffered_packets'],0)} / 50.000"),('Đỉnh số flow mở',str(live['buffer_counters']['peak_open_flows']))],[4,2.5])
fig('live_timeline.png','Hình 4.5. Flow đã vào API và RSS theo các mẫu nhật ký ngày 18/10/2026. Đồ thị không phải phép đo realtime mới.')
p('Có 176.425 gói được chấp nhận và xuất ra, tương ứng 1.225 flow trong CSV và API. Kết quả này xác nhận cân bằng bộ đếm bên trong pipeline cho lượt đã ghi nhận, không chứng minh không mất gói trước khi ứng dụng nhận từ card mạng. Đỉnh buffer đạt 48.495 gói, tương đương 96,99% cap thử nghiệm, nên dư địa chỉ còn 3,01%. Việc hoàn thành một lượt 20 phút không đủ để kết luận ổn định khi tải cao hoặc chạy nhiều giờ.')
p('RSS lớn nhất trong các mẫu nhật ký lần lượt là 463,05 MiB cho API, 522,93 MiB cho capture và 97,66 MiB cho feeder. Đây là cực đại quan sát theo chu kỳ lấy mẫu, không phải cực đại liên tục và không nên cộng thành một đỉnh RAM đồng thời. CPU tích lũy tại mẫu cuối lần lượt là 1.300,67 giây, 124,55 giây và 7,80 giây. CPU tích lũy không phải phần trăm tải CPU.')
h('4.6.4 Độ trễ và giới hạn hàng đợi')
p('Độ trễ từ gói tin đến cảnh báo gồm thời gian chờ kết thúc flow, xuất CSV, chu kỳ feeder, xử lý API và chờ SHAP. Trong mã lifecycle hiện hành, ngưỡng tuổi flow mặc định là 90 giây và idle timeout là 240 giây. Đây là tham số quản lý vòng đời, không phải cam kết mọi cảnh báo xuất hiện sau đúng khoảng thời gian đó. Thời gian mô hình suy luận theo lô cũng không thể thay thế độ trễ đầu cuối theo từng flow.')
p(f"Trong lần đối chứng, dự đoán toàn bộ 700.000 flow mất {fmt(q['inference_seconds'],2)} giây trong vòng đo có gọi mô hình theo lô. SHAP cho 1.339 flow mất {fmt(v['rq2']['shap_full_rerun_seconds'],3)} giây, còn vòng chạy lại LIME mất {fmt(v['rq2']['lime_full_rerun_seconds'],2)} giây và có cả thao tác đối chiếu kết quả. Các thời gian này phụ thuộc máy và phạm vi đo, không phải phép so sánh tốc độ thuần nhất hoặc thông lượng của API.")
p('Hàng đợi SHAP được giới hạn 200 tác vụ chờ. Khi đầy, tác vụ giải thích mới có thể bị bỏ trong khi dự đoán và cảnh báo vẫn được giữ. Cap buffer capture là giới hạn khác, áp dụng cho gói chưa xuất và bộ nhớ gói. Bỏ hai giới hạn này có thể làm tăng bộ nhớ và độ trễ không kiểm soát. Báo cáo chưa có phân bố độ trễ đầu cuối p50, p95 và p99 dưới tải có kiểm soát, nên chưa đưa ra cam kết phục vụ realtime ở mức tải cụ thể.')

section('4.7 Phân tích trường hợp trên traffic thực tế')
p('Hai tệp test.pcapng và tesst2.pcapng được trích xuất lại bằng project-v2 và project-v3 trong thư mục tạm. Mỗi cấu hình được chạy lặp để so sánh CSV chính xác theo byte. Sau đó, các flow được chuẩn hóa và đưa vào mô hình, SHAP và LIME trong bộ nhớ. Phép thử không gửi dữ liệu vào cơ sở dữ liệu đang sử dụng [1].')
table('Bảng 4.10. Kết quả phát lại PCAP với project-v3',['Tệp','Gói đối soát','Flow','Benign','Hulk'],[[r['file'],r['supported_packet_oracle'],r['candidate']['flow_count'],r['candidate']['labels'].get('Benign',0),r['candidate']['labels'].get('DoS attacks-Hulk',0)] for r in pc['runs']],[2.2,1.2,1,1,1.1])
p('Cả hai tệp tạo CSV giống nhau khi trích xuất lặp với cùng phiên bản. Tổng gói của các flow khớp bộ đếm gói được hỗ trợ trong PCAP. Project-v3 cho 38 flow ở test.pcapng và 61 flow ở tesst2.pcapng, trong khi project-v2 lần lượt cho 33 và 59 flow. Thay đổi quy tắc đóng flow có thể thay đổi số flow dù tổng gói giữ nguyên. Không được so số lượng cảnh báo giữa hai phiên bản như độ chính xác nếu chưa ghép flow và có nhãn thật độc lập.')
h('4.7.1 Một flow được dự đoán là Hulk')
case=next(r for r in pc['runs'] if r['file']=='tesst2.pcapng')['candidate']['alert_xai'][0]
p(f"Flow có chỉ số 0 trong kết quả project-v3 của tesst2.pcapng được dự đoán DoS attacks-Hulk với xác suất {fmt(case['probability']*100,2)}%. FIN Flag Cnt có giá trị 2 và đóng góp SHAP dương khoảng 5,8652. Fwd Pkt Len Max có giá trị 78 và đóng góp khoảng 2,9739. Dst Port có giá trị 443 và đóng góp âm khoảng 0,9221 về độ lớn. Các đóng góp này giải thích vì sao mô hình nghiêng về Hulk, không xác nhận hoạt động mạng là tấn công.")
fig('pcap_shap.png','Hình 4.6. Năm đặc trưng SHAP của flow được chọn từ tesst2.pcapng, trích xuất project-v3.')
table('Bảng 4.11. Ý nghĩa các đặc trưng trong trường hợp đang xét',['Đặc trưng','Cách hiểu'],[
('FIN Flag Cnt','Số gói có cờ FIN theo bộ trích xuất của flow. FIN liên quan kết thúc chiều truyền TCP, không tự nó là dấu hiệu tấn công.'),('Fwd Pkt Len Max','Độ dài gói lớn nhất theo chiều forward theo quy ước bộ trích xuất. Phải giữ nhất quán cách đo độ dài khi so train với PCAP.'),('Dst Port','Cổng đích của flow. Cổng 443 không đủ để xác nhận hay loại trừ tấn công.'),('Tot Fwd Pkts','Tổng số gói theo chiều forward của flow.'),('Init Fwd Win Byts','Giá trị cửa sổ TCP ban đầu theo chiều forward theo quy ước trích xuất.')],[1.7,4.8])
p('Kiểm tra trực tiếp train trong vùng FIN Flag Cnt từ 1, Fwd Pkt Len Max từ 66 và Fwd Seg Size Min dưới 32 tìm thấy 445 dòng, tất cả mang nhãn Hulk. Đây là bằng chứng về phân bố nhãn trong một vùng đặc trưng cụ thể của train. Nó hỗ trợ giả thuyết rằng mô hình dựa vào mẫu liên quan đóng kết nối và môi trường thu thập, nhưng không chứng minh riêng FIN gây ra mọi cảnh báo Hulk. Các ngưỡng này dùng để đối chứng vùng đã khảo sát, không phải quy tắc xác định tấn công mới.')
h('4.7.2 Vì sao LIME chưa giải thích được flow này')
p('LIME tìm hiểu quyết định của XGBoost bằng cách tạo nhiều vector đặc trưng giả lập gần flow đang xét, rồi cho XGBoost dự đoán các vector đó. Đây là dữ liệu số được sinh trong phép tính, không phải gói tin được gửi ra mạng. LIME quan sát khi đặc trưng thay đổi thì dự đoán thay đổi ra sao, từ đó xây dựng một mô hình đơn giản để giải thích quyết định tại flow gốc.')
p('Các mẫu giả lập không được coi trọng như nhau. Mẫu gần flow gốc có trọng số lớn, mẫu xa có trọng số nhỏ. Với flow đang xét, chương trình đã tạo 1.000 mẫu, nhưng gần như toàn bộ ảnh hưởng tập trung vào mẫu gốc. Các mẫu còn lại có trọng số quá nhỏ nên hầu như không đóng góp vào phép khớp mô hình. Có nhiều mẫu được tạo ra nhưng vẫn thiếu thông tin so sánh hữu ích quanh flow này.')
p('Có thể hiểu bằng việc muốn biết tăng một đặc trưng sẽ làm dự đoán tăng hay giảm. Nếu chỉ một điểm dữ liệu thực sự có ảnh hưởng, LIME không có đủ những điểm lân cận để quan sát sự thay đổi đó. Chỉ số cỡ mẫu hữu hiệu bằng 1 diễn tả tình trạng này. Trong ví dụ, dù 1.000 trọng số đều chưa bằng 0 về mặt số học, trọng số lớn nhất ngoài mẫu gốc chỉ khoảng 1,80 × 10⁻⁸⁹, gần như không có tác dụng.')
p('Vì vậy, hệ thống hiển thị trạng thái chưa đủ mẫu lân cận hữu ích và không đưa ra danh sách đặc trưng LIME như một lời giải thích đáng tin cậy. Nhãn Hulk vẫn là kết quả của XGBoost, còn cảnh báo LIME cho biết chưa giải thích được kết quả đó bằng phép thử hiện tại. Nó không có nghĩa XGBoost ngừng chạy, không xác nhận nhãn Hulk đúng và cũng không kết luận mọi traffic realtime đều không dùng được LIME. Cả tám cảnh báo Hulk trong hai PCAP được thử gặp tình trạng này, trong khi LIME vẫn đạt ngưỡng R² trên 1.151 flow của tập đánh giá RQ2.')
h('4.7.3 Diễn giải traffic bình thường và báo nhầm')
p('Người thu thập mô tả hai PCAP là traffic sử dụng thông thường, nhưng các tệp đối chứng chưa có nhãn độc lập xác nhận cho từng flow. Vì vậy, báo cáo dùng thuật ngữ cảnh báo Hulk nghi báo nhầm và không tính FPR từ tám cảnh báo này. Để đo FPR thực địa, cần xác định trước tập flow bình thường bằng quy trình có kiểm soát và ghi nhận mẫu số. Tương tự, 250 nhãn Hulk và một nhãn Infilteration trong nhật ký Wi-Fi không tự trở thành 251 báo nhầm đã xác nhận.')

section('4.8 Đối chiếu nghiên cứu liên quan và thảo luận hạn chế')
h('4.8.1 Liên hệ với vấn đề chất lượng dữ liệu CIC')
p('Engelen và cộng sự mô tả các lỗi xây dựng flow, gắn nhãn và đếm cờ trong CICIDS2017. Tài liệu mở rộng giải thích rằng việc đóng flow ở FIN đầu tiên có thể tạo phần đuôi TCP mang hướng ngược. Khi hướng đó được kế thừa sau timeout, quá trình gắn nhãn dựa trên hướng có thể gán Benign cho kết nối tấn công tiếp theo. Tài liệu cũng ghi nhận lỗi chỉ tăng bộ đếm cờ ở gói đầu tiên [5].')
p('Nghiên cứu Error Prevalence in NIDS datasets mở rộng khảo sát sang CSE-CIC-IDS2018. Trang tài liệu cho bộ 2018 xác nhận phần triển khai Hulk chịu vấn đề tương tự nghiên cứu trước và phân biệt các flow thử tấn công không có payload [6]. Hai nguồn này cung cấp cơ sở để kiểm tra chất lượng đặc trưng và nhãn của bộ dữ liệu, không cung cấp bằng chứng trực tiếp rằng mọi lỗi dự đoán của nguyên mẫu có cùng nguyên nhân.')
table('Bảng 4.12. Đối chiếu phát hiện bên ngoài với bằng chứng của dự án',['Nội dung','Bằng chứng dự án','Giới hạn kết luận'],[
('Lỗi đếm cờ trong công cụ CIC cũ [5]','Các cột cờ train nằm trong khoảng 0 đến 1. PCAP có số đếm lớn hơn 1.','Chưa truy được đầy đủ pipeline tiền xử lý gốc để quy nguyên nhân cho một phiên bản công cụ.'),('Vấn đề Hulk trong bộ 2018 [6]','Vùng đặc trưng đã khảo sát chứa 445 mẫu train, đều là Hulk.','Phân bố nhãn hỗ trợ giả thuyết lệch miền, chưa chứng minh quan hệ nhân quả.'),('Sai nhãn do hướng và phần đuôi TCP [5]','Lifecycle v3 có kiểm thử đóng flow và đối soát gói.','Sửa pipeline hiện tại không sửa được nhãn đã dùng để huấn luyện mô hình cũ.')],[1.7,2.4,2.4])
h('4.8.2 Các yếu tố giới hạn tính khái quát')
p('Trùng lặp đặc trưng giữa train và test cùng việc chọn cấu hình trên test làm giảm độ độc lập của đánh giá RQ1. Tập mẫu RQ2 chỉ gồm dự đoán đúng làm giới hạn khả năng suy rộng chất lượng giải thích sang các lỗi nhận diện. Những lớp có rất ít mẫu test cũng có ước lượng recall nhạy với vài trường hợp đơn lẻ. Báo cáo vì vậy không so sánh thứ hạng mô hình với công trình khác nếu không thống nhất tập dữ liệu, cách chia tập và định nghĩa chỉ số.')
p('Các đặc trưng phụ thuộc cách gom flow, timeout, hướng truyền, độ dài gói và cách đếm cờ. Kiểm tra đủ 78 cột chỉ xác nhận cấu trúc đầu vào. Tương thích về ý nghĩa còn cần đối chiếu bộ trích xuất với các gói chuẩn có kết quả kỳ vọng và truy xuất nguồn dữ liệu huấn luyện. SHAP có thể phân rã chính xác một quyết định dựa trên tương quan không phù hợp, nên cộng tính tốt không khắc phục sai lệch mô hình.')
p('Môi trường chạy lại phát cảnh báo khi nạp mô hình và LabelEncoder được lưu bởi phiên bản thư viện khác. Dù ma trận nhầm lẫn và kết quả XAI đã khớp trong các phép thử lần này, điều đó không thay thế quản lý môi trường tái lập. Dự án cần lưu phiên bản phụ thuộc và định dạng mô hình ổn định trước khi triển khai ở máy khác.')
h('4.8.3 Phạm vi đạt được và công việc còn mở')
p('RQ1 đã có kết quả phân loại tái lập trên tập test hiện có. RQ2 đã có giải thích tái lập và đối chứng thay thế đặc trưng, đồng thời bộc lộ khác biệt giữa SHAP và LIME. RQ3 đã nối được các nguồn dữ liệu vào cùng pipeline và có kiểm thử quản lý capture, giao diện, giới hạn tài nguyên. Kết quả này xác nhận nguyên mẫu thực hiện được các chức năng đã thử, chưa xác nhận độ chính xác ngoài miền hoặc vận hành liên tục dưới tải cao.')
p('Các bước đánh giá tiếp theo cần ưu tiên tập kiểm tra độc lập không trùng train, traffic có nhãn xác minh, đối chiếu đặc trưng theo gói chuẩn và đo độ trễ đầu cuối dưới nhiều mức tải. Thí nghiệm thay đổi tập huấn luyện hoặc loại bỏ đặc trưng nghi ngờ phải được tách khỏi mô hình gốc để giữ khả năng đối chiếu RQ1, RQ2 và RQ3. Chương này không đưa kết quả huấn luyện lại hoặc RQ4 vào phạm vi kết luận.')

section('4.9 Tổng kết chương')
p('Kết quả dự đoán trên 700.000 flow được tái lập hoàn toàn ở cấp ma trận nhầm lẫn. Mô hình đạt accuracy 97,9076% và macro F1 85,8058%, nhưng recall Infilteration và SlowHTTPTest còn thấp. FPR trên Benign của tập test là 0,2324%. Chỉ số này được giới hạn ở dữ liệu test 2018 và không dùng thay cho FPR của traffic thu trực tiếp.')
p('SHAP và LIME trên tập 1.339 flow tái lập trong sai số số học. SHAP có mức giảm xác suất lớn hơn LIME trong phép thay thế đặc trưng đã định nghĩa. Đồng thuận top-5 giữa hai phương pháp còn thấp. LIME gặp suy biến vùng lân cận trên các cảnh báo PCAP được thử, trong khi SHAP vẫn cho thấy những đặc trưng đẩy điểm về Hulk. Cả hai phương pháp giải thích đầu ra mô hình, không xác thực nhãn an ninh.')
p('Nguyên mẫu đã qua bảy nhóm kiểm thử, kiểm tra nhập CSV, phát lại hai PCAP và thử Wi-Fi thật trong 30 giây. Lượt realtime mới đối soát được 2.645 gói và 70 flow, sau đó dừng hoàn tất. Nhật ký Wi-Fi 20 phút trước đó được dùng riêng để phân tích tài nguyên và vận hành kéo dài. Các giới hạn về độc lập dữ liệu, tương thích đặc trưng, nhãn thực địa và tải dài hạn vẫn cần được xử lý trước khi kết luận hệ thống đủ tin cậy cho vận hành thực tế.')
h('Nguồn số liệu và tài liệu đối chiếu trong chương')
refs=[
'[1] Bộ đối chứng ngày 28/10/2026, Report/chapter4_assets. verification.json lưu kiểm tra dữ liệu, suy luận toàn test, SHAP và LIME. supplement.json lưu đối chứng thay thế đặc trưng và tổng hợp nhật ký. pcap_recheck.json và rq3_test_results.json lưu phát lại PCAP và kiểm thử hệ thống. Các script verify_chapter4.py, verify_chapter4_supplement.py và recheck_rq3_chapter4.py cho phép truy vết phép kiểm tra.',
'[2] RQ1_Model_Training_xboost. Mã chọn siêu tham số, mô hình best_xgboost_model.pkl, label_encoder.pkl và results/confusion_matrix_values.csv. Dữ liệu đối chiếu tại dataset/CICID-2018_processed.',
'[3] RQ2/runs/20261009. Các kết quả gd3_cohorts, gd4_shap_per_flow, gd6_lime_per_flow, gd7_agreement, gd9_stability_robustness và gd10_faithfulness. Định nghĩa phép thay thế đặc trưng được đối chiếu với scripts/stage10_faithfulness.py.',
'[4] RQ3_IDS_System. Cấu hình và mã nguồn hiện hành, các script Stage14, 15, 21, 26, 27, 29, 36, 37 và 38. Nhật ký lịch sử docs/live_20min_ht3_retry_20261018.json được đọc lại. Lượt mới 30 giây được lưu tại Report/chapter4_assets/realtime_revision_20261028.json. Kết quả chạy lại 10 seed, nhiễu đầu vào và số mẫu LIME ở Report/chapter4_assets/revision_rq2.',
'[5] Engelen, G., Rimmer, V. và Joosen, W. (2021). Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study. Tài liệu mở rộng của tác giả. https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html. Truy cập ngày 28/10/2026.',
'[6] Liu, L., Engelen, G., Lynar, T., Essam, D. và Joosen, W. (2022). Error Prevalence in NIDS datasets: A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018. IEEE CNS. DOI 10.1109/CNS56114.2022.9947235. Tài liệu bộ 2018 tại https://intrusion-detection.distrinet-research.be/CNS2022/CSECICIDS2018.html. Truy cập ngày 28/10/2026.',
'[7] Tài liệu thực nghiệm RF của dự án. RQ1_Model_Training_xboost/RQ1_docx/Tong_hop_Random_Forest.docx và Bao_Cao_Tong_Hop_Thuc_Nghiem_RQ1_RandomForest_XGBoost.docx. Các bảng mô tả cấu hình và kết quả RF được đối chiếu giữa hai tài liệu. Chưa có tệp mô hình RF và dự đoán gốc trong workspace để chạy lại.'
]
for ref in refs:
    para=p(ref)
    para.paragraph_format.space_after=Pt(4)
    for run in para.runs:run.font.size=Pt(9.5)

for name in ['Normal','Heading 1','Heading 2','Heading 3']:
    style=d.styles[name];style.font.name='Times New Roman'
    fonts=style.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ['ascii','hAnsi','eastAsia','cs']:fonts.set(qn('w:'+attr),'Times New Roman')
    for attr in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:
        if qn('w:'+attr) in fonts.attrib:del fonts.attrib[qn('w:'+attr)]
d.styles['Heading 3'].font.size=Pt(13)
d.styles['Heading 3'].font.bold=True
d.styles['Heading 3'].font.color.rgb=RGBColor(0,0,0)
for sec in d.sections:
    footer=sec.footer.paragraphs[0];footer.alignment=2
    run=footer.add_run();field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');run._r.addnext(field)
d.core_properties.title='Chương 4. Kết quả thực nghiệm và thảo luận'
d.core_properties.subject='RQ1, RQ2, RQ3. Số liệu được đối chứng ngày 28/10/2026.'
d.save(base.OUTPUT)
print('COMPLETE',base.OUTPUT,'paragraphs',len(d.paragraphs),'tables',len(d.tables),'figures',len(d.inline_shapes))
