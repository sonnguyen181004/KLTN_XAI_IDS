"""Read-only lab CSV inference and Java/dataset semantics audit; no live traffic."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def fixture(path):
    from scapy.all import Ether, IP, TCP, Raw, wrpcap
    packets = []
    def add(port, specs):
        for t, reverse, flags, size, window in specs:
            src, dst = ('192.0.2.2', '192.0.2.1') if reverse else ('192.0.2.1', '192.0.2.2')
            sport, dport = (443, port) if reverse else (port, 443)
            p = Ether(src='02:00:00:00:00:01', dst='02:00:00:00:00:02')/IP(src=src, dst=dst)/TCP(sport=sport, dport=dport, flags=flags, window=window)
            if size:
                p /= Raw(b'x' * size)
            p.time = 1700000000 + t
            packets.append(p)
    add(40001, [(0, False, 'PA', 10, 1000), (.1, True, 'PA', 20, 2000),
                (.2, False, 'PA', 30, 1000), (.3, True, 'PA', 40, 3000), (.4, False, 'PA', 50, 1000)])
    for port, backwards_first in [(40002, False), (40003, True)]:
        add(port, [(1, False, 'A', 0, 1000), (1.1, True, 'A', 0, 2000),
                   (1.2, backwards_first, 'FA', 0, 1000), (1.3, not backwards_first, 'A', 0, 2000),
                   (1.4, not backwards_first, 'FA', 0, 2000), (1.5, backwards_first, 'A', 0, 1000)])
    add(40004, [(2, False, 'A', 10, 1000), (2.1, True, 'A', 20, 2000),
                (123, True, 'A', 30, 2000), (123.1, False, 'A', 40, 1000)])
    packets.sort(key=lambda p: p.time)
    wrpcap(str(path), packets)
    print('fixture packets', len(packets))


if __name__ == '__main__' and '--fixture' in sys.argv:
    fixture(Path(sys.argv[-1]))
    sys.exit(0)

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0, str(ROOT / 'RQ3_IDS_System/scripts'))
sys.path.insert(0, str(ROOT / 'RQ3_IDS_System/app'))
from stage23_audit_feature_semantics import scan, relations
from feeder import row_to_payload
os.environ.setdefault('JAVA_M0_TRIAL_TOKEN', 'read-only-lab-audit')
from service import manager, FEATURE_MAP
from run_java_live_m0 import java_environment


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def flag_stats(path):
    cols = [n for n in manager.names if 'Flag' in n or 'Flags' in n]
    summary = {n: {'min': None, 'max': None, 'above_one': 0} for n in cols}
    for batch in pq.ParquetFile(path).iter_batches(columns=cols, batch_size=131072):
        for n in cols:
            a = batch.column(n).to_numpy(zero_copy_only=False)
            s = summary[n]
            lo, hi = float(np.nanmin(a)), float(np.nanmax(a))
            s['min'] = lo if s['min'] is None else min(s['min'], lo)
            s['max'] = hi if s['max'] is None else max(s['max'], hi)
            s['above_one'] += int((a > 1).sum())
    return summary


result = {'scope': 'CSV inference is not Java re-extraction; dataset relations are not full historical extractor equivalence',
          'lab': {}, 'datasets': {}, 'models': {}}
for model, relative in [('M0', 'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl'),
                        ('M1', 'IDS_M1_Lab/models/m1_xgboost_model.pkl')]:
    result['models'][model] = {'path': relative, 'sha256': digest(ROOT / relative),
                               'features': manager.models[model]['names'], 'classes': manager.models[model]['classes']}
result['m1_rq4_reference_sha256'] = digest(ROOT / 'RQ4_Retrain_Compare/models/m1_xgboost_model.pkl')
for kind, session, port in [('hulk', 'ff8f0fa5051b45389a9393023effc083', 80),
                            ('ssh', 'a10c3bc274594a00be959997bf552236', 22)]:
    source = ROOT / 'IDS_M1_Lab/data/capture_sessions' / session / 'flows.csv'
    raw = pd.read_csv(source)
    payloads = [row_to_payload(r, list(raw.columns), True) for r in raw.to_dict('records')]
    x = pd.DataFrame(payloads).reindex(columns=manager.names)
    assert np.isfinite(x.to_numpy()).all()
    canonical = x.copy()
    for old, new in [('src_ip', 'Src IP'), ('dst_ip', 'Dst IP'), ('src_port', 'Src Port'),
                     ('dst_port', 'Dst Port'), ('timestamp', 'Timestamp')]:
        canonical[new] = raw[old]
    manager.import_csv(kind + '_normalized.csv', canonical.to_csv(index=False))
    assert all(np.allclose([r['features'][n] for n in manager.names], x.iloc[i].to_numpy(), rtol=1e-12, atol=1e-8)
               for i, r in enumerate(manager.records))
    item = {'source': str(source.relative_to(ROOT)), 'sha256': digest(source), 'rows': len(raw),
            'extractor_versions': raw['extractor_version'].value_counts().to_dict(),
            'pcap_in_session': [str(p.relative_to(source.parent)) for p in source.parent.rglob('*')
                                if p.suffix.lower() in ('.pcap', '.pcapng')],
            'time_conversion': 'seconds to microseconds once via project feeder; rates unchanged',
            'target_port': port, 'rows_target_port': int((raw.dst_port == port).sum()), 'models': {}}
    for model, bundle in manager.models.items():
        proba = bundle['model'].predict_proba(x[bundle['names']])
        labels = np.array(bundle['classes'])[proba.argmax(axis=1)]
        observed = manager.flows(model)
        assert labels.tolist() == [r['prediction'] for r in observed]
        item['models'][model] = {'labels': pd.Series(labels).value_counts().to_dict(),
            'target_port_labels': pd.Series(labels[raw.dst_port == port]).value_counts().to_dict(),
            'service_matches_direct_model': True,
            'shap_errors': sum(bool(r['error']) for r in observed),
            'shap_max_additivity_error': max((r['shap']['additivity_error'] for r in observed if r['shap']), default=None)}
    result['lab'][kind] = item
    print('LAB', kind, item['models'], flush=True)

for name, relative in [('M0_train', 'dataset/CICID-2018_processed/train_set.parquet'),
                        ('M1_reference_train', 'RQ4_Retrain_Compare/data/d2_train.parquet')]:
    path = ROOT / relative
    info = scan(path)
    info['flag_stats'] = flag_stats(path)
    schema_features = [n for n in pq.read_schema(path).names if n in manager.names]
    info['78_feature_order_matches'] = schema_features == manager.names
    result['datasets'][name] = info
    print('DATASET', name, info['rows'], flush=True)

out = HERE / 'output' / ('semantics_' + uuid.uuid4().hex[:8])
out.mkdir(parents=True)
pcap = out / 'known_packets.pcap'
subprocess.run([str(ROOT / 'RQ3_IDS_System/.venv_capture/Scripts/python.exe'), __file__, '--fixture', str(pcap)], check=True)
proc = subprocess.run([str(HERE / 'upstream/gradlew.bat'), 'exeCMD', f'-PtrialInput={pcap}',
                       f'-PtrialOutput={out}', '--offline', '--no-daemon', '--console=plain'],
                      cwd=HERE / 'upstream', env=java_environment(), capture_output=True,
                      text=True, encoding='utf-8', errors='replace', timeout=120)
(out / 'java.log').write_text(proc.stdout + proc.stderr, encoding='utf-8')
assert proc.returncode == 0, proc.stdout[-1000:] + proc.stderr[-1000:]
j = pd.read_csv(out / 'known_packets.pcap_Flow.csv')
jx = j[[FEATURE_MAP[n] for n in manager.names]].copy()
jx.columns = manager.names
first = jx.loc[j['Src Port'] == 40001].iloc[0]
expected = {'Tot Fwd Pkts': 3, 'Tot Bwd Pkts': 2, 'Flow Duration': 400000,
            'TotLen Fwd Pkts': 90, 'TotLen Bwd Pkts': 60, 'Fwd Pkt Len Mean': 30,
            'Fwd Pkt Len Std': 20, 'Bwd Pkt Len Std': 20 / np.sqrt(2),
            'Down/Up Ratio': 0, 'PSH Flag Cnt': 5, 'ACK Flag Cnt': 5,
            'Fwd PSH Flags': 1, 'Bwd PSH Flags': 0, 'Init Bwd Win Byts': 3000,
            'Pkt Len Mean': 160/6, 'Pkt Size Avg': 32}
checks = {n: {'expected': v, 'actual': float(first[n]), 'matches': bool(np.isclose(first[n], v))} for n, v in expected.items()}
assert all(c['matches'] for c in checks.values()), checks
python_csv = out / 'known_packets_python.csv'
python_proc = subprocess.run([str(ROOT / 'RQ3_IDS_System/.venv_capture/Scripts/python.exe'),
    str(ROOT / 'RQ3_IDS_System/scripts/run_live_capture.py'), '--pcap-input', str(pcap),
    '--output', str(python_csv), '--extractor', 'project'], capture_output=True,
    text=True, encoding='utf-8', errors='replace', timeout=90)
(out / 'python.log').write_text(python_proc.stdout + python_proc.stderr, encoding='utf-8')
assert python_proc.returncode == 0, python_proc.stderr[-1000:]
py = pd.read_csv(python_csv)
pyx = pd.DataFrame([row_to_payload(r, list(py.columns), True) for r in py.to_dict('records')]).reindex(columns=manager.names)
pyfirst = pyx.loc[py['src_port'] == 40001].iloc[0]
different = [n for n in manager.names if not np.isclose(first[n], pyfirst[n], rtol=1e-5, atol=1e-5)]
result['java_fixture'] = {'csv': str((out / 'known_packets.pcap_Flow.csv').relative_to(ROOT)),
    'pcap_sha256': digest(pcap), 'input_packets': 21, 'output_flow_rows': len(j),
    'packet_sum_in_features': int((jx['Tot Fwd Pkts']+jx['Tot Bwd Pkts']).sum()),
    'checks': checks, 'flows': j[['Src Port', 'Dst Port', 'Total Fwd Packet', 'Total Bwd packets', 'FIN Flag Count']].to_dict('records')}
result['same_packet_python_fixture'] = {'extractor_versions': py.extractor_version.value_counts().to_dict(),
    'output_flow_rows': len(py), 'packet_sum_in_features': int((pyx['Tot Fwd Pkts']+pyx['Tot Bwd Pkts']).sum()),
    'numeric_flow_differences': {n: {'java': float(first[n]), 'python': float(pyfirst[n])} for n in different},
    'comparison_scope': '5 packets of one complete numeric fixture, no row-order matching across split flows'}
result['java_provenance'] = {'upstream_commit': subprocess.check_output(['git', '-C', str(HERE/'upstream'), 'rev-parse', 'HEAD'], text=True).strip(),
    'live_source_matches_build_source': digest(HERE/'LiveTrial.java') == digest(HERE/'upstream/src/main/java/cic/cs/unb/ca/ifm/LiveTrial.java'),
    'live_source_sha256': digest(HERE/'LiveTrial.java'),
    'last_live_log_sha256': digest(HERE/'output/dashboard_5e1b1eae9e28.log'),
    'core_modified_files': subprocess.check_output(['git', '-C', str(HERE/'upstream'), 'diff', '--name-only', '--', 'src/main/java/cic/cs/unb/ca/jnetpcap'], text=True).splitlines()}
target = HERE / 'lab_semantics_audit_20261117.json'
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('FIXTURE', result['java_fixture'], flush=True)
print('SAVED', target, flush=True)
