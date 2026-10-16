"""List relevant Word paragraphs, including table cells, without changing documents."""
from pathlib import Path
from zipfile import ZipFile
import re
from lxml import etree
ROOT = Path(__file__).resolve().parents[1]
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
for path in ROOT.rglob('*.docx'):
    if path.name.startswith('~$') or any(x.startswith('.') for x in path.relative_to(ROOT).parts):
        continue
    with ZipFile(path) as z:
        for part in z.namelist():
            if not part.startswith('word/') or not part.endswith('.xml'):
                continue
            xml = etree.fromstring(z.read(part))
            paragraphs = xml.xpath('//w:p', namespaces=NS)
            for i, p in enumerate(paragraphs):
                text = ''.join(p.xpath('.//w:t/text()', namespaces=NS))
                if re.search(r'FPR|FNR|5[,.]748|báo (động |cáo )?(giả|sai)|false positive|12[.,]?071', text, re.I):
                    print(f'{path.relative_to(ROOT)} | {part} | {i} | {text}')
