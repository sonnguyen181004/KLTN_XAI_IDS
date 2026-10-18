"""Opt-in, bounded real-NIC test through API + Streamlit controls, isolated IDS DB.

Raw CSV/logs remain in a temporary evidence directory, not in Git. Only sanitized
counts/outcomes are exported. Requires explicit --interface (no automatic capture).
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from unittest.mock import patch
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
from ingestion_checkpoint import save_checkpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interface', required=True)
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    if not 10 <= args.seconds <= 120:
        parser.error('Smoke test duration must be 10–120 seconds')
    if args.result.exists():
        parser.error('Result already exists; choose a new evidence filename')
    folder = Path(tempfile.mkdtemp(prefix='ids_live_control_'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    token = uuid.uuid4().hex
    headers = {'X-IDS-Control-Token': token}
    env = {**os.environ, 'IDS_DB_PATH': str(folder/'test.db'), 'IDS_CAPTURE_CONTROL_TOKEN': token,
           'IDS_CAPTURE_API_URL': url, 'IDS_CAPTURE_SESSION_DIR': str(folder/'sessions'),
           'PYTHONIOENCODING': 'utf-8'}
    result = dict(started_at=datetime.now(timezone.utc).isoformat(), requested_seconds=args.seconds,
                  interface=args.interface, evidence_directory=str(folder), status='failed',
                  scope='real Wi-Fi/API/model/AppTest smoke test; not FPR or long-duration certification')
    with (folder/'api.log').open('wb') as log:
        api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        def get():
            response = requests.get(url+'/capture/status', headers=headers, timeout=5)
            response.raise_for_status()
            return response.json()['session']
        try:
            for _ in range(90):
                if api.poll() is not None:
                    raise RuntimeError('Isolated API exited; inspect evidence log')
                try:
                    if requests.get(url+'/health', timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(.5)
            else:
                raise RuntimeError('API startup timeout')
            from streamlit.testing.v1 import AppTest
            source = f'import sys; sys.path.insert(0,{str(ROOT/"app")!r})\nfrom capture_ui import render_capture\nrender_capture({url!r})'
            # AppTest has no real browser IP; API still verifies local HTTP + token.
            with patch.dict(os.environ, {'IDS_CAPTURE_CONTROL_TOKEN': token}), patch('capture_ui.local_browser', return_value=True):
                ui = AppTest.from_string(source).run(timeout=20)
                ui.text_input(key='capture_interface').set_value(args.interface).run()
                next(b for b in ui.button if b.label == 'Bắt đầu capture').click().run(timeout=20)
                assert not ui.exception, ui.exception
                deadline = time.monotonic()+45
                while time.monotonic() < deadline:
                    state = get()
                    if state and state['status'] == 'running':
                        break
                    if state and state['status'] in ('failed', 'unknown'):
                        raise RuntimeError('Capture startup failed: '+str(state.get('reason')))
                    time.sleep(.25)
                else:
                    raise RuntimeError('Capture readiness timeout')
                started = time.monotonic()
                print('LIVE_RUNNING', flush=True)
                while time.monotonic()-started < args.seconds:
                    time.sleep(max(0, min(5, args.seconds-(time.monotonic()-started))))
                    state = get()
                    print(json.dumps(dict(elapsed=round(time.monotonic()-started, 1), status=state['status'],
                                          acknowledged=state.get('acknowledged_rows'))), flush=True)
                    if state['status'] != 'running':
                        raise RuntimeError('Capture stopped before requested test duration')
                result['running_seconds'] = round(time.monotonic()-started, 3)
                ui.run(timeout=20)
                next(b for b in ui.button if b.label == 'Dừng capture').click().run(timeout=20)
                assert not ui.exception, ui.exception
                stopped = time.monotonic()
                while time.monotonic()-stopped < 150:
                    state = get()
                    if not state['active'] or state['status'] == 'unknown':
                        break
                    time.sleep(.5)
                result['stop_drain_seconds'] = round(time.monotonic()-stopped, 3)
                result['session'] = state
                assert state['status'] == 'completed' and not state['active'], state
                run_dir = folder/'sessions'/state['run_id']
                with (run_dir/'flows.csv').open(encoding='utf-8-sig', newline='') as stream:
                    rows = sum(1 for row in csv.DictReader(stream) if any(row.values()))
                conn = sqlite3.connect(folder/'test.db')
                try:
                    api_count = conn.execute('SELECT COUNT(*) FROM FlowRecord WHERE capture_run_id=?',
                                             (state['prediction_run_id'],)).fetchone()[0]
                finally:
                    conn.close()
                result.update(csv_rows=rows, api_flows=api_count,
                              queue=requests.get(url+'/explain_queue_status', timeout=5).json())
                counts = dict((key, int(value)) for key, value in re.findall(r'(accepted_packets|exported_packets|limit_rejected|peak_buffered_packets)=(\d+)',
                    (run_dir/'capture.log').read_text(encoding='utf-8')))
                result['packet_counters'] = counts
                assert rows > 0 and rows == api_count == state['feeder_result']['acknowledged'] == state['capture_result']['rows']
                assert counts['accepted_packets'] == counts['exported_packets'] and counts['limit_rejected'] == 0
                ui.run(timeout=20)
                assert not ui.exception
                result['apptest_start_stop_refresh'] = 'passed'
                result['status'] = 'passed'
        except BaseException as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
            try:
                result['controller_at_failure'] = requests.get(url+'/capture/status', headers=headers, timeout=5).json()
            except requests.RequestException:
                pass
        finally:
            try:
                state = get()
                if state and state['active'] and state['status'] != 'unknown':
                    requests.post(url+'/capture/stop', headers=headers, json={'run_id': state['run_id']}, timeout=5)
                    for _ in range(140):
                        state = get()
                        if not state['active'] or state['status'] == 'unknown':
                            break
                        time.sleep(.5)
                if not state or not state['active']:
                    api.terminate()  # Only this test-owned API; owned workers already reaped.
                    api.wait(timeout=15)
                    result['isolated_api_stopped'] = True
                else:
                    result.update(isolated_api_stopped=False, attention_api_pid=api.pid)
            except Exception as exc:
                result['cleanup_error'] = str(exc)
            result['finished_at'] = datetime.now(timezone.utc).isoformat()
            save_checkpoint(args.result, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
