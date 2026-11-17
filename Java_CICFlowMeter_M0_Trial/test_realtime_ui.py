"""Opt-in real Wi-Fi capture through dashboard controls; writes a local evidence file.

Run only with authorization to capture. Makes up to six ordinary HTTPS GETs.
Uses a separate API; never resets databases or modifies model artifacts.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time

os.environ['JAVA_M0_TRIAL_TOKEN'] = 'live-ui-regression'
os.environ['JAVA_TRIAL_API_URL'] = 'http://127.0.0.1:18767'
import requests
import uvicorn
from streamlit.testing.v1 import AppTest
from streamlit.proto.WidgetStates_pb2 import WidgetStates, WidgetState
from service import app, manager

HERE = Path(__file__).resolve().parent
evidence = {'passed': False, 'scope': 'Real Java Wi-Fi capture + HTTP API + Streamlit AppTest; no browser visual QA',
            'traffic': [], 'models': {}}


def check(state):
    assert not state.exception, [x.message for x in state.exception]
    assert not state.error, [x.value for x in state.error]


def button(state, label):
    return next(b for b in state.button if b.label == label).click().run()


def click_flow(state, flow_id):
    table = next(d for d in state.dataframe if 'Flow ID' in d.value.columns)
    index = list(table.value['Flow ID']).index(flow_id)
    event = WidgetState(id=table.proto.id, string_value=json.dumps(
        {'selection': {'rows': [index], 'columns': [], 'cells': []}}))
    current = state._tree.get_widget_states()
    return state._run(widget_state=WidgetStates(
        widgets=[w for w in current.widgets if w.id != event.id] + [event]))


def ordinary_traffic():
    for _ in range(6):
        try:
            with requests.get('https://example.com/', timeout=8,
                              headers={'Connection': 'close'}) as response:
                evidence['traffic'].append({'http_status': response.status_code, 'bytes': len(response.content)})
        except requests.RequestException as exc:
            evidence['traffic'].append({'error': type(exc).__name__})
        time.sleep(2)


server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=18767, log_level='error'))
server_thread = threading.Thread(target=server.run, daemon=True)
server_thread.start()
try:
    deadline = time.monotonic() + 15
    while not server.started and time.monotonic() < deadline:
        time.sleep(.1)
    assert server.started
    state = AppTest.from_file(str(HERE / 'dashboard.py'), default_timeout=90).run()
    check(state)
    # Actual Java/Npcap enumeration through the UI; no fake device or capture.
    state = button(state, 'Bắt đầu Java')
    check(state)
    deadline = time.monotonic() + 90
    while manager.phase == 'starting' and time.monotonic() < deadline:
        time.sleep(.25)
    assert manager.phase == 'capturing', manager.status()
    start = time.monotonic()
    evidence['interface'] = manager.interface
    evidence['run_id'] = manager.run_id
    print('CAPTURING', manager.run_id, flush=True)
    traffic = threading.Thread(target=ordinary_traffic, daemon=True)
    traffic.start()
    while time.monotonic() - start < 30:
        time.sleep(.5)
    evidence['rows_before_stop'] = len(manager.records)
    state = state.run()
    check(state)
    state = button(state, 'Dừng và ghi nốt flow')
    check(state)
    evidence['seconds_until_stop_requested'] = round(time.monotonic() - start, 2)
    manager.thread.join(timeout=120)
    traffic.join(timeout=55)
    assert not manager.thread.is_alive(), 'Capture/drain did not finish'
    assert manager.process.poll() == 0
    status = manager.status()
    assert status['phase'] == 'finished', status
    evidence['packet_summary'] = status['packet_summary']
    counts = dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)', status['packet_summary']))
    assert counts['accepted_packets'] > 0, 'No real TCP/UDP packets captured'
    with manager.csv_path.open(encoding='utf-8-sig', newline='') as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == status['rows'] == counts['closed_flows'] + counts['flushed_flows']
    evidence['csv_rows'] = len(rows)
    evidence['process_exit'] = manager.process.returncode
    evidence['seconds_through_drain'] = round(time.monotonic() - start, 2)
    headers = {'X-Trial-Token': os.environ['JAVA_M0_TRIAL_TOKEN']}
    for model in ('M0', 'M1'):
        flows = manager.flows(model)
        assert any(r['prediction'] for r in flows)
        for r in flows:
            response = requests.get(f'http://127.0.0.1:18767/flows/{r["id"]}',
                                    params={'model': model}, headers=headers, timeout=15)
            assert response.status_code == 200, (model, r['id'], response.text)
            json.loads(response.text, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        state = state.run()
        state = state.radio[0].set_value(model).run()
        check(state)
        table = next(d for d in state.dataframe if 'Flow ID' in d.value.columns)
        visible = set(table.value['Flow ID'])
        selected = next(r for r in reversed(flows) if r['prediction'] and r['id'] in visible)
        state = click_flow(state, selected['id'])
        check(state)
        assert any(f'Flow ID: {selected["id"]} ' in x.value for x in state.caption)
        if manager.flow(selected['id'], model)['shap'] is None:
            state = button(state, 'Tính SHAP cho flow này')
            check(state)
        state = button(state, 'Tính LIME cho flow này')
        check(state)
        detail = manager.flow(selected['id'], model)
        assert detail['shap']['class_explained'] == detail['prediction']
        assert detail['lime'] is not None
        evidence['models'][model] = {'labels': manager.status(model)['labels'],
            'invalid_rows': sum(r['prediction'] is None for r in flows),
            'detail_http_200': len(flows), 'selected_flow': selected['id'],
            'selected_label': detail['prediction'], 'shap_error': detail['shap'].get('additivity_error'),
            'lime_status': detail['lime'].get('status'), 'lime_diagnostics': detail['lime'].get('diagnostics'),
            'ui_row_click_and_xai': 'PASS'}
        print(model, evidence['models'][model], flush=True)
    for name, path in [('M0', HERE.parent / 'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl'),
                       ('M1', HERE.parent / 'IDS_M1_Lab/models/m1_xgboost_model.pkl')]:
        evidence['models'][name]['model_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    evidence['passed'] = True
finally:
    if manager.process is not None and manager.process.poll() is None:
        manager.stop()
    if manager.thread:
        manager.thread.join(timeout=30)
    server.should_exit = True
    server_thread.join(timeout=8)
    evidence['cleanup_process_stopped'] = manager.process is None or manager.process.poll() is not None
    (HERE / 'output/realtime_ui_latest.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print('RESULT', json.dumps(evidence, ensure_ascii=True), flush=True)
