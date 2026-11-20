"""Build the Vietnamese Chapter 4 draft from verified RQ1-RQ3 evidence."""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Chuong_4_Ket_qua_thuc_nghiem_VI.docx"


def set_cell_fill(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def set_cell_border(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for side in ("top", "left", "bottom", "right"):
        edge = OxmlElement(f"w:{side}")
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), "4")
        edge.set(qn("w:color"), "D9D9D9")
        borders.append(edge)


def set_cell_padding(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = OxmlElement("w:tcMar")
    for side in ("top", "left", "bottom", "right"):
        tag = OxmlElement(f"w:{side}")
        tag.set(qn("w:w"), "100")
        tag.set(qn("w:type"), "dxa")
        margins.append(tag)
    tc_pr.append(margins)


def paragraph(doc, text):
    p = doc.add_paragraph(text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def main():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(13)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.line_spacing = 1.08
    normal.paragraph_format.space_after = Pt(8)

    for name, size, before in (("Heading 1", 18, 12), ("Heading 2", 14, 12)):
        style = doc.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(8)

    doc.add_heading("CHƯƠNG 4\nKẾT QUẢ THỰC NGHIỆM VÀ THẢO LUẬN", 1)
    doc.add_heading("4.1 Giới thiệu và thiết lập thực nghiệm", 2)

    paragraph(
        doc,
        "Chương này báo cáo kết quả của ba giai đoạn đã nêu ở Chương 3. RQ1 đánh giá phân loại trên CSE-CIC-IDS2018. RQ2 kiểm tra giải thích SHAP và LIME cho mô hình đã chọn. RQ3 tích hợp mô hình vào hệ thống IDS và kiểm tra ba nguồn CSV, PCAP, thu trực tiếp. Đơn vị dự đoán là một flow, không phải một gói tin. Kết quả phân loại, giải thích và vận hành được trình bày riêng theo phạm vi dữ liệu của từng phép đánh giá.",
    )

    paragraph(
        doc,
        "RQ1 sử dụng 2.800.000 flow huấn luyện và 700.000 flow kiểm tra, mỗi flow có 78 đặc trưng số và một trong 15 nhãn. XGBoost được cấu hình 100 vòng tăng cường, độ sâu cây tối đa 8, tốc độ học 0,08, phương pháp hist và hạt giống 42. RQ2 giữ nguyên mô hình và cố định tập 1.339 định danh flow để đánh giá giải thích. RQ3 nạp lại mô hình cùng bộ mã hóa nhãn của RQ1 và giữ đúng thứ tự 78 đặc trưng cho cả ba nguồn.",
    )

    caption = doc.add_paragraph("Bảng 4.1. Thiết lập chính của các phép đánh giá RQ1, RQ2 và RQ3")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.keep_with_next = True

    rows = [
        ("Giai đoạn", "Dữ liệu và cấu hình được đối chiếu", "Đầu ra đánh giá"),
        (
            "RQ1",
            "Train 2.800.000 flow, test 700.000 flow, 78 đặc trưng, 15 lớp. XGBoost có 100 vòng tăng cường, độ sâu tối đa 8, tốc độ học 0,08.",
            "Ma trận nhầm lẫn và chỉ số phân loại trên tập test 2018.",
        ),
        (
            "RQ2",
            "Mô hình RQ1 và tập 1.339 flow. LIME dùng 1.000 mẫu nhiễu, kernel width 3,312 và tập nền 2.000 mẫu.",
            "Đóng góp SHAP, giải thích LIME và các kiểm tra chất lượng giải thích.",
        ),
        (
            "RQ3",
            "Mô hình 15 lớp, 78 đặc trưng. CSV, PCAP và thu trực tiếp dùng chung API dự đoán.",
            "Đối soát flow, dự đoán, cảnh báo, trạng thái giải thích và số liệu vận hành.",
        ),
    ]
    table = doc.add_table(rows=0, cols=3)
    table.autofit = False
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        widths = (Inches(0.8), Inches(3.25), Inches(2.45))
        for cell, value, width in zip(cells, values, widths):
            cell.width = width
            cell.text = value
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_border(cell)
            set_cell_padding(cell)
            if row_index == 0:
                set_cell_fill(cell, "DCEAF5")
                for run in cell.paragraphs[0].runs:
                    run.bold = True
            elif row_index % 2 == 0:
                set_cell_fill(cell, "F7F9FB")
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.08
                for run in p.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)
        if row_index == 0:
            tr_pr = table.rows[0]._tr.get_or_add_trPr()
            repeat = OxmlElement("w:tblHeader")
            repeat.set(qn("w:val"), "true")
            tr_pr.append(repeat)

    closing = paragraph(
        doc,
        "Chỉ số phân loại ở mục 4.3 dùng nhãn của tập test 2018. Kết quả ở mục 4.4 dùng tập mẫu và cấu hình giải thích đã khóa của RQ2. Kiểm thử RQ3 đối soát flow qua ba đường nhập liệu và trạng thái xử lý. Nhãn Hulk do mô hình dự đoán trong một phiên Wi-Fi không phải nhãn tấn công đã xác minh. Do đó, số cảnh báo thu trực tiếp không được dùng để tính FPR nếu thiếu nhãn độc lập.",
    )
    closing.paragraph_format.space_before = Pt(10)

    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
