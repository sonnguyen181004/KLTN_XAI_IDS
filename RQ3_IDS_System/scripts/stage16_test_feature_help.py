"""Presentation-only checks: complete glossary, plain-language values/signs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from feature_help import GLOSSARY, describe, number, reading, effect
from feeder import CICFLOWMETER_COLUMN_MAP


def main():
    assert set(GLOSSARY) == set(CICFLOWMETER_COLUMN_MAP.values())
    assert len(GLOSSARY) == 78
    assert all(info['meaning'] and info['unit'] and info['title'] for info in GLOSSARY.values())
    assert 'không phải số cuộc tấn công' in reading('FIN Flag Cnt', 1)
    assert 'TCP' in reading('Protocol', 6)
    assert 'ms' in reading('Fwd IAT Min', 1000)
    assert '20 byte' == reading('Fwd Seg Size Min', 20)
    assert number(1) == '1' and number(1000) == '1 000'
    assert number(0) == '0' and number(.5) == '0,5'
    assert 'Đẩy' in effect(2, 'Hulk', 'SHAP')
    assert 'Kéo' in effect(-2, 'Hulk', 'SHAP')
    assert 'Không phải quan hệ nhân quả' in effect(2, 'Hulk', 'LIME')
    assert 'Hệ số bằng 0' in effect(0, 'Hulk', 'LIME')
    assert 'Chưa có' in effect(None, 'Hulk', 'SHAP')
    assert 'sao chép' in describe('CWE Flag Count')['note']
    print('PASS 78/78 feature definitions, units, number formatting and sign explanations')


if __name__ == '__main__':
    main()
