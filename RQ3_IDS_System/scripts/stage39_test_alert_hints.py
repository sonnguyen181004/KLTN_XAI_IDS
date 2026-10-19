"""Gợi ý đọc cảnh báo (app/alert_hints.py): quy tắc, nhãn LIME, câu "vì sao nghi ngờ", và con số 445/0
trong lời gợi ý phải khớp train_set.parquet thật. Không ghi DB, không mở API."""
import json
import sys
import unittest
import warnings
from pathlib import Path

RQ3 = Path(__file__).resolve().parents[1]
REPO = RQ3.parent
sys.path.insert(0, str(RQ3 / "app"))
from alert_hints import HULK_FIN_TRAIN, fin_data_hint, lime_badge, why_suspect  # noqa: E402
from feature_help import describe, reading  # noqa: E402


class HintRules(unittest.TestCase):
    def test_matches_only_hulk_with_fin_data_and_small_header(self):
        self.assertEqual(fin_data_hint('DoS attacks-Hulk', 2, 93, 20)['tag'], 'FIN + có dữ liệu')
        self.assertIn('445/445', fin_data_hint('DoS attacks-Hulk', 1, 1490, 20)['text'])
        self.assertIsNone(fin_data_hint('Benign', 2, 93, 20))
        self.assertIsNone(fin_data_hint('Bot', 2, 93, 20))
        self.assertIsNone(fin_data_hint('DoS attacks-Hulk', 0, 93, 20))      # không có FIN
        self.assertIsNone(fin_data_hint('DoS attacks-Hulk', 2, 0, 20))       # flow rỗng
        self.assertIsNone(fin_data_hint('DoS attacks-Hulk', 2, 93, 32))      # ngoài vùng đã đo
        self.assertIsNone(fin_data_hint('DoS attacks-Hulk', None, 93, 20))   # thiếu dữ liệu: không đoán

    def test_text_is_a_hint_not_a_verdict(self):
        text = fin_data_hint('DoS attacks-Hulk', 2, 93, 20)['text']
        self.assertIn('có thể là báo nhầm', text)
        self.assertIn('không phải kết luận', text)
        self.assertNotIn('chắc chắn', text)

    def test_lime_badge(self):
        alert = dict(is_alert=True)
        self.assertEqual(lime_badge(dict(is_alert=False)), '—')
        self.assertEqual(lime_badge({**alert, 'lime_status': 'not_requested'}), 'Chưa chạy')
        self.assertEqual(lime_badge({**alert, 'lime_status': 'ok'}), 'Hợp lệ')
        for status in ('insufficient_neighborhood', 'zero_coefficients', 'undefined_fit'):
            self.assertEqual(lime_badge({**alert, 'lime_status': status}), 'Không đủ tin cậy')
        self.assertEqual(lime_badge({**alert, 'lime_status': 'legacy_unchecked'}), 'Cũ, chưa kiểm')

    def test_why_suspect_uses_only_positive_shap(self):
        top5 = [dict(feature='FIN Flag Cnt', value=2.0, phi=5.8), dict(feature='Fwd Pkt Len Max', value=93.0, phi=2.4),
                dict(feature='Dst Port', value=443.0, phi=-0.4)]
        sentence = why_suspect(top5, describe, reading)
        self.assertIn(describe('FIN Flag Cnt')['title'].split(' — ')[0], sentence)
        self.assertIn(describe('Fwd Pkt Len Max')['title'].split(' — ')[0], sentence)
        self.assertNotIn(describe('Dst Port')['title'].split(' — ')[0], sentence)
        self.assertLess(len(sentence), 200, 'câu phải ngắn, không kèm cả đoạn giải nghĩa')
        self.assertIsNone(why_suspect([dict(feature='Dst Port', value=443.0, phi=-1.0)], describe, reading))
        self.assertIsNone(why_suspect(None, describe, reading))


class EvidenceMatchesData(unittest.TestCase):
    def test_sample_is_real_model_hulk_and_hint_counts_match_train(self):
        import joblib
        import pandas as pd
        warnings.filterwarnings('ignore')
        sample = json.loads((RQ3 / 'data/samples/sample_hulk_fin_data.json').read_text(encoding='utf-8'))
        model = joblib.load(REPO / 'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl')
        encoder = joblib.load(REPO / 'RQ1_Model_Training_xboost/saved_models/label_encoder.pkl')
        row = pd.DataFrame([[sample[c] for c in model.feature_names_in_]], columns=list(model.feature_names_in_))
        label = encoder.classes_[int(model.predict_proba(row)[0].argmax())]
        self.assertEqual(label, 'DoS attacks-Hulk')
        self.assertIsNotNone(fin_data_hint(label, sample['FIN Flag Cnt'], sample['Fwd Pkt Len Max'], sample['Fwd Seg Size Min']))
        train = pd.read_parquet(REPO / 'dataset/CICID-2018_processed/train_set.parquet',
                                columns=['Label', 'FIN Flag Cnt', 'Fwd Pkt Len Max', 'Fwd Seg Size Min'])
        region = train[(train['FIN Flag Cnt'] >= 1) & (train['Fwd Pkt Len Max'] >= 66) & (train['Fwd Seg Size Min'] < 32)]
        self.assertEqual(int((region.Label == 'DoS attacks-Hulk').sum()), HULK_FIN_TRAIN['hulk'])
        self.assertEqual(int((region.Label == 'Benign').sum()), HULK_FIN_TRAIN['benign'])
        self.assertEqual(len(region), HULK_FIN_TRAIN['hulk'] + HULK_FIN_TRAIN['benign'], 'vùng này có thêm lớp khác')


if __name__ == '__main__':
    unittest.main(verbosity=2)
