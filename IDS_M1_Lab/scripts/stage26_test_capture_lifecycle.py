"""V3 lifecycle oracles; synthetic packets only, no network/production DB."""
import csv
import tempfile
import unittest
import threading
from pathlib import Path
from unittest.mock import patch

from stage20_test_capture_adapter import packet
from capture_lifecycle import LifecycleSession, LIFECYCLE_VERSION
from scapy.layers.inet import TCP
from scapy.packet import Padding


def tcp_packet(when, direction='f', flags='A', seq=0, ack=0, payload=0):
    p = packet(when, direction, flags, payload)
    p[TCP].seq, p[TCP].ack = seq, ack
    return p


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

    def test_rst_exports_packet_and_tuple_reuse_starts_new_flow(self):
        s = self.session()
        for p in (tcp_packet(0, flags='S', seq=10), tcp_packet(1, 'b', 'RA'), tcp_packet(2, flags='S', seq=20)):
            s.process(p)
        rows = self.rows(s)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['flow_end_reason'], 'tcp_rst_observed')
        self.assertEqual(rows[0]['rst_flag_cnt'], '1')

    def test_fin_waits_for_both_directions_and_ack(self):
        s = self.session()
        for p in (tcp_packet(0, flags='FA', seq=100), tcp_packet(1, 'b', 'A', ack=101),
                  tcp_packet(2, 'b', 'FA', seq=200, ack=101)):
            s.process(p)
            self.assertEqual(s.n_exported, 0)
        s.process(tcp_packet(3, flags='A', ack=201))
        self.assertEqual(s.n_exported, 1)
        self.assertEqual(self.rows(s)[0]['flow_end_reason'], 'tcp_fin_ack_observed')

    def test_fin_payload_wraparound_and_retransmission(self):
        s = self.session()
        s.process(tcp_packet(0, flags='FA', seq=2**32-2, payload=2))
        s.process(tcp_packet(1, flags='FA', seq=2**32-2, payload=2))
        s.process(tcp_packet(2, 'b', 'FA', seq=99, ack=0))  # Does not cover FIN end=1.
        s.process(tcp_packet(3, flags='A', ack=100))
        self.assertEqual(s.n_exported, 0)
        s.process(tcp_packet(4, 'b', 'A', ack=1))
        self.assertEqual(self.rows(s)[0]['flow_end_reason'], 'tcp_fin_ack_observed')

    def test_single_fin_and_midstream_data_do_not_close(self):
        s = self.session()
        s.process(tcp_packet(0, flags='FA', seq=100))
        s.process(tcp_packet(1, 'b', 'PA', ack=101, payload=10))
        self.assertEqual(s.n_exported, 0)
        self.assertEqual(self.rows(s)[0]['flow_end_reason'], 'flush')

    def test_syn_retransmission_and_different_isn(self):
        s = self.session()
        s.process(tcp_packet(0, flags='S', seq=10))
        s.process(tcp_packet(1, flags='S', seq=10))
        self.assertEqual(s.n_exported, 0)
        s.process(tcp_packet(2, flags='S', seq=20))
        rows = self.rows(s)
        self.assertEqual([r['tot_fwd_pkts'] for r in rows], ['2', '1'])
        self.assertEqual(rows[0]['flow_end_reason'], 'tcp_new_syn')

    def test_midstream_new_syn_is_not_merged(self):
        s = self.session()
        s.process(tcp_packet(0, flags='PA', payload=10))
        s.process(tcp_packet(1, flags='S', seq=50))
        self.assertEqual(self.rows(s)[0]['flow_end_reason'], 'tcp_new_syn')

    def test_simultaneous_open_is_not_split(self):
        s = self.session()
        s.process(tcp_packet(0, flags='S', seq=10))
        s.process(tcp_packet(1, 'b', 'S', seq=20))
        s.process(tcp_packet(2, flags='SA', seq=10, ack=21))
        self.assertEqual(len(self.rows(s)), 1)

    def test_tcp_and_udp_never_merge(self):
        s = self.session()
        s.process(packet(0)); s.process(packet(1, udp=True))
        self.assertEqual(len(self.rows(s)), 2)

    def test_default_cli_selects_v3_and_keeps_v2_explicit(self):
        from run_live_capture import make_session
        for mode, expected in [('project', True), ('project-v3', True), ('project-v2', False)]:
            s = make_session(str(Path(self.tmp.name)/f'{mode}.csv'), mode)
            self.sessions.append(s)
            self.assertEqual(isinstance(s, LifecycleSession), expected)

    def test_gc_and_packet_admission_are_atomic(self):
        s = self.session()
        errors = []
        def gc():
            try:
                for _ in range(100):
                    s.garbage_collect(1700000000)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=gc)
        thread.start()
        for i in range(100):
            s.process(packet(i / 10))
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(self.rows(s)), 1)

    def test_write_failure_retains_late_reason_on_flush(self):
        s = self.session(); s.process(packet(2))
        with patch.object(s.output_writer, 'write', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                s.process(packet(1))
        self.assertEqual(s.packets_count, 2)
        self.assertIn('late_packet', [r['flow_end_reason'] for r in self.rows(s)])

    def test_expiry_reason_uses_earliest_deadline_even_when_gc_is_delayed(self):
        results = []
        for gc_first in (False, True):
            s = self.session(); s.process(packet(0))
            if gc_first:
                s.garbage_collect(1700000090)
            s.process(packet(300))
            results.append(self.rows(s))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0]['flow_end_reason'], 'active_timeout')

    def test_late_policy_is_independent_of_gc_and_other_tuple(self):
        results = []
        for gc_first in (False, True):
            s = self.session(); s.process(packet(0))
            s.process(packet(10, udp=True))
            if gc_first:
                s.garbage_collect(1700000090)
            s.process(packet(2))
            rows = self.rows(s)
            self.assertEqual(s.n_late, 1)
            self.assertEqual(sum(r['flow_end_reason'] == 'late_packet' for r in rows), 1)

    def test_ethernet_padding_does_not_consume_tcp_sequence_space(self):
        s = self.session()
        p = tcp_packet(0, flags='FA', seq=100) / Padding(b'\x00' * 6)
        p.time = 1700000000
        s.process(p)
        s.process(tcp_packet(1, 'b', 'FA', seq=200, ack=101))
        s.process(tcp_packet(2, flags='A', ack=201))
        self.assertEqual(self.rows(s)[0]['flow_end_reason'], 'tcp_fin_ack_observed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
