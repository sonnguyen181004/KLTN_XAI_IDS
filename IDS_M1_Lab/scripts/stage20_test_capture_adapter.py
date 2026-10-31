"""Independent packet-oracle tests; run with .venv_capture Python. No live capture."""
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import signal
from types import SimpleNamespace
from unittest.mock import patch

from scapy.all import Ether, IP, IPv6, TCP, UDP, Raw, rdpcap, wrpcap

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RQ3/'app'))
from capture_adapter import (ProjectFlowSession, EXTRACTOR_VERSION, statistics,
                             ProjectFlowV1, TrainCandidateFlow, CANDIDATE_VERSION)


def packet(when, direction='f', flags='A', payload=0, udp=False):
    src,dst = ('192.0.2.1','192.0.2.2') if direction=='f' else ('192.0.2.2','192.0.2.1')
    sport,dport = (40000,443) if direction=='f' else (443,40000)
    transport = UDP(sport=sport,dport=dport) if udp else TCP(sport=sport,dport=dport,flags=flags,window=1024)
    result = Ether()/IP(src=src,dst=dst)/transport
    if payload:
        result /= Raw(b'x'*payload)
    result.time = 1700000000+when
    return result


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ids_capture_test_')
        self.folder = Path(self.temp.name)
        self.sessions = []

    def tearDown(self):
        for session in self.sessions:
            session.flush_flows()
        self.temp.cleanup()

    def session(self):
        session = ProjectFlowSession(output_mode='csv',output=str(self.folder/f'{len(self.sessions)}.csv'))
        self.sessions.append(session)
        return session

    def feed(self, packets):
        path = self.folder/'fixture.pcap'
        wrpcap(str(path),packets)
        decoded = list(rdpcap(str(path)))
        session = self.session()
        for p in decoded:
            session.process(p)
        return session,decoded

    def test_packet_counts_flags_rates_and_iat(self):
        session,packets = self.feed([packet(0,flags='S'),packet(.1,'b','SA'),packet(.2),
            packet(.3,flags='PA',payload=100),packet(.4,'b','FA'),packet(.5,flags='FA')])
        data = session.get_flows()[0].get_data()
        self.assertEqual((data['tot_fwd_pkts'],data['tot_bwd_pkts']),(4,2))
        self.assertEqual((data['syn_flag_cnt'],data['ack_flag_cnt'],data['fin_flag_cnt']),(2,5,2))
        self.assertAlmostEqual(data['flow_iat_mean'],.1)
        self.assertAlmostEqual(data['bwd_iat_tot'],.3)
        self.assertAlmostEqual(data['bwd_iat_mean'],.3)
        self.assertEqual(data['bwd_iat_std'],0)
        self.assertEqual(data['flow_pkts_s'],12.)
        self.assertEqual(data['totlen_fwd_pkts'],sum(len(p) for p in packets if p[IP].src=='192.0.2.1'))
        self.assertEqual(data['extractor_version'],EXTRACTOR_VERSION)

    def test_single_interval_and_empty_stats(self):
        self.assertEqual(statistics([.3]),dict(total=.3,mean=.3,std=0.,min=.3,max=.3))
        self.assertEqual(statistics([])['mean'],0)
        session,_ = self.feed([packet(0),packet(.1,'b')])
        self.assertAlmostEqual(session.get_flows()[0].get_data()['flow_iat_mean'],.1)

    def test_cwr_and_urg_are_independent(self):
        for flags,cwr,urg in [('C',1,0),('U',0,1),('CU',1,1)]:
            with self.subTest(flags=flags):
                session,_ = self.feed([packet(0,flags=flags),packet(.1)])
                data=session.get_flows()[0].get_data()
                self.assertEqual((data['cwr_flag_count'],data['urg_flag_cnt']),(cwr,urg))

    def test_activity_idle_and_repeat_export(self):
        session,_ = self.feed([packet(0),packet(.1),packet(8.1,'b'),packet(8.2)])
        flow=session.get_flows()[0]
        data=flow.get_data()
        self.assertAlmostEqual(data['idle_mean'],8.)
        self.assertAlmostEqual(data['active_mean'],.1,places=6)
        self.assertEqual(data,flow.get_data())

    def test_udp_and_protocol_key(self):
        session,_ = self.feed([packet(0,flags='S'),packet(.1,'b','SA'),
                              packet(.2,udp=True,payload=10),packet(.3,'b',udp=True,payload=10)])
        flows=session.get_flows()
        self.assertEqual(len(flows),2)
        self.assertEqual({f.protocol for f in flows},{6,17})
        self.assertEqual(sum(len(f.packets) for f in flows),4)

    def test_bulk_first_packet_included_once(self):
        session,_ = self.feed([packet(i*.1,flags='PA',payload=100) for i in range(5)])
        data=session.get_flows()[0].get_data()
        self.assertEqual(data['tot_fwd_pkts'],5)
        self.assertEqual(data['fwd_byts_b_avg'],500)
        self.assertEqual(data['fwd_pkts_b_avg'],5)
        self.assertAlmostEqual(data['fwd_blk_rate_avg'],1250.)

    def test_timeout_reverse_and_shutdown_flush(self):
        session,_ = self.feed([packet(0),packet(1,'b'),packet(300,'b')])
        # Old flow exported at its own clock; next segment starts from its first packet.
        self.assertEqual(len(session.get_flows()),1)
        session.flush_flows()
        session.flush_flows()
        with Path(session.output).open(newline='') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),2)
        self.assertEqual(sum(int(r['tot_fwd_pkts'])+int(r['tot_bwd_pkts']) for r in rows),3)
        self.assertEqual(rows[-1]['src_ip'],'192.0.2.2')
        with self.assertRaises(RuntimeError):
            session.process(packet(301))

    def test_gc_concurrent_with_admission(self):
        session=self.session()
        errors=[]
        def collect():
            try:
                for _ in range(100):
                    session.garbage_collect(1699999999)
            except Exception as e:
                errors.append(e)
        worker=threading.Thread(target=collect)
        worker.start()
        for i in range(100):
            session.process(packet(i*.01))
        worker.join()
        self.assertFalse(errors)
        self.assertEqual(sum(len(f.packets) for f in session.get_flows()),100)

    # HT2.1 characterization of v2, NOT desired future semantics. A future
    # versioned lifecycle fix must deliberately revise these expectations.
    def test_v2_quiet_flow_uses_idle_not_wall_clock_age(self):
        session = self.session()
        session.process(packet(0))
        session.garbage_collect(1700000090)
        self.assertEqual(session.n_exported, 0)
        session.garbage_collect(1700000239)
        self.assertEqual(session.n_exported, 0)
        session.garbage_collect(1700000240)
        self.assertEqual((session.n_exported, session.n_exported_packets), (1, 1))

    def test_v2_fin_and_rst_do_not_close_flow(self):
        for ending in ('FA', 'RA'):
            with self.subTest(ending=ending):
                session = self.session()
                for p in [packet(0, flags='S'), packet(1, 'b', 'SA'), packet(2, flags=ending)]:
                    session.process(p)
                self.assertEqual(session.n_exported, 0)
                self.assertEqual(len(session.get_flows()), 1)
                session.flush_flows()
                self.assertEqual(session.n_exported_packets, 3)

    def test_v2_duration_boundary_includes_triggering_packet(self):
        for end in (90, 180):
            with self.subTest(end=end):
                session = self.session()
                for when in (0, 89, end):
                    session.process(packet(when))
                self.assertEqual(session.n_exported_packets, 3)
                self.assertFalse(session.get_flows())
                with Path(session.output).open(newline='') as stream:
                    row = next(csv.DictReader(stream))
                self.assertEqual(float(row['flow_duration']), end)

    def test_v2_idle_exact_boundary_depends_on_gc_order(self):
        no_gc, with_gc = self.session(), self.session()
        for session in (no_gc, with_gc):
            session.process(packet(0))
        with_gc.garbage_collect(1700000240)
        for session in (no_gc, with_gc):
            session.process(packet(240))
            session.flush_flows()
            self.assertEqual(session.n_exported_packets, 2)
        # process uses >240 before admission, GC uses >=240: segmentation differs.
        self.assertEqual(no_gc.n_exported, 1)
        self.assertEqual(with_gc.n_exported, 2)

    def test_v2_reused_tuple_syn_is_merged_before_timeout(self):
        session = self.session()
        for p in [packet(0, flags='S'), packet(1, 'b', 'SA'),
                  packet(2, flags='RA'), packet(3, flags='S')]:
            session.process(p)
        self.assertEqual(len(session.get_flows()), 1)
        self.assertEqual(len(session.get_flows()[0].packets), 4)

    def test_v2_out_of_order_packet_can_produce_negative_iat(self):
        session = self.session()
        for when in (0, 2, 1):
            session.process(packet(when))
        data = session.get_flows()[0].get_data()
        self.assertEqual(data['flow_iat_min'], -1)
        self.assertEqual(data['fwd_iat_min'], -1)

    def test_production_cli_offline_is_reproducible_and_versioned(self):
        path=self.folder/'cli.pcap'
        wrpcap(str(path),[packet(0,flags='S'),packet(.1,'b','SA'),packet(.2)])
        outputs=[]
        for i in range(2):
            target=self.folder/f'cli{i}.csv'
            proc=subprocess.run([sys.executable,str(RQ3/'scripts/run_live_capture.py'),
                '--pcap-input',str(path),'--output',str(target),'--extractor','project-v2'],capture_output=True,
                text=True,encoding='utf-8',errors='replace',timeout=30,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            self.assertNotIn(b'\r\r\n',target.read_bytes())
            with target.open(newline='') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['extractor_version'],EXTRACTOR_VERSION)
            self.assertEqual(int(rows[0]['tot_fwd_pkts'])+int(rows[0]['tot_bwd_pkts']),3)
            outputs.append(rows)
        self.assertEqual(*outputs)

    def test_non_ipv4_and_non_transport_are_explicitly_ignored(self):
        session=self.session()
        session.process(Ether()/IPv6()/TCP())
        session.process(Ether()/IP())
        self.assertEqual(session.n_ignored,2)
        self.assertFalse(session.get_flows())

    def test_first_zero_window_preserved_both_directions(self):
        packets = [packet(0), packet(.1), packet(.2,'b'), packet(.3,'b')]
        for p,window in zip(packets, [0,4096,0,8192]):
            p[TCP].window = window
        session,decoded = self.feed(packets)
        data = session.get_flows()[0].get_data()
        self.assertEqual((data['init_fwd_win_byts'],data['init_bwd_win_byts']), (0,0))
        # Historical baseline remains reproducible, including its known defect.
        from cicflowmeter.features.context import PacketDirection as D
        old = ProjectFlowV1(decoded[0],D.FORWARD)
        old.add_packet(decoded[1],D.FORWARD)
        self.assertEqual(old.get_data()['init_fwd_win_byts'],4096)

    def test_experimental_conventions_are_explicit_and_limited(self):
        import math
        from cicflowmeter.features.context import PacketDirection as D
        session,decoded = self.feed([packet(0),packet(.1,payload=100),packet(.2,'b')])
        baseline = session.get_flows()[0].get_data()
        candidate = TrainCandidateFlow(decoded[0],D.FORWARD)
        candidate.add_packet(decoded[1],D.FORWARD)
        candidate.add_packet(decoded[2],D.REVERSE)
        result = candidate.get_data()
        self.assertAlmostEqual(result['fwd_pkt_len_std'],100/math.sqrt(2))
        self.assertEqual(result['down_up_ratio'],0)
        self.assertEqual(result['extractor_version'],CANDIDATE_VERSION)
        allowed = {'fwd_pkt_len_std','bwd_pkt_len_std','down_up_ratio',
                   'init_fwd_win_byts','init_bwd_win_byts','extractor_version'}
        self.assertTrue({k for k in baseline if baseline[k] != result[k]} <= allowed)
        _,udp = self.feed([packet(0,udp=True)])
        value = TrainCandidateFlow(udp[0],D.FORWARD).get_data()
        self.assertEqual((value['init_fwd_win_byts'],value['init_bwd_win_byts']),(-1,-1))

    def test_cli_refuses_existing_output(self):
        path = self.folder/'protected.csv'
        path.write_text('existing evidence\n')
        proc = subprocess.run([sys.executable,str(RQ3/'scripts/run_live_capture.py'),
            '--pcap-input',str(self.folder/'missing.pcap'),'--output',str(path)],
            capture_output=True,timeout=30)
        self.assertNotEqual(proc.returncode,0)
        self.assertEqual(path.read_text(),'existing evidence\n')

    def test_signal_stop_stays_responsive_and_flushes_once(self):
        import run_live_capture as cli
        for sig in (signal.SIGINT, getattr(signal, 'SIGBREAK', signal.SIGINT)):
            with self.subTest(signal=sig):
                calls = []
                state = {'alive': True}
                sniffer = SimpleNamespace(running=True, stop_cb=lambda: None,
                    thread=SimpleNamespace(is_alive=lambda: state['alive']))
                sniffer.start = lambda: calls.append('start')
                def stop(join):
                    self.assertFalse(join)
                    state['alive'] = False
                    calls.append('stop')
                sniffer.stop = stop
                sniffer.join = lambda timeout: calls.append(('join', timeout))
                def cleanup():
                    self.assertFalse(state['alive'])
                    # Repeated Ctrl+C during final export must not abort cleanup.
                    signal.raise_signal(sig)
                    calls.append('flush')
                previous = signal.getsignal(sig)
                with patch.object(cli.time, 'sleep', side_effect=lambda _: signal.raise_signal(sig)):
                    cli.wait_for_capture(sniffer, cleanup=cleanup)
                self.assertEqual(calls, ['start', 'stop', ('join', 0), 'flush'])
                self.assertEqual(signal.getsignal(sig), previous)

    def test_transient_health_error_is_latched_after_safe_flush(self):
        import run_live_capture as cli
        state = {'alive': True}
        sniffer = SimpleNamespace(running=True, stop_cb=lambda: None,
            thread=SimpleNamespace(is_alive=lambda: state['alive']), start=lambda: None)
        sniffer.stop = lambda join: state.update(alive=False)
        sniffer.join = lambda timeout: None
        flushed = []
        with patch.object(cli, 'check_health', side_effect=[PermissionError('control read failed'), None]) as check:
            with self.assertRaisesRegex(PermissionError, 'control read failed'):
                cli.wait_for_capture(sniffer, cleanup=lambda: flushed.append(True), health_check=check)
        self.assertEqual(flushed, [True])
        self.assertFalse(state['alive'])

    def test_timed_capture_stop_and_error_propagation(self):
        import run_live_capture as cli
        state = {'alive': True}
        sniffer = SimpleNamespace(running=True, stop_cb=lambda: None,
            thread=SimpleNamespace(is_alive=lambda: state['alive']), start=lambda: None)
        sniffer.stop = lambda join: state.update(alive=False)
        sniffer.join = lambda timeout: None
        with patch.object(cli.time, 'monotonic', side_effect=[0, 2, 2, 2, 2]):
            cli.wait_for_capture(sniffer, seconds=1)
        self.assertFalse(state['alive'])
        def fail(timeout):
            raise RuntimeError('capture failed')
        sniffer.join = fail
        before = signal.getsignal(signal.SIGINT)
        with self.assertRaisesRegex(RuntimeError, 'capture failed'):
            cli.wait_for_capture(sniffer)
        self.assertEqual(signal.getsignal(signal.SIGINT), before)


if __name__=='__main__':
    unittest.main(verbosity=2)
