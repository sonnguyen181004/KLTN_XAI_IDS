"""Audit the 78-column contract without changing production data or extractors.

Main environment: pyarrow/numpy/model; capture worker: existing .venv_capture.
Writes only the explicitly selected audit JSON and temporary fixture PCAP/CSV.
No network traffic is transmitted; no API requests or production DB writes.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RQ3 = ROOT / 'RQ3_IDS_System'
sys.path.insert(0, str(RQ3 / 'app'))


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def capture_worker(output):
    import csv
    from importlib.metadata import version
    from scapy.all import Ether, IP, TCP, UDP, Raw, rdpcap, wrpcap
    from cicflowmeter.flow_session import FlowSession

    def tcp(direction, when, flags='A', payload=0, options=None):
        src, dst = ('192.0.2.1', '192.0.2.2') if direction == 'f' else ('192.0.2.2', '192.0.2.1')
        sport, dport = (40000, 443) if direction == 'f' else (443, 40000)
        p = Ether()/IP(src=src, dst=dst)/TCP(sport=sport, dport=dport, flags=flags,
             window=1024 if direction == 'f' else 2048, options=options or [])
        if payload:
            p /= Raw(b'x' * payload)
        p.time = 1700000000 + when
        return p

    fixtures = {
        'tcp_six_packets': [tcp('f', 0, 'S'), tcp('b', .1, 'SA'), tcp('f', .2),
                            tcp('f', .3, 'PA', 100), tcp('b', .4, 'FA'), tcp('f', .5, 'FA')],
        'cwr_without_urg': [tcp('f', 0, 'C'), tcp('f', .1, 'A')],
        'urg_without_cwr': [tcp('f', 0, 'U'), tcp('f', .1, 'A')],
        'tcp_options_idle': [tcp('f', 0, 'S', options=[('MSS', 1460), ('WScale', 7)]),
                             tcp('f', .1, 'PA', 10), tcp('b', 8.1, 'A'), tcp('f', 8.2, 'FA')],
        'bulk_five_payloads': [tcp('f', i * .1, 'PA', 100) for i in range(5)],
        'two_packets_one_iat': [tcp('f', 0, 'S'), tcp('b', .1, 'SA')],
    }
    packets = []
    for i, direction in enumerate(('f', 'b', 'f')):
        src, dst = ('192.0.2.1', '192.0.2.2') if direction == 'f' else ('192.0.2.2', '192.0.2.1')
        sport, dport = (40000, 443) if direction == 'f' else (443, 40000)
        p = Ether()/IP(src=src, dst=dst)/UDP(sport=sport, dport=dport)/Raw(b'x'*10)
        p.time = 1700000000 + i * .1
        packets.append(p)
    fixtures['udp_three_packets'] = packets
    fixtures['tcp_udp_same_endpoints'] = [tcp('f', 0, 'S'), tcp('b', .1, 'SA'), *packets[2:]]
    result = {'cicflowmeter_version': version('cicflowmeter'), 'fixtures': []}
    with tempfile.TemporaryDirectory(prefix='ids_contract_fixtures_') as folder:
        for name, packets in fixtures.items():
            path = Path(folder) / (name + '.pcap')
            wrpcap(str(path), packets)
            decoded = list(rdpcap(str(path)))
            session = FlowSession(output_mode='csv', output=str(Path(folder)/(name+'.csv')), verbose=False)
            for p in decoded:
                session.process(p)
            flows = list(session.get_flows())
            assert len(flows) == 1, (name, len(flows))
            observed = flows[0].get_data()
            # Independent fixture oracle uses actual decoded PCAP, not extractor methods.
            forward = [p for p in decoded if p[IP].src == '192.0.2.1']
            backward = [p for p in decoded if p[IP].src == '192.0.2.2']
            true_flags = {flag: sum(TCP in p and bool(int(p[TCP].flags) & mask) for p in decoded)
                          for flag, mask in [('fin',1), ('syn',2), ('rst',4), ('psh',8), ('ack',16), ('urg',32), ('ece',64), ('cwr',128)]}
            expected = dict(packets=len(decoded), forward_packets=len(forward), backward_packets=len(backward),
                distinct_ip_protocols=sorted({int(p[IP].proto) for p in decoded}),
                flags=true_flags, frame_bytes_forward=sum(len(p) for p in forward),
                transport_payload_bytes_forward=sum(len(p[TCP if TCP in p else UDP].payload) for p in forward),
                ipv4_header_bytes_forward=sum(p[IP].ihl*4 for p in forward),
                transport_header_bytes_forward=sum(p[TCP].dataofs*4 if TCP in p else 8 for p in forward),
                duration_seconds=float(decoded[-1].time-decoded[0].time),
                backward_iat_seconds=[float(backward[i].time-backward[i-1].time) for i in range(1,len(backward))],
                all_iat_seconds=[float(decoded[i].time-decoded[i-1].time) for i in range(1,len(decoded))])
            session.flush_flows()
            if name == 'tcp_six_packets':
                replay = Path(folder)/'production.csv'
                proc = subprocess.run([sys.executable, str(RQ3/'scripts/run_live_capture.py'),
                    '--pcap-input', str(path), '--output', str(replay), '--extractor', 'legacy'], capture_output=True,
                    text=True, encoding='utf-8', errors='replace', timeout=30,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                assert proc.returncode == 0, proc.stderr
                with replay.open(encoding='utf-8-sig', newline='') as stream:
                    actual = list(csv.DictReader(stream))
                assert len(actual) == 1
                assert all(abs(float(actual[0][k])-float(v)) < 1e-7 for k,v in observed.items()
                           if isinstance(v, (int, float)))
                result['production_replay_matches_fixture'] = True
            result['fixtures'].append(dict(name=name, expected=expected, extracted_flow_count=len(flows), extracted=observed))
        # Isolate stats helper from first-packet duplication.
        from cicflowmeter.utils import get_statistics
        result['single_iat_helper'] = dict(input_seconds=[.1], output=get_statistics([.1]))
    output.write_text(json.dumps(result, indent=2, default=float), encoding='utf-8')


def scan(path, columns):
    import numpy as np
    import pyarrow.parquet as pq
    parquet = pq.ParquetFile(path)
    result = {name: dict(n=0, finite=0, nonzero=0, negative=0, greater_than_one=0,
                         noninteger=0, minimum=None, maximum=None) for name in columns}
    for batch in parquet.iter_batches(batch_size=131072, columns=columns):
        for name, column in zip(columns, batch.columns):
            values = column.to_numpy(zero_copy_only=False).astype('float64', copy=False)
            finite = values[np.isfinite(values)]
            r = result[name]
            r['n'] += len(values)
            r['finite'] += len(finite)
            r['nonzero'] += int(np.count_nonzero(finite))
            r['negative'] += int(np.count_nonzero(finite < 0))
            r['greater_than_one'] += int(np.count_nonzero(finite > 1))
            r['noninteger'] += int(np.count_nonzero(finite != np.floor(finite)))
            if len(finite):
                lo, hi = float(finite.min()), float(finite.max())
                r['minimum'] = lo if r['minimum'] is None else min(r['minimum'], lo)
                r['maximum'] = hi if r['maximum'] is None else max(r['maximum'], hi)
    return dict(file=str(path.relative_to(ROOT)), rows=parquet.metadata.num_rows, columns=result)


def assessment(name):
    """Conservative interpretation of inspected implementation and fixture evidence."""
    if name in ('Dst Port', 'Protocol', 'Flow Duration'):
        return 'checked_fixture_only', 'Giá trị/đổi đơn vị khớp fixture đơn giao thức; chưa chứng nhận toàn bộ flow segmentation.'
    if name == 'CWE Flag Count':
        return 'confirmed_extractor_defect', 'Cột CWR sao chép Fwd URG Flags; fixture tách CWR/URG xác nhận sai.'
    if 'Flag' in name:
        return 'support_mismatch', 'Train/daily có miền 0/1 hoặc hằng; extractor đếm nhiều gói và có thể lặp cờ gói đầu.'
    if name.startswith(('Active ', 'Idle ')):
        return 'confirmed_extractor_defect', 'Fixture có khoảng nghỉ 8s nhưng active/idle đều 0; latest_timestamp được cập nhật trước update_subflow.'
    if '/b Avg' in name or 'Blk Rate' in name:
        return 'support_mismatch', 'Các cột bulk hằng 0 trong train; extractor có bulk khác 0. Chưa xác minh nguồn cleaning.'
    if name.startswith('Subflow '):
        return 'definition_unverified', 'Python sao chép tổng gói/byte, chưa chứng minh tương đương phép chia subflow của nguồn train.'
    if 'Header Len' in name or name == 'Fwd Seg Size Min':
        return 'definition_mismatch_reference', 'Python dùng header IPv4; Java tham chiếu dùng header transport; fixture UDP/options phân biệt được.'
    if name.startswith('Init '):
        return 'sentinel_mismatch', 'Train có -1; Python khởi tạo 0 khi thiếu chiều/TCP, dùng 0 làm điều kiện cập nhật lại window.'
    if 'IAT' in name:
        return 'confirmed_extractor_defect', 'Lặp gói đầu thêm IAT=0; helper bỏ thống kê khi chỉ có 1 khoảng đo (Bwd IAT 0.3s thành 0).'
    if name == 'Down/Up Ratio':
        return 'definition_mismatch_reference', 'Python chia số thực và chịu lặp gói đầu; train chỉ quan sát số nguyên; Java tham chiếu chia nguyên.'
    if 'Pkt Len' in name or 'TotLen ' in name or 'Seg Size Avg' in name or name in ('Pkt Size Avg', 'Flow Byts/s'):
        return 'definition_mismatch_reference', 'Python dùng len(packet), gồm lớp link/IP/transport; Java tham chiếu dùng payload. Lặp gói đầu còn làm lệch thống kê.'
    if name in ('Tot Fwd Pkts', 'Tot Bwd Pkts', 'Flow Pkts/s', 'Fwd Pkts/s', 'Bwd Pkts/s', 'Fwd Act Data Pkts'):
        return 'confirmed_extractor_defect', 'Gói đầu mỗi flow được lưu trong constructor rồi add_packet lần nữa; sai đếm và đại lượng phụ thuộc.'
    raise AssertionError('Unclassified feature: '+name)


def main(output):
    import numpy as np
    import yaml
    from predict import Detector
    from feeder import CICFLOWMETER_COLUMN_MAP, row_to_payload
    from normalize import normalize_flow, TIME_COLUMNS
    cfg = yaml.safe_load((RQ3/'config.yaml').read_text(encoding='utf-8'))
    detector = Detector(ROOT/cfg['paths']['model'], ROOT/cfg['paths']['label_encoder'])
    names = detector.feature_names
    assert len(names) == 78 and set(CICFLOWMETER_COLUMN_MAP.values()) == set(names)
    assert len(set(CICFLOWMETER_COLUMN_MAP.values())) == len(CICFLOWMETER_COLUMN_MAP)
    print('Scanning all 78 train columns...', flush=True)
    train = scan(ROOT/cfg['paths']['train_set'], names)
    selected = [n for n in names if 'Flag' in n or '/b Avg' in n or 'Blk Rate' in n
                or n.startswith(('Active ', 'Idle '))]
    daily = []
    for path in sorted((ROOT/'dataset/CICID-2018').glob('*.parquet')):
        print('Scanning earlier cleaned source:', path.name, flush=True)
        daily.append(scan(path, selected))
    capture_python = RQ3/'.venv_capture/Scripts/python.exe'
    with tempfile.TemporaryDirectory(prefix='ids_contract_worker_') as folder:
        artifact = Path(folder)/'fixtures.json'
        proc = subprocess.run([str(capture_python), str(Path(__file__).resolve()), '--fixture-worker',
            '--output', str(artifact)], capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=90, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if proc.returncode:
            raise RuntimeError(proc.stdout + proc.stderr)
        fixture = json.loads(artifact.read_text(encoding='utf-8'))
    for f in fixture['fixtures']:
        payload = row_to_payload({k: str(v) for k,v in f['extracted'].items()}, list(f['extracted']), True)
        normalized = normalize_flow(payload, names)
        assert normalized.shape == (1,78) and list(normalized.columns) == names
        f['mapped_duration_microseconds'] = float(normalized['Flow Duration'].iloc[0])
        f['prediction_diagnostic_only'] = detector.predict_flow(normalized)
    with sqlite3.connect((ROOT/cfg['paths']['sqlite_db']).as_uri()+'?mode=ro', uri=True) as db:
        saved = db.execute("SELECT features_json FROM FlowRecord WHERE source='pcap_replay'").fetchall()
    vectors = np.array([[json.loads(r[0])[n] for n in names] for r in saved])
    source_folder = RQ3/'.venv_capture/Lib/site-packages/cicflowmeter'
    flow_tree = ast.parse((source_folder/'flow.py').read_text(encoding='utf-8'))
    expressions = {}
    for node in ast.walk(flow_tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(t,ast.Name) and t.id == 'data' for t in node.targets) and isinstance(node.value,ast.Dict):
                expressions.update({ast.literal_eval(k):ast.unparse(v) for k,v in zip(node.value.keys,node.value.values)})
            for t in node.targets:
                if isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id == 'data':
                    expressions[ast.literal_eval(t.slice)] = ast.unparse(node.value)
    inverse = {v:k for k,v in CICFLOWMETER_COLUMN_MAP.items()}
    contract = []
    for i,name in enumerate(names):
        stats = train['columns'][name]
        outside = int(((vectors[:,i] < stats['minimum']) | (vectors[:,i] > stats['maximum'])).sum()) if len(vectors) else 0
        status, note = assessment(name)
        contract.append(dict(feature=name, capture_column=inverse[name], assessment=status, interpretation=note,
            extractor_expression=expressions[inverse[name]],
            seconds_to_microseconds=name in TIME_COLUMNS, train=stats,
            stored_pcap_flows=len(vectors), pcap_outside_train_minmax=outside))
    import pyarrow.parquet as pq
    flag_by_label = pq.read_table(ROOT/cfg['paths']['train_set'],columns=['Label','FIN Flag Cnt']).to_pandas()
    label_stats = flag_by_label.groupby('Label').agg(n=('Label','size'), fin_nonzero=('FIN Flag Cnt',lambda v:int((v>0).sum()))).reset_index().to_dict('records')
    result = dict(scope='diagnostic only; no compatibility certification', model_version=detector.model_version,
        mapping_count=len(contract), time_conversion_columns=TIME_COLUMNS, train=train,
        train_fin_by_label=label_stats,
        earlier_cleaned_daily=daily, capture=fixture, feature_contract=contract,
        extractor_sha256={str(p.relative_to(source_folder)):sha256(p) for p in source_folder.rglob('*.py')},
        provenance_limit='Raw original CSV/PCAP and cleaning/sampling script not located in repository; daily inputs are already cleaned Parquet.')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=float),encoding='utf-8')
    matrix = ['# Đối chiếu đủ 78 đặc trưng', '',
        'Sinh từ stage19; schema khớp không đồng nghĩa ngữ nghĩa tương thích. Trạng thái dựa trên fixture và source đã kiểm tra. Java master chỉ là tham chiếu hiện tại, chưa xác nhận đúng binary V3 đã tạo dataset 2018.', '',
        '| # | Đặc trưng model | Cột Python | Nhận định | Bằng chứng/giới hạn |',
        '|---|---|---|---|---|']
    for i,row in enumerate(contract,1):
        matrix.append(f"| {i} | {row['feature']} | {row['capture_column']} | {row['assessment']} | {row['interpretation']} |")
    output.with_name('feature_compatibility_matrix_20261016.md').write_text('\n'.join(matrix)+'\n',encoding='utf-8')
    print('WROTE',output,flush=True)
    print('TRAIN_CONSTANT_COLUMNS', [n for n,s in train['columns'].items() if s['minimum']==s['maximum']],flush=True)
    for f in fixture['fixtures']:
        print('FIXTURE',f['name'],'actual_packets',f['expected']['packets'],
              'extracted_packets',f['extracted']['tot_fwd_pkts']+f['extracted']['tot_bwd_pkts'],flush=True)
    print('ALL 78 COLUMNS MAPPED; production replay cross-check passed; semantic compatibility remains unresolved',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture-worker',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    (capture_worker if args.fixture_worker else main)(args.output)
