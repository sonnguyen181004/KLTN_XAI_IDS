"""Build the Vietnamese M0 report, preserving all 19 original screenshots."""
from pathlib import Path
import json, hashlib, io
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START,WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

H=Path(__file__).resolve().parent
A=H/'output/report_assets'
D=json.loads((H/'attack_load_audit_20261118.json').read_text(encoding='utf-8'))
P=D['pcaps']; doc=Document()
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
def table(headers,rows):
    t=doc.add_table(rows=1,cols=len(headers));t.style='Table Grid'
    for c,s in zip(t.rows[0].cells,headers):c.text=str(s)
    for row in rows:
        for c,s in zip(t.add_row().cells,row):c.text=str(s)
    for row in t.rows:
        pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after=Pt(3)
                for r in p.runs:r.font.size=Pt(10)
    for c in t.rows[0].cells:
        for r in c.paragraphs[0].runs:r.bold=True
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    textdraft.extend([' | '.join(map(str,headers))]+[' | '.join(map(str,r)) for r in rows])
    doc.add_paragraph()
def num(x,n=2):return f'{x:,.{n}f}'.replace(',','X').replace('.',',').replace('X','.')
def stat(k):return P[k]['profiles']['M0']
def pic(path,caption,width=17):
    p=doc.add_paragraph();p.paragraph_format.keep_with_next=True
    p.add_run().add_picture(str(path),width=Cm(width))
    p.alignment=1
    c=doc.add_paragraph(caption,'Caption');c.alignment=1;textdraft.append(caption)

doc.add_heading('BÁO CÁO THỬ NGHIỆM TẤN CÔNG TRONG LAB',0)
para('Mô hình M0 và bộ trích xuất Java CICFlowMeter\nĐối chiếu PCAP, mức tải và các trường hợp nhận nhầm\nNgày kiểm tra 18/11/2026')
heading('1. Phạm vi và kết quả chính')
para('Báo cáo đánh giá M0 trên chín tệp PCAP đã lưu từ các cuộc thử SSH brute force, GoldenEye, Hulk-Go, Slowloris và LOIC-HTTP. Các tệp được trích xuất lại bằng profile Java đang dành cho M0, sau đó dự đoán bằng chính model hiện có. Không huấn luyện lại model, không sửa giá trị đặc trưng để đạt nhãn mong muốn và không tạo thêm traffic trong lần kiểm tra này.')
para('GoldenEye là kịch bản có tỷ lệ nhãn trùng tên công cụ cao nhất trong các lượt đã kiểm tra. Tăng mức đồng thời của Hulk-Go vẫn chủ yếu tạo nhãn HOIC và GoldenEye. Tăng số socket của Slowloris vẫn không tạo nhãn Slowloris. LOIC-HTTP sinh nhiều nhãn Hulk, HOIC và Benign. Các kết quả này cho thấy tăng tải không bảo đảm M0 nhận đúng loại tấn công.')
para('Có hai vấn đề cần xử lý riêng. Thứ nhất, tổng số packet được tính vào flow của Java M0 thấp hơn số packet TCP của cặp máy lab trong tám trên chín PCAP. Thứ hai, ngay với các flow đã được dự đoán, quyết định của model có thể dựa mạnh vào đặc trưng môi trường như cửa sổ TCP, kích thước header và cờ kết thúc kết nối. Chưa có đủ bằng chứng để quy toàn bộ sai lệch cho dataset hoặc cho một đặc trưng duy nhất.')
heading('2. Hệ thống thử nghiệm và cách đối chiếu')
para('Kali 192.168.11.133 tạo traffic tới Ubuntu 192.168.11.134. SSH sử dụng cổng 22 và Apache phục vụ HTTP ở cổng 80. Windows thu gói trên VMnet1 và chạy dashboard M0. Ảnh cấu hình Apache đã xác nhận dịch vụ hoạt động và trả HTTP 200. Việc có request tới server không đồng nghĩa server đã bị làm mất khả năng phục vụ.')
para('M0 là XGBoost 15 lớp, nhận 78 đặc trưng của từng flow. Bộ trích xuất dùng profile m0-current-unverified. Tên này phản ánh việc chưa chứng minh toàn bộ cách tính của phiên bản hiện tại trùng với phiên bản đã tạo dữ liệu huấn luyện gốc. Kiểm tra lần này xác nhận đúng thứ tự 78 cột và các giá trị hữu hạn của tập flow lab được thống kê. Điều đó chưa chứng minh mọi đặc trưng có cùng quy ước lịch sử với dataset.')
para('PCAP được chuyển sang định dạng pcap bằng editcap, đọc gói bằng tshark và trích xuất lại bằng Java. Chỉ giữ flow TCP giữa đúng hai IP lab, với cổng dịch vụ 22 hoặc 80 ở một trong hai đầu. Cách lọc hai chiều giữ được cả phần kết thúc TCP bị tách thành flow ngược chiều. Vì vậy, số flow trong báo cáo có thể khác ảnh dashboard chụp khi phiên chưa kết thúc hoặc ảnh chỉ lọc chiều đi tới server.')
para('Các tỷ lệ bên dưới là phân bố dự đoán trong phạm vi kịch bản. Chúng chưa phải accuracy hoặc FPR đã xác nhận bằng nhãn chuẩn cho từng flow. Một phiên công cụ có thể chứa flow khởi tạo, kết thúc hoặc yêu cầu chưa hoàn chỉnh. Thời gian PCAP là khoảng từ gói TCP lab đầu tiên tới gói cuối cùng, không phải thời gian lệnh chạy được chứng minh bằng log.')
heading('3. Mức tải đã thay đổi như thế nào')
table(['Công cụ','Mức đầu','Mức tăng','Ý nghĩa'],[
['GoldenEye','1 worker, 2 socket mỗi worker','2 worker, 5 socket mỗi worker','Mức đồng thời cấu hình từ 2 lên 10 socket; không bảo đảm request/giây tăng 5 lần.'],
['Hulk-Go','HULKMAXPROCS=3; 30 giây','HULKMAXPROCS=6; 30 giây','Tăng giới hạn đồng thời từ 3 lên 6.'],
['Slowloris','5 socket; nghỉ 10 giây; 60 giây','10 socket; nghỉ 10 giây; 60 giây','Gấp đôi socket mục tiêu, giữ khoảng gửi header và thời lượng.'],
['LOIC-HTTP','Không có PCAP mức đầu để ghép cặp','Ảnh cho thấy 5 thread, ô socket/thread 25','Thanh Speed không quy đổi trực tiếp thành request/giây.']])
para('Thông số cấu hình được đối chiếu với câu lệnh và ảnh đã lưu trong phiên làm việc. PCAP tự nó không chứng minh số worker hoặc biến môi trường đã đặt. Các file có hậu tố 2 được người thực hiện xác nhận là lượt tăng tải. GoldenEye từng có cả lệnh 30 giây và 120 giây, nhưng dos_oldeney.pcapng chỉ chứa khoảng 28 giây traffic lab nên báo cáo không coi đây là bản ghi đầy đủ của lượt 120 giây.')
rows=[]
for k in P:
    v=P[k];rows.append([v['file'],num(v['span_seconds']),v['lab_tcp_packets'],v['tcp_streams'],v['http_requests'],num(v['http_requests_per_capture_second'])])
table(['PCAP','Khoảng bắt (s)','Gói TCP','Kết nối TCP','Request HTTP','Request/s'],rows)
para('Request HTTP được đếm từ trường giải mã của tshark, đã kiểm tra các lần xuất hiện trong từng gói. Slowloris không có request hoàn chỉnh được giải mã trong hai PCAP, nhưng server trả 408 và 400. Vì vậy, giá trị request bằng 0 không có nghĩa công cụ không gửi byte hoặc không mở kết nối. TCP stream cũng không đồng nhất với flow của CICFlowMeter.')
for title,k1,k2 in [('GoldenEye','dos_oldeney','oldeneye2'),('Hulk-Go','hulk-go','hulk2')]:
    a,b=P[k1],P[k2];ratio=b['http_requests_per_capture_second']/a['http_requests_per_capture_second']
    para(f'{title} tăng từ {num(a["http_requests_per_capture_second"])} lên {num(b["http_requests_per_capture_second"])} request/s tính trên khoảng bắt, tương đương {num(ratio)} lần. Đây là tải quan sát được, khác với hệ số tăng tham số của công cụ.')
para('Slowloris tăng từ 10 lên 20 kết nối TCP trong PCAP, từ 163 lên 337 gói. Số phản hồi 408 tăng từ 5 lên 10 và số phản hồi 400 cũng tăng từ 5 lên 10. Lượt tăng tải tạo thêm kết nối nhưng không làm thay đổi loại phản hồi quan sát được.')
pic(A/'load_chart.png','Biểu đồ 1. Tải quan sát từ PCAP trước và sau khi tăng tham số.')

heading('4. Kết quả dự đoán M0 trên PCAP')
expected={'ssbrute':'SSH-Bruteforce','ss2':'SSH-Bruteforce','dos_oldeney':'DoS attacks-GoldenEye','oldeneye2':'DoS attacks-GoldenEye','hulk-go':'DoS attacks-Hulk','hulk2':'DoS attacks-Hulk','slowloris1':'DoS attacks-Slowloris','slowloris2':'DoS attacks-Slowloris','LOIC':'DDOS attack-LOIC-HTTP'}
rows=[]
for k in P:
    s=stat(k);n=s['lab_valid'];yes=s['labels'].get(expected[k],0);ben=s['labels'].get('Benign',0)
    rows.append([k,n,yes,num(100*yes/n)+'%',ben,n-yes-ben])
table(['Lượt','Flow hợp lệ','Trùng tên loại','Tỷ lệ trùng','Benign','Tấn công khác'],rows)
para('Không có flow không hữu hạn trong tập flow lab ở bảng này. Cột trùng tên loại chỉ đối chiếu tên lớp model với tên kịch bản, không thay thế kiểm tra nhãn chuẩn. Đặc biệt, nhãn SSH xuất hiện trên một phần kết thúc kết nối không đủ để kết luận toàn bộ hành vi brute force đã được phát hiện đúng.')
heading('4.1. SSH brute force bằng Hydra và Patator',2)
para('Hydra dùng 20 mật khẩu sai với một task. Nhật ký Ubuntu cho thấy nhiều lần xác thực thất bại. PCAP ssbrute có 201 gói TCP lab, nhưng tổng gói được Java M0 đưa vào flow là 195. Cả 5 flow được lọc đều có nhãn Benign. Đây là bằng chứng model không cảnh báo các flow này, dù log phía server đã ghi nhận thử mật khẩu sai.')
para('Patator cũng dùng danh sách 20 mật khẩu sai, một thread và không retry. Nhật ký đã ghi 18 lần xác thực thất bại cùng 2 lỗi phiên. PCAP ss2 có 160 gói và 3 kết nối TCP. Java M0 tạo 4 flow lab, gồm 3 Benign và 1 SSH-Bruteforce. Flow SSH có thể là phần phụ do tách kết nối, không phải 1 trong 4 cuộc tấn công độc lập. Lần kiểm tra trước đã ghi nhận một phần kết thúc chỉ có hai gói. Không được diễn giải kết quả này thành phát hiện đúng 25% số lần thử mật khẩu.')
para('M0 nhận thống kê flow, không đọc được mật khẩu bên trong SSH mã hóa và không trực tiếp nhận chuỗi sự kiện Failed password từ Ubuntu. Nhiều lần thử có thể diễn ra trong cùng kết nối. Khi số gói, thời gian và kích thước khác dữ liệu học, model có thể chọn Benign. Việc đổi Hydra sang Patator không bảo đảm tái tạo cùng phiên bản SSH, nhịp xác thực hoặc cách đóng flow của dataset. Hình 1 là ảnh lịch sử có IP khác nên được giữ để minh họa, không dùng làm số liệu của hai PCAP này.')
heading('4.2. GoldenEye',2)
for k in ['dos_oldeney','oldeneye2']:
    s=stat(k);para(f'{P[k]["file"]} có {s["lab_valid"]} flow lab. Phân bố M0 gồm '+', '.join(f'{n} {lab}' for lab,n in s['labels'].items())+'.')
para('Tỷ lệ nhãn GoldenEye giảm từ 98,06% xuống 94,31% dù tải request tăng. Số flow tăng không kéo theo tỷ lệ nhận đúng tên công cụ tăng. Trung vị thời lượng flow tăng từ khoảng 0,323 lên 0,596 giây. Khác biệt số flow giữa kết nối và Java ở lượt tăng tải cho thấy cần kiểm tra thêm cách tách flow khi kết nối đóng.')
para('Trong một flow GoldenEye được lấy lại từ oldeneye2, SHAP cho thấy Fwd Seg Size Min bằng 32 có đóng góp khoảng 7,07 và Bwd Pkt Len Std khoảng 608,43 có đóng góp khoảng 4,49 vào điểm lớp GoldenEye. Đặc trưng thứ nhất liên quan header TCP phía gửi, đặc trưng thứ hai mô tả độ phân tán kích thước gói phía trả lời. Đây là lý do model tăng điểm lớp ở mẫu cụ thể, chưa phải bằng chứng rằng hai giá trị đó tự định nghĩa một cuộc tấn công. Các hình 2 đến 5 thể hiện lệnh chạy, kết quả và các ca giải thích khác nhau.')
heading('4.3. Hulk-Go',2)
para('Ở mức đầu, M0 trả 275 HOIC, 36 GoldenEye, 30 Benign và 2 Hulk trên 343 flow lab. Ở mức tăng tải, kết quả là 1.301 HOIC, 719 GoldenEye, 450 Benign và 5 Hulk trên 2.475 flow. Tỷ lệ nhãn Hulk chỉ khoảng 0,58% ở mức đầu và 0,20% ở mức tăng. Phần lớn flow bị nhận sang loại khác, không phải tất cả đều bị coi là bình thường.')
para('PCAP mức đầu có 6.855 request với Connection giữ kết nối. Kiểm tra trước ghi nhận 285 kết nối chứa nhiều hơn một request. Trong dữ liệu train M0 đã kiểm tra, 155.042 mẫu Hulk có cửa sổ TCP ban đầu tập trung ở 225, 26.883 hoặc 0, không có 64.240. Traffic lab dùng 64.240. Khác biệt này là bằng chứng lệch phân bố, nhưng không tự chứng minh riêng cửa sổ TCP gây mọi lỗi.')
para('Một mẫu Hulk-Go tăng tải bị gán HOIC có đóng góp SHAP của Init Fwd Win Byts bằng 64.240 khoảng 6,05 vào điểm HOIC. Một mẫu khác nhận GoldenEye có đóng góp lớn từ kích thước header và độ phân tán gói phản hồi. Vì thế, việc công cụ được gọi là Hulk không ép vector đặc trưng rơi vào vùng model đã học cho Hulk. M0 đang phân loại thống kê của flow, không nhận diện tên tiến trình trên Kali. Các hình 6 đến 11 minh họa log server và các nhãn khác nhau trong cùng phiên.')
heading('4.4. Slowloris',2)
para('Mức đầu tạo 16 flow Java, gồm 12 Benign và 4 Hulk. Mức tăng tải tạo 36 flow, gồm 33 Benign và 3 Hulk. Không có nhãn Slowloris ở cả hai mức. Tỷ lệ Benign tăng từ 75,00% lên 91,67%, nhưng chỉ có một lượt ở mỗi mức nên chưa thể kết luận tăng socket luôn làm model kém hơn.')
para('Cả hai PCAP đều chứa phản hồi 408 và 400. Trung vị thời lượng flow M0 gần như giữ nguyên, khoảng 19,53 và 19,37 giây. Trong 3.620 mẫu Slowloris của train M0 đã được kiểm tra trước, trung vị thời lượng khoảng 106,30 giây. Như vậy, thêm socket chủ yếu tạo thêm kết nối có cùng kiểu tồn tại ngắn trong lab, không làm từng flow giống mẫu điển hình của dataset. Chưa đọc cấu hình timeout Apache trong VM nên không khẳng định chính xác module hoặc tham số nào đã đóng kết nối.')
para('Ở một flow mức tăng tải bị gán Hulk, FIN Flag Cnt bằng 1 đóng góp khoảng 5,87 và Fwd Pkt Len Max bằng 168 đóng góp khoảng 2,99 vào điểm Hulk. Cờ FIN là tín hiệu kết thúc TCP, không phải bằng chứng riêng của Hulk. Đây là ví dụ model dùng mẫu đặc trưng đã học để chọn nhãn không đúng tên kịch bản. Hình 12 đến 15 cho thấy lệnh Slowloris, tổng kết và hai lời giải thích khác nhau.')
heading('4.5. LOIC-HTTP',2)
para('PCAP LOIC ghi khoảng 142,12 giây traffic lab, 36.995 kết nối TCP và 36.995 request HTTP. Không thể coi đây là lượt đã dừng đúng 30 giây. Java M0 tách thành 52.641 flow lab, gồm 22.323 Hulk, 21.302 Benign và 9.016 HOIC. Không có nhãn LOIC-HTTP. Số flow lớn hơn số kết nối cho thấy cần phân biệt kết nối hoàn chỉnh với các phần mà extractor tách ra.')
para('Ở mẫu LOIC bị gán Hulk, FIN và kích thước gói phía gửi có đóng góp dương lớn. Ở mẫu bị gán HOIC, cửa sổ TCP ban đầu có đóng góp lớn. Các hình 16 đến 19 minh họa đúng việc LOIC đang chạy nhưng model trả nhãn khác. LOIC không chạy được công cụ Hulk. Nhãn Hulk trên dashboard là kết quả dự đoán, không phải bằng chứng người thực hiện đã chuyển sang Hulk. Một nguồn Kali cũng chưa tái hiện tính phân tán của một cuộc DDoS nhiều máy.')

heading('5. Vì sao nhiều flow tấn công lại được dự đoán Benign')
para('Tên cuộc thử là thông tin của người tổ chức. M0 chỉ nhận 78 số đo của từng flow. Model không nhìn thấy lệnh GoldenEye, Hulk-Go hay Slowloris, không nhận log xác thực và không trực tiếp nhận tổng số kết nối của nguồn trong một cửa sổ thời gian. Một chuỗi nhiều kết nối có thể gây nghi vấn khi xem chung nhưng từng flow riêng lẻ vẫn được model xếp vào Benign.')
para('Tăng tải có hai tác động khác nhau. Nó có thể tăng số flow mỗi giây, đồng thời thay đổi thời gian, số gói và phản hồi trong từng flow. M0 chỉ khai thác được những thay đổi có mặt trong vector đầu vào. Nếu chỉ tăng số bản sao của kiểu flow mà model đang nhận sai, hệ thống có thể tạo nhiều nhãn sai hơn. Kết quả Slowloris và Hulk-Go trong báo cáo phù hợp với khả năng này, nhưng cần lặp lại nhiều lượt để kiểm chứng xu hướng.')
para('Khác biệt môi trường còn gồm phiên bản công cụ, thư viện HTTP, hệ điều hành, TCP window, nội dung trang web, phiên bản SSH, chính sách đóng kết nối và vị trí bắt gói. Thay đổi server hoặc extractor có thể đổi vector dù mục đích cuộc thử không thay đổi. Các mẫu SHAP đã kiểm tra cho thấy model nhạy với một số yếu tố này. SHAP giải thích quyết định model, không chứng minh nguyên nhân vật lý của cuộc tấn công.')
heading('5.1. Những gì tài liệu về dataset cho phép kết luận',2)
para('Tài liệu WTMC2021 ghi nhận lỗi đếm cờ TCP và vấn đề tách flow khi gặp FIN. Cùng tài liệu mô tả Hulk dùng Python urllib2 đã gửi Connection: close thay vì giữ kết nối. Tài liệu CNS2022 xác nhận Hulk của CSE-CIC-IDS2018 chịu cùng vấn đề [1, 2]. Do đó, Hulk-Go giữ kết nối trong lab không phải bản sao tương đương của traffic Hulk lịch sử. Các phát hiện này hỗ trợ giả thuyết lệch dữ liệu, chưa xác định mức đóng góp của từng lỗi vào model M0.')
para('Không thể kết luận dataset thiếu nhãn chỉ vì model không trả nhãn đó. Bằng chứng hiện có cho thấy mô hình có tên các lớp nhưng các mẫu lab không được xếp vào chúng. Việc thiếu đại diện cho công cụ, server và mức tải mới khác với việc thiếu một lớp trong danh mục. Muốn kết luận lỗi nhãn ở đúng bộ train M0, cần truy vết mẫu train tới PCAP và pipeline tạo bộ dữ liệu đó.')
heading('5.2. Giới hạn trích xuất cần ghi nhận',2)
rows=[]
for k,v in P.items():
    s=stat(k);rows.append([k,v['lab_tcp_packets'],s['lab_flow_packet_sum'],v['lab_tcp_packets']-s['lab_flow_packet_sum']])
table(['Lượt','Gói TCP trong PCAP','Tổng gói trong flow M0','Chênh lệch'],rows)
para('Chênh lệch ở bảng này là thiếu trong việc hạch toán gói vào các flow Java, không phải bằng chứng Wireshark làm mất gói khi capture. Gói đã có trong PCAP nhưng không được phản ánh đầy đủ trong tổng bộ đếm flow. Lần rà soát này chưa định vị chính xác từng gói bị bỏ qua nên chưa kết luận tất cả chênh lệch đều do FIN hoặc retransmission. Vì vậy, không nên tuyên bố bước trích xuất M0 đã hoàn toàn đúng với dataset.')
para('Kết quả nạp model còn có cảnh báo khác phiên bản thư viện so với lúc lưu artifact. Phiên kiểm tra vẫn trả dự đoán, nhưng cần cố định môi trường và đối chiếu một tập đầu vào chuẩn trước khi dùng số liệu làm kết quả cuối của luận văn. Báo cáo không dùng việc chạy thành công để phủ nhận cảnh báo tương thích.')
heading('6. Cách đọc các ảnh và giá trị SHAP')
para('Xác suất lớp thắng là đầu ra model, không phải xác suất đã xác minh rằng cuộc tấn công thực sự xảy ra. SHAP trong hệ thống giải thích điểm thô của lớp được chọn. Giá trị 5,87 không phải 5,87% và không có trần bằng 1. Thanh dương đẩy điểm lớp lên, thanh âm kéo điểm xuống so với giá trị nền. Phải đọc kèm tên lớp đang được giải thích.')
table(['Đặc trưng','Nội dung đo','Điều không thể suy ra riêng lẻ'],[
['Init Fwd Win Byts','Cửa sổ TCP ban đầu phía gửi','Không tự chứng minh HOIC hoặc Hulk.'],
['FIN Flag Cnt','Số cờ FIN theo quy ước extractor','Kết nối bình thường cũng kết thúc bằng FIN.'],
['Fwd Seg Size Min','Kích thước header/segment tối thiểu phía gửi theo extractor','Không phải số worker của công cụ.'],
['Bwd Pkt Len Std','Độ lệch chuẩn kích thước gói chiều về','Có thể bị chi phối bởi nội dung và cách server trả lời.'],
['Flow Duration','Thời gian từ đầu tới cuối flow, đơn vị microsecond trong đầu vào này','Không đồng nhất với thời gian chạy cả cuộc thử.']])
para('Các mẫu SHAP bổ sung được lấy theo quy tắc cố định, chọn dòng đầu tiên của từng nhãn phổ biến trong CSV đã tái trích xuất. Đây là ví dụ cục bộ, không phải trung bình SHAP toàn cuộc thử. Các ảnh cũ giữ nguyên trạng thái và số đếm tại lúc chụp. Không trộn số đếm trên ảnh với kết quả offline mới để tạo một bảng tổng giả định.')
heading('7. Kết luận và công việc tiếp theo')
para('M0 đã chạy được chuỗi bắt gói, tạo flow, dự đoán và hiển thị giải thích. GoldenEye có kết quả nhận dạng tên lớp tốt trong các PCAP này. Khả năng khái quát sang SSH brute force, Hulk-Go, Slowloris và LOIC-HTTP còn hạn chế. Việc tăng tải đã được xác nhận bằng số gói, kết nối và request, nhưng chưa khắc phục nhầm nhãn.')
para('Ưu tiên tiếp theo là truy vết các gói chưa được tính vào flow M0, kiểm tra quy ước FIN, hướng flow và phần kết thúc kết nối trên PCAP cố định. Sau đó mới đánh giá lại model trên cùng dữ liệu. Không ép cờ TCP về một giá trị chỉ vì giá trị đó làm model trả đúng tên tấn công.')
para('Để đánh giá thực tế, cần giữ log công cụ và log server cùng mốc thời gian, phân loại flow khởi tạo và kết thúc, thu traffic bình thường đối chứng, rồi lặp mỗi cấu hình nhiều lượt. Chỉ khi có nhãn đủ tin cậy mới tính precision, recall và FPR. Nên bổ sung đánh giá theo phiên hoặc cửa sổ thời gian để xem hành vi lặp lại của nguồn, nhưng kết quả của tầng này phải tách khỏi dự đoán từng flow của M0.')
heading('8. Nguồn số liệu và khả năng chạy lại')
para('Số liệu mới được lưu trong attack_load_audit_20261118.json. Script audit_attack_loads.py tái trích xuất PCAP và dự đoán. Script enrich_attack_load_audit.py kiểm lại số request và lấy ví dụ SHAP. Báo cáo này chỉ sử dụng phần M0. CSV gói, CSV Java gốc và 78 đặc trưng kèm dự đoán được lưu tại output/attack_load_report_20261118. Sổ lệnh chạy lab nằm trong README.md cùng thư mục.')
para('Mã SHA-256 của model M0 dùng trong lần kiểm tra là '+D['models']['M0']['sha256']+'. Checksum từng PCAP nằm trong JSON kết quả, giúp tránh nhầm khi thay tệp cùng tên.')
para('[1] DistriNet. Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study, Extended Documentation. https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html. Truy cập ngày 18/11/2026.')
para('[2] DistriNet. Error Prevalence in NIDS datasets, Improved CSE-CIC-IDS2018 Documentation. https://intrusion-detection.distrinet-research.be/CNS2022/CSECICIDS2018.html. Truy cập ngày 18/11/2026.')

captions=[
('SSH brute force trong ảnh lịch sử','Ảnh hiển thị 105 flow, 103 Benign và 2 SSH-Bruteforce. Địa chỉ trên ảnh là 192.168.64.143 và 192.168.64.142, khác cặp máy 192.168.11.133 và 192.168.11.134 trong PCAP được kiểm tra lần này. Ảnh được giữ làm bằng chứng lịch sử, không dùng 105 flow này để tính kết quả của ssbrute hoặc ss2.'),
('Lệnh GoldenEye và bộ đếm của công cụ','Ảnh ghi lệnh GoldenEye với giới hạn 30 giây và các dòng đếm request. Bộ đếm công cụ phản ánh hoạt động phía phát, không phải số flow model nhận được. Cần đối chiếu PCAP và log server để xác định những yêu cầu đã đi qua mạng và có phản hồi.'),
('Dashboard M0 trong lượt GoldenEye','Tại lúc chụp, dashboard có 742 flow, gồm 186 Benign và 556 cảnh báo. Nhãn GoldenEye chiếm phần lớn cảnh báo nhưng vẫn có nhãn khác. Trạng thái capturing cho biết số đếm chưa phải tổng cuối phiên. Kết quả PCAP tái trích xuất được trình bày riêng ở mục 4.2.'),
('Một flow GoldenEye bị dự đoán Benign','Ảnh hiển thị Benign với xác suất 96,25%. Biểu đồ giải thích dành cho lớp Benign, vì vậy các đóng góp dương đang nâng điểm Benign. Xác suất cao không xác nhận traffic thật là bình thường. Cần xem flow này thuộc phần gửi yêu cầu, phần đóng kết nối hay traffic khác trong phiên.'),
('Một flow được dự đoán GoldenEye','Ảnh hiển thị GoldenEye với xác suất 94,08%. Kích thước header phía gửi và các thống kê chiều về có ảnh hưởng tới điểm lớp. Đây là một ca nhận đúng tên kịch bản, nhưng không đại diện cho toàn bộ flow của lượt chạy.'),
('Apache ghi nhận request từ Kali trong lượt Hulk-Go','Log cho thấy Ubuntu nhận nhiều HTTP GET từ 192.168.11.133 và trả mã 200. Điều này xác nhận request đến server. Mã 200 và log request chưa chứng minh server bị quá tải hoặc mất dịch vụ. Muốn kết luận tác động phải có phép đo độ trễ và khả năng phục vụ khách hợp lệ.'),
('Lệnh Hulk-Go với mức đồng thời ban đầu','Ảnh ghi HULKMAXPROCS=3 và giới hạn 30 giây. Exit code 124 xuất hiện khi lệnh timeout kết thúc lượt theo giới hạn. Đây không tự động là lỗi tấn công chưa chạy. Lượt tăng tải đổi giới hạn đồng thời lên 6, còn tên công cụ vẫn là Hulk-Go.'),
('Các nhãn M0 sau lượt Hulk-Go','Ảnh tổng kết có 352 flow, gồm 39 Benign và 313 cảnh báo, với HOIC chiếm phần lớn. Một số dòng còn có địa chỉ ngoài cặp máy lab. Vì vậy, số tổng trên ảnh khác bảng đã lọc PCAP. Tên công cụ Hulk-Go không đồng nghĩa tất cả cảnh báo phải có tên Hulk.'),
('Flow Hulk-Go được gán HOIC','Ảnh cho thấy HOIC có xác suất 65,54%, cao hơn các lớp còn lại. Model đã cảnh báo nhưng phân loại khác tên cuộc thử. Đây là lỗi phân biệt loại khi flow được xác nhận thuộc kịch bản, khác với bỏ sót thành Benign.'),
('Một flow trong phiên được gán Hulk','Ảnh hiển thị Hulk 77,02% và biểu đồ SHAP. Một flow nhận đúng tên Hulk không phủ nhận việc đa số flow khác bị gán HOIC. Cần đọc kết quả toàn bộ tập flow đã lọc, không chọn riêng một ảnh đúng để kết luận cuộc thử thành công.'),
('SHAP của mẫu bị gán HOIC','Trong ảnh, cửa sổ TCP ban đầu phía gửi có đóng góp dương nổi bật vào lớp HOIC. Đây là lời giải thích cho quyết định của M0. Nó không chứng minh máy Kali thực sự chạy HOIC và cũng không chứng minh giá trị cửa sổ đó chỉ tồn tại ở HOIC trong train.'),
('Slowloris giữ các kết nối chưa hoàn tất','Ảnh ghi 5 socket, gửi tiếp header sau mỗi 10 giây và giới hạn 60 giây. Có thời điểm công cụ phải tạo lại socket. Việc giữ kết nối chậm tạo ít request hoàn chỉnh, nên không thể dùng số request HTTP hoàn chỉnh để kết luận công cụ không hoạt động.'),
('M0 không tạo nhãn Slowloris ở mức đầu','Ảnh tổng kết 16 flow gồm 12 Benign và 4 Hulk, không có Slowloris. Số liệu này phù hợp kết quả tái trích xuất của slowloris1. Bốn cảnh báo cho thấy M0 nhận thấy mẫu khác Benign ở một số flow, nhưng vẫn gán sai tên loại.'),
('SHAP của flow Slowloris bị gán Benign','Ảnh cho thấy Benign 87,85%. Đặc trưng chiều gửi và thời gian của phần flow đang xem ảnh hưởng tới điểm lớp. Những phần kết thúc rất ngắn có thể khác xa kết nối giữ chậm đầy đủ. Không dùng riêng ảnh này để kết luận toàn bộ phiên Slowloris là traffic thường.'),
('SHAP của flow Slowloris bị gán Hulk','Ảnh hiển thị Hulk 60,14%, với FIN Flag Cnt có đóng góp dương lớn. FIN chỉ thể hiện đóng kết nối. Kết quả minh họa việc M0 có thể dựa vào dấu hiệu đóng TCP để chọn Hulk dù công cụ thực tế là Slowloris.'),
('Giao diện LOIC-HTTP đang hoạt động','Đích trên ảnh là Ubuntu 192.168.11.134, phương thức HTTP và cổng 80. Nút Stop flooding cho thấy công cụ đang chạy. LOIC là công cụ riêng, không phải chế độ chạy Hulk. Timeout trong giao diện không được hiểu là thời lượng tự dừng toàn cuộc thử.'),
('Dashboard trong lúc dừng lượt LOIC','Ảnh ghi 3.814 flow, 1.560 Benign và 2.254 cảnh báo, trạng thái stopping. Đây là số đếm tại lúc chụp và chưa tương đương toàn bộ PCAP dài khoảng 142 giây. Không dùng số này thay cho kết quả offline 52.641 flow lab.'),
('Flow LOIC bị gán Hulk với xác suất cao','Ảnh cho thấy Hulk 99,24%, với đóng góp lớn từ FIN và kích thước gói phía gửi. Xác suất cao vẫn có thể đi kèm nhầm tên loại khi traffic mới nằm khác phân bố huấn luyện. Không đổi nhãn chuẩn của cuộc thử thành Hulk chỉ để khớp dashboard.'),
('Flow LOIC bị gán HOIC với xác suất cao','Ảnh hiển thị HOIC 99,61%. Cửa sổ TCP ban đầu có đóng góp lớn trong lời giải thích. Cùng một công cụ LOIC có thể tạo nhiều dạng flow nên model trả nhiều nhãn. Cần giữ cả các ca Benign, Hulk và HOIC khi báo cáo, thay vì chỉ giữ ảnh có cảnh báo.')]
sec=doc.add_section(WD_SECTION_START.NEW_PAGE);sec.orientation=WD_ORIENT.LANDSCAPE
sec.page_width=Cm(29.7);sec.page_height=Cm(21);sec.top_margin=sec.bottom_margin=Cm(1.5);sec.left_margin=sec.right_margin=Cm(1.7)
for i,(title,explanation) in enumerate(captions,1):
    if i>1:doc.add_page_break()
    heading(f'Hình {i}. {title}')
    from PIL import Image
    img=A/(str(i)+'.png'); w,h=Image.open(img).size
    width=min(26.0,11.6*w/h)
    pic(img,f'Hình {i}. Ảnh gốc do người thực hiện lưu trong báo cáo.',width)
    para(explanation)
doc.save(H/'bcao_tancon.docx')
(A/'report_text.txt').write_text('\n\n'.join(textdraft),encoding='utf-8')
orig=Document(A/'original.docx')
old=[hashlib.sha256(orig.part.related_parts[b.get(qn('r:embed'))].blob).hexdigest() for p in orig.paragraphs for b in p._p.xpath('.//a:blip')]
new=[hashlib.sha256(doc.part.related_parts[b.get(qn('r:embed'))].blob).hexdigest() for p in doc.paragraphs for b in p._p.xpath('.//a:blip')]
assert all(h in new for h in old) and len(old)==19
print('SAVED',len(doc.paragraphs),'paragraphs;',len(new),'images; original 19 retained')
