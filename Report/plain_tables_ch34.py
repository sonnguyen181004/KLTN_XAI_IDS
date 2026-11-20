from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor, Pt

root=Path(__file__).resolve().parent.parent
src=root/'Chuong_3_4_Phuong_phap_va_Ket_qua_VI_den_trang.docx'
out=root/'Chuong_3_4_VI_bang_den_trang.docx'
d=Document(src)
before=[[ [c.text for c in row.cells] for row in t.rows] for t in d.tables]
for t in d.tables:
    t.style='Table Grid'
    pr=t._tbl.tblPr
    for tag in ['tblBorders','shd','tblLook']:
        for n in list(pr.findall(qn('w:'+tag))):pr.remove(n)
    borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        n=OxmlElement('w:'+side)
        for key,val in [('val','single'),('sz','6'),('color','000000')]:n.set(qn('w:'+key),val)
        borders.append(n)
    pr.append(borders)
    for i,row in enumerate(t.rows):
        for cell in row.cells:
            cp=cell._tc.get_or_add_tcPr()
            for tag in ['shd','tcBorders']:
                for n in list(cp.findall(qn('w:'+tag))):cp.remove(n)
            shd=OxmlElement('w:shd');shd.set(qn('w:fill'),'FFFFFF');shd.set(qn('w:val'),'clear');cp.append(shd)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.bold=i==0;r.font.color.rgb=RGBColor(0,0,0)
assert before==[[[c.text for c in row.cells] for row in t.rows] for t in d.tables]
for p in d.paragraphs:
    if p._p.xpath('.//w:drawing'):
        p.paragraph_format.line_spacing=1
        p.paragraph_format.space_before=Pt(8)
        p.paragraph_format.space_after=Pt(6)
d.save(out)
print(out)
