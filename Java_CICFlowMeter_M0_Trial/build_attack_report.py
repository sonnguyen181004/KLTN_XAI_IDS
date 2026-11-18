"""Build the Vietnamese M0 report, preserving all 19 original screenshots."""
from pathlib import Path
import argparse, hashlib, io
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

H=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=H/'bcao_tancon.docx')
args=parser.parse_args()
A=H/'output/report_assets'
A.mkdir(parents=True,exist_ok=True)
source=A/'original.docx'
if not source.exists(): source=H/'bcao_tancon.docx'
orig=Document(source)
image_blobs=[orig.part.related_parts[b.get(qn('r:embed'))].blob for p in orig.paragraphs for b in p._p.xpath('.//a:blip')]
assert len(image_blobs)==19, 'Expected 19 original screenshots'
doc=Document()
sec=doc.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=sec.bottom_margin=Cm(1.8);sec.left_margin=Cm(2.1);sec.right_margin=Cm(1.7)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Caption']:
    s=doc.styles[name];s.font.name='Times New Roman';s.font.color.rgb=RGBColor(0,0,0)
    s.font.size=Pt(12 if name=='Normal' else 14)
    s.paragraph_format.space_after=Pt(7)
doc.styles['Normal'].paragraph_format.line_spacing=1.12
doc.styles['Title'].font.size=Pt(19)
doc.styles['Heading 1'].font.size=Pt(15)
doc.styles['Caption'].font.size=Pt(11)
for style in doc.styles:
    for border in style.element.xpath('.//w:pBdr'):
        border.getparent().remove(border)
footer=sec.footer.paragraphs[0];footer.alignment=2
footer.add_run('Báo cáo thực nghiệm M0 | ')
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
textdraft=[]
def para(t):
    textdraft.append(t);return doc.add_paragraph(t)
def heading(t,level=1):
    textdraft.append(t);doc.add_heading(t,level)
captions = [
    ('SSH brute force trong ảnh lịch sử', 'Ảnh ghi 103 Benign và 2 SSH-Bruteforce. M0 chỉ đọc thống kê flow, không đọc được mật khẩu trong SSH mã hóa hoặc log xác thực thất bại. Thử nhiều mật khẩu vẫn có thể bị coi là Benign nếu flow khác mẫu đã học. Đây là ảnh cũ ở dải IP 192.168.64.x, không phải lượt ss2 hôm nay.'),
    ('Lệnh GoldenEye và bộ đếm của công cụ', 'GoldenEye mức đầu dùng 1 worker, 2 socket. Mức tăng dùng 2 worker, 5 socket mỗi worker. Tải đo tăng khoảng 180 lên 251 request/s, nhưng tăng request không bảo đảm từng flow giống mẫu GoldenEye trong train.'),
    ('Dashboard M0 trong lượt GoldenEye', 'Tại lúc chụp, dashboard có 742 flow, gồm 186 Benign và 556 cảnh báo. Nhãn GoldenEye chiếm phần lớn cảnh báo nhưng vẫn có nhãn khác. Trạng thái capturing cho biết số đếm chưa phải tổng cuối phiên. Trong PCAP, tỷ lệ nhãn GoldenEye ở mức đầu và mức tăng lần lượt là 98,06% và 94,31%.'),
    ('Một flow GoldenEye bị dự đoán Benign', 'M0 chọn Benign 96,25%. Init Fwd Win Byts là cửa sổ TCP ban đầu phía gửi, giá trị 278 góp khoảng 1,38 vào điểm Benign. Fwd Pkt Len Max bằng 0 là độ dài dữ liệu lớn nhất phía gửi theo extractor, lại kéo điểm Benign xuống khoảng 1,26. Vì vậy, không thể nói cứ gói dài bằng 0 là Benign. Model kết hợp nhiều đặc trưng, còn phần flow này có thể chỉ phản ánh đoạn đóng kết nối.'),
    ('Một flow được dự đoán GoldenEye', 'M0 chọn GoldenEye 94,08%. Fwd Seg Size Min là kích thước header TCP nhỏ nhất phía gửi, có đóng góp dương lớn nhất trong ảnh. Pkt Len Mean mô tả độ dài gói trung bình và cũng tăng điểm GoldenEye. Tot Bwd Pkts là số gói chiều về, có đóng góp âm. Model chọn lớp theo tổng tác động, không phải chỉ một đặc trưng. Header phụ thuộc môi trường TCP nên không riêng GoldenEye mới có.'),
    ('Apache ghi nhận request từ Kali trong lượt Hulk-Go', 'Log cho thấy Ubuntu nhận nhiều HTTP GET từ 192.168.11.133 và trả mã 200. Điều này xác nhận request đến server. Mã 200 và log request chưa chứng minh server bị quá tải hoặc mất dịch vụ. Muốn kết luận tác động phải có phép đo độ trễ và khả năng phục vụ khách hợp lệ.'),
    ('Lệnh Hulk-Go với mức đồng thời ban đầu', 'HULKMAXPROCS tăng từ 3 lên 6, cùng giới hạn 30 giây. Tải đo tăng khoảng 229 lên 295 request/s. Hulk-Go giữ kết nối khác cách triển khai Hulk lịch sử được mô tả trong nghiên cứu dataset, nên tăng tải chưa làm hai kiểu traffic tương đương.'),
    ('Các nhãn M0 sau lượt Hulk-Go', 'Ảnh ghi 313 cảnh báo và 39 Benign, chủ yếu là HOIC. Sau tăng tải, PCAP có 1.301 HOIC, 719 GoldenEye, 450 Benign và chỉ 5 Hulk. M0 cảnh báo nhiều flow nhưng vẫn nhầm loại vì đặc trưng lab khác mẫu Hulk đã học.'),
    ('Flow Hulk-Go được gán HOIC', 'M0 chọn HOIC 65,54% vì vector đặc trưng làm điểm lớp này cao nhất, không phải Kali thực sự chạy HOIC. Hulk-Go khác traffic Hulk lịch sử về cách giữ kết nối và đặc trưng TCP. Đây là nhầm loại tấn công, khác với bỏ sót thành Benign.'),
    ('Một flow trong phiên được gán Hulk', 'M0 chọn Hulk 77,02%. Fwd Seg Size Min bằng 32 byte, tức header TCP nhỏ nhất phía gửi, tăng điểm Hulk khoảng 4,72. Init Fwd Win Byts bằng 346 là cửa sổ TCP ban đầu, giảm điểm Hulk khoảng 1,34. FIN Flag Cnt bằng 1 là một cờ kết thúc kết nối, tăng điểm khoảng 0,81. Các dấu hiệu TCP này giải thích quyết định model, không tự chứng minh công cụ nào đã tạo traffic.'),
    ('SHAP của mẫu bị gán HOIC', 'M0 gán HOIC. Init Fwd Win Byts bằng 64.240 là cửa sổ TCP ban đầu phía gửi, không phải tốc độ tấn công, và tăng điểm HOIC khoảng 6,17. Dst Port bằng 80 là cổng dịch vụ HTTP, tăng thêm khoảng 0,58. Trong train M0 đã kiểm tra, lớp Hulk không có cửa sổ 64.240. Đây là dấu hiệu lệch phân bố, nhưng không có nghĩa mọi flow cửa sổ này đều là HOIC.'),
    ('Slowloris giữ các kết nối chưa hoàn tất', 'Mức đầu giữ 5 socket, gửi header cách 10 giây trong 60 giây. Mức sau tăng lên 10 socket, giữ nguyên khoảng nghỉ và thời lượng. Tăng số kết nối chưa bảo đảm mỗi kết nối tồn tại lâu như mẫu Slowloris trong dataset.'),
    ('M0 không tạo nhãn Slowloris ở mức đầu', 'Mức đầu có 12 Benign và 4 Hulk. Mức tăng có 33 Benign và 3 Hulk, vẫn không có Slowloris. Trung vị thời lượng flow lab khoảng 19 giây, trong khi train M0 của lớp Slowloris khoảng 106 giây. Tăng socket chưa khắc phục khác biệt này.'),
    ('SHAP của flow Slowloris bị gán Benign', 'M0 chọn Benign 87,85%. Fwd Pkt Len Max và Fwd Pkt Len Mean lần lượt là độ dài dữ liệu lớn nhất và trung bình phía gửi, đều bằng 0. Giá trị thứ nhất giảm điểm Benign khoảng 1,94, còn giá trị thứ hai tăng khoảng 0,58. Fwd IAT Tot là tổng khoảng cách thời gian giữa các gói phía gửi, chỉ 624 microsecond. Phần flow rất ngắn không thể hiện đầy đủ hành vi Slowloris, nhưng không phải riêng giá trị 0 đã khiến model chọn Benign.'),
    ('SHAP của flow Slowloris bị gán Hulk', 'M0 gán Hulk 60,14%. FIN Flag Cnt bằng 1 đếm cờ kết thúc TCP, tăng điểm Hulk khoảng 5,87. Fwd Pkt Len Max bằng 168 byte là độ dài dữ liệu lớn nhất phía gửi, tăng thêm khoảng 2,99. Hai đặc trưng đẩy model về Hulk dù công cụ thực tế là Slowloris. FIN và gói có kích thước này không phải dấu hiệu độc quyền của Hulk, nên dự đoán có thể nhầm.'),
    ('Giao diện LOIC-HTTP đang hoạt động', 'Đích trên ảnh là Ubuntu 192.168.11.134, phương thức HTTP và cổng 80. Nút Stop flooding cho thấy công cụ đang chạy. LOIC là công cụ riêng, không phải chế độ chạy Hulk. Timeout trong giao diện không được hiểu là thời lượng tự dừng toàn cuộc thử.'),
    ('Dashboard trong lúc dừng lượt LOIC', 'Ảnh lúc dừng ghi 1.560 Benign và 2.254 cảnh báo. Toàn PCAP có 21.302 Benign, 22.323 Hulk và 9.016 HOIC, không có LOIC-HTTP. Các phần flow có thống kê khác nhau có thể rơi vào vùng model đã học cho Benign hoặc lớp tấn công khác.'),
    ('Flow LOIC bị gán Hulk với xác suất cao', 'M0 gán Hulk 99,24%. FIN Flag Cnt bằng 1 tăng điểm Hulk khoảng 5,87. Fwd Pkt Len Max bằng 140 byte tăng thêm khoảng 2,99. Ngược lại, Fwd Seg Size Min bằng 20 byte, tức header TCP nhỏ nhất phía gửi, giảm điểm khoảng 0,76. Tổng tác động vẫn nghiêng về Hulk dù traffic do LOIC tạo ra. Xác suất cao phản ánh quyết định của model, không bảo đảm đúng tên tấn công.'),
    ('Flow LOIC bị gán HOIC với xác suất cao', 'M0 gán HOIC 99,61%. Init Fwd Win Byts bằng 64.240 tăng điểm HOIC khoảng 6,17, còn Dst Port bằng 80 tăng khoảng 0,58. Tot Bwd Pkts bằng 4 là số gói chiều về. Flow Duration bằng 4.257 microsecond là thời lượng flow, khoảng 4,26 mili giây, không phải thời gian chạy cả cuộc thử. Ảnh cho thấy model dựa mạnh vào cửa sổ TCP hơn các đặc trưng còn lại được hiển thị, nên có thể nhầm LOIC thành HOIC.'),
]
sec=doc.sections[0]
sec.top_margin=sec.bottom_margin=Cm(1.5)
sec.left_margin=sec.right_margin=Cm(1.6)
doc.styles['Normal'].font.size=Pt(11)
doc.styles['Normal'].paragraph_format.line_spacing=1.05
for i,(title,explanation) in enumerate(captions,1):
    if i%2==1 and i>1:doc.add_page_break()
    heading(f'Hình {i}. {title}',2)
    from PIL import Image
    img=image_blobs[i-1]; w,h=Image.open(io.BytesIO(img)).size
    width=min(17.8,8.0*w/h)
    p=doc.add_paragraph();p.alignment=1;p.paragraph_format.keep_with_next=True
    p.add_run().add_picture(io.BytesIO(img),width=Cm(width))
    para(explanation)
doc.add_page_break()
heading('Kết luận chung')
para('M0 nhận phần lớn flow GoldenEye đúng tên lớp, nhưng SSH brute force, Hulk-Go, Slowloris và LOIC-HTTP còn bị bỏ sót thành Benign hoặc gán sang loại khác. Tăng tải tạo thêm traffic, chưa khắc phục nhầm nhãn.')
para('Hạn chế của dataset không đơn giản là thiếu tên lớp. Dữ liệu huấn luyện được tạo trong môi trường, phiên bản công cụ và cách trích flow cụ thể, nên chưa chắc đại diện cho lab hiện tại. WTMC2021 ghi nhận lỗi đếm cờ TCP, vấn đề tách flow và Hulk Python gửi Connection: close thay vì giữ kết nối. CNS2022 xác nhận vấn đề Hulk này cũng xuất hiện trong CSE-CIC-IDS2018. Đây là căn cứ nghi ngờ model học dấu hiệu của công cụ hoặc môi trường, không chứng minh mọi lỗi đều do dataset.')
para('Benign xuất hiện vì M0 chỉ nhìn thống kê từng flow. Một đoạn kết nối ngắn hoặc phần đóng TCP có thể không thể hiện hành vi tấn công của cả phiên. Khi đặc trưng khác mẫu train, model có thể chọn Benign hoặc lớp tấn công khác. SHAP giải thích model dựa vào gì, không xác nhận nhãn đó đúng.')
para('Các giá trị SHAP nêu dưới ảnh là đóng góp vào điểm thô của lớp đang giải thích. Số dương tăng điểm lớp, số âm giảm điểm lớp so với giá trị nền. SHAP 5,87 không phải 5,87% và không có trần bằng 1. Fwd và Bwd là hai chiều theo cách extractor xác định hướng flow, không luôn đồng nghĩa với kẻ tấn công và nạn nhân.')
para('Java M0 còn có tổng gói trong flow thấp hơn PCAP ở 8/9 tệp đã kiểm tra. Cần kiểm tra chênh lệch này trước khi quy lỗi chỉ cho model hoặc dataset. Kết quả hiện tại chưa đủ để khẳng định M0 nhận diện ổn định mọi loại tấn công.')
para('Nguồn số liệu là attack_load_audit_20261118.json, kiểm tra ngày 18/11/2026. Tài liệu đối chiếu của DistriNet:')
para('https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html')
para('https://intrusion-detection.distrinet-research.be/CNS2022/CSECICIDS2018.html')
doc.save(args.output)
(A/'report_text.txt').write_text('\n\n'.join(textdraft),encoding='utf-8')
old=[hashlib.sha256(blob).hexdigest() for blob in image_blobs]
new=[hashlib.sha256(doc.part.related_parts[b.get(qn('r:embed'))].blob).hexdigest() for p in doc.paragraphs for b in p._p.xpath('.//a:blip')]
assert all(h in new for h in old) and len(old)==19
print('SAVED',len(doc.paragraphs),'paragraphs;',len(new),'images; original 19 retained')
