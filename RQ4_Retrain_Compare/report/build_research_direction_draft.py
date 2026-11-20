from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = Path(__file__).resolve().parent
OUTPUT = REPORT_DIR / "Bao_cao_RQ4_so_sanh_dataset_cu_va_moi.docx"
FIG_FALSE_POSITIVE = REPORT_DIR / "hinh1_benign_bao_nham.png"
FIG_FIN = REPORT_DIR / "hinh2_fin_benign.png"

NAVY = "17365D"
BLUE = "2F75B5"
PALE_BLUE = "D9EAF7"
PALE_GRAY = "F2F4F7"
WHITE = "FFFFFF"
TEXT = RGBColor(31, 41, 55)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=90, bottom=80, end=90):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_row_cant_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def clear_paragraph_border(paragraph):
    p_pr = paragraph._p.get_or_add_pPr()
    old = p_pr.find(qn("w:pBdr"))
    if old is not None:
        p_pr.remove(old)
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "nil")
    bottom.set(qn("w:sz"), "0")
    bottom.set(qn("w:space"), "0")
    bottom.set(qn("w:color"), "auto")
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def set_font(run, name="Times New Roman", size=13, bold=None, color=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def configure_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(13)
    normal.font.color.rgb = TEXT
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing = 1.3
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.first_line_indent = Cm(1)

    title = doc.styles["Title"]
    title.font.name = "Times New Roman"
    title._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    title.font.size = Pt(19)
    title.font.bold = True
    title.font.color.rgb = RGBColor(23, 54, 93)
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(8)

    for style_name, size, color, before, after in (
        ("Heading 1", 15, NAVY, 14, 7),
        ("Heading 2", 13.5, BLUE, 10, 5),
    ):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True


def add_field(paragraph, instruction):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])
    set_font(run, size=10)


def add_header_footer(section):
    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run("BẢN NHÁP ĐỊNH HƯỚNG NGHIÊN CỨU")
    set_font(r, name="Arial", size=8.5, bold=True, color=RGBColor(89, 89, 89))

    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    r = p.add_run("Trang ")
    set_font(r, size=10)
    add_field(p, "PAGE")


def add_paragraph(doc, text, bold_lead=None, no_indent=False, italic=False):
    p = doc.add_paragraph()
    if no_indent:
        p.paragraph_format.first_line_indent = Cm(0)
    if bold_lead and text.startswith(bold_lead):
        lead = p.add_run(bold_lead)
        set_font(lead, bold=True)
        tail = p.add_run(text[len(bold_lead):])
        set_font(tail)
    else:
        r = p.add_run(text)
        set_font(r, italic=italic)
    return p


def add_callout(doc, heading, text):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    set_row_cant_split(table.rows[0])
    cell = table.cell(0, 0)
    set_cell_shading(cell, PALE_BLUE)
    set_cell_margins(cell, top=140, start=180, bottom=140, end=180)
    p = cell.paragraphs[0]
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(heading)
    set_font(r, bold=True, color=RGBColor.from_string(NAVY))
    p2 = cell.add_paragraph()
    p2.paragraph_format.first_line_indent = Cm(0)
    p2.paragraph_format.space_after = Pt(0)
    r2 = p2.add_run(text)
    set_font(r2)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(f"• {item}")
        set_font(r)


def add_numbered(doc, items):
    for number, item in enumerate(items, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(f"{number}. {item}")
        set_font(r)


def add_table(doc, headers, rows, widths=None, caption=None):
    if caption:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(caption)
        set_font(r, size=11, italic=True)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = False if widths else True
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for idx, value in enumerate(headers):
        cell = hdr.cells[idx]
        set_cell_shading(cell, NAVY)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
        if widths:
            cell.width = Cm(widths[idx])
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(str(value))
        set_font(r, size=10.5, bold=True, color=RGBColor(255, 255, 255))
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for cidx, value in enumerate(row):
            cell = cells[cidx]
            if ridx % 2 == 1:
                set_cell_shading(cell, PALE_GRAY)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if widths:
                cell.width = Cm(widths[cidx])
            p = cell.paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if cidx == 0 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(value))
            set_font(r, size=10.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_figure(doc, image_path, caption, width=6.2):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(3)
    p.add_run().add_picture(str(image_path), width=Inches(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.first_line_indent = Cm(0)
    cap.paragraph_format.space_after = Pt(7)
    r = cap.add_run(caption)
    set_font(r, size=11, italic=True)


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.keep_with_next = True
    return p


def build():
    doc = Document()
    configure_styles(doc)
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.6)
    section.right_margin = Cm(2.2)
    section.header_distance = Cm(0.9)
    section.footer_distance = Cm(0.9)
    add_header_footer(section)

    p = doc.add_paragraph(style="Title")
    p.add_run("Định hướng nghiên cứu từ kết quả RQ1 RQ2 RQ3 đến RQ4")
    clear_paragraph_border(p)
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.first_line_indent = Cm(0)
    p2.paragraph_format.space_after = Pt(3)
    r = p2.add_run("So sánh mô hình XGBoost huấn luyện trên CSE-CIC-IDS2018 bản gốc và bản improved")
    set_font(r, size=14, bold=True, color=RGBColor.from_string(BLUE))
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.first_line_indent = Cm(0)
    p3.paragraph_format.space_after = Pt(16)
    r = p3.add_run("Bản nháp phục vụ trao đổi hướng nghiên cứu")
    set_font(r, size=11.5, italic=True, color=RGBColor(89, 89, 89))

    add_callout(
        doc,
        "Luận điểm trung tâm",
        "Kết quả RQ1 chứng minh mô hình học tốt trên tập kiểm thử cùng nguồn. RQ2 cho thấy mô hình dựa mạnh vào một số dấu hiệu của môi trường tạo dữ liệu. RQ3 phát hiện các dấu hiệu đó gây báo nhầm khi mô hình gặp lưu lượng thật. RQ4 vì vậy không bắt đầu từ nhu cầu tăng thêm điểm số, mà từ nhu cầu kiểm tra liệu sửa dữ liệu huấn luyện có loại bỏ đường tắt mà mô hình đã học hay không.",
    )

    add_heading(doc, "Tóm tắt RQ1 RQ2 và RQ3 đã thực hiện", 1)
    add_table(
        doc,
        ["Câu hỏi", "Nội dung đã thực hiện", "Kết quả chính", "Ý nghĩa đối với bước tiếp theo"],
        [
            ["RQ1", "Huấn luyện và đánh giá XGBoost trên 3,5 triệu flow của CSE-CIC-IDS2018 bản CSV gốc, dùng 78 đặc trưng và chia dữ liệu phân tầng theo tỷ lệ 80 phần trăm cho train và 20 phần trăm cho kiểm thử.", "Accuracy đạt 97,91%, Macro F1 đạt 85,81% và F1 của DoS Hulk đạt 99,997%. Có 194.149 dòng kiểm thử trùng hoàn toàn với train.", "Mô hình đạt điểm cao trên dữ liệu cùng nguồn, nhưng phép đánh giá chưa chứng minh khả năng khái quát sang lưu lượng khác môi trường."],
            ["RQ2", "Giải thích dự đoán của mô hình bằng SHAP và LIME, sau đó kiểm tra độ trung thành, độ đồng thuận, độ ổn định và mức phù hợp với tri thức miền.", "AUC comprehensiveness của SHAP đạt 0,812, cao hơn LIME ở mức 0,458. SHAP thắng LIME tại năm đặc trưng quan trọng nhất trên 78,3% flow. Dự đoán Hulk phụ thuộc mạnh vào Fwd Seg Size Min.", "Lời giải thích gợi ra khả năng mô hình học dấu vết của môi trường tạo dữ liệu thay cho đặc trưng hành vi DoS."],
            ["RQ3", "Đưa mô hình vào hệ thống IDS nhận CSV, PCAP và lưu lượng bắt trực tiếp. Bộ trích đặc trưng và đường dự đoán được kiểm tra lại để loại trừ lỗi triển khai.", "Trong 784 flow Benign thực tế, M0 báo 149 flow là tấn công, tương đương 19,0%. Có 148 flow cùng rơi vào một vùng đặc trưng và đều bị gán nhãn Hulk. Khi đặt FIN bằng 0, cả 148 flow đổi nhãn.", "Lỗi báo nhầm xuất phát từ quy tắc mô hình đã học trên dữ liệu cũ. Kết quả này chuyển hướng nghiên cứu sang kiểm tra chất lượng và mức bao phủ của dữ liệu huấn luyện."],
        ],
        widths=[1.5, 5.1, 5.2, 5.0],
        caption="Bảng 1 Tóm tắt công việc và kết quả của RQ1 RQ2 và RQ3",
    )
    add_paragraph(
        doc,
        "Chuỗi kết quả trên dẫn đến RQ4. Câu hỏi không còn là mô hình đạt bao nhiêu điểm trên tập kiểm thử cùng nguồn, mà là dữ liệu huấn luyện cũ đã thiếu loại Benign nào và việc huấn luyện lại trên bản improved có làm thay đổi hành vi của mô hình hay không. Thực nghiệm ban đầu cho thấy M1, mô hình huấn luyện trên dữ liệu improved, không báo nhầm flow nào trong 784 flow Benign thực tế. Tuy vậy, M1 chỉ nhận đúng 3,73% flow Hulk của bộ kiểm thử cũ. Kết quả đối nghịch này cho thấy hai bộ dữ liệu mô tả cùng nhãn bằng hai phân phối đặc trưng khác nhau. RQ4 vì vậy được xây dựng như một nghiên cứu về sai lệch dữ liệu, khả năng khái quát và vai trò chẩn đoán của XAI.",
    )

    add_heading(doc, "1 Câu chuyện nghiên cứu hình thành từ RQ1 đến RQ4", 1)
    add_heading(doc, "1.1 RQ1 cho kết quả nội bộ cao nhưng chưa trả lời khả năng khái quát", 2)
    add_paragraph(
        doc,
        "RQ1 sử dụng 3,5 triệu flow được lấy mẫu từ CSE-CIC-IDS2018, gồm 70% Benign và 30% tấn công. Dữ liệu được chia phân tầng theo tỷ lệ 80% cho train và 20% cho kiểm thử. Mô hình dùng 78 đặc trưng số, bỏ Timestamp và địa chỉ IP, sau đó chọn cấu hình độ sâu 8, learning rate 0,08, 100 cây, tree method hist và seed 42. Trên 700.000 dòng kiểm thử, mô hình M0 đạt Accuracy 97,91%, Macro F1 85,81%, FPR Benign 0,2324% và FNR tấn công 5,7481%.",
    )
    add_paragraph(
        doc,
        "Kết quả này xác nhận quy trình huấn luyện hoạt động đúng trên phân phối cũ. Dù vậy, 194.149 dòng kiểm thử, tương đương 27,74%, trùng hoàn toàn với dòng train. F1 gần tuyệt đối của Hulk vì thế cần được đọc cùng điều kiện đánh giá. RQ1 trả lời tốt câu hỏi mô hình có tái hiện mẫu trong bộ dữ liệu hay không, nhưng chưa kiểm tra liệu ranh giới quyết định có còn đúng khi cách tạo flow hoặc môi trường mạng thay đổi.",
    )
    add_table(
        doc,
        ["Chỉ số RQ1", "Giá trị", "Ý nghĩa trong mạch nghiên cứu"],
        [
            ["Accuracy", "97,91%", "Hiệu năng tổng thể cao trên tập kiểm thử cùng nguồn"],
            ["Macro F1", "85,81%", "Hiệu năng giữa các lớp chưa đồng đều"],
            ["F1 DoS Hulk", "99,997%", "Hulk gần như được nhận dạng tuyệt đối trong phân phối cũ"],
            ["Dòng kiểm thử trùng train", "194.149 dòng", "Giới hạn mức độc lập của phép đánh giá"],
        ],
        widths=[4.2, 3.2, 9.4],
        caption="Bảng 2 Kết quả RQ1 và ý nghĩa đối với bước nghiên cứu tiếp theo",
    )

    add_heading(doc, "1.2 RQ2 biến XAI thành công cụ kiểm tra điều mô hình đã học", 2)
    add_paragraph(
        doc,
        "RQ2 triển khai SHAP và LIME trên cohort 1.339 flow dự đoán đúng. Kiểm tra faithfulness cho thấy AUC comprehensiveness của SHAP đạt 0,812, cao hơn LIME ở mức 0,458 và đối chứng ngẫu nhiên ở mức 0,111. Tại k bằng 5, SHAP thắng LIME trên 78,3% flow. Mức đồng thuận Jaccard Top 5 giữa hai phương pháp chỉ đạt 0,141, dù cao hơn mốc ngẫu nhiên 0,036. Vì vậy, SHAP được dùng làm nguồn giải thích chính, còn LIME được giữ như đối chứng cục bộ có cổng chất lượng.",
    )
    add_paragraph(
        doc,
        "Điểm quan trọng hơn nằm ở nội dung giải thích. Với lớp Hulk, Fwd Seg Size Min đứng đầu với độ lớn SHAP trung bình 6,49, trong khi Init Fwd Win Byts ở vị trí kế tiếp chỉ đạt 0,23. Các đặc trưng này có thể phản ánh cấu hình hệ điều hành, công cụ tạo lưu lượng hoặc cách CICFlowMeter xây dựng flow. RQ2 chưa chứng minh dữ liệu sai, nhưng đã gợi ra khả năng mô hình nhận dạng dấu vết của môi trường lab thay cho hành vi DoS.",
    )

    add_heading(doc, "1.3 RQ3 làm lộ khoảng cách giữa điểm kiểm thử và hành vi vận hành", 2)
    add_paragraph(
        doc,
        "RQ3 tích hợp mô hình vào hệ thống nhận CSV, PCAP và lưu lượng bắt trực tiếp. Bộ trích đặc trưng của hệ thống được đối chiếu với tshark về số gói, cờ FIN, cửa sổ nhận ban đầu và thời lượng. Dự đoán ngoại tuyến trên dữ liệu đã lưu cũng khớp với kết quả của hệ thống. Các phép kiểm tra này loại trừ hai nguyên nhân triển khai trực tiếp là sai cách trích đặc trưng và sai đường gọi mô hình.",
    )
    add_paragraph(
        doc,
        "Khi chạy trên 784 flow Benign do người dùng xác nhận, M0 báo 149 flow là tấn công, tương đương FPR 19,0%. Có 148 flow đồng thời thỏa ba điều kiện FIN Flag Cnt từ 1 trở lên, Fwd Pkt Len Max từ 66 trở lên và Fwd Seg Size Min dưới 32. Cả 148 flow đều bị gán nhãn Hulk. Trong train cũ, vùng này chỉ có 445 dòng và tất cả đều mang nhãn Hulk. Không có dòng Benign nào làm đối trọng. Phép can thiệp đặt FIN bằng 0 làm cả 148 flow đổi nhãn và chỉ còn 4 trên 784 flow bị báo tấn công. SHAP của M0 cũng đặt FIN Flag Cnt ở vị trí ảnh hưởng lớn nhất đối với nhóm báo nhầm này.",
    )
    add_callout(
        doc,
        "Điểm chuyển từ RQ3 sang RQ4",
        "Mô hình không hỏng vì mã triển khai. Mô hình đang áp dụng đúng quy tắc mà nó học từ train cũ, nhưng quy tắc đó sai khi gặp kết nối Benign hoàn chỉnh trong môi trường thật. Vấn đề nghiên cứu chuyển từ đánh giá mô hình sang kiểm tra sự đầy đủ và cách biểu diễn của dữ liệu huấn luyện.",
    )

    add_heading(doc, "1.4 Khoảng trống nghiên cứu được xác định sau RQ3", 2)
    add_paragraph(
        doc,
        "Các kết quả RQ1 đến RQ3 chưa trả lời liệu báo nhầm xuất phát từ thiếu mẫu Benign, lỗi tạo đặc trưng, khác biệt định nghĩa flow hay sự kết hợp của các yếu tố này. Điểm kiểm thử cao không đủ để phân biệt các khả năng đó. SHAP xác định đặc trưng gây ra quyết định, nhưng bản thân SHAP không chứng minh quan hệ nhân quả với lỗi dữ liệu. Cần một thực nghiệm có đối chứng, giữ nguyên mô hình và quy trình, chỉ thay nguồn dữ liệu huấn luyện rồi đánh giá chéo trên dữ liệu cũ, dữ liệu improved và lưu lượng thật.",
    )

    add_heading(doc, "2 Câu hỏi nghiên cứu và giả thuyết cho RQ4", 1)
    add_callout(
        doc,
        "Câu hỏi nghiên cứu RQ4",
        "Khi giữ nguyên thuật toán XGBoost, siêu tham số, 78 đặc trưng, cách lấy mẫu, cách chia train và kiểm thử cùng cấu hình SHAP LIME của RQ1 và RQ2, việc huấn luyện lại trên CSE-CIC-IDS2018 improved có giảm báo nhầm trên lưu lượng Benign thực tế hay không, và sự thay đổi dữ liệu làm thay đổi khả năng khái quát cùng lời giải thích của mô hình như thế nào.",
    )
    add_paragraph(
        doc,
        "RQ4 có thể kiểm tra bốn giả thuyết làm việc. Đây là giả thuyết định hướng cho bản nháp, không phải kết luận đã được chứng minh hoàn toàn.",
    )
    add_bullets(
        doc,
        [
            "H1. Train cũ thiếu Benign TCP vừa mang FIN vừa có dữ liệu, khiến mô hình xem vùng đặc trưng này như dấu hiệu của Hulk.",
            "H2. Mô hình huấn luyện trên dữ liệu improved sẽ giảm rõ rệt FPR trên 784 flow Benign thực tế vì dữ liệu mới đã phủ vùng đặc trưng bị thiếu.",
            "H3. Hiệu năng đánh giá chéo sẽ giảm mạnh khi mô hình được thử trên bộ dữ liệu khác nguồn, cho thấy thay đổi phân phối giữa hai bản dữ liệu lớn hơn sai khác do thuật toán.",
            "H4. SHAP của mô hình mới sẽ không còn dùng FIN như tín hiệu quyết định Hulk trên nhóm flow Benign thực tế, nhưng mô hình vẫn có thể phụ thuộc vào dấu vết môi trường khác.",
        ],
    )

    add_heading(doc, "3 Thiết kế thực nghiệm RQ4", 1)
    add_heading(doc, "3.1 Nguyên tắc đối chứng", 2)
    add_paragraph(
        doc,
        "Thiết kế RQ4 giữ nguyên các quyết định đã khóa ở RQ1 và RQ2. Cả M0b và M1 dùng XGBClassifier với độ sâu 8, learning rate 0,08, 100 cây, tree method hist và seed 42. Mô hình nhận cùng 78 đặc trưng và không dùng Timestamp hoặc địa chỉ IP. Cách lấy mẫu giữ tỷ lệ 70% Benign và 30% tấn công, giữ toàn bộ lớp hiếm, sau đó chia phân tầng 80% cho train và 20% cho kiểm thử. Cấu hình SHAP và LIME không được chọn lại theo kết quả RQ4.",
    )
    add_paragraph(
        doc,
        "Bản improved không có SlowHTTPTest và chỉ có FTP BruteForce dưới dạng Attempted. Hai lớp này bị loại, nên không gian nhãn chung còn 13 lớp. M0b được huấn luyện lại trên dữ liệu cũ với cùng 13 lớp để tách ảnh hưởng của số lớp khỏi ảnh hưởng của nguồn dữ liệu. M1 dùng 2.728.397 dòng train từ bản improved. M0 gốc 15 lớp được giữ làm mốc tham chiếu cho RQ1 đến RQ3.",
    )
    add_table(
        doc,
        ["Mô hình", "Dữ liệu huấn luyện", "Vai trò"],
        [
            ["M0", "Dữ liệu cũ 15 lớp", "Mốc RQ1 RQ2 RQ3"],
            ["M0b", "Dữ liệu cũ 13 lớp chung", "Đối chứng công bằng về không gian nhãn"],
            ["M1", "Dữ liệu improved 13 lớp", "Kiểm tra ảnh hưởng của nguồn dữ liệu"],
        ],
        widths=[2.2, 6.2, 8.4],
        caption="Bảng 3 Vai trò của các mô hình trong thiết kế RQ4",
    )

    add_heading(doc, "3.2 Bộ đánh giá", 2)
    add_table(
        doc,
        ["Bộ dữ liệu đánh giá", "Nội dung", "Câu hỏi được kiểm tra"],
        [
            ["Bộ kiểm thử cũ", "Tập kiểm thử của RQ1", "Mô hình còn nhận dạng phân phối cũ hay không"],
            ["Bộ kiểm thử improved", "Tập kiểm thử phân tầng của bản improved", "Mô hình học được phân phối improved hay không"],
            ["Lưu lượng Benign thực tế", "784 flow Benign bắt trên máy người dùng", "Báo nhầm khi triển khai có giảm hay không"],
        ],
        widths=[4.2, 6.0, 6.6],
        caption="Bảng 4 Các bộ dữ liệu đánh giá dùng trong RQ4",
    )
    add_paragraph(
        doc,
        "Các chỉ số chính gồm Accuracy, Macro Precision, Macro Recall, Macro F1, FPR của Benign, FNR của tấn công, recall Hulk và kết quả theo từng lớp. Bộ lưu lượng thực tế chỉ có Benign, nên chỉ số thích hợp là FPR và số flow bị gán nhãn tấn công. Phân tích XAI so sánh độ trung thành, mức đồng thuận SHAP LIME và đặc trưng chi phối các quyết định trên cùng nhóm flow.",
    )

    add_heading(doc, "4 Kết quả ban đầu của RQ4", 1)
    add_heading(doc, "4.1 Khác biệt dữ liệu nằm đúng tại vùng gây báo nhầm", 2)
    add_paragraph(
        doc,
        "Trong 1.322.801 flow Benign TCP của train cũ, chỉ 9.815 flow mang FIN, tương đương 0,74%. Chỉ 26 flow vừa mang FIN vừa có dữ liệu và không flow nào có FIN cùng dữ liệu từ 66 byte trở lên. Trong 1.100.982 flow Benign TCP của train improved, 49,87% mang FIN, 43,57% vừa có FIN vừa có dữ liệu và 36,88% có FIN cùng dữ liệu từ 66 byte trở lên. Vùng ba điều kiện gây báo nhầm chứa 0 Benign trong train cũ nhưng chứa 405.347 Benign trong train improved.",
    )
    add_figure(
        doc,
        FIG_FIN,
        "Hình 1 Tỷ lệ flow Benign TCP mang FIN trong hai bộ train",
        width=6.25,
    )
    add_paragraph(
        doc,
        "Sự khác biệt không dừng ở số mẫu. Hulk của train cũ có trung vị 2 gói chiều đi, Fwd Pkt Len Max bằng 0 và FIN bằng 0. Hulk của train improved có trung vị 5 gói chiều đi, Fwd Pkt Len Max bằng 348 và FIN bằng 2. Hai bộ dữ liệu vì vậy biểu diễn cùng tên lớp bằng hai kiểu flow khác nhau. Đây là cơ sở để dự đoán rằng một mô hình học trên bộ này sẽ suy giảm khi được đánh giá trên bộ kia.",
    )

    add_heading(doc, "4.2 Kết quả đánh giá chéo xác nhận thay đổi phân phối", 2)
    add_table(
        doc,
        ["Mô hình và bộ kiểm thử", "Macro F1", "FPR Benign", "Recall Hulk"],
        [
            ["M0 trên bộ kiểm thử cũ", "88,96%", "0,23%", "99,997%"],
            ["M0 trên bộ kiểm thử improved", "65,97%", "21,12%", "99,98%"],
            ["M1 trên bộ kiểm thử improved", "99,30%", "0,0015%", "99,997%"],
            ["M1 trên bộ kiểm thử cũ", "25,84%", "3,83%", "3,73%"],
        ],
        widths=[5.7, 3.5, 3.7, 3.7],
        caption="Bảng 5 Kết quả đánh giá chéo giữa dữ liệu cũ và dữ liệu improved",
    )
    add_paragraph(
        doc,
        "M1 đạt kết quả gần tuyệt đối trên bộ kiểm thử cùng nguồn, nhưng mất phần lớn khả năng nhận dạng Hulk của bộ kiểm thử cũ. M0 cũng báo nhầm 21,12% Benign trên bộ kiểm thử improved và gần như gán toàn bộ 100.819 Benign nằm trong vùng ba điều kiện thành tấn công. Kết quả hai chiều này không ủng hộ diễn giải rằng một mô hình tốt hơn mô hình còn lại theo nghĩa tổng quát. Nó cho thấy định nghĩa flow và phân phối đặc trưng chi phối ranh giới quyết định.",
    )

    add_heading(doc, "4.3 Báo nhầm trên lưu lượng thật biến mất với M1", 2)
    add_paragraph(
        doc,
        "Trên 784 flow Benign thực tế, M0 báo nhầm 19,0% và M0b báo nhầm 19,6%. M1 không báo nhầm flow nào. Riêng 148 flow trong vùng gây lỗi, M0 gán toàn bộ thành Hulk còn M1 gán toàn bộ thành Benign. Kết quả này ủng hộ H2 trong phạm vi bộ lưu lượng đã thu, đồng thời cho thấy việc giảm số lớp từ 15 xuống 13 không giải quyết được lỗi vì M0b vẫn tái hiện hành vi của M0.",
    )
    add_figure(
        doc,
        FIG_FALSE_POSITIVE,
        "Hình 2 Tỷ lệ Benign bị báo thành tấn công trên ba bộ đánh giá",
        width=6.25,
    )

    add_heading(doc, "4.4 Giải thích của mô hình thay đổi sau khi thay dữ liệu", 2)
    add_paragraph(
        doc,
        "Trên 148 flow gây báo nhầm, SHAP của M0 đặt FIN Flag Cnt ở vị trí đầu với ảnh hưởng trung bình 5,865 đối với lớp được dự đoán. Sau khi chuyển sang M1, cả 148 flow được dự đoán Benign và Init Bwd Win Byts đứng đầu phần giải thích với ảnh hưởng trung bình 2,056. FIN không còn nằm trong nhóm tám đặc trưng chi phối. Phép so sánh này cho thấy lời giải thích thay đổi cùng dữ liệu huấn luyện, phù hợp với cơ chế được suy ra từ RQ3.",
    )
    add_paragraph(
        doc,
        "Trên cohort của M1, AUC comprehensiveness của SHAP đạt 0,836, cao hơn LIME ở mức 0,557 và đối chứng ngẫu nhiên ở mức 0,107. SHAP thắng LIME tại k bằng 5 trên 82,5% flow. Jaccard Top 5 tăng từ 0,141 ở M0 lên 0,213 ở M1, nhưng mức đồng thuận vẫn thấp. Do đó, RQ4 nên dùng SHAP làm công cụ chẩn đoán chính và không diễn giải sự đồng thuận giữa hai phương pháp như bằng chứng về tính đúng của lời giải thích.",
    )

    add_heading(doc, "4.5 Điểm số rất cao của M1 vẫn cần giới hạn cách diễn giải", 2)
    add_paragraph(
        doc,
        "Kiểm tra nhãn xáo trộn cho Accuracy 70,0%, đúng bằng tỷ lệ lớp đông nhất, và Macro F1 chỉ 6,33%. Không phát hiện nhóm đặc trưng giống nhau nhưng mang nhãn xung đột. Tuy nhiên, chỉ 2.739 dòng train, tương đương 0,1%, đã cho Macro F1 96,63%. Trong mẫu kiểm tra lân cận, 74,48% dòng kiểm thử có một dòng train gần như giống hệt. Nhiều lớp tấn công cũng chỉ xuất hiện trong một ngày hoặc từ một địa chỉ nguồn. Các bằng chứng này cho thấy bài toán improved dễ phân tách trong chính môi trường lab. Macro F1 99,30% chưa thể được diễn giải là chất lượng ngoài đời.",
    )

    add_heading(doc, "5 Diễn giải khoa học dự kiến", 1)
    add_heading(doc, "5.1 Kết luận có thể bảo vệ từ dữ liệu hiện có", 2)
    add_paragraph(
        doc,
        "Dữ liệu cũ gần như không chứa Benign TCP hoàn chỉnh vừa mang FIN vừa có dữ liệu. Trong khi đó, cùng vùng đặc trưng lại chỉ chứa Hulk. XGBoost đã học ranh giới phù hợp với train cũ và áp dụng ranh giới đó khi chạy thật. Dữ liệu improved bổ sung số lượng lớn Benign trong vùng bị thiếu, khiến tỷ lệ báo nhầm trên 784 flow Benign thực tế giảm từ 19,0% xuống 0%. Đánh giá chéo cho thấy thay đổi này đồng thời làm mô hình không còn nhận dạng phần lớn Hulk của bộ kiểm thử cũ. Vì vậy, kết luận phù hợp nhất là sửa cách biểu diễn dữ liệu làm thay đổi bài toán học, chứ không đơn thuần cải thiện một mô hình giữ nguyên bài toán.",
    )

    add_heading(doc, "5.2 Kết luận chưa đủ bằng chứng", 2)
    add_bullets(
        doc,
        [
            "Chưa thể khẳng định thiếu mẫu Benign là nguyên nhân duy nhất, vì bản cũ và bản improved còn khác cách tạo flow và định nghĩa một số đặc trưng.",
            "Chưa thể khẳng định M1 khái quát tốt cho mọi mạng thực tế, vì bộ lưu lượng đã thu chỉ gồm 784 flow Benign từ một máy và không có tấn công thật làm đối chứng.",
            "Chưa thể xem Accuracy gần 100% là bằng chứng M1 tốt hơn tuyệt đối, vì các lớp tấn công mang dấu vết ngày, nguồn và chiến dịch rất rõ.",
            "Chưa thể kết luận SHAP giải thích đúng quan hệ nhân quả. SHAP chỉ cho biết đặc trưng nào chi phối dự đoán của mô hình đã học.",
        ],
    )

    add_heading(doc, "5.3 Đóng góp dự kiến của RQ4", 2)
    add_numbered(
        doc,
        [
            "Nối kết quả đánh giá nội bộ với lỗi vận hành bằng một chuỗi bằng chứng từ RQ1, RQ2 và RQ3.",
            "Xác định một vùng đặc trưng gây báo nhầm và đối chiếu trực tiếp mức phủ của vùng này trong hai bộ train.",
            "Thực hiện so sánh có đối chứng giữa M0b và M1 khi giữ nguyên thuật toán, siêu tham số, đặc trưng và quy trình XAI.",
            "Chứng minh rằng sửa dữ liệu có thể loại bỏ một lỗi vận hành cụ thể nhưng đồng thời làm lộ sự không tương thích giữa hai phân phối Hulk.",
            "Đề xuất cách dùng XAI như công cụ chẩn đoán sai lệch dữ liệu, thay vì chỉ dùng để minh họa một dự đoán sau khi mô hình đã hoàn tất.",
        ],
    )

    add_heading(doc, "6 Công việc cần hoàn tất để RQ4 đạt chuẩn bài nghiên cứu", 1)
    add_numbered(
        doc,
        [
            "Bổ sung bộ kiểm thử ngoài nguồn có cả Benign và tấn công. Bộ này nên được thu ở thời điểm hoặc môi trường khác, có nhãn được kiểm tra độc lập và không dùng để chọn mô hình.",
            "Thực hiện kịch bản kiểm soát gồm kết nối HTTP Benign đóng bằng FIN và lưu lượng Hulk tái tạo. Mục tiêu là đo trực tiếp hai loại sai số trong cùng điều kiện thu thập.",
            "Xác nhận nguồn tải, phiên bản và checksum của bộ improved. Báo cáo cần ghi rõ quy tắc bỏ nhãn Attempted và ánh xạ 78 đặc trưng.",
            "Báo cáo khoảng tin cậy cho FPR, Macro F1 và chênh lệch dự đoán trên cùng mẫu. Khi hai mô hình đánh giá trên cùng flow, có thể dùng kiểm định cặp phù hợp thay cho chỉ so sánh tỷ lệ.",
            "Tách kết luận về hiệu năng cùng nguồn khỏi kết luận về khái quát. Phần thảo luận cần đặt kết quả blocked split, dòng gần trùng và dấu vết địa chỉ nguồn cạnh điểm số chính.",
        ],
    )

    add_heading(doc, "7 Khung bài báo dự kiến", 1)
    add_table(
        doc,
        ["Phần", "Nội dung chính"],
        [
            ["Đặt vấn đề", "Mâu thuẫn giữa điểm kiểm thử cao và báo nhầm khi triển khai"],
            ["Nghiên cứu liên quan", "Lỗi CICFlowMeter, sai lệch bộ dữ liệu IDS và XAI cho chẩn đoán mô hình"],
            ["Phương pháp", "Chuỗi RQ1 đến RQ4, mô hình đối chứng, bộ kiểm thử chéo và chỉ số"],
            ["Kết quả", "Khác biệt vùng FIN, đánh giá chéo, lưu lượng thực tế và thay đổi SHAP LIME"],
            ["Thảo luận", "Dataset shift, shortcut learning, giới hạn của điểm số cùng nguồn"],
            ["Hạn chế", "Nguồn improved, lưu lượng thực tế chỉ từ một máy và thiếu bộ kiểm thử tấn công ngoài nguồn"],
            ["Kết luận", "Dữ liệu sửa lỗi loại bỏ báo nhầm cụ thể nhưng chưa giải quyết đầy đủ khả năng khái quát"],
        ],
        widths=[4.0, 12.8],
        caption="Bảng 6 Cấu trúc đề xuất cho bài viết RQ4",
    )

    add_heading(doc, "8 Kết luận định hướng", 1)
    add_paragraph(
        doc,
        "Câu chuyện nghiên cứu của đề tài không nên kết thúc ở điểm số cao của RQ1. Giá trị của chuỗi RQ nằm ở việc mỗi bước làm lộ một giới hạn của bước trước. RQ1 tạo mô hình và thiết lập mốc hiệu năng. RQ2 cho biết mô hình dựa vào những đặc trưng nào và chỉ ra dấu hiệu phụ thuộc môi trường. RQ3 kiểm tra mô hình trong hệ thống thật, loại trừ lỗi triển khai và phát hiện báo nhầm Hulk có cấu trúc. RQ4 kiểm tra nguồn gốc dữ liệu của lỗi đó bằng huấn luyện lại có đối chứng.",
    )
    add_paragraph(
        doc,
        "Kết quả hiện có ủng hộ luận điểm rằng dữ liệu cũ thiếu một vùng Benign phổ biến, khiến mô hình học đường tắt dựa trên FIN và kích thước dữ liệu. Dữ liệu improved làm báo nhầm trên 784 flow Benign thực tế biến mất, nhưng đánh giá chéo cũng chứng minh hai bản dữ liệu không tương thích ở lớp Hulk. Hướng viết phù hợp là trình bày RQ4 như nghiên cứu về chất lượng dữ liệu và khả năng khái quát của IDS dựa trên flow, trong đó SHAP được dùng để nối hành vi dự đoán với sai lệch dữ liệu. Kết luận của RQ4 cần thêm một bộ kiểm thử ngoài nguồn có cả Benign lẫn tấn công.",
    )

    doc.core_properties.title = "Định hướng nghiên cứu từ RQ1 RQ2 RQ3 đến RQ4"
    doc.core_properties.subject = "Bản nháp hướng nghiên cứu RQ4 cho hệ thống IDS có giải thích"
    doc.core_properties.author = "Nhóm thực hiện đề tài"
    doc.core_properties.comments = "Bản nháp phục vụ trao đổi học thuật"
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
