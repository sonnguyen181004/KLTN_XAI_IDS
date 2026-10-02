from pathlib import Path
import csv
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent  # script nam trong RQ2_Tools
OUT = ROOT / 'RQ2_Tai_lieu' / 'Bao_cao_hoan_chinh_RQ2_SHAP_LIME.docx'
LIME = ROOT / 'RQ2_LIME_FI'

doc = Document()
sec = doc.sections[0]
sec.top_margin, sec.bottom_margin = Inches(.68), Inches(.68)
sec.left_margin, sec.right_margin = Inches(.72), Inches(.72)

styles = doc.styles
styles['Normal'].font.name = 'Aptos'; styles['Normal'].font.size = Pt(10.5)
styles['Normal']._element.rPr.rFonts.set(qn('w:ascii'), 'Aptos')
styles['Normal']._element.rPr.rFonts.set(qn('w:hAnsi'), 'Aptos')
styles['Normal'].paragraph_format.space_after = Pt(5)
styles['Normal'].paragraph_format.line_spacing = 1.12
for n, s in [('Title', 21), ('Heading 1', 15), ('Heading 2', 12)]:
    st = styles[n]; st.font.name = 'Aptos Display' if n == 'Title' else 'Aptos'; st.font.bold = True
    st.font.size = Pt(s); st.font.color.rgb = RGBColor(0,0,0)
    st._element.rPr.rFonts.set(qn('w:ascii'), st.font.name); st._element.rPr.rFonts.set(qn('w:hAnsi'), st.font.name)
title_ppr = styles['Title']._element.get_or_add_pPr()
for old_border in title_ppr.findall(qn('w:pBdr')):
    title_ppr.remove(old_border)

def shade(cell, color):
    p = cell._tc.get_or_add_tcPr(); e = OxmlElement('w:shd'); e.set(qn('w:fill'), color); p.append(e)
def border(cell):
    p=cell._tc.get_or_add_tcPr(); b=p.first_child_found_in('w:tcBorders')
    if b is None: b=OxmlElement('w:tcBorders'); p.append(b)
    for x in ('top','left','bottom','right','insideH','insideV'):
        e=b.find(qn('w:'+x))
        if e is None: e=OxmlElement('w:'+x); b.append(e)
        e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'5'); e.set(qn('w:color'),'D9D9D9')
def cell(cell, text, bold=False, head=False, center=False):
    cell.text=''; p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after=Pt(1); p.paragraph_format.space_before=Pt(1)
    r=p.add_run(str(text)); r.bold=bold; r.font.size=Pt(8.8 if head else 8.9)
    if head: r.font.color.rgb=RGBColor(255,255,255); shade(cell,'17365D')
    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; border(cell)
def tab(headers, rows, widths=None):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    for i,h in enumerate(headers): cell(t.rows[0].cells[i],h,True,True,True)
    for j,row in enumerate(rows):
        cells = t.add_row().cells
        for i,v in enumerate(row):
            cell(cells[i],v,False,False,i in (1,) and len(row)>2)
            if j%2: shade(cells[i],'F3F7FB')
    if widths:
        for row in t.rows:
            for i,w in enumerate(widths): row.cells[i].width=Inches(w)
    doc.add_paragraph()
    return t
def H(text, level=1):
    q=doc.add_paragraph(text,style=f'Heading {level}'); q.paragraph_format.space_before=Pt(11 if level==1 else 7); q.paragraph_format.space_after=Pt(4); return q
def P(text): return doc.add_paragraph(text)
def bullet(text):
    q=doc.add_paragraph(style='List Bullet'); q.add_run(text)
def image(path, width=6.0, caption=None):
    q=doc.add_paragraph(); q.alignment=WD_ALIGN_PARAGRAPH.CENTER; q.add_run().add_picture(str(path),width=Inches(width))
    if caption:
        c=doc.add_paragraph(caption); c.alignment=WD_ALIGN_PARAGRAPH.CENTER; c.runs[0].italic=True; c.runs[0].font.size=Pt(9)

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

# title and executive answer
t=doc.add_paragraph('Bao cao hoan chinh RQ2 SHAP LIME',style='Title'); t.alignment=WD_ALIGN_PARAGRAPH.CENTER
s=doc.add_paragraph('Đánh giá chất lượng lời giải thích của XGBoost trên CSE CIC IDS2018'); s.alignment=WD_ALIGN_PARAGRAPH.CENTER; s.runs[0].italic=True
P('Kết luận chính của RQ2 là: trên cohort ghép cặp 1.339 flow, SHAP và LIME không thường xuyên chọn cùng Top 5 feature; SHAP có Domain Precision và faithfulness cao hơn LIME trong các phép đo đã chọn. LIME chạy đúng quy trình nhưng Local R² thấp, nên chỉ được dùng như phương pháp đối chứng cục bộ chứ không phải căn cứ chính để kết luận nguyên nhân dự đoán của XGBoost.')

H('1 Cau hoi nghien cuu va cau tra loi')
tab(['Sub RQ', 'Câu hỏi', 'Kết quả chính'],[
['2.1','SHAP và LIME có chọn các feature giống nhau không?','Jaccard at 5 = 0,213. Mức giống nhau Top 5 thấp - trung bình.'],
['2.2','Feature quan trọng có phù hợp tín hiệu được kỳ vọng theo cơ chế tấn công không?','Domain Precision at 5: SHAP = 0,187; LIME = 0,111. Cả hai thấp.'],
['2.3','Lời giải thích có ổn định và bền vững không?','LIME: Local R² median = 0,068; stability median Jaccard at 5 = 0,415.'],
['2.4','Feature được chọn có thực sự ảnh hưởng đến quyết định model không?','Faithfulness at k = 5: SHAP = 95,74%; LIME = 90,44%.'],
],[.55,2.85,3.4])
P('Bốn chỉ số trên đo bốn khía cạnh khác nhau. Không được cộng, trung bình hay diễn giải chúng thành một tỷ lệ duy nhất như “RQ2 đúng X phần trăm”.')

H('2 Pham vi va tinh tai lap')
P('Báo cáo hợp nhất ba nhóm bằng chứng: (i) SHAP global đã tính trên toàn bộ test set 700.000 flow, (ii) SHAP per-flow và LIME per-flow trên cohort ghép cặp, và (iii) các script đánh giá agreement, domain, stability robustness và faithfulness. Các so sánh trực tiếp SHAP - LIME chỉ dùng cohort ghép cặp.')
tab(['Thành phần','Thiết lập đã khóa','Lý do'],[
['Model','XGBoost 15 lớp, 100 cây, max depth 8, learning rate 0,08, 78 feature','Cùng model đã chọn trong RQ1.'],
['Cohort ghép cặp','1.339 flow dự đoán đúng, seed 42, tối đa 100 flow mỗi lớp','Đảm bảo SHAP và LIME giải thích đúng cùng sample và cùng output.'],
['Lớp hiếm','Brute Force XSS: 44 flow; SQL Injection: 9 flow','Giữ toàn bộ flow đúng có sẵn. Kết luận theo hai lớp này chỉ có tính minh họa.'],
['SHAP','TreeExplainer, raw margin, tree path dependent, không approximate','Phù hợp trực tiếp với XGBoost; kiểm tra additivity.'],
['LIME','Background 8.002 flow; 5.000 sample per flow; kernel width 6,624; discretize continuous','Fit Ridge surrogate cục bộ để giải thích predicted label.'],
],[1.25,2.6,2.95])
P('Cohort chỉ giữ flow dự đoán đúng để đối chiếu knowledge domain theo nhãn lớp không bị lẫn với lỗi dự đoán. Điều này không có nghĩa model không cần giải thích flow sai. Error cohort tồn tại để làm case study riêng, nhưng không được trộn vào trung bình chính của RQ2.')

H('3 Phuong phap va cac chi so')
tab(['Chỉ số','Công thức hoặc ý tưởng','Cách diễn giải đúng'],[
['Jaccard at k','Số feature chung trong Top k chia số feature thuộc hợp của hai Top k','Đo trùng tập feature. 0 là không trùng, 1 là trùng hoàn toàn.'],
['Spearman','Tương quan thứ hạng, chỉ trên feature chung','Đo thứ tự tương đối khi có ít nhất hai feature chung. Không có nghĩa hai thang đo bằng nhau.'],
['Signed agreement','Tỷ lệ feature chung có cùng dấu','Chỉ là chỉ số phụ: SHAP dùng raw margin còn LIME fit theo xác suất.'],
['Domain Precision at 5','Số feature Top 5 khớp expected signals chia 5','Đối chiếu có cấu trúc với kiến thức miền; không phải điểm đúng từ chuyên gia SOC.'],
['Local R²','R² của Ridge surrogate LIME quanh một flow','Đo LIME bắt chước XGBoost tốt hay kém. Đây là chỉ số chất lượng cốt lõi của LIME.'],
['Faithfulness','Top k làm giảm score lớp gốc mạnh hơn random khi thay bằng donor train','Đo ảnh hưởng tương đối lên model trong protocol donor substitution; không chứng minh nhân quả ngoài model.'],
],[1.45,2.8,2.55])

H('4 SHAP global tren toan bo 700000 test flow')
P('Phần này dùng kết quả SHAP đã chạy trên toàn bộ 700.000 flow test. Mục tiêu là xem xu hướng model ở quy mô lớn. Đây là bằng chứng bổ sung cho SHAP, không phải phép so sánh trực tiếp với LIME. LIME không chạy trên 700.000 flow vì mỗi explanation cần sinh 5.000 mẫu lân cận, dẫn đến chi phí tính toán không thực tế.')
tab(['Nội dung global','Kết quả','Cách sử dụng trong RQ2'],[
['Top feature theo lớp','Đã tổng hợp trên toàn bộ flow của 14 lớp tấn công','Mô tả xu hướng XGBoost dựa vào feature nào khi phân loại một lớp ở quy mô lớn.'],
['Faithfulness Top 3','98,17% win rate; coverage 100,00%','Bằng chứng bổ sung rằng Top 3 SHAP thường làm score model giảm mạnh hơn random.'],
['Faithfulness Top 5','99,31% win rate; 695.140 / 699.996 flow đủ điều kiện; coverage 99,9994%','Không gộp với 95,74% SHAP trên cohort 1.339 flow.'],
['Faithfulness Top 10','99,83% win rate; coverage 92,85%','Coverage giảm vì không phải flow nào cũng có đủ 10 feature SHAP dương.'],
['Ổn định lấy mẫu','Overlap Top 10 thấp nhất 80%; Spearman thấp nhất 0,9898','Kết quả tổng hợp SHAP khá ổn định khi thay cap 100, 500, 1.000 và seed.'],
['Nhiễu thời gian ±10%','Đổi nhãn 0,2102% trên 2,1 triệu lượt nhiễu','Đa số nhãn giữ nguyên; một số lớp khó vẫn nhạy với nhiễu.'],
['Thời gian SHAP','Mean 19,11 ms; P95 22,19 ms cho 15 output trên CPU i7 12700H, 4 luồng','Tham khảo cho RQ3 hoặc batch review, không phải bảo đảm latency mọi máy.'],
],[1.5,2.25,3.05])
tab(['Lớp tấn công','Top 1 SHAP global','Số flow của lớp trong lần tổng hợp'],[
['Bot','Dst Port','25.162'],['Brute Force Web','Fwd Pkt Len Mean','122'],['Brute Force XSS','Init Fwd Win Byts','46'],['DDoS HOIC','Init Fwd Win Byts','59.580'],['DDoS LOIC UDP','Tot Fwd Pkts','346'],['DDoS LOIC HTTP','Fwd Pkts/s','51.354'],['DoS GoldenEye','Fwd Seg Size Min','3.694'],['DoS Hulk','Fwd Seg Size Min','38.760'],['DoS SlowHTTPTest','Fwd Seg Size Min','1.735'],['DoS Slowloris','Bwd IAT Max','905'],['FTP BruteForce','Fwd Seg Size Min','3.507'],['Infilteration','Fwd Header Len','14.315'],['SQL Injection','Init Fwd Win Byts','17'],['SSH Bruteforce','Dst Port','10.457'],
],[1.75,2.7,2.35])
image(LIME/'report_charts/shap_global_top5_four_representative_classes.png',6.55,'Hình 1. Top 5 SHAP global của bốn lớp đại diện. SQL Injection chỉ có 17 flow nên chỉ có ý nghĩa minh họa.')
P('Benign không có trong bảng này vì lần xuất Top feature SHAP global cũ chỉ tạo CSV cho 14 lớp tấn công. Điều này không phải SHAP thiếu Benign: phần so sánh cùng cohort của báo cáo vẫn có Top 1 SHAP Benign là Fwd Pkt Len Max. Khi cần Top 5 global Benign, phải chạy hoặc xuất thêm riêng từ 490.000 flow Benign, không được dùng Top 1 cohort thay cho global.')
P('Kết luận phần global: SHAP cung cấp xu hướng ổn định và faithfulness cao ở quy mô toàn test set. Tuy nhiên, các con số global không trả lời SHAP giống LIME bao nhiêu, vì LIME không chạy trên cùng 700.000 flow. Câu hỏi so sánh đó chỉ được trả lời ở cohort ghép cặp bên dưới.')

H('5 Ket qua Sub RQ 2 1 Tuong dong SHAP LIME')
P('SHAP và LIME được ghép theo sample id và feature của cùng 1.339 flow. SHAP xếp hạng theo absolute SHAP value; LIME xếp hạng theo absolute weight. Kết quả macro là trung bình không trọng số của 15 lớp.')
tab(['k','Jaccard macro','Spearman macro','Signed agreement macro','Kết luận'],[
['3','0,241','0,818','0,959','Có ít feature chung, nhưng thứ tự và chiều của feature chung khá gần nhau.'],
['5','0,213','0,476','0,896','Top 5 trùng lặp thấp - trung bình. Đây là mức dùng làm kết luận chính.'],
['10','0,239','0,380','0,847','Mở rộng danh sách không làm hai phương pháp hội tụ đáng kể.'],
],[.45,1.1,1.25,1.55,2.45])
image(LIME/'report_charts/agreement_shap_lime.png',6.2,'Hình 2. Agreement SHAP - LIME theo Top k trên cùng cohort 1.339 flow.')
agree = read_csv(LIME/'rq2_agreement/20260929_075049_171393/summary_by_class.csv')
rows=[]
for r in agree:
    rows.append([r['true_label'],r['N'],f"{float(r['jaccard_5_mean']):.3f}", 'NA' if not r['spearman_5_mean'] else f"{float(r['spearman_5_mean']):.3f}", 'NA' if not r['signed_agreement_5_mean'] else f"{float(r['signed_agreement_5_mean']):.3f}"])
tab(['Lớp','N','Jaccard at 5','Spearman','Cùng dấu'],rows,[1.9,.45,1.15,1.05,1.0])
P('SSH BruteForce có Jaccard at 5 cao nhất (0,480), trong khi SQL Injection bằng 0 và không đủ feature chung để tính Spearman. Vì SQL Injection chỉ có 9 flow, không được suy rộng riêng kết quả lớp này thành kết luận toàn bộ phương pháp.')

H('6 Ket qua Sub RQ 2 2 Doi chieu kien thuc mien')
P('Expected signals được xác định trước theo cơ chế của từng loại tấn công. Vì cohort chính chỉ gồm dự đoán đúng, true label bằng predicted label; nhờ đó việc so với expected signals theo lớp là nhất quán.')
tab(['Phương pháp','Macro Domain Precision at 5','Diễn giải'],[
['SHAP','0,187','Khoảng 18,7 phần trăm feature Top 5 khớp bảng expected signals theo trung bình lớp.'],
['LIME','0,111','Khoảng 11,1 phần trăm; thấp hơn SHAP trong cùng điều kiện.'],
],[1.4,2.1,3.8])
domain=read_csv(LIME/'rq2_domain/20260929_075107_865652/summary_by_class.csv')
tab(['Lớp','N','SHAP Precision at 5','LIME Precision at 5'],[[r['true_label'],r['N'],f"{float(r['shap_precision_at_5_mean']):.3f}",f"{float(r['lime_precision_at_5_mean']):.3f}"] for r in domain],[2.15,.5,1.55,1.55])
P('Giá trị thấp không chứng minh model hoặc SHAP và LIME “sai”. CICFlowMeter chứa thống kê flow, trong khi tín hiệu chuyên gia có thể cần payload HTTP, log web, log xác thực hoặc PCAP. Đây là giới hạn của dữ liệu và bộ expected signals đơn giản hóa. Vì chưa có chấm điểm SOC độc lập, không gọi Domain Precision là “tỷ lệ giải thích đúng”.')

H('7 Ket qua Sub RQ 2 3 Chat luong va do on dinh cua LIME')
P('LIME sinh các sample lân cận rồi fit Ridge regression. Nếu Ridge không tái tạo được hành vi XGBoost quanh flow, các feature ranking chỉ là xấp xỉ yếu. Do đó Local R² cần được đọc trước khi sử dụng Top 5 LIME.')

H('6.1 Local R² nói lên điều gì, giải thích bằng ngôn ngữ đơn giản', 2)
P('Với mỗi flow cần giải thích, LIME tạo ra hàng nghìn phiên bản gần giống flow đó bằng cách thay đổi nhẹ giá trị các đặc trưng, hỏi XGBoost dự đoán từng phiên bản, rồi vẽ một đường thẳng, tức mô hình Ridge tuyến tính, cố gắng bắt chước cách XGBoost quyết định trong vùng lân cận đó. Đặc trưng nào có hệ số lớn trên đường thẳng này thì LIME xem là quan trọng.')
P('Local R² đo đúng một việc: đường thẳng đó bắt chước XGBoost giống đến mức nào. R² bằng 1 nghĩa là bắt chước hoàn hảo; R² bằng 0 nghĩa là đường thẳng gần như không liên quan gì đến cách model thực sự quyết định.')
P('Vì vậy, Local R² median 0,068 có nghĩa là đường thẳng của LIME chỉ mô tả được khoảng 6,8 phần trăm hành vi thật của XGBoost quanh flow đang xét; khoảng 93 phần trăm còn lại nằm ngoài khả năng mô tả của nó. Có thể hình dung như việc dùng một cây thước thẳng để vẽ theo đường viền của một vật thể cong và gồ ghề: chỉ khớp ở một đoạn rất ngắn, phần còn lại lệch nhiều.')
P('Đây không phải lỗi chọn tham số. Nhóm đã thử tăng gấp đôi số mẫu lân cận lên 10.000 và thử tắt rời rạc hóa đặc trưng; cả hai cấu hình đều không cải thiện, thậm chí cho median R² thấp hơn cấu hình gốc, như bảng chẩn đoán ở trên. Nguyên nhân nằm ở bản chất bài toán: ranh giới quyết định của XGBoost với 100 cây trên không gian 78 chiều quá phi tuyến để một mô hình tuyến tính cục bộ mô tả tốt.')
P('Kết quả này là một phát hiện nghiên cứu hợp lệ chứ không phải một lỗi cần khắc phục. Hạn chế của local surrogate tuyến tính trên dữ liệu nhiều chiều và phi tuyến là điều đã được ghi nhận trong nghiên cứu về XAI. Việc tinh chỉnh tham số cho tới khi R² đạt mức đẹp rồi mới báo cáo mới là cách làm sai phương pháp; báo cáo trung thực con số thấp kèm quy trình chẩn đoán đã thử là cách làm đúng.')
P('Hệ quả thực tế gồm hai điểm. Thứ nhất, Top 5 đặc trưng do LIME đưa ra trên bộ dữ liệu này chỉ nên được dùng làm tham khảo đối chứng, không nên dùng làm căn cứ chính khi giải thích một cảnh báo cho analyst. Thứ hai, và quan trọng hơn về mặt diễn giải, kết quả Sub-RQ 2.1 phải được đọc thận trọng: mức trùng Top 5 thấp giữa hai phương pháp, Jaccard 0,213, có thể phần lớn bắt nguồn từ chính việc surrogate của LIME quá yếu, chứ không nhất thiết chứng minh rằng SHAP và LIME nhìn model theo hai cách khác nhau một cách có hệ thống. Local R² thấp do đó là một yếu tố gây nhiễu cho kết luận về độ tương đồng và phải được nêu rõ khi diễn giải con số Jaccard.')
tab(['Chẩn đoán Local R² trên 60 flow','Median R²','Mean R²','Kết luận'],[
['Baseline 5.000 sample, discretize true','0,062','0,113','Cấu hình chính.'],
['10.000 sample','0,048','0,102','Không cải thiện.'],
['5.000 sample, discretize false','0,029','0,115','Không cải thiện.'],
],[3.2,1.0,1.0,1.65])
P('Trên toàn bộ 1.339 flow, Local R² median là 0,068 và mean là 0,119, thấp hơn ngưỡng cảnh báo 0,30. Vì vậy, trong các cấu hình đã thử, LIME không tạo được surrogate tuyến tính đủ tốt cho ranh giới phi tuyến của XGBoost trên 78 feature.')
image(LIME/'report_charts/lime_r2_by_class.png',5.8,'Hình 1. Phân bố Local R² của LIME theo lớp; đường đỏ là ngưỡng 0,30.')
stab=read_csv(LIME/'rq2_stability_robustness/20260929_075115_407964/summary_stability_by_class.csv')
tab(['Stability LIME','Phạm vi','Kết quả','Cách hiểu'],[
['Khác seed','289 flow, tối đa 20 flow mỗi lớp, 8 seed','Median Jaccard at 5 = 0,415','Top 5 thay đổi đáng kể giữa các lần chạy. Ổn định mức trung bình.'],
['Nhiễu thời gian 1 phần trăm','289 flow, 3 seed','Jaccard = 0,450; đổi nhãn = 3,00 phần trăm','Explanation thay đổi nhiều hơn nhãn dự đoán.'],
['Nhiễu thời gian 5 phần trăm','289 flow, 3 seed','Jaccard = 0,449; đổi nhãn = 4,15 phần trăm','Mức giao feature gần như không đổi.'],
['Nhiễu thời gian 10 phần trăm','289 flow, 3 seed','Jaccard = 0,448; đổi nhãn = 5,77 phần trăm','Không suy rộng ngoài tập con 289 flow.'],
],[1.55,1.55,1.65,2.1])
image(LIME/'report_charts/robustness_lime.png',5.8,'Hình 2. Robustness của LIME trước nhiễu thời gian trên tập con 289 flow.')

H('8 Ket qua Sub RQ 2 4 Faithfulness ghep cap')
P('Hai phương pháp dùng cùng protocol donor substitution: giữ cố định lớp dự đoán ban đầu; chọn Top k feature đóng góp dương; thay giá trị bằng 10 donor từ train set với seed 173; so với 20 random controls dùng seed 2026. “Win” nghĩa là mức giảm raw margin của tập feature được chọn lớn hơn random quá 10 mũ trừ 6.')
faith=read_csv(LIME/'rq2_faithfulness/20260929_075246_729773/summary_overall.csv')
faith_rows=[]
for r in faith:
    faith_rows.append([r['method'].upper(),r['k'],r['N'],r['n_eligible'],f"{float(r['coverage_percent']):.2f}%",f"{float(r['win_rate_percent']):.2f}%",f"{float(r['mean_margin_drop_method']):.3f}",f"{float(r['mean_margin_drop_random']):.3f}"])
tab(['Phương pháp','k','N','Đủ ĐK','Coverage','Win rate','Margin drop method','Margin drop random'],faith_rows,[.9,.35,.45,.55,.7,.75,1.25,1.25])
P('Ở k = 5, SHAP thắng đối chứng ngẫu nhiên ở 95,74 phần trăm flow đủ điều kiện, trong khi LIME đạt 90,44 phần trăm. SHAP cao hơn LIME ở cả k = 3, 5 và 10. Với SHAP k = 10, coverage chỉ 80,36 phần trăm nên không được so sánh với k khác mà bỏ qua coverage.')
image(LIME/'report_charts/winrate_shap_vs_lime.png',5.9,'Hình 3. Faithfulness win rate của SHAP và LIME trên cùng cohort 1.339 flow.')
P('Kết quả này khác với SHAP faithfulness 99,31 phần trăm trên toàn bộ 700.000 test flow trước đó. 99,31 phần trăm chỉ là bằng chứng global bổ sung cho SHAP, không thay thế và không được gộp với phép so sánh ghép cặp 1.339 flow trong RQ2.')

H('9 Doi chieu Top feature theo lop')
P('Top feature không phải một danh sách chung cho tất cả flow. Bảng dưới dùng đúng cùng cohort ghép cặp 1.339 flow cho cả hai phương pháp. Mỗi cột là feature có mean absolute attribution lớn nhất trong các flow dự đoán đúng của từng lớp. Vì vậy bảng có đủ cả 15 lớp, gồm Benign, và không trộn kết quả global với kết quả cohort.')
lime_top=read_csv(LIME/'lime_top5_by_class.csv')
first_lime={}
for r in lime_top:
    first_lime.setdefault(r['true_label'],r['feature'])
import pandas as pd
shap_long=pd.read_csv(ROOT/'RQ2_SHAP/rq2_paired_cohort/20260929_073435_637739/shap_per_flow_long.csv')
manifest=pd.read_csv(ROOT/'RQ2_SHAP/rq2_paired_cohort/20260929_073435_637739/manifest_main.csv')
shap_cohort=shap_long.merge(manifest[['sample_id','true_label']],on='sample_id',how='inner')
shap_first=(shap_cohort.groupby(['true_label','feature'],as_index=False)['abs_shap_value'].mean()
            .sort_values(['true_label','abs_shap_value'],ascending=[True,False])
            .groupby('true_label',as_index=False).first().set_index('true_label')['feature'].to_dict())
top_rows=[]
for label in first_lime:
    top_rows.append([label,first_lime[label],shap_first.get(label,'NA')])
tab(['Lớp','Top 1 LIME cohort 1.339','Top 1 SHAP cohort 1.339'],top_rows,[2.0,2.25,2.25])
P('Ví dụ, Benign có Top 1 SHAP cohort là Fwd Pkt Len Max; SSH BruteForce có Dst Port nổi bật ở cả hai phương pháp. Nhưng tương đồng tại một lớp không phủ định kết quả Jaccard per-flow thấp: RQ2 phải ưu tiên metric per-flow đã ghép cặp.')

H('10 Tra loi tong hop RQ2')
P('Trên dữ liệu CSE CIC IDS2018 và XGBoost đã khóa từ RQ1, SHAP là lựa chọn phù hợp hơn để làm lời giải thích chính cho RQ2. Trong cohort ghép cặp 1.339 flow, SHAP có Domain Precision at 5 cao hơn LIME (0,187 so với 0,111) và faithfulness win rate cao hơn ở k = 3, 5, 10. LIME không đồng thuận mạnh với SHAP ở Top 5 (Jaccard 0,213) và Local R² thấp cho thấy surrogate tuyến tính cục bộ chưa mô tả tốt model nền. Vì vậy, LIME đóng vai trò phép đối chứng và bằng chứng về giới hạn của local surrogate, không dùng để thay thế SHAP.')
P('Phát biểu này là có điều kiện theo dataset, model, cohort và protocol đã nêu. Nó không khẳng định SHAP là lời giải thích nhân quả của hành vi tấn công, không khẳng định mọi feature Top 5 là dấu hiệu tấn công thực tế, và không thay thế validation bằng PCAP, payload hoặc đánh giá chuyên gia SOC.')

H('11 Gioi han va huong hoan thien tiep theo')
for x in [
'SQL Injection có 9 flow và Brute Force XSS có 44 flow trong cohort. Chỉ báo cáo mô tả cho các lớp hiếm, không đưa kết luận thống kê mạnh riêng theo lớp.',
'Domain signals là bộ kỳ vọng dựa trên cơ chế tấn công. Để tăng tính thuyết phục, có thể có hai người đánh giá SOC độc lập, định nghĩa rubric trước và đo mức đồng thuận.',
'Donor substitution có thể tạo mẫu ngoài phân phối do ghép feature từ flow train sang flow test. Faithfulness hiện là ảnh hưởng tương đối trong protocol này, không phải nhân quả.',
'Nếu triển khai RQ3 realtime, dùng SHAP cho cảnh báo quan trọng hoặc batch review. Không dùng Local R² thấp của LIME như bằng chứng chính cho analyst.',
]: bullet(x)

H('Phu luc Nguon bang chung va code')
tab(['Nhóm','Nguồn đã đối chiếu','Vai trò trong báo cáo'],[
['SHAP','Bao_cao_RQ_SHAP_XGBoost.docx; build_cohort_and_shap.py','Kết quả SHAP global, cohort per-flow, cấu hình TreeExplainer và additivity.'],
['LIME','RQ2_LIME_Ket_Qua_Final.docx; RQ2_LIME_Bao_Cao_Rieng.docx; run_lime_paired_cohort.py','Cấu hình LIME, Local R², Top feature, stability và robustness.'],
['So sánh','evaluate_agreement.py; evaluate_domain.py; paired_faithfulness.py','Định nghĩa phép đo và CSV summary trên cohort ghép cặp.'],
],[1.0,3.3,2.2])
P('Các script kiểm tra sample id, số feature và predicted label trước khi ghép dữ liệu. SHAP kiểm tra additivity với raw margin. Đây là các điều kiện cần để so sánh per-flow có ý nghĩa.')

H('Phu luc B Giai thich feature CICFlowMeter trong RQ2')
P('Phụ lục này giải thích các feature xuất hiện trong Top feature SHAP hoặc LIME của báo cáo. Chúng là thống kê của network flow, không phải nội dung payload. Ví dụ, feature có tên SQL hoặc XSS không tồn tại trong 78 feature CICFlowMeter; vì vậy không thể dùng riêng một feature flow để khẳng định đã nhìn thấy câu lệnh SQL Injection hay mã XSS.')
H('B 1 Dia chi dich va thong ke goi',2)
tab(['Feature','Ý nghĩa đơn giản','Cách hiểu khi xuất hiện trong XAI'],[
['Dst Port','Cổng dịch vụ ở phía đích của flow, ví dụ SSH thường dùng 22.','Model có thể đang nhận diện loại dịch vụ hoặc môi trường. Không tự chứng minh có brute force.'],
['Tot Fwd Pkts','Tổng số packet từ nguồn đến đích trong flow.','Lớn có thể phản ánh lưu lượng gửi nhiều, ví dụ DDoS UDP; cần đọc cùng thời lượng flow.'],
['Tot Bwd Pkts','Tổng số packet từ đích về nguồn.','Cho biết mức phản hồi hai chiều, không phải số lần đăng nhập thất bại trực tiếp.'],
['Fwd Act Data Pkts','Số packet chiều đi mang payload dữ liệu thực.','Phân biệt phần nào traffic chỉ bắt tay TCP với traffic có dữ liệu.'],
['Fwd Pkt Len Max','Độ dài packet chiều đi lớn nhất trong flow, đơn vị byte.','Một packet lớn bất thường có thể làm model tách nhóm flow, nhưng không chỉ ra nội dung packet.'],
['Fwd Pkt Len Mean','Độ dài packet chiều đi trung bình, đơn vị byte.','Mô tả kích thước packet điển hình của flow.'],
['Fwd Pkt Len Std','Độ lệch chuẩn độ dài packet chiều đi.','Cao nghĩa là độ dài packet biến thiên mạnh; là dấu hiệu thống kê, không phải payload.'],
['Fwd Seg Size Min','Kích thước TCP segment nhỏ nhất theo chiều đi.','Có thể phản ánh các segment rất nhỏ trong một kiểu flow; cần kiểm tra cùng IAT và packet count.'],
['Fwd Header Len','Tổng độ dài header của packet chiều đi.','Thường liên quan đến số packet và loại header; không nên diễn giải tách rời.'],
['Bwd Header Len','Tổng độ dài header của packet chiều về.','Mô tả phần header ở chiều phản hồi của flow.'],
],[1.45,2.55,2.9])
H('B 2 Thoi gian toc do va kich thuoc cua flow',2)
tab(['Feature','Ý nghĩa đơn giản','Cách hiểu khi xuất hiện trong XAI'],[
['Flow Duration','Khoảng thời gian từ packet đầu đến packet cuối của flow, thường tính microsecond.','Flow dài/ngắn là dấu hiệu hành vi thời gian; không tự xác nhận Slowloris hay DoS.'],
['Fwd IAT Mean','Thời gian trung bình giữa các packet liên tiếp chiều đi.','Đo nhịp gửi packet theo chiều đi.'],
['Fwd IAT Min','Khoảng cách thời gian nhỏ nhất giữa hai packet chiều đi.','Giá trị nhỏ có thể gợi ý burst traffic.'],
['Fwd IAT Tot','Tổng các khoảng thời gian giữa packet chiều đi.','Liên quan trực tiếp đến nhịp và thời lượng gửi.'],
['Fwd IAT Std','Độ lệch chuẩn khoảng cách thời gian chiều đi.','Cao nghĩa là nhịp gửi không đều.'],
['Bwd IAT Min','Khoảng cách thời gian nhỏ nhất giữa packet chiều về.','Mô tả tốc độ phản hồi nhanh nhất ở phía đích.'],
['Bwd IAT Max','Khoảng cách thời gian lớn nhất giữa packet chiều về.','Một khoảng chờ phản hồi dài có thể là tín hiệu gián tiếp về hành vi thời gian.'],
['Bwd IAT Std','Độ lệch chuẩn khoảng cách packet chiều về.','Đo biến thiên nhịp phản hồi. Không thấy trực tiếp SQL payload.'],
['Bwd IAT Tot','Tổng khoảng thời gian giữa các packet chiều về.','Đại diện cho thời gian phản hồi tích lũy.'],
['Flow IAT Max','Khoảng cách thời gian lớn nhất giữa bất kỳ hai packet liên tiếp trong flow.','Cho biết flow có khoảng im lặng dài hay không.'],
['Flow IAT Min','Khoảng cách thời gian nhỏ nhất trong toàn flow.','Cho biết burst nhanh nhất của flow.'],
['Flow Byts/s','Số byte trung bình mỗi giây của flow.','Đo thông lượng; phải đọc cùng duration để tránh diễn giải sai flow rất ngắn.'],
['Fwd Pkts/s','Số packet chiều đi trung bình mỗi giây.','Feature tốc độ; thường hữu ích cho các kiểu flood nhưng không đủ để kết luận loại DDoS.'],
],[1.45,2.55,2.9])
H('B 3 Co TCP va cua so TCP',2)
tab(['Feature','Ý nghĩa đơn giản','Cách hiểu khi xuất hiện trong XAI'],[
['FIN Flag Cnt','Số packet có cờ TCP FIN, báo hiệu kết thúc kết nối.','Có thể phản ánh kiểu đóng kết nối trong dataset; không phải dấu hiệu tấn công phổ quát.'],
['RST Flag Cnt','Số packet có cờ TCP RST, reset kết nối.','Có thể xuất hiện khi kết nối bị từ chối hoặc reset; không đồng nghĩa với brute force.'],
['SYN Flag Cnt','Số packet có cờ TCP SYN, bắt đầu bắt tay TCP.','Nhiều SYN có thể liên quan đến hoạt động thiết lập kết nối, nhưng phải phân tích theo flow/kịch bản.'],
['URG Flag Cnt','Số packet có cờ TCP URG.','Là thống kê cờ hiếm; không nên tự suy diễn thành hành vi độc hại.'],
['Fwd URG Flags','Số cờ URG xuất hiện ở chiều nguồn đến đích.','Hướng của cờ URG cần được đọc cùng protocol và traffic context.'],
['ECE Flag Cnt','Số packet có cờ Explicit Congestion Echo.','Liên quan tín hiệu tắc nghẽn TCP; thường dễ phản ánh đặc điểm môi trường hơn cơ chế tấn công.'],
['CWE Flag Count','Số packet có cờ Congestion Window Reduced.','Cờ TCP liên quan phản ứng tắc nghẽn, không phải Common Weakness Enumeration.'],
['Init Fwd Win Byts','Kích thước cửa sổ TCP ban đầu theo chiều đi, đơn vị byte.','Cho biết tham số bắt tay/stack TCP; có thể bị model dùng như dấu vết dịch vụ hoặc môi trường.'],
['Init Bwd Win Byts','Kích thước cửa sổ TCP ban đầu theo chiều về, đơn vị byte.','Phản ánh phía phản hồi hoặc TCP stack; không chứng minh loại tấn công.'],
['Fwd PSH Flags','Số cờ TCP PSH ở chiều đi.','Cho biết packet yêu cầu đẩy dữ liệu tới ứng dụng; vẫn là metadata chứ không phải payload.'],
],[1.45,2.55,2.9])
H('B 4 Hoat dong va trang thai flow',2)
tab(['Feature','Ý nghĩa đơn giản','Cách hiểu khi xuất hiện trong XAI'],[
['Idle Max','Khoảng idle dài nhất của flow, tức thời gian không có packet.','Hữu ích để mô tả flow có thời gian im lặng dài; cần cẩn trọng với flow ngắn.'],
['Active Std','Độ lệch chuẩn của các giai đoạn active của flow.','Cho biết mức biến thiên các khoảng flow đang hoạt động.'],
['Subflow Fwd Pkts','Số packet chiều đi trong subflow theo cách CICFlowMeter chia flow.','Là thống kê nội bộ của FlowMeter, không phải một kết nối con nhìn thấy ở ứng dụng.'],
], [1.45,2.55,2.9])
P('Nguyên tắc khi trình bày: một feature có thể có attribution cao vì nó là dấu hiệu của dịch vụ, cấu hình máy, môi trường sinh dữ liệu hoặc tương quan dataset. Do đó, SHAP/LIME cho biết model đang dựa vào feature nào để ra quyết định; chúng không tự xác lập quan hệ nhân quả hay xác nhận payload tấn công.')

for section in doc.sections:
    f=section.footer.paragraphs[0]; f.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=f.add_run('RQ2 SHAP va LIME | CSE CIC IDS2018 | XGBoost 15 lop'); r.font.size=Pt(8); r.font.color.rgb=RGBColor(100,100,100)
doc.core_properties.title='Bao cao hoan chinh RQ2 SHAP LIME'
doc.core_properties.subject='Bao cao tong hop RQ2 ve SHAP va LIME'
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
