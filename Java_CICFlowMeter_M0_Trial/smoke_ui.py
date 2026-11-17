"""Exercise table row clicks, invalid flows, XAI and model switching on an isolated API."""
import os
import csv
import json
import threading
import time
from pathlib import Path

os.environ['JAVA_M0_TRIAL_TOKEN'] = 'offline-ui-test'
os.environ['JAVA_TRIAL_API_URL'] = 'http://127.0.0.1:18766'
import uvicorn
from streamlit.testing.v1 import AppTest
from streamlit.proto.WidgetStates_pb2 import WidgetStates, WidgetState
import service
from service import app, manager

service.list_interfaces = lambda: [(r'\Device\NPF_FAKE', 'WiFi 6 test')]
with (Path(__file__).parent / 'output/test.pcap_Flow.csv').open(encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        manager._accept_row(row)
manager.run_id = 'ui-regression'
bad = next(r['id'] for r in manager.records if r['prediction'] is None)
alert = next(r['id'] for r in manager.records if r['prediction'] not in (None, 'Benign'))
server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=18766, log_level='error'))
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
for _ in range(100):
    if server.started:
        break
    time.sleep(.1)

def click_flow(state, flow_id):
    table = next(d for d in state.dataframe if 'Flow ID' in d.value.columns)
    index = list(table.value['Flow ID']).index(flow_id)
    event = WidgetState(id=table.proto.id, string_value=json.dumps({'selection': {'rows': [index], 'columns': [], 'cells': []}}))
    current = state._tree.get_widget_states()
    merged = [w for w in current.widgets if w.id != event.id] + [event]
    return state._run(widget_state=WidgetStates(widgets=merged))

def check(state):
    assert not state.exception, [x.message for x in state.exception]
    assert not state.error, [x.value for x in state.error]

try:
    state = AppTest.from_file(str(Path(__file__).parent / 'dashboard.py'), default_timeout=60).run()
    check(state)
    for model in ('M0', 'M1'):
        if state.radio[0].value != model:
            state = state.radio[0].set_value(model).run()
        state = click_flow(state, bad)
        assert not state.exception
        assert any('không hợp lệ' in x.value for x in state.error)
        assert any(f'Flow ID: {bad} ' in x.value for x in state.caption)
        state = click_flow(state, alert)
        check(state)
        assert any(f'Flow ID: {alert} ' in x.value for x in state.caption)
        lime_button = next(b for b in state.button if b.label == 'Tính LIME cho flow này')
        state = lime_button.click().run()
        check(state)
        assert manager.flow(alert, model)['lime'] is not None
        if manager.flow(alert, model)['shap'] is None:
            state = next(b for b in state.button if b.label == 'Tính SHAP cho flow này').click().run()
            check(state)
        assert manager.flow(alert, model)['shap']['class_explained'] == manager.flow(alert, model)['prediction']
        manager._accept_row(row)
        state = state.run()
        check(state)
        assert any(f'Flow ID: {alert} ' in x.value for x in state.caption), 'Selection changed when new flow arrived'
        state = next(x for x in state.selectbox if x.label == 'Nhãn dự đoán').set_value('Không hợp lệ').run()
        assert not state.exception
        table = next(d for d in state.dataframe if 'Flow ID' in d.value.columns)
        assert set(table.value['Nhãn']) == {'Không hợp lệ'}
        state = next(x for x in state.selectbox if x.label == 'Nhãn dự đoán').set_value('Tất cả').run()
        check(state)
        print(model, 'PASS: table click, invalid/valid details, SHAP, LIME, stable selection')
    assert 'Đánh giá giải thích' in [t.label for t in state.tabs]
finally:
    server.should_exit = True
    thread.join(timeout=8)
