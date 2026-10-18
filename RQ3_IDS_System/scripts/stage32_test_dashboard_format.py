"""Pure presentation regression: no API, DB or capture process."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
from dashboard_format import integer_text, protocol_text, endpoint, bounded_page


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


if __name__ == '__main__':
    unittest.main(verbosity=2)
