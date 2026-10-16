"""Isolated regression: temporary DB/server, real model, Streamlit AppTest.

No live DB, CSV or PCAP is modified. Run from any directory with project dependencies.
"""
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import db
import monitoring
from flow_metadata import timestamp_utc


def main():
    with tempfile.TemporaryDirectory(prefix='ids_ui_test_') as folder:
        target = Path(folder) / 'test.db'
        # Old schema plus old data, then migrate twice: no data loss.
        conn = sqlite3.connect(target)
        conn.executescript(db.SCHEMA_SQL)
        db.insert_flow(conn, 'legacy', '2026-01-01T00:00:00+00:00', 'api', {'Dst Port': 80}, None)
        db.insert_prediction(conn, 'legacy', 'Benign', {'Benign': 1.0}, 'fixture', '2026-01-01T00:00:00+00:00')
        conn.close()
        db.init_db(target).close()
        conn = db.init_db(target)
        assert monitoring.detail(conn, 'legacy')['flow_timestamp_utc'] is None
        # Explicit synthetic read-model fixtures; not an accuracy evaluation.
        for i in range(205):
            fid = f'fixture-{i:04}'
            stamp = f'2026-01-02T00:{i // 60:02}:{i % 60:02}+00:00'
            db.insert_flow(conn, fid, stamp, 'api', {'Dst Port': 443}, None)
            conn.execute('UPDATE FlowRecord SET capture_run_id=? WHERE flow_id=?', ('fixture', fid))
            db.insert_prediction(conn, fid, 'Benign', {'Benign': 1.0}, 'fixture', stamp)
        assert monitoring.summary(conn, {'capture_run_id': 'fixture'})['flows'] == 205
        assert len(monitoring.flows(conn, {}, 50, 0)['flows']) == 50
        assert monitoring.flows(conn, {'capture_run_id': '__legacy__'})['count'] == 1
        conn.close()
        assert timestamp_utc('2026-10-16T07:21:30', '+07:00') == '2026-10-16T00:21:30+00:00'
        assert timestamp_utc('2026-10-16T07:21:30') is None
        print('PASS migration, aggregation >200, pagination, legacy/timezone')

        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        env = {**os.environ, 'IDS_DB_PATH': str(target), 'PYTHONIOENCODING': 'utf-8'}
        with open(Path(folder) / 'api.log', 'w', encoding='utf-8') as log:
            proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                for _ in range(120):
                    try:
                        if requests.get(url + '/health', timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    if proc.poll() is not None:
                        raise RuntimeError('API failed: ' + (Path(folder) / 'api.log').read_text(encoding='utf-8'))
                    time.sleep(.25)
                else:
                    raise RuntimeError('API startup timeout')
                def get(path, **params):
                    response = requests.get(url + path, params=params, timeout=10)
                    response.raise_for_status(); return response.json()
                assert get('/dashboard/summary', capture_run_id='fixture')['flows'] == 205
                assert get('/flows', capture_run_id='fixture', offset=200, limit=50)['count'] == 205
                assert len(get('/flows', capture_run_id='fixture', offset=200, limit=50)['flows']) == 5
                assert requests.get(url + '/flows', params={'limit': -1}).status_code == 422
                assert requests.get(url + '/flows', params={'since': '2026-01-01'}).status_code == 422
                assert requests.get(url + '/flows/missing').status_code == 404
                data = pd.read_csv(ROOT / 'data/clean_holdout_set.csv')
                features = [c for c in data.columns if c not in ('label_true', 'flow_id')]
                real = []
                for label in ['Benign', 'DoS attacks-Hulk']:
                    row = data[data.label_true == label].iloc[0]
                    payload = {c: float(row[c]) for c in features}
                    response = requests.post(url + '/predict', json=payload, params={
                        'capture_run_id': 'real-model-test', 'run_name': 'Real model isolated test',
                        'src_ip': '192.0.2.1', 'dst_ip': '198.51.100.1', 'src_port': 50000,
                        'flow_timestamp': '2026-10-16T07:21:30', 'capture_timezone': '+07:00',
                        'extractor_version': 'metadata-test-version'}, timeout=15)
                    response.raise_for_status(); real.append(response.json())
                assert not real[0]['is_alert'] and real[1]['is_alert'], real
                for _ in range(100):
                    detail = get('/flows/' + real[1]['flow_id'])
                    if detail['shap_top5']:
                        break
                    time.sleep(.1)
                assert detail['shap_top5'] and detail['branch'] in ('A', 'B')
                assert get('/alerts', capture_run_id='real-model-test')['count'] == 1
                assert detail['src_ip'] == '192.0.2.1' and len(detail['features']) == 78
                assert detail['flow_timestamp_utc'] == '2026-10-16T00:21:30+00:00'
                assert detail['extractor_version'] == 'metadata-test-version'
                benign = get('/flows/' + real[0]['flow_id'])
                assert benign['explanation_status'] == 'not_required' and not benign['shap_top5']
                assert get('/dashboard/summary', capture_run_id='real-model-test')['flows'] == 2
                print('PASS real prediction, metadata, async SHAP, Benign and alert detail')
                # Same feature vector with/without metadata must have identical predictions.
                response = requests.post(url + '/predict', json={**payload, 'src_port': 50000}, timeout=15)
                response.raise_for_status()
                assert response.json()['probabilities'] == real[1]['probabilities']
                assert len(get('/flows/' + response.json()['flow_id'])['features']) == 78
                from streamlit.testing.v1 import AppTest
                with patch.dict(os.environ, {'IDS_API_URL': url}):
                    at = AppTest.from_file(str(ROOT / 'app/dashboard.py')).run(timeout=30)
                    assert not at.exception, at.exception
                    assert {'Giám sát flow', 'Hướng dẫn live', 'Nạp CSV / PCAP'} <= {tab.label for tab in at.tabs}
                    assert any('chưa có nút bật hoặc tắt' in item.value for item in at.info)
                    assert any('run_live_capture.py' in item.value for item in at.code)
                    at.selectbox(key='run_choice').set_value('real-model-test').run(timeout=30)
                    assert not at.exception, at.exception
                    at.session_state['selected_flow'] = real[0]['flow_id']
                    at.run(timeout=30)
                    assert not at.exception and any('Benign:' in item.value for item in at.info)
                    at.session_state['selected_flow'] = real[1]['flow_id']
                    at.run(timeout=30)
                    assert not at.exception, at.exception
                    at.button(key='lime_' + real[1]['flow_id']).click().run(timeout=60)
                    assert not at.exception, at.exception
                    explained = get('/flows/' + real[1]['flow_id'])
                    assert explained['lime_diagnostics']['samples'] == 1000
                    if explained['lime_status'] == 'ok':
                        assert explained['lime_local_r2'] is not None
                    else:
                        assert explained['lime_local_r2'] is None and explained['agreement_jaccard5'] is None
                    comparison = get('/flows/' + real[1]['flow_id'] + '/comparison')
                    assert len(comparison['features']) == 78 and comparison['background_n'] == 2000
                    assert all('Xem định nghĩa' not in r['meaning'] for r in comparison['features'])
                    assert any(r['benign']['n'] > 0 for r in comparison['features'])
                    at.selectbox(key='feature_guide_' + real[1]['flow_id']).set_value('FIN Flag Cnt').run(timeout=30)
                    assert not at.exception, at.exception
                    assert any('không phải số cuộc tấn công' in element.value for element in at.markdown)
                    at.run(timeout=30)
                    assert at.session_state['selected_flow'] == real[1]['flow_id']
                    at.selectbox(key='run_choice').set_value('__all__').run(timeout=30)
                    assert not at.exception, at.exception
                    before = get('/dashboard/summary')['flows']
                    csv_data = data[data.label_true == 'Benign'].head(1).to_csv(index=False).encode('utf-8')
                    at.file_uploader(key='csv_uploader').upload('one.csv', csv_data, 'text/csv').run(timeout=30)
                    at.button(key='send_csv').click().run(timeout=30)
                    assert not at.exception, at.exception
                    assert get('/dashboard/summary')['flows'] == before + 1
                    assert at.session_state['upload_result'] == (1, [])
                    at.run(timeout=30)
                    assert get('/dashboard/summary')['flows'] == before + 1  # no resubmission on refresh
                    capture_python = ROOT / '.venv_capture/Scripts/python.exe'
                    if capture_python.exists():
                        pcap = Path(folder) / 'synthetic.pcap'
                        subprocess.run([str(capture_python), str(ROOT / 'scripts/make_synthetic_pcap.py'), str(pcap)],
                            check=True, capture_output=True, timeout=30,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                        at.file_uploader(key='pcap_uploader').upload('synthetic.pcap', pcap.read_bytes(), 'application/octet-stream').run(timeout=30)
                        before = get('/dashboard/summary')['flows']
                        at.button(key='send_pcap').click().run(timeout=150)
                        assert not at.exception, at.exception
                        assert get('/dashboard/summary')['flows'] > before, [e.value for e in at.error]
                        print('PASS real PCAP extraction + prediction via UI')
                    else:
                        print('SKIP PCAP: .venv_capture not installed')
                    print('PASS CSV upload, run auto-selection, no duplicate send on refresh')
                print('PASS dashboard render, run filter, Benign/alert, LIME click, stable selection')
                # Feeder cursor handles blank lines without sending duplicate rows.
                from feeder import run_feeder
                csv_path = Path(folder) / 'feeder.csv'
                pd.DataFrame([{**payload, 'timestamp': '2026-10-16 07:21:30', 'src_ip': '192.0.2.1'}]).to_csv(csv_path, index=False)
                with csv_path.open('a') as stream:
                    stream.write('\n')
                with patch('feeder.requests.post', wraps=requests.post) as post:
                    run_feeder(csv_path, url, .01, False, max_iterations=2, capture_timezone='+07:00')
                    assert post.call_count == 1
                print('PASS feeder blank-line deduplication and per-run metadata')
                # Numerical regression: background-constant bulk-rate feature far from support.
                extreme = {**payload, 'Bwd Blk Rate Avg': 1264390243.902439}
                response = requests.post(url + '/predict', json=extreme,
                                         params={'capture_run_id': 'degenerate-fixture'}, timeout=15)
                response.raise_for_status()
                event = response.json()
                assert event['is_alert']
                response = requests.post(url + '/explain', json={'alert_id': event['alert_id']}, timeout=30)
                response.raise_for_status()
                invalid = response.json()
                assert invalid['status'] == 'insufficient_neighborhood'
                assert invalid['diagnostics']['nonzero_weights'] == 1
                assert invalid['local_r2'] is None and invalid['agreement_jaccard5'] is None and invalid['top_k'] == []
                with patch.dict(os.environ, {'IDS_API_URL': url}):
                    at = AppTest.from_file(str(ROOT / 'app/dashboard.py')).run(timeout=30)
                    assert not at.exception, at.exception
                    assert any('LIME chưa giải thích' in item.value for item in at.warning)
                    assert any('không còn các ví dụ lân cận hữu ích' in item.value for item in at.markdown)
                    assert any(tab.label == 'Đối chứng đặc trưng' for tab in at.tabs)
                print('PASS degenerate LIME guard, null R2/agreement, diagnostic UI and feature comparison')
            finally:
                proc.terminate()
                proc.wait(timeout=10)
    print('ALL DASHBOARD REDESIGN TESTS PASSED (temporary data only)')


if __name__ == '__main__':
    main()
