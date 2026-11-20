from pathlib import Path
import re, shutil, json, math
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent.parent
QA=ROOT/'Report/.qa_ch34'; QA.mkdir(exist_ok=True)
OUT=ROOT/'Chuong_3_4_Phuong_phap_va_Ket_qua_VI_den_trang.docx'
BACK=QA/'before_revision.docx'
if not BACK.exists(): shutil.copy2(OUT,BACK)
d=Document(BACK); ps=list(d.paragraphs)

def diagram(name, height, boxes, arrows):
    im=Image.new('RGB',(1800,height),'white'); dr=ImageDraw.Draw(im)
    regular='C:/Windows/Fonts/arial.ttf'; bold='C:/Windows/Fonts/arialbd.ttf'
    for pts in arrows:
        dr.line(pts, fill='black',width=5)
        x,y=pts[-1]; px,py=pts[-2]; a=math.atan2(y-py,x-px)
        dr.polygon([(x,y),(x-19*math.cos(a-.45),y-19*math.sin(a-.45)),(x-19*math.cos(a+.45),y-19*math.sin(a+.45))],fill='black')
    for (x,y,w,h,title,body) in boxes:
        dr.rectangle((x,y,x+w,y+h),fill='white',outline='black',width=3)
        ft=ImageFont.truetype(bold,38); fb=ImageFont.truetype(regular,36)
        dr.text((x+w/2,y+23),title,font=ft,fill='black',anchor='mt')
        for j,line in enumerate(body.split('\n')):
            dr.text((x+w/2,y+78+j*44),line,font=fb,fill='black',anchor='mt')
    im.save(QA/name,dpi=(300,300))

diagram('research.png',1040,[
 (120,30,1560,155,'DỮ LIỆU VÀ PHẠM VI','CSE-CIC-IDS2018 • 78 đặc trưng • 15 lớp'),
 (120,245,1560,195,'RQ1   SO SÁNH VÀ CHỌN MÔ HÌNH','Thử siêu tham số Random Forest và XGBoost\nSo sánh chỉ số phân loại và ghi rõ giới hạn cách chọn cấu hình'),
 (120,500,1560,195,'RQ2   ĐÁNH GIÁ SHAP VÀ LIME','Giữ nguyên mô hình • cố định tập mẫu và cấu hình\nĐồng thuận, mức khớp cục bộ, ổn định và độ trung thực'),
 (120,755,1560,220,'RQ3   TRIỂN KHAI VÀ KIỂM THỬ NGUYÊN MẪU','CSV, PCAP và bắt trực tiếp dùng chung mô hình\nKiểm tra pipeline, giao diện, vòng đời capture và tài nguyên\nPhân tích cảnh báo thực tế trong phạm vi có bằng chứng')
], [[(900,185),(900,245)],[(900,440),(900,500)],[(900,695),(900,755)]])
diagram('architecture.png',1550,[
 (35,25,510,180,'CSV ĐẶC TRƯNG','Dữ liệu có sẵn\nKhông trích xuất lại gói'),
 (645,25,510,180,'TỆP PCAP','Gói tin đã lưu\nTrích xuất ngoại tuyến'),
 (1255,25,510,180,'CARD MẠNG','Bắt trực tiếp bằng Npcap\nTiến trình capture'),
 (645,275,1120,180,'BỘ TRÍCH XUẤT FLOW','Gom gói theo vòng đời flow • tính đặc trưng\nXuất CSV và metadata khi flow được đóng'),
 (35,530,1730,180,'CHUẨN HÓA VÀ API DỰ ĐOÁN','Bộ cấp dữ liệu gửi flow • kiểm tra 78 cột, thứ tự và đơn vị\nXGBoost trả nhãn, xác suất • lưu flow và cảnh báo vào SQLite'),
 (35,790,810,215,'SHAP CHẠY NỀN','Cảnh báo vào hàng đợi tối đa 200 tác vụ\nLuồng nền tính SHAP và các cờ lưu ý\nHàng đợi đầy vẫn giữ dự đoán, cảnh báo'),
 (955,790,810,215,'LIME THEO YÊU CẦU','Chỉ chạy khi người dùng yêu cầu\nKiểm tra vùng mẫu và mô hình cục bộ\nThông báo rõ khi chưa giải thích được'),
 (35,1090,1730,180,'LƯU TRỮ VÀ GIAO DIỆN','SQLite lưu kết quả • Streamlit truy vấn qua API\nHiển thị flow, dự đoán, SHAP, LIME và nhánh lưu ý A hoặc B'),
 (35,1340,1730,170,'ĐIỀU KHIỂN CAPTURE DO API QUẢN LÝ','Giao diện gửi lệnh bắt hoặc dừng • API quản lý capture và bộ cấp dữ liệu\nTheo dõi trạng thái, ngăn phiên trùng • làm mới trang không tạo phiên mới')
], [[(900,205),(900,275)],[(1510,205),(1510,275)],[(290,205),(290,530)],[(1200,455),(1200,530)],[(430,710),(430,790)],[(1360,710),(1360,790)],[(430,1005),(430,1090)],[(1360,1005),(1360,1090)]])

changes={
3:'Nghiên cứu giải quyết ba câu hỏi RQ1, RQ2 và RQ3 theo trình tự lựa chọn mô hình, đánh giá phương pháp giải thích và tích hợp vào nguyên mẫu IDS. Đơn vị phân tích là flow mạng được biểu diễn bằng 78 đặc trưng số. Hình 3.1 trình bày quan hệ giữa các giai đoạn.',
4:'RQ1 khảo sát siêu tham số của Random Forest và XGBoost trên CSE-CIC-IDS2018, so sánh kết quả phân loại rồi xác định mô hình dùng cho các giai đoạn sau. Việc đánh giá sử dụng accuracy, precision, recall, F1 theo lớp và trung bình macro. Tỷ lệ báo nhầm trên Benign được tách khỏi tỷ lệ bỏ sót tấn công. Kết quả và giới hạn của quy trình lựa chọn được trình bày ở mục 4.3.',
5:'RQ2 giữ nguyên mô hình được triển khai để so sánh TreeSHAP và LIME Tabular trên cùng các flow và cùng lớp cần giải thích. Tập chính gồm 1.339 flow dự đoán đúng. Tập 151 flow dự đoán sai được phân tích riêng. Các phép đánh giá gồm mức đồng thuận đặc trưng, mức khớp cục bộ của LIME, độ ổn định qua seed và nhiễu đầu vào, cùng độ trung thực theo phép thay thế đặc trưng.',
6:'RQ3 tích hợp mô hình và các bộ giải thích vào nguyên mẫu sử dụng FastAPI, SQLite và Streamlit. Ba đường nhập liệu gồm CSV, PCAP và bắt trực tiếp dùng chung mô hình dự đoán. Kiểm thử tập trung vào đối soát dữ liệu, quản lý tiến trình, trạng thái giải thích và tài nguyên. Phân tích lưu lượng thực tế làm rõ giới hạn của dự đoán ngoài miền huấn luyện, chưa thay thế đánh giá với nhãn tấn công được xác minh.',
13:'Nghiên cứu sử dụng các tệp dữ liệu đã xử lý từ CSE-CIC-IDS2018. Bài toán của dự án gồm 15 nhãn, trong đó có Benign và 14 nhãn tấn công. Các nhóm gồm DoS, DDoS, vét cạn mật khẩu FTP và SSH, tấn công web, Bot và Infilteration. Tên Infilteration được giữ theo bộ mã hóa nhãn của dự án. Mỗi flow có 78 đặc trưng đầu vào, bao gồm thời lượng, số gói, độ dài gói, cờ TCP, khoảng thời gian giữa các gói và cửa sổ TCP. Đây là tập đặc trưng được dự án sử dụng, không phải khẳng định mọi bản phân phối của bộ dữ liệu đều có cùng cấu trúc.',
15:'Theo tài liệu chuẩn bị dữ liệu của dự án, nguồn đầu vào gồm 10 tệp Parquet với 15.589.784 flow. Quy trình loại cột Timestamp, giữ 78 đặc trưng số và lấy mẫu 3.500.000 flow, gồm 2.450.000 Benign và 1.050.000 flow tấn công. Dữ liệu được chia phân tầng thành 2.800.000 flow huấn luyện và 700.000 flow kiểm tra. Các mô hình cây sử dụng giá trị đặc trưng mà không áp dụng phép chuẩn hóa thang đo như bước bắt buộc của mô hình. Kiểm tra hai tệp đã xử lý xác nhận số dòng, số cột và tình trạng giá trị khuyết hoặc vô cực. Phép kiểm tra này không tái dựng toàn bộ quá trình từ gói tin gốc.',
17:'Tập huấn luyện phục vụ xây dựng mô hình và lấy dữ liệu nền cho giải thích. Tập kiểm tra cung cấp kết quả phân loại và các tập con của RQ2. Tập giải thích chính được lấy trong nhóm dự đoán đúng, tối đa 100 flow mỗi lớp, nên các lớp hiếm có thể có ít hơn 100 mẫu. Tập phát triển gồm 250 flow từ phần dự đoán đúng còn lại. Mã lấy mẫu loại giao nhau theo chỉ số flow giữa tập phát triển, tập giải thích chính và tập lỗi. Điều này không đồng nghĩa với độc lập hoàn toàn về vector đặc trưng hoặc độc lập giữa train và test. Kết quả kiểm tra trùng đặc trưng được trình bày ở mục 4.2.',
20:'Nghiên cứu so sánh Random Forest và XGBoost vì hai phương pháp xử lý dữ liệu bảng và cho phép khảo sát quan hệ phi tuyến giữa các đặc trưng flow. Random Forest kết hợp các cây được huấn luyện trên các mẫu dữ liệu khác nhau. XGBoost xây dựng các cây theo quá trình tăng cường tuần tự. Phạm vi thực nghiệm không bao gồm mạng nơ-ron hoặc mô hình tuyến tính, nên không kết luận hai phương pháp vượt trội các nhóm đó.',
21:'Sau bước so sánh, mô hình XGBoost đã lưu được dùng thống nhất cho RQ2 và RQ3. Cấu hình sử dụng phương pháp hist để xây dựng cây. TreeSHAP phân rã đầu ra của mô hình cây thành các đóng góp đặc trưng, còn LIME xấp xỉ hành vi dự đoán bằng mô hình cục bộ. Việc giữ nguyên mô hình cho phép đối chiếu giải thích ngoại tuyến với kết quả trong nguyên mẫu.',
23:'XGBoost được khảo sát với bảy cấu hình kết hợp độ sâu 4, 6, 8 hoặc 12 và tốc độ học từ 0,05 đến 0,10. Mỗi cấu hình dùng 100 vòng tăng cường và phương pháp hist. Mã khảo sát chấm điểm trên tập kiểm tra và xếp hạng theo macro F1. Vì tập này đã tham gia lựa chọn, kết quả không được diễn giải như đánh giá trên một tập độc lập chưa từng được sử dụng.',
25:'Cấu hình triển khai dùng n_estimators bằng 100, max_depth bằng 8, learning_rate bằng 0,08, tree_method là hist và mục tiêu multi:softprob. Với 15 lớp, 100 vòng tăng cường tương ứng 1.500 cây trong tệp mô hình. Cấu hình này được giữ nguyên khi kiểm tra lại dự đoán và khi triển khai hệ thống.',
26:'Bảng khảo sát có cấu hình đạt macro F1 cao hơn cấu hình đã triển khai. Tài liệu chưa nêu quy tắc định lượng đủ rõ cho lựa chọn cuối cùng, nên nghiên cứu phân biệt cấu hình được triển khai với cấu hình đứng đầu bảng khảo sát. Các kết quả so sánh và sự khác nhau giữa quy trình tinh chỉnh hai thuật toán được trình bày ở Chương 4.',
29:'TreeSHAP và LIME được so sánh trên cùng lớp mục tiêu. Các đặc trưng được xếp hạng theo độ lớn tuyệt đối của đóng góp. Phép đánh giá gồm Jaccard tại các mức top-k, tương quan thứ hạng Spearman và Kendall, độ trùng thứ hạng có trọng số RBO, đồng thuận dấu và Jaccard theo nhóm đặc trưng.',
30:'Gọi Sₖ và Lₖ là tập k đặc trưng đứng đầu của SHAP và LIME. Jaccard được tính bằng số đặc trưng thuộc phần giao chia cho số đặc trưng thuộc phần hợp. Các mức k được khảo sát là 3, 5, 10 và 20.',
31:'Jaccard@k = |Sₖ ∩ Lₖ| / |Sₖ ∪ Lₖ|',
32:'Giá trị nằm trong đoạn từ 0 đến 1. Giá trị lớn hơn thể hiện mức trùng đặc trưng cao hơn, không xác nhận phương pháp giải thích hoặc nhãn dự đoán là đúng.',
33:'Spearman và Kendall được tính trên hợp hai tập top-k và trên toàn bộ 78 đặc trưng. Hai phạm vi phản ánh thứ hạng ở phần đầu danh sách và trên toàn bộ đầu vào, nên kết quả phải ghi rõ phạm vi tính.',
34:'RBO dành trọng số lớn hơn cho vị trí đầu danh sách. Đồng thuận dấu chỉ được tính trên các đặc trưng cùng xuất hiện trong hai tập đang so sánh. Jaccard theo nhóm gom các đặc trưng cùng nhóm thống kê trước khi tính giao và hợp. SHAP được tính trên điểm thô của mô hình, còn LIME khớp xác suất lớp, nên độ lớn đóng góp của hai phương pháp không được so trực tiếp như cùng một thang đo.',
36:'LIME sinh các vector đặc trưng nhiễu, lấy đầu ra của XGBoost tại các vector đó và khớp một mô hình tuyến tính có trọng số theo khoảng cách. Chất lượng của phép xấp xỉ phụ thuộc cả mức khớp và lượng thông tin hữu ích trong vùng mẫu được sinh.',
37:'RQ2 sử dụng R² cục bộ với ngưỡng 0,3 để thống kê tỷ lệ giải thích đạt mức khớp quy định. R² thấp cho biết mô hình cục bộ khớp yếu, không tự đồng nghĩa với vùng mẫu suy biến. Trong RQ3, hệ thống kiểm tra thêm cỡ mẫu hiệu dụng, trọng số lân cận và trạng thái hệ số. Khi thiếu mẫu hữu ích, giao diện báo chưa giải thích được thay vì trình bày hệ số bằng 0 như kết quả có ý nghĩa.',
40:'Độ ổn định qua seed được đo bằng Jaccard top-5 trung bình giữa các cặp kết quả LIME với 10 seed. TreeSHAP được tính lại khi giữ nguyên mô hình, cấu hình và đầu vào để kiểm tra tính tái lập trong điều kiện đó. Không suy rộng tính tái lập này thành bất biến trước thay đổi đầu vào hoặc thay đổi cấu hình giải thích.',
41:'Phép thử nhiễu cộng Gaussian với độ lệch chuẩn bằng 1%, 5% hoặc 10% độ lệch chuẩn của từng đặc trưng trên train, rồi cắt giá trị về khoảng của train. SHAP và LIME tiếp tục giải thích lớp mục tiêu ban đầu. Jaccard top-5 giữa đầu vào gốc và đầu vào nhiễu đo mức giữ lại các đặc trưng đứng đầu. Thử nghiệm bổ sung thay số mẫu LIME trên 150 flow thuộc tập phát triển trong khi giữ kernel đã khóa.',
44:'Phép thay thế đặt lần lượt k đặc trưng đứng đầu về giá trị nền, sau đó đo xác suất của cùng lớp mục tiêu. Gọi p ban đầu là xác suất trước thay thế và p thay thế là xác suất sau thay thế, mức giảm được tính như sau.',
45:'Δpₖ = p ban đầu − p thay thế',
46:'Mức giảm lớn hơn cho thấy nhóm đặc trưng được chọn tác động mạnh hơn đến đầu ra dưới phép thay thế đang xét. Đây không phải chứng minh nhân quả hoặc bằng chứng flow là tấn công. Phép thay thế có thể tạo tổ hợp đặc trưng không ứng với một flow mạng hợp lệ.',
50:'Kiến trúc giữ các chức năng thu thập, trích xuất, chuẩn hóa, dự đoán, giải thích và hiển thị. Hình 3.2 gộp luồng dữ liệu và thành phần triển khai để tránh lặp sơ đồ. CSV có sẵn đặc trưng đi vào bước chuẩn hóa. PCAP và gói bắt trực tiếp đi qua bộ trích xuất flow trước khi được bộ cấp dữ liệu gửi tới API. FastAPI gọi XGBoost và lưu kết quả vào SQLite. Streamlit truy vấn kết quả qua API để hiển thị. Hệ thống xử lý khi flow được xuất, không suy luận sau mỗi gói tin.',
51:'Hình 3.2. Kiến trúc nguyên mẫu với ba nguồn dữ liệu, xử lý giải thích và quản lý capture.',
53:'Cảnh báo được lưu và phản hồi mà không phải chờ SHAP hoàn thành. Hàng đợi SHAP có giới hạn 200 tác vụ chờ và được xử lý bằng luồng nền trong tiến trình API. Khi hàng đợi đầy, tác vụ giải thích mới có thể bị bỏ nhưng dự đoán và cảnh báo vẫn được giữ. Giao diện cần thể hiện trạng thái giải thích thay vì suy ra không có cảnh báo. LIME chỉ chạy khi người dùng yêu cầu. Cơ chế này tách thời gian chờ giải thích khỏi phản hồi dự đoán, nhưng không bảo đảm độ trễ cố định dưới mọi mức tải.',
56:'Nhánh A hoặc B chỉ điều chỉnh thông tin lưu ý trên giao diện. Nhánh A được chọn khi cả cờ đặc trưng môi trường và cờ lớp hiếm đều không bật. Nhánh B được chọn khi có ít nhất một cờ bật. Các cờ không đổi nhãn, không ẩn cảnh báo và không xác nhận độ chính xác của dự đoán. Chỉ số giảm xác suất sau thay top-5 bằng trung vị là phép đánh giá bổ sung tại một mức k và một giá trị nền, không phải toàn bộ phép đo độ trung thực của RQ2 và không quyết định nhánh. Kiểm tra tính hợp lệ của LIME được thực hiện riêng, không dùng nhánh A làm chứng nhận LIME đáng tin cậy.',
63:'Kiểm thử CSV xác nhận đọc đặc trưng, chuẩn hóa, gửi dự đoán, giữ metadata và xử lý yêu cầu lặp. Kiểm thử PCAP xác nhận trích xuất flow, đối soát gói được hỗ trợ và tái lập CSV khi chạy cùng cấu hình. Kiểm thử bắt trực tiếp dùng Wi-Fi thật để kiểm tra thao tác bắt, dừng, xử lý nốt dữ liệu và giải phóng tiến trình. Kiểm thử chức năng không tự cung cấp accuracy hoặc FPR nếu đầu vào không có nhãn độc lập.',
64:'Các kết quả được tổ chức theo nội dung đánh giá thay vì mã thí nghiệm nội bộ. Phần phân loại báo cáo chỉ số từ tập có nhãn. Phần giải thích trình bày mức đồng thuận, độ ổn định và độ trung thực. Phần vận hành kiểm tra tính nhất quán dữ liệu, vòng đời tiến trình, hàng đợi, tài nguyên và phạm vi đo thời gian. Phần trường hợp thực tế phân tích dự đoán và giải thích của từng flow, đồng thời nêu rõ giới hạn xác minh nhãn.',
67:'Tên cột giống nhau chưa bảo đảm đặc trưng train và đặc trưng từ PCAP có cùng ý nghĩa. Quy tắc đóng flow, hướng truyền, thời gian chờ và đếm cờ có thể làm thay đổi giá trị đầu vào. Nguồn tiền xử lý tạo Parquet chưa được truy vết đầy đủ nên chưa thể quy mọi sai lệch cho một phiên bản CICFlowMeter cụ thể. Kiểm thử bằng gói chuẩn xác nhận hành vi bộ trích xuất hiện tại, không sửa nhãn hay đặc trưng của dữ liệu huấn luyện đã lưu.',
69:'Nhiễu Gaussian trong phép thử tỷ lệ với độ lệch chuẩn từng cột, không phải cùng một lượng nhiễu cho mọi đặc trưng. Phép thử đo độ nhạy của giải thích trên dữ liệu số. Các vector tạo ra chưa chắc thỏa quan hệ giữa số gói, byte, cờ TCP và thời lượng của một kết nối thật. Vì vậy không dùng kết quả này để kết luận khả năng chống tấn công né tránh.',
71:'Phương pháp nghiên cứu nối việc so sánh Random Forest và XGBoost với đánh giá SHAP, LIME và triển khai nguyên mẫu IDS. Các giai đoạn giữ rõ nguồn dữ liệu, lớp mục tiêu, cấu hình và phạm vi của từng phép đo. Tập giải thích và tập phát triển được tách theo chỉ số flow nhưng vẫn xuất phát từ tập kiểm tra của dự án.',
72:'Chương 4 trình bày kết quả theo cùng trình tự, gồm lựa chọn mô hình, chất lượng giải thích, kiểm thử ba đường nhập liệu và phân tích traffic thực tế. Giới hạn về tính độc lập của dữ liệu, tương thích đặc trưng và độ trễ vận hành được giữ trong diễn giải kết quả.',
78:'Chỉ số phân loại ở mục 4.3 dùng nhãn của tập kiểm tra 2018. Mục 4.4 dùng tập mẫu và cấu hình giải thích đã khóa ở RQ2. Mục 4.5 trình bày chức năng nguyên mẫu, mục 4.6 kiểm thử CSV, PCAP và bắt trực tiếp, còn mục 4.7 phân tích các flow thực tế. Nhãn Hulk mà mô hình dự đoán trong một phiên Wi-Fi chưa phải nhãn tấn công đã xác minh, nên không dùng số cảnh báo để tính FPR khi thiếu nhãn độc lập.',
93:'Macro F1 cao nhất trong bảng quét là 85,95% tại độ sâu 12 và tốc độ học 0,08. Cấu hình độ sâu 8 và tốc độ học 0,10 đạt 85,94%. Mô hình triển khai dùng độ sâu 8 và tốc độ học 0,08, đạt 85,81%. Tài liệu cũ mô tả lựa chọn cân bằng nhưng chưa đưa ra quy tắc định lượng đủ rõ để tái lập quyết định chọn cấu hình này. Vì vậy báo cáo gọi đây là cấu hình triển khai, không phải cấu hình có F1 cao nhất. Cột cuối của bảng là FNR trên các lớp tấn công, không phải FPR trên Benign.',
181:'LIME sinh nhiều vector đặc trưng theo phân bố nền, cho XGBoost dự đoán từng vector rồi khớp một mô hình đơn giản để mô tả quyết định quanh flow gốc. Các vector này là dữ liệu số sinh trong phép tính, không phải gói tin gửi ra mạng. Việc sinh nhiều mẫu không bảo đảm các mẫu đều gần flow cần giải thích.'
}
for idx,text in changes.items(): ps[idx].text=text
for idx in [8,9,10,54,57]:
    ps[idx]._element.getparent().remove(ps[idx]._element)
for t in list(d.tables):
    if 'Chỗ dành cho sơ đồ' in t.cell(0,0).text: t._element.getparent().remove(t._element)

def before(anchor,text,style=None):
    p=anchor.insert_paragraph_before(text,style); return p
def figure(anchor,file):
    p=before(anchor,''); p.alignment=1;p.paragraph_format.keep_with_next=True
    p.add_run().add_picture(str(QA/file),width=Inches(6.12))
figure(ps[7],'research.png'); figure(ps[51],'architecture.png')
before(ps[18],'Tập phát triển không trùng chỉ số flow với tập giải thích chính. Trong 250 flow phát triển, 150 flow được chọn để khảo sát cấu hình LIME. Cấu hình khóa dùng kernel width 3,312, 1.000 mẫu nhiễu, 78 đặc trưng và không chia khoảng liên tục. Tập nền gồm 2.000 mẫu huấn luyện lấy với seed 42. Tiêu chí chọn dựa trên trung vị R², với thời gian chạy dùng để phân xử các cấu hình gần bằng nhau [4].')
before(ps[18],'Bảng 3.1. Vai trò của các tập dữ liệu').paragraph_format.keep_with_next=True
t=d.add_table(rows=1,cols=3); t.style='Table Grid'
for c,x in zip(t.rows[0].cells,['Tập dữ liệu','Quy mô','Vai trò']):c.text=x
for row in [('Huấn luyện','2.800.000 flow','Huấn luyện mô hình và lấy dữ liệu nền.'),('Kiểm tra','700.000 flow','Đánh giá phân loại và lấy các tập con RQ2.'),('Giải thích chính','1.339 flow','So sánh SHAP và LIME trên dự đoán đúng.'),('Phát triển','250 flow','Khảo sát cấu hình LIME trên tập con 150 flow.'),('Phân tích lỗi','151 flow','Phân tích riêng các dự đoán sai.')]:
    for c,x in zip(t.add_row().cells,row):c.text=x
ps[18]._p.addprevious(t._tbl)
before(ps[55],'API sở hữu trạng thái và tiến trình capture cùng bộ cấp dữ liệu. Giao diện chỉ gửi lệnh và đọc trạng thái. Làm mới Streamlit không tạo phiên bắt mới. Khi dừng, hệ thống cần đóng các flow còn mở, xử lý nốt dữ liệu rồi xác nhận tiến trình kết thúc. Hệ thống chặn phiên trùng và theo dõi lỗi worker. Capture là tiến trình riêng, khác với luồng nền xử lý SHAP trong API [5].')
before(ps[84],'Phép băm 78 đặc trưng, không đưa nhãn và chỉ số dòng vào khóa, ghi nhận 194.149 dòng test có vector xuất hiện trong train, tương đương 27,7356% tập test. Đây là số dòng test trùng đặc trưng, không phải số cặp trùng. Kết quả không xác nhận cùng nguồn gói tin, nhưng cho thấy hai tập chưa độc lập hoàn toàn về biểu diễn đầu vào [6].')
before(ps[97],'Số liệu Random Forest được đối chiếu từ báo cáo gốc [3]. Tệp mô hình và dự đoán RF gốc chưa có để chạy lại suy luận trong lần đối chứng này. XGBoost được chạy lại trên đủ 700.000 flow. Hai mô hình cũng dùng cách chọn tham số khác nhau, nên so sánh này phản ánh kết quả đã ghi nhận của dự án, chưa phải đối chứng hai thuật toán dưới cùng một giao thức tinh chỉnh.')
before(ps[166],'Lượt 20 phút dùng giới hạn thử nghiệm 50.000 gói và 64 MiB. Đỉnh buffer ghi nhận 48.495 gói, tương đương 96,99% giới hạn số gói. Việc hoàn tất lượt chạy không chứng minh còn đủ dư địa ở tải cao hơn. Không dùng lượt này để xác nhận mọi cấu hình giới hạn khác hoặc khả năng chạy liên tục nhiều giờ.')

# Correct the regression table against the saved logs, without rerunning capture.
tt=next(t for t in d.tables if t.cell(0,0).text=='Nhóm kiểm thử')
rows=[('Vòng đời flow','Đóng flow và đối soát gói với dữ liệu tổng hợp.','22 kiểm thử đạt'),('Bộ cấp dữ liệu','Xác nhận, checkpoint và xử lý sự cố gửi flow.','8 kiểm thử đạt'),('Giới hạn capture','Giới hạn buffer và tình huống chạm ngưỡng.','6 kiểm thử đạt'),('Tính hợp lệ LIME','Trường hợp bình thường, suy biến, hệ số phẳng và tái lập đồng thời.','Các xác nhận đạt'),('Giao diện và API','API với mô hình thật, CSV, PCAP và AppTest.','Các xác nhận đạt'),('Quản lý worker','Supervisor và worker với card mạng giả lập.','7 kiểm thử đạt'),('Điều khiển giao diện','Quyền điều khiển, nút bắt, dừng và làm mới.','5 kiểm thử đạt')]
while len(tt.rows)>1:tt._tbl.remove(tt.rows[-1]._tr)
for row in rows:
    for c,x in zip(tt.add_row().cells,row): c.text=x

refs=[
'[1] G. Engelen, V. Rimmer và W. Joosen, Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study, WTMC, 2021. Tài liệu mở rộng: https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html',
'[2] L. Liu, G. Engelen, T. Lynar, D. Essam và W. Joosen, Error Prevalence in NIDS datasets: A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018, IEEE CNS, 2022. DOI: 10.1109/CNS56114.2022.9947235.',
'[3] Hồ sơ RQ1 của dự án, Tổng hợp Random Forest và Báo cáo tổng hợp thực nghiệm RQ1 RandomForest XGBoost. Đối chiếu với bảng quét cấu hình và mô hình XGBoost đã lưu.',
'[4] Hồ sơ RQ2 của dự án, cấu hình thí nghiệm và kết quả lượt 20261009. Các nội dung đối chiếu gồm lấy mẫu, khóa cấu hình LIME, đồng thuận, ổn định, độ trung thực và tập phân tích lỗi.',
'[5] Hồ sơ RQ3 của dự án, Kiến trúc hệ thống IDS, tài liệu vận hành và mã nguồn quản lý capture, hàng đợi SHAP, đánh giá cờ lưu ý và giao diện.',
'[6] Hồ sơ đối chứng Chương 4 ngày 28/10/2026, kiểm tra dữ liệu, suy luận XGBoost, SHAP, LIME, kiểm thử hồi quy, phát lại PCAP và lượt Wi-Fi 30 giây. Lượt Wi-Fi 20 phút được phân tích riêng từ nhật ký ngày 18/10/2026.'
]
for ref in refs[:2]:d.add_paragraph(ref)
for p in d.paragraphs:
    if re.search(r'\s*\[[3-6]\]',p.text):
        for run in p.runs:run.text=re.sub(r'\s*\[[3-6]\]','',run.text)

# Use consistent, restrained thesis typography and prevent split rows.
for p in d.paragraphs:
    for node in list(p._p.xpath('./w:pPr/w:pBdr')):node.getparent().remove(node)
    p.paragraph_format.widow_control=True
    if p.text.startswith('CHƯƠNG '):
        p.style=d.styles['Title'];p.alignment=1
        p.paragraph_format.page_break_before=True
    elif re.match(r'^[34]\.\d+\.\d+ ',p.text):p.style=d.styles['Heading 3']
    elif re.match(r'^[34]\.\d+ ',p.text):p.style=d.styles['Heading 2']
    caption=bool(re.match(r'^(Hình|Bảng) [34]\.\d+\.',p.text))
    if caption:
        p.alignment=1
        p.paragraph_format.keep_with_next=p.text.startswith('Bảng ')
    for r in p.runs:
        r.font.name='Times New Roman';r.font.color.rgb=RGBColor(0,0,0)
        r.font.size=Pt(11 if caption or p.text.startswith('[') else 13)
    if p.style.name=='Normal':
        p.paragraph_format.space_after=Pt(6);p.paragraph_format.line_spacing=1.08
        if not caption and p.text:p.alignment=3
    if p.text.startswith('['):p.paragraph_format.keep_together=True
for name,size in [('Normal',13),('Title',16),('Heading 2',14),('Heading 3',13)]:
    st=d.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
    for node in list(st.element.xpath('./w:pPr/w:pBdr')):node.getparent().remove(node)
for p in d.paragraphs:
    if p.text.startswith('CHƯƠNG '):
        for r in p.runs:r.font.size=Pt(16);r.bold=True
for t in d.tables:
    t.autofit=False
    for node in list(t._tbl.xpath('./w:tblPr/w:tblpPr')):node.getparent().remove(node)
    widths=[c.width for c in t.columns]
    if all(widths) and sum(widths)>Inches(6.26):
        ratio=Inches(6.26)/sum(widths)
        for col,w in zip(t.columns,widths):col.width=int(w*ratio)
        for row in t.rows:
            for c,w in zip(row.cells,widths):c.width=int(w*ratio)
    for i,row in enumerate(t.rows):
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        if i==0:row._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for c in row.cells:
            if t.cell(0,0).text=='Nhóm kiểm thử':
                cp=c._tc.get_or_add_tcPr(); borders=OxmlElement('w:tcBorders')
                for side in ['top','left','bottom','right']:
                    b=OxmlElement('w:'+side);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'777777');borders.append(b)
                cp.append(borders)
            for p in c.paragraphs:
                p.paragraph_format.keep_with_next=i==0
                p.paragraph_format.space_after=Pt(3)
                for r in p.runs:r.font.name='Times New Roman';r.font.size=Pt(10);r.bold=i==0

text='\n'.join(p.text for p in d.paragraphs)+'\n'+'\n'.join(c.text for t in d.tables for row in t.rows for c in row.cells)
assert not re.search(r'\bE[1-5]\b',text)
assert 'Chỗ dành' not in text
assert len(d.inline_shapes)==9
(QA/'report_text.txt').write_text(text,encoding='utf-8')
d.save(OUT)
print(json.dumps({'output':str(OUT),'tables':len(d.tables),'figures':len(d.inline_shapes)},ensure_ascii=False))
