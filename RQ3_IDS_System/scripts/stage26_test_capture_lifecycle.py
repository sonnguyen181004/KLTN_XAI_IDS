"""V3 lifecycle oracles; synthetic packets only, no network/production DB."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stage20_test_capture_adapter import packet
from capture_lifecycle import LifecycleSession, LIFECYCLE_VERSION


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ids_lifecycle_')
        self.sessions = []

    def tearDown(self):
        for session in self.sessions:
            session.flush_flows()
        self.tmp.cleanup()

    def session(self, **kwargs):
        output = Path(self.tmp.name) / f'{len(self.sessions)}.csv'
        session = LifecycleSession(output_mode='csv', output=str(output), **kwargs)
        self.sessions.append(session)
        return session

    def rows(self, session):
        session.flush_flows()
        with open(session.output, encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(sum(int(r['tot_fwd_pkts']) + int(r['tot_bwd_pkts']) for r in rows), session.packets_count)
        self.assertEqual(session.n_exported_packets, session.packets_count)
        self.assertTrue(all(r['extractor_version'] == LIFECYCLE_VERSION for r in rows))
        return rows

    def test_active_boundary_independent_of_gc_order(self):
        results = []
        for gc_first in (False, True):
            s = self.session()
            s.process(packet(0)); s.process(packet(89))
            if gc_first:
                s.garbage_collect(1700000090)
            s.process(packet(90))
            results.append(self.rows(s))
        self.assertEqual(results[0], results[1])
        self.assertEqual([r['tot_fwd_pkts'] for r in results[0]], ['2', '1'])
        self.assertEqual(results[0][0]['flow_end_reason'], 'active_timeout')

    def test_idle_boundary_independent_of_gc_order(self):
        results = []
        for gc_first in (False, True):
            s = self.session(max_age=1000)
            s.process(packet(0))
            if gc_first:
                s.garbage_collect(1700000240)
            s.process(packet(240))
            results.append(self.rows(s))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0]['flow_end_reason'], 'idle_timeout')

    def test_quiet_flow_is_exported_at_max_age(self):
        s = self.session(); s.process(packet(0))
        s.garbage_collect(1700000089.99)
        self.assertEqual(s.n_exported, 0)
        s.garbage_collect(1700000090)
        self.assertEqual(s.n_exported, 1)
        self.rows(s)

    def test_late_packet_is_visible_and_never_negative_iat(self):
        s = self.session()
        for t in (0, 2, 1, 3):
            s.process(packet(t))
        rows = self.rows(s)
        self.assertEqual(s.n_late, 1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['flow_end_reason'], 'late_packet')
        self.assertTrue(all(float(r['flow_iat_min']) >= 0 for r in rows))

    def test_late_packet_after_export_does_not_reopen_old_flow(self):
        s = self.session()
        s.process(packet(0)); s.process(packet(100)); s.process(packet(2))
        rows = self.rows(s)
        self.assertEqual(len(rows), 3)
        self.assertEqual(s.n_late, 1)

    def test_same_time_packets_are_not_late(self):
        s = self.session()
        s.process(packet(0)); s.process(packet(0, 'b'))
        self.assertEqual(len(self.rows(s)), 1)
        self.assertEqual(s.n_late, 0)

    def test_writer_failure_keeps_buffered_flow(self):
        s = self.session(); s.process(packet(0))
        with patch.object(s.output_writer, 'write', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                s.garbage_collect(1700000090)
        self.assertEqual(len(s.get_flows()), 1)
        self.assertEqual(s.n_exported, 0)
        self.rows(s)

    def test_flush_idempotent_and_closed_session_rejects_packets(self):
        s = self.session(); s.process(packet(0))
        self.rows(s); s.flush_flows()
        self.assertEqual(s.n_exported, 1)
        with self.assertRaises(RuntimeError):
            s.process(packet(1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
