"""Bounded-buffer tests and synthetic repeated-drain load; no network capture."""
import csv
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from stage20_test_capture_adapter import packet, RQ3
from capture_lifecycle import LifecycleSession, CaptureLimitError
from scapy.all import wrpcap


class CaptureLimitsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ids_limits_')
        self.sessions = []

    def tearDown(self):
        for s in self.sessions:
            s.flush_flows()
        self.tmp.cleanup()

    def session(self, **limits):
        s = LifecycleSession(output_mode='csv', output=str(Path(self.tmp.name)/f'{len(self.sessions)}.csv'), **limits)
        self.sessions.append(s)
        return s

    def test_packet_limit_rejects_before_admission_and_flushes_accepted(self):
        s = self.session(max_buffered_packets=2)
        s.process(packet(0)); s.process(packet(1))
        with self.assertRaises(CaptureLimitError):
            s.process(packet(2))
        self.assertEqual(s.packets_count, 2)
        self.assertEqual(s.n_limit_rejected, 1)
        s.flush_flows()
        self.assertEqual(s.n_exported_packets, 2)
        self.assertEqual(s.buffered_bytes, 0)

    def test_flow_limit_and_byte_limit(self):
        s = self.session(max_open_flows=1)
        s.process(packet(0))
        with self.assertRaises(CaptureLimitError):
            s.process(packet(1, udp=True))
        s = self.session(max_buffered_bytes=len(packet(0)))
        s.process(packet(0))
        with self.assertRaises(CaptureLimitError):
            s.process(packet(1))

    def test_zero_negative_and_noninteger_limits_refused(self):
        for value in (0, -1, True, 2.5):
            with self.assertRaises(ValueError):
                self.session(max_open_flows=value)

    def test_low_disk_refuses_export_without_deleting_buffer(self):
        s = self.session()
        s.process(packet(0))
        with patch('capture_lifecycle.shutil.disk_usage', return_value=SimpleNamespace(free=0)):
            with self.assertRaises(OSError):
                s.garbage_collect(None)
        self.assertEqual(s.n_exported_packets, 0)
        self.assertEqual(len(s.get_flows()), 1)
        s.garbage_collect(None)
        self.assertEqual(s.n_exported_packets, 1)

    def test_repeated_drains_keep_buffer_bounded(self):
        s = self.session(max_buffered_packets=64)
        started = time.perf_counter()
        tracemalloc.start()
        try:
            for cycle in range(50):
                for i in range(64):
                    s.process(packet(cycle + i/1000, udp=True, payload=64))
                s.garbage_collect(None)
                self.assertEqual(s.buffered_bytes, 0)
                self.assertEqual(len(s.get_flows()), 0)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(s.packets_count, 3200)
        self.assertEqual(s.n_exported_packets, 3200)
        self.assertEqual(s.peak_buffered_packets, 64)
        print(f'SYNTHETIC: packets=3200 exported=3200 peak_buffer=64 elapsed_s={time.perf_counter()-started:.3f} traced_python_peak_bytes={peak}', flush=True)

    def test_real_cli_limit_is_failure_not_success_and_keeps_partial_csv(self):
        pcap = Path(self.tmp.name)/'input.pcap'
        output = Path(self.tmp.name)/'output.csv'
        wrpcap(str(pcap), [packet(0), packet(1), packet(2)])
        proc = subprocess.run([sys.executable, str(RQ3/'scripts/run_live_capture.py'),
            '--pcap-input', str(pcap), '--output', str(output), '--max-buffered-packets', '2'],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn('Đã đọc hết', proc.stdout)
        self.assertNotIn('Đã dừng an toàn', proc.stdout)
        self.assertIn('limit_rejected=1', proc.stdout)
        with output.open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(sum(int(r['tot_fwd_pkts'])+int(r['tot_bwd_pkts']) for r in rows), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
