"""No live capture; simulate background/callback failure and verify CLI exit."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from capture_health import start_gc, stop_gc, check_health, guarded_process


class CaptureHealthTests(unittest.TestCase):
    def test_gc_error_is_retained_and_thread_stops(self):
        s = SimpleNamespace(garbage_collect=Mock(side_effect=OSError('disk full')))
        start_gc(s, interval=.001)
        self.assertTrue(s._gc_stop.wait(2))
        stop_gc(s)
        with self.assertRaisesRegex(RuntimeError, 'disk full'):
            check_health(s)
        self.assertEqual(s.garbage_collect.call_count, 1)

    def test_callback_error_survives_sniffer_swallowing_it(self):
        s = SimpleNamespace(process=Mock(side_effect=OSError('writer failed')))
        with self.assertRaises(OSError):
            guarded_process(s)(object())
        with self.assertRaisesRegex(RuntimeError, 'writer failed'):
            check_health(s)
        with self.assertRaises(RuntimeError):
            guarded_process(s)(object())
        self.assertEqual(s.process.call_count, 1)

    def test_gc_join_timeout_refuses_safe_flush(self):
        s = SimpleNamespace(_gc_stop=Mock(), _gc_thread=Mock())
        s._gc_thread.is_alive.return_value = True
        with self.assertRaisesRegex(RuntimeError, 'GC chưa dừng'):
            stop_gc(s)

    def test_normal_stop_and_callback(self):
        s = SimpleNamespace(garbage_collect=Mock(), process=Mock(return_value=None))
        start_gc(s, interval=100)
        stop_gc(s)
        check_health(s)
        guarded_process(s)(object())
        self.assertFalse(s._gc_thread.is_alive())
        self.assertEqual(s.process.call_count, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
