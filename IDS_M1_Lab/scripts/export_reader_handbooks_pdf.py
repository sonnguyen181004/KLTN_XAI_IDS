"""Reader PDFs from handbook content, not a Word layout validation.

ReportLab fallback because the bundled Windows runtime has no LibreOffice.
Use bundled Python. Render final PDFs with bundled Poppler for visual QA.
"""
from pathlib import Path
from xml.sax.saxutils import escape
from docx import Document
from docx.table import Table as WordTable
from docx.text.paragraph import Paragraph as WordParagraph
from docx.oxml.ns import qn
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/handbooks'
fonts = Path('C:/Windows/Fonts')
for name, file in [('VN', 'arial.ttf'), ('VN-Bold', 'arialbd.ttf'), ('Mono', 'consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(fonts/file)))
pdfmetrics.registerFontFamily('VN', normal='VN', bold='VN-Bold', italic='VN', boldItalic='VN-Bold')
styles = {
    'Normal': ParagraphStyle('body', fontName='VN', fontSize=10.5, leading=15, spaceAfter=7),
    'Title': ParagraphStyle('title', fontName='VN-Bold', fontSize=24, leading=30, spaceAfter=15, keepWithNext=True),
    'Subtitle': ParagraphStyle('subtitle', fontName='VN', fontSize=12, leading=17, spaceAfter=15, keepWithNext=True),
    'Heading 1': ParagraphStyle('h1', fontName='VN-Bold', fontSize=17, leading=22, spaceAfter=12, keepWithNext=True),
    'Heading 2': ParagraphStyle('h2', fontName='VN-Bold', fontSize=12.5, leading=17, spaceBefore=7, spaceAfter=7, keepWithNext=True),
    'List Bullet': ParagraphStyle('bullet', fontName='VN', fontSize=10.5, leading=15, leftIndent=12, firstLineIndent=-8, spaceAfter=5),
    'Code': ParagraphStyle('code', fontName='Mono', fontSize=8.5, leading=12, spaceAfter=2),
    'Cell': ParagraphStyle('cell', fontName='VN', fontSize=9.3, leading=13),
    'CellHead': ParagraphStyle('cellhead', fontName='VN-Bold', fontSize=9.3, leading=13),
}


def footer(canvas, doc):
    canvas.setFont('VN', 8)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawRightString(letter[0]-48, 27, f'RQ3  |  18/10/2026  |  {doc.page}')


def export(path):
    src = Document(path)
    story = []
    for element in src.element.body:
        if element.tag == qn('w:p'):
            para = WordParagraph(element, src)
            if element.xpath('.//w:br[@w:type="page"]'):
                story.append(PageBreak())
                continue
            if not para.text.strip():
                continue
            style = para.style.name
            if any(r.font.name == 'Consolas' for r in para.runs): style = 'Code'
            text = escape(para.text)
            if style == 'List Bullet': text = '• ' + text
            story.append(Paragraph(text, styles.get(style, styles['Normal'])))
        elif element.tag == qn('w:tbl'):
            tbl = WordTable(element, src)
            data = []
            for i, row in enumerate(tbl.rows):
                data.append([Paragraph(escape(c.text), styles['CellHead' if i == 0 else 'Cell']) for c in row.cells])
            widths = [c.width.inches*72 if c.width else 100 for c in tbl.columns]
            factor = 516/sum(widths)
            t = Table(data, colWidths=[w*factor for w in widths], repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), .4, colors.HexColor('#D9D9D9')),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#DCE6F1')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F5F7FA')]),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 7), ('RIGHTPADDING', (0,0), (-1,-1), 7),
                ('TOPPADDING', (0,0), (-1,-1), 7), ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ]))
            story.extend([t, Spacer(1,8)])
    pdf = path.with_suffix('.pdf')
    doc = SimpleDocTemplate(str(pdf), pagesize=letter, rightMargin=48, leftMargin=48,
                            topMargin=45, bottomMargin=43, title=src.core_properties.title,
                            author='Dự án RQ3 IDS')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(pdf)
    print(pdf.name, len(reader.pages), 'pages')
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        print(i, len(text), text.splitlines()[0][:85])


if __name__ == '__main__':
    for path in sorted(OUT.glob('*.docx')):
        export(path)
