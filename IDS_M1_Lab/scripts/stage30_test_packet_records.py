"""Exact retained-record parity and memory experiment; no live traffic/DB."""
import csv
import gc
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import tracemalloc
from unittest.mock import patch

from stage20_test_capture_adapter import packet
from capture_lifecycle import LifecycleSession, LifecycleFlow
from capture_packet_record import PacketRecord
from cicflowmeter.features.context import PacketDirection
from scapy.utils import PcapReader
from scapy.layers.inet import TCP
from scapy.packet import Padding

ROOT = Path(__file__).resolve().parents[2]


def extract(source, output, compact):
    # Identity conversion reproduces the pre-change V3 storage, not V1/V2.
    convert = PacketRecord.from_packet if compact else lambda p: p
    with patch('capture_lifecycle.PacketRecord.from_packet', new=convert):
        session = LifecycleSession(output_mode='csv', output=str(output),
                                   max_buffered_packets=50000, max_buffered_bytes=67108864)
        try:
            with PcapReader(str(source)) as reader:
                for p in reader:
                    session.process(p)
            session.flush_flows()
        finally:
            session.output_writer.file.close()
    return session.packets_count, session.n_exported_packets


def memory(compact):
    gc.collect()
    convert = PacketRecord.from_packet if compact else lambda p: p
    tracemalloc.start()
    try:
        # No Mock call history: it would retain the original packet arguments.
        with patch('capture_lifecycle.PacketRecord.from_packet', new=convert):
            flow = LifecycleFlow(packet(0, payload=1200), PacketDirection.FORWARD)
            for i in range(1, 1000):
                flow.add_packet(packet(i/1000, payload=1200), PacketDirection.FORWARD)
            gc.collect()
            current, peak = tracemalloc.get_traced_memory()
        return dict(retained_python_bytes=current, peak_python_bytes=peak,
                    packets=len(flow.packets))
    finally:
        tracemalloc.stop()


def main(output, model_python):
    if output.exists():
        raise FileExistsError(output)
    # Edge cases: every flag, UDP, zero window, payload/padding, reverse IAT.
    fixtures = [packet(0, flags='S'), packet(.1, 'b', flags='SA'),
                packet(.2, flags='FPUAEC', payload=31), packet(.3, udp=True, payload=50)]
    fixtures[0][TCP].window = 0
    fixtures[2] = fixtures[2]/Padding(b'pad')
    fixtures[2].time = fixtures[1].time + .1
    for p in fixtures:
        a = LifecycleFlow(p, PacketDirection.FORWARD)
        convert = lambda q: q
        with patch('capture_lifecycle.PacketRecord.from_packet', new=convert):
            b = LifecycleFlow(p, PacketDirection.FORWARD)
        assert a.get_data() == b.get_data()
        assert a.get_data() == a.get_data(), 'Snapshot mutated state'
        assert isinstance(a.packets[0][0], PacketRecord)
    report = dict(status='passed', fixture_packets=len(fixtures), runs=[],
                  note='Exact CSV parity against V3 original storage; no ground truth/FPR. Memory is tracemalloc, not RSS.')
    with tempfile.TemporaryDirectory(prefix='ids_record_parity_') as temp:
        for name in ('test.pcapng', 'tesst2.pcapng'):
            source = ROOT/name
            assert source.exists(), source
            paths = [Path(temp)/f'{name}.{mode}.csv' for mode in ('original', 'compact')]
            counters = [extract(source, path, compact) for path, compact in zip(paths, (False, True))]
            assert counters[0] == counters[1]
            assert counters[0][0] == counters[0][1]
            assert paths[0].read_bytes() == paths[1].read_bytes(), name
            with paths[0].open(encoding='utf-8', newline='') as stream:
                rows = list(csv.DictReader(stream))
            # Model lives in the main Python environment, not capture's venv.
            check = subprocess.run([model_python, str(Path(__file__).with_name('stage30_verify_model_parity.py')),
                                    *map(str, paths)], capture_output=True, text=True, timeout=120)
            assert check.returncode == 0, check.stdout + check.stderr
            report['runs'].append(dict(file=name, sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                       packets=counters[0][0], flows=len(rows), exact_csv_equal=True,
                                       model_parity=json.loads(check.stdout)))
            print('EXACT PARITY', name, counters[0], len(rows), flush=True)
    report['memory'] = {mode: memory(compact) for mode, compact in (('original', False), ('compact', True))}
    assert report['memory']['compact']['retained_python_bytes'] < report['memory']['original']['retained_python_bytes']*.5
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main(Path(sys.argv[1]), sys.argv[2])
