"""Giải thích nhánh A/B (app/branch_help.py, GET /branch_rules). Luật thật ở reliability.py; ở đây chỉ kiểm phần trình bày
khớp luật, không gõ cứng số: ngưỡng, danh sách đặc trưng, số mẫu đều đến từ `rules` (giống API trả)."""
import sys
import unittest
from pathlib import Path

import _testdb  # noqa: F401  (đặt IDS_DB_PATH về thư mục tạm trước khi import app)

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RQ3 / "app"))
import branch_help as bh  # noqa: E402
from reliability import ReliabilityScorer  # noqa: E402

RULES = dict(env_features=['Dst Port', 'Fwd Seg Size Min', 'Init Fwd Win Byts', 'FIN Flag Cnt'], env_threshold=2, rare_min_samples=100,
             top_k=5, train_samples_per_class={'Hulk': 5000, 'SQL': 70}, importance={
                 'Dst Port': dict(rank=1, of=78, share_pct=23.5), 'FIN Flag Cnt': dict(rank=None, of=78, share_pct=0.0)})


def flow(top5, count, env_flag, rare_flag, branch, label='Hulk'):
    return dict(branch=branch, predicted_label=label, shap_top5=[dict(feature=f, phi=1.0, value=1) for f in top5],
                env_fingerprint_count=count, env_fingerprint_flag=env_flag, rare_class_flag=rare_flag)


class Facts(unittest.TestCase):
    def test_not_yet_branched_returns_none(self):
        self.assertIsNone(bh.branch_facts(dict(branch=None), RULES))

    def test_branch_b_by_env_flag(self):
        f = bh.branch_facts(flow(['FIN Flag Cnt', 'Dst Port', 'Pkt Len Max', 'x', 'y'], 2, 1, 0, 'B'), RULES)
        self.assertEqual([i['feature'] for i in f['hits']], ['FIN Flag Cnt', 'Dst Port'])
        self.assertTrue(f['env_on'] and not f['rare_on'] and f['hits_match'] and not f['config_drift'])
        s = bh.summary(f)
        self.assertEqual(s['level'], 'warn')
        self.assertIn('nhánh B', s['title'])
        self.assertIn('không có nghĩa là báo nhầm', s['action'])
        self.assertIn('2/4', s['meaning'])

    def test_branch_a_says_not_correctness(self):
        f = bh.branch_facts(flow(['a', 'b', 'c', 'd', 'e'], 0, 0, 0, 'A'), RULES)
        s = bh.summary(f)
        self.assertEqual(s['level'], 'ok')
        self.assertIn('không có nghĩa là kết quả đúng', s['action'])

    def test_branch_b_by_rare_class_only(self):
        f = bh.branch_facts(flow(['a', 'b', 'c', 'd', 'e'], 0, 0, 1, 'B', label='SQL'), RULES)
        self.assertEqual(f['n_train'], 70)
        self.assertIn('70 mẫu train', ' '.join(bh.reasons(f)))
        self.assertEqual([c[2] for c in bh.flag_chips(f)], ['ok', 'warn'])

    def test_steps_follow_the_flow_values(self):
        f = bh.branch_facts(flow(['Dst Port', 'Fwd Seg Size Min', 'a', 'b', 'c'], 2, 1, 0, 'B'), RULES)
        steps = {n: t for n, _, t in bh.decision_steps(f)}
        self.assertIn('Dst Port, Fwd Seg Size Min', steps['2'])
        self.assertIn('ngưỡng 2', steps['2'])
        self.assertIn('Kết quả: nhánh B', steps['4'])

    def test_thousands_separator_in_sample_counts(self):
        rules = {**RULES, 'train_samples_per_class': {'Hulk': 155042}}
        chips = bh.flag_chips(bh.branch_facts(flow(['a'] * 5, 0, 0, 0, 'A'), rules))
        self.assertIn('155.042', chips[1][1])


class ConfigDrift(unittest.TestCase):
    def test_old_alert_computed_with_fewer_env_features_is_flagged_not_hidden(self):
        # Lúc tính chỉ đếm 1 đặc trưng (danh sách cũ ngắn hơn) nên lưu nhánh A; danh sách hiện tại khớp 2 -> sẽ là B.
        f = bh.branch_facts(flow(['Dst Port', 'FIN Flag Cnt', 'a', 'b', 'c'], 1, 0, 0, 'A'), RULES)
        self.assertTrue(f['config_drift'])
        self.assertEqual((f['branch'], f['current_branch']), ('A', 'B'))
        note = bh.drift_note(f)
        self.assertIn('nhánh sẽ là B', note)
        step2 = {n: t for n, _, t in bh.decision_steps(f)}['2']
        self.assertIn('số đã lưu lúc tính', step2)

    def test_no_drift_no_note(self):
        f = bh.branch_facts(flow(['Dst Port', 'a', 'b', 'c', 'd'], 1, 0, 0, 'A'), RULES)
        self.assertIsNone(bh.drift_note(f))


class MatchesTheRealRule(unittest.TestCase):
    def test_presentation_agrees_with_reliability_decide_branch_for_all_flag_pairs(self):
        for env in (0, 1):
            for rare in (0, 1):
                real, _ = ReliabilityScorer._decide_branch(env, rare)
                f = bh.branch_facts(flow(['Dst Port', 'FIN Flag Cnt', 'a', 'b', 'c'] if env else ['a'] * 5, 2 if env else 0, env, rare, real), RULES)
                self.assertEqual('B' if (f['env_on'] or f['rare_on']) else 'A', real)
                self.assertEqual(bh.summary(f)['level'], 'warn' if real == 'B' else 'ok')

    def test_labels(self):
        self.assertEqual(bh.branch_short('A'), '✓ Bình thường')
        self.assertEqual(bh.branch_short('B'), '⚠ Xem lại')
        self.assertEqual(bh.branch_short(None), '—')
        self.assertEqual(bh.branch_option('B'), 'B · cần xem lại')


class Evidence(unittest.TestCase):
    def test_table_marks_hypothesis_and_uses_measured_numbers(self):
        rows = bh.evidence_rows(RULES, lambda name: dict(title='nghĩa ' + name))
        self.assertEqual([r['Đặc trưng'] for r in rows], RULES['env_features'])
        self.assertIn('Hạng 1/78', rows[0]['Đã đo được (từ model)'])
        self.assertIn('Chưa kiểm chứng', rows[0]['Phản ánh môi trường lab?'])
        self.assertEqual(rows[3]['Đã đo được (từ model)'], 'Model không dùng đặc trưng này')
        self.assertIn('chưa kiểm chứng', bh.hypothesis_status().lower())

    def test_rare_classes_come_from_counts(self):
        self.assertEqual(bh.rare_classes(RULES), [('SQL', 70)])
        self.assertEqual(bh.rare_classes({**RULES, 'rare_min_samples': 10}), [])


class ApiRules(unittest.TestCase):
    def test_branch_rules_endpoint_reads_config_and_model(self):
        import main
        rules = main.branch_rules()
        self.assertEqual(rules['env_features'], list(main.cfg['environment_fingerprint_features']))
        self.assertEqual(rules['env_threshold'], main.cfg['environment_fingerprint_flag_threshold'])
        self.assertEqual(rules['rare_min_samples'], main.cfg['rare_class_min_train_samples'])
        self.assertEqual(set(rules['importance']), set(rules['env_features']))
        for info in rules['importance'].values():
            self.assertEqual(info['of'], len(main.detector.feature_names))
            self.assertTrue(0 <= info['share_pct'] <= 100)
            self.assertTrue(info['rank'] is None or 1 <= info['rank'] <= info['of'])
        self.assertLessEqual(sum(i['share_pct'] for i in rules['importance'].values()), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
