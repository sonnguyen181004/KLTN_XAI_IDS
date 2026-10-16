"""Run without training: python -B -m unittest discover -s RQ1_Model_Training_xboost -p test_ids_metrics.py"""
import csv
import math
from pathlib import Path
import unittest
import numpy as np
from ids_metrics import ids_detection_metrics


class DetectionMetricsTests(unittest.TestCase):
    def test_multiclass_and_permuted_benign(self):
        cm = np.array([[90, 7, 3], [2, 15, 3], [4, 5, 11]])
        result = ids_detection_metrics(cm, 0)
        self.assertEqual(result, dict(fp=10, tn=90, fn=6, tp=34, fpr_pct=10., fnr_pct=15.))
        order = [2, 0, 1]
        self.assertEqual(ids_detection_metrics(cm[np.ix_(order, order)], 1), result)

    def test_absent_classes(self):
        self.assertTrue(math.isnan(ids_detection_metrics([[0, 0], [1, 9]], 0)['fpr_pct']))
        self.assertTrue(math.isnan(ids_detection_metrics([[9, 1], [0, 0]], 0)['fnr_pct']))
        self.assertEqual(ids_detection_metrics([[9, 0], [0, 3]], 0)['fpr_pct'], 0)

    def test_invalid(self):
        for cm, idx in [([[1, 2]], 0), ([[1, -1], [0, 1]], 0),
                        ([[1.5]], 0), ([[float('nan')]], 0), ([[1]], 2)]:
            with self.assertRaises(ValueError):
                ids_detection_metrics(cm, idx)

    def test_saved_confusion_matrix(self):
        root = Path(__file__).resolve().parent / 'results'
        with (root / 'confusion_matrix_values.csv').open(encoding='utf-8-sig', newline='') as f:
            table = list(csv.reader(f))
        labels = table[0][1:]
        self.assertEqual(labels, [row[0] for row in table[1:]])
        cm = np.array([[int(v) for v in row[1:]] for row in table[1:]])
        result = ids_detection_metrics(cm, labels.index('Benign'))
        self.assertEqual((result['fp'], result['tn'], result['fn'], result['tp']),
                         (1139, 488861, 12071, 197929))
        self.assertEqual(int(cm.sum()), 700000)
        self.assertAlmostEqual(result['fpr_pct'], 1139 / 490000 * 100)
        self.assertAlmostEqual(result['fnr_pct'], 12071 / 210000 * 100)
        print('Saved matrix:', result)
        with (root / 'bang_2_ket_qua_chinh_thuc_rq1.csv').open(encoding='utf-8-sig', newline='') as f:
            summary = list(csv.reader(f))[1:]
        fpr_text = next(v for k, v in summary if 'FPR' in k)
        fnr_text = next(v for k, v in summary if 'FNR' in k)
        self.assertEqual(fpr_text, f"{result['fpr_pct']:.4f}% (FP={result['fp']}, TN={result['tn']})")
        self.assertEqual(fnr_text, f"{result['fnr_pct']:.4f}% (FN={result['fn']}, TP={result['tp']})")
        with (root / 'bang_1_ket_qua_quet_tham_so_thuc_te.csv').open(encoding='utf-8-sig', newline='') as f:
            header = next(csv.reader(f))
        self.assertTrue(header[6].startswith('FNR Attack'))


if __name__ == '__main__':
    unittest.main()
