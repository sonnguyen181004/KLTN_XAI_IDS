"""Read-only row-wise train/test hypotheses plus independent packet fixtures.

No production API/DB, packet transmission, model inference or input rewrites.
JSON contains aggregate evidence, not data rows or personal IP addresses.
Run normally with the main Python; --fixture-worker uses .venv_capture.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RQ3 = ROOT / 'RQ3_IDS_System'
RTOL, ATOL = 2e-5, 1e-3  # Float32 inputs; diagnostic tolerance, not exact equality.


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def relations(v):
    """Each hypothesis returns (eligible rows, matching eligible rows)."""
    result = {}

    def check(name, eligible, observed, candidate):
        eligible = eligible & np.isfinite(observed) & np.isfinite(candidate)
        result[name] = (int(eligible.sum()), int((eligible & np.isclose(
            observed, candidate, rtol=RTOL, atol=ATOL)).sum()))

    f, b = v['Tot Fwd Pkts'], v['Tot Bwd Pkts']
    for direction, n in [('Fwd', f), ('Bwd', b)]:
        total = v[f'TotLen {direction} Pkts']
        mean = v[f'{direction} Pkt Len Mean']
        gap = v[f'{direction} Pkt Len Max'] - v[f'{direction} Pkt Len Min']
        std = v[f'{direction} Pkt Len Std']
        check(f'{direction}.total_equals_n_times_mean', n > 0, total, n * mean)
        # Exactly two observations determine both candidate SDs from min/max.
        # Require gap >= 1 to prevent equal/near-zero values matching both.
        check(f'{direction}.two_packet_std_population', (n == 2) & (gap >= 1), std, gap / 2)
        check(f'{direction}.two_packet_std_sample', (n == 2) & (gap >= 1), std, gap / np.sqrt(2))
        iat_gap = v[f'{direction} IAT Max'] - v[f'{direction} IAT Min']
        check(f'{direction}.two_interval_iat_std_population', (n == 3) & (iat_gap >= 1),
              v[f'{direction} IAT Std'], iat_gap / 2)
        check(f'{direction}.two_interval_iat_std_sample', (n == 3) & (iat_gap >= 1),
              v[f'{direction} IAT Std'], iat_gap / np.sqrt(2))
        check(f'{direction}.header_equals_20_times_n', n > 0,
              v[f'{direction} Header Len'], 20 * n)
        check(f'{direction}.subflow_packets_equal_total', n > 0,
              v[f'Subflow {direction} Pkts'], n)
        check(f'{direction}.subflow_bytes_equal_total', total > 0,
              v[f'Subflow {direction} Byts'], total)
    ratio = np.divide(b, f, out=np.zeros_like(b), where=f > 0)
    fractional = (f > 0) & (ratio != np.floor(ratio))
    check('ratio.fractional_cases_floor', fractional, v['Down/Up Ratio'], np.floor(ratio))
    check('ratio.fractional_cases_real', fractional, v['Down/Up Ratio'], ratio)
    n = f + b
    total = v['TotLen Fwd Pkts'] + v['TotLen Bwd Pkts']
    check('length.global_mean_times_n_equals_directional_total', n > 0,
          v['Pkt Len Mean'] * n, total)
    check('length.average_size_equals_global_mean', n > 0,
          v['Pkt Size Avg'], v['Pkt Len Mean'])
    check('length.average_size_times_n_equals_mean_times_n_plus_one', n > 0,
          v['Pkt Size Avg'] * n, v['Pkt Len Mean'] * (n + 1))
    check('length.nonzero_mean_average_size_equals_global_mean', (n > 0) & (v['Pkt Len Mean'] > 0),
          v['Pkt Size Avg'], v['Pkt Len Mean'])
    # Candidate extra length is diagnostic only; without packets it is not
    # possible to establish which packet (if any) was counted an extra time.
    extra = v['Pkt Len Mean'] * (n + 1) - total
    low, high = v['Pkt Len Min'], v['Pkt Len Max']
    eligible = (n > 0) & np.isfinite(extra) & np.isfinite(low) & np.isfinite(high)
    tolerance = ATOL + RTOL * np.maximum(np.abs(total), np.abs(v['Pkt Len Mean'] * (n+1)))
    result['length.candidate_extra_within_packet_min_max'] = (
        int(eligible.sum()), int((eligible & (extra >= low-tolerance) & (extra <= high+tolerance)).sum()))
    udp = v['Protocol'] == 17
    tcp_missing_bwd = (v['Protocol'] == 6) & (b == 0)
    for direction in ('Fwd', 'Bwd'):
        check(f'window.udp_{direction}_minus_one', udp, v[f'Init {direction} Win Byts'],
              np.full_like(n, -1))
    check('window.tcp_missing_bwd_minus_one', tcp_missing_bwd, v['Init Bwd Win Byts'],
          np.full_like(n, -1))
    return result


def scan(path):
    import pyarrow.parquet as pq
    columns = ['Protocol', 'Tot Fwd Pkts', 'Tot Bwd Pkts', 'Down/Up Ratio',
               'Pkt Len Mean', 'Pkt Len Min', 'Pkt Len Max', 'Pkt Size Avg',
               'Init Fwd Win Byts', 'Init Bwd Win Byts']
    for d in ('Fwd', 'Bwd'):
        columns += [f'TotLen {d} Pkts', f'{d} Pkt Len Mean', f'{d} Pkt Len Min',
                    f'{d} Pkt Len Max', f'{d} Pkt Len Std', f'{d} Header Len',
                    f'Subflow {d} Pkts', f'Subflow {d} Byts',
                    f'{d} IAT Min', f'{d} IAT Max', f'{d} IAT Std']
    parquet = pq.ParquetFile(path)
    stats = {}
    for batch in parquet.iter_batches(batch_size=131072, columns=columns):
        v = {name: column.to_numpy(zero_copy_only=False).astype('float64')
             for name, column in zip(columns, batch.columns)}
        for name, (eligible, matched) in relations(v).items():
            r = stats.setdefault(name, dict(eligible=0, matched=0))
            r['eligible'] += eligible
            r['matched'] += matched
    for r in stats.values():
        r['unmatched'] = r['eligible'] - r['matched']
        r['match_fraction'] = r['matched'] / r['eligible'] if r['eligible'] else None
    return dict(path=str(path.relative_to(ROOT)), rows=parquet.metadata.num_rows,
                file_bytes=path.stat().st_size, file_sha256=sha256(path),
                schema_sha256=hashlib.sha256(str(parquet.schema_arrow).encode()).hexdigest(),
                hypotheses=stats)


def fixture_worker():
    from importlib.metadata import version
    sys.path.insert(0, str(RQ3))
    from app.capture_adapter import ProjectFlowV1 as ProjectFlow, V1_VERSION as EXTRACTOR_VERSION
    from cicflowmeter.features.context import PacketDirection as D
    from scapy.all import Ether, IP, TCP, UDP, Raw

    def packet(when, payload=0, window=1000, udp=False, reverse=False, options=None):
        src, dst = ('192.0.2.1', '192.0.2.2') if not reverse else ('192.0.2.2', '192.0.2.1')
        sport, dport = (40000, 443) if not reverse else (443, 40000)
        transport = UDP(sport=sport, dport=dport) if udp else TCP(
            sport=sport, dport=dport, flags='A', window=window, options=options or [])
        p = Ether()/IP(src=src, dst=dst)/transport
        if payload:
            p /= Raw(b'x' * payload)
        p = Ether(bytes(p))  # Decode real header lengths, as when reading PCAP.
        p.time = 1700000000. + when
        return p

    def extract(packets):
        flow = ProjectFlow(packets[0], D.FORWARD)
        for p in packets[1:]:
            flow.add_packet(p, D.FORWARD if p[IP].src == packets[0][IP].src else D.REVERSE)
        return flow.get_data()

    packets = [packet(0, options=[('MSS', 1460), ('WScale', 7)]), packet(.1, payload=100)]
    row = extract(packets)
    frames = [len(p) for p in packets]
    payloads = [len(p[TCP].payload) for p in packets]
    transport_headers = [p[TCP].dataofs * 4 for p in packets]
    assert row['totlen_fwd_pkts'] == sum(frames)
    assert np.isclose(row['fwd_pkt_len_std'], np.std(frames, ddof=0))
    assert not np.isclose(row['fwd_pkt_len_std'], np.std(frames, ddof=1))
    assert row['fwd_header_len'] == 40 != sum(transport_headers)
    assert row['fwd_seg_size_min'] == 20
    assert row['init_bwd_win_byts'] == 0
    zero = extract([packet(0, window=0), packet(.1, window=4096)])
    assert zero['init_fwd_win_byts'] == 4096  # Confirms current overwrite, not correct semantics.
    udp = extract([packet(0, udp=True), packet(.1, payload=10, udp=True)])
    assert udp['init_fwd_win_byts'] == udp['init_bwd_win_byts'] == 0
    ratio = extract([packet(0), packet(.1), packet(.2, reverse=True)])
    assert ratio['down_up_ratio'] == .5
    subflow = extract([packet(0, payload=10), packet(.1, payload=20), packet(2, payload=30)])
    assert subflow['subflow_fwd_pkts'] == subflow['tot_fwd_pkts'] == 3
    assert subflow['subflow_fwd_byts'] == subflow['totlen_fwd_pkts']
    bulk = extract([packet(i * .1, payload=100) for i in range(5)])
    assert bulk['fwd_byts_b_avg'] == 500 and bulk['fwd_pkts_b_avg'] == 5
    return dict(extractor_version=EXTRACTOR_VERSION, cicflowmeter_version=version('cicflowmeter'), assertions_passed=True,
        two_forward_packets=dict(payload_lengths=payloads, frame_lengths=frames,
            transport_headers=transport_headers, project_total=row['totlen_fwd_pkts'],
            project_header=row['fwd_header_len'], project_std=row['fwd_pkt_len_std'],
            population_frame_std=float(np.std(frames)), sample_frame_std=float(np.std(frames, ddof=1)),
            population_payload_std=float(np.std(payloads)), sample_payload_std=float(np.std(payloads, ddof=1))),
        zero_initial_window_then_4096=dict(expected_first_observation=0,
            project_value=zero['init_fwd_win_byts']),
        missing_backward_window=row['init_bwd_win_byts'], udp_windows=[udp['init_fwd_win_byts'], udp['init_bwd_win_byts']],
        ratio_two_forward_one_backward=ratio['down_up_ratio'],
        subflow_with_1_9_second_gap=dict(packets=subflow['subflow_fwd_pkts'], bytes=subflow['subflow_fwd_byts']),
        five_payload_bulk={k:bulk[k] for k in ('fwd_byts_b_avg','fwd_pkts_b_avg','fwd_blk_rate_avg')})


class HypothesisTests(unittest.TestCase):
    @staticmethod
    def values():
        v = {name:np.array([0., 0., 0.]) for name in (
            'Tot Fwd Pkts', 'Tot Bwd Pkts', 'Protocol', 'Down/Up Ratio',
            'Pkt Len Mean', 'Pkt Len Min', 'Pkt Len Max', 'Pkt Size Avg',
            'Init Fwd Win Byts', 'Init Bwd Win Byts')}
        for d in ('Fwd', 'Bwd'):
            for name in (f'TotLen {d} Pkts', f'{d} Pkt Len Mean', f'{d} Pkt Len Min',
                         f'{d} Pkt Len Max', f'{d} Pkt Len Std', f'{d} Header Len',
                         f'Subflow {d} Pkts', f'Subflow {d} Byts',
                         f'{d} IAT Min', f'{d} IAT Max', f'{d} IAT Std'):
                v[name] = np.array([0., 0., 0.])
        return v

    def test_real_relations_eligibility_and_finite_filter(self):
        v = self.values()
        v['Tot Fwd Pkts'] = np.array([2., 2., 2.])
        v['Fwd Pkt Len Max'] = np.array([100., 100., np.nan])
        v['Fwd Pkt Len Std'] = np.array([50., 100/np.sqrt(2), 0.])
        r = relations(v)
        self.assertEqual(r['Fwd.two_packet_std_population'], (2, 1))
        self.assertEqual(r['Fwd.two_packet_std_sample'], (2, 1))
        self.assertEqual(r['Bwd.two_packet_std_sample'], (0, 0))
        self.assertEqual(r['ratio.fractional_cases_floor'], (0, 0))

    def test_two_observation_standard_deviations_are_distinguished(self):
        n, gap = np.array([2., 2., 1., 2.]), np.array([100., 100., 100., 0.])
        std = np.array([50., 100 / np.sqrt(2), 0., 0.])
        mask = (n == 2) & (gap >= 1)
        self.assertEqual(int((mask & np.isclose(std, gap/2, rtol=RTOL, atol=ATOL)).sum()), 1)
        self.assertEqual(int((mask & np.isclose(std, gap/np.sqrt(2), rtol=RTOL, atol=ATOL)).sum()), 1)

    def test_fractional_ratio_cases_distinguish_floor_from_real(self):
        f, b = np.array([2., 4., 1.]), np.array([1., 3., 2.])
        ratio = b/f
        self.assertEqual(int((ratio != np.floor(ratio)).sum()), 2)
        self.assertTrue(np.array_equal(np.floor(ratio), [0, 0, 2]))


def main(output, include_daily=False):
    import yaml
    cfg = yaml.safe_load((RQ3/'config.yaml').read_text(encoding='utf-8'))
    datasets = {}
    for name in ('train_set', 'test_set'):
        print('Scanning', name, flush=True)
        datasets[name] = scan(ROOT/cfg['paths'][name])
    if include_daily:
        for path in sorted((ROOT/'dataset/CICID-2018').glob('*_clean.parquet')):
            print('Scanning', path.name, flush=True)
            datasets['daily/' + path.stem] = scan(path)
    with tempfile.TemporaryDirectory(prefix='ids_semantic_probe_') as folder:
        evidence = Path(folder)/'fixtures.json'
        proc = subprocess.run([str(RQ3/'.venv_capture/Scripts/python.exe'), str(Path(__file__).resolve()),
            '--fixture-worker', '--output', str(evidence)], capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=60,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if proc.returncode:
            raise RuntimeError(proc.stdout + proc.stderr)
        fixtures = json.loads(evidence.read_text(encoding='utf-8'))
    result = dict(scope='Row-wise hypotheses only; not historical V3 parity certification or accuracy measurement',
        source_sha256={str(p.relative_to(ROOT)):sha256(p) for p in
                       (Path(__file__).resolve(), RQ3/'app/capture_adapter.py')},
        tolerance=dict(relative=RTOL, absolute=ATOL), datasets=datasets, packet_fixtures=fixtures,
        limits=['No original paired PCAP/CSV or preprocessing pipeline located.',
                'Data relations do not prove which historical extractor or cleaning operation produced them.',
                'No runtime/default feature transformations, model or LIME changes.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    for name, data in datasets.items():
        print(name, data['rows'], 'rows', flush=True)
        for hypothesis, r in data['hypotheses'].items():
            print(hypothesis, f"{r['matched']}/{r['eligible']}", flush=True)
    print('FIXTURE ASSERTIONS PASS; WROTE', output, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture-worker', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--include-daily', action='store_true', help='Also scan all local 2018 daily cleaned inputs')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=[sys.argv[0]])
    elif args.output is None:
        parser.error('--output is required unless --self-test')
    elif args.fixture_worker:
        args.output.write_text(json.dumps(fixture_worker(), indent=2), encoding='utf-8')
    else:
        main(args.output, include_daily=args.include_daily)
