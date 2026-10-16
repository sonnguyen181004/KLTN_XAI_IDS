"""Independent packet-oracle tests; run with .venv_capture Python. No live capture."""
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from scapy.all import Ether, IP, IPv6, TCP, UDP, Raw, rdpcap, wrpcap

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RQ3/'app'))
from capture_adapter import ProjectFlowSession, EXTRACTOR_VERSION, statistics


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

    def test_production_cli_offline_is_reproducible_and_versioned(self):
        path=self.folder/'cli.pcap'
        wrpcap(str(path),[packet(0,flags='S'),packet(.1,'b','SA'),packet(.2)])
        outputs=[]
        for i in range(2):
            target=self.folder/f'cli{i}.csv'
            proc=subprocess.run([sys.executable,str(RQ3/'scripts/run_live_capture.py'),
                '--pcap-input',str(path),'--output',str(target)],capture_output=True,
                text=True,encoding='utf-8',errors='replace',timeout=30,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
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


if __name__=='__main__':
    unittest.main(verbosity=2)
