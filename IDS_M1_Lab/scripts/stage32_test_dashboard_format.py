"""Pure presentation regression: no API, DB or capture process."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
from datetime import datetime, timedelta, timezone
from dashboard_format import integer_text, protocol_text, endpoint, bounded_page, time_text, age_text


class DashboardFormatTests(unittest.TestCase):
    def test_integer_ports_and_protocols(self):
        self.assertEqual(integer_text(443.0), '443')
        self.assertEqual(integer_text(0), '0')
        self.assertEqual(protocol_text(6.0), 'TCP')
        self.assertEqual(protocol_text('17'), 'UDP')
        self.assertEqual(protocol_text(99), '99')

    def test_missing_not_fabricated(self):
        self.assertEqual(protocol_text(None), 'Chưa có')
        self.assertEqual(endpoint(None, None), 'IP chưa được cung cấp : Chưa có')
        self.assertEqual(endpoint('192.0.2.1', 443.0), '192.0.2.1 : 443')

    def test_page_bounds_empty_and_filter_shrink(self):
        self.assertEqual(bounded_page(8, 0), (1, 1))
        self.assertEqual(bounded_page(5, 205), (5, 5))
        self.assertEqual(bounded_page(5, 2), (1, 1))
        self.assertEqual(bounded_page(-1, 100), (1, 2))

    def test_time_is_always_gmt7_in_one_format(self):
        now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        utc = '2026-10-19T11:58:56.055116+00:00'
        self.assertEqual(time_text(utc, now=now), '19/10/2026 18:58:56')
        self.assertEqual(time_text(utc, compact=True, now=now), '19/10 18:58:56')
        self.assertEqual(time_text(utc, compact=True, seconds=False, now=now), '19/10 18:58')
        self.assertEqual(time_text('2026-10-19T11:58:56Z', now=now), '19/10/2026 18:58:56')
        self.assertEqual(time_text('2026-10-19T18:58:56+07:00', now=now), '19/10/2026 18:58:56')
        self.assertEqual(time_text(datetime(2026, 10, 19, 18, 58, 56, tzinfo=timezone(timedelta(hours=7))), now=now), '19/10/2026 18:58:56')

    def test_compact_keeps_year_when_not_current_year(self):
        now = datetime(2027, 1, 2, tzinfo=timezone.utc)
        self.assertEqual(time_text('2026-12-31T23:00:00+00:00', compact=True, now=now), '01/01 06:00:00')  # đã qua nửa đêm GMT+7 nên là năm hiện tại
        self.assertEqual(time_text('2026-10-19T00:00:00+00:00', compact=True, now=now), '19/10/2026 07:00:00')

    def test_missing_naive_and_garbage_are_not_guessed(self):
        self.assertEqual(time_text(None), 'Chưa có')
        self.assertEqual(time_text(''), 'Chưa có')
        self.assertEqual(time_text('2026-10-19T18:58:56'), '19/10/2026 18:58:56 (chưa rõ múi giờ)')
        self.assertEqual(time_text('không phải giờ'), 'không phải giờ')

    def test_age_text(self):
        now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        ago = lambda **kw: (now - timedelta(**kw)).isoformat()
        self.assertEqual(age_text(ago(seconds=2), now), 'vừa xong')
        self.assertEqual(age_text(ago(seconds=45), now), '45 giây trước')
        self.assertEqual(age_text(ago(minutes=3, seconds=10), now), '3 phút trước')
        self.assertEqual(age_text(ago(hours=13), now), '13 giờ trước')
        self.assertEqual(age_text(ago(days=2, hours=5), now), '2 ngày trước')
        self.assertIn('tương lai', age_text((now + timedelta(minutes=5)).isoformat(), now))
        self.assertEqual(age_text(None, now), '')
        self.assertEqual(age_text('2026-10-20T11:00:00', now), '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
