"""Regression: zero-duration Java flow remains readable for both models over HTTP."""
import csv
import io
import json
import os
from pathlib import Path

os.environ['JAVA_M0_TRIAL_TOKEN'] = 'invalid-flow-regression'
import requests
import threading
import time
import uvicorn
from service import app, manager, TOKEN

source = Path(__file__).parent / 'output/dashboard_86b5e6f743c5.csv'
raw = source.read_bytes()
rows = list(csv.DictReader(io.StringIO(raw[:raw.rfind(b'\n')+1].decode('utf-8-sig'))))
bad = rows[107]
assert bad['Flow Duration'] == '0' and bad['Flow Bytes/s'] == 'Infinity'
manager.records = []
manager._accept_row(bad)
manager._accept_row(rows[0])
for invalid_value in ('NaN', '-Infinity', ''):
    variant = rows[0].copy()
    variant['Flow Bytes/s'] = invalid_value
    manager._accept_row(variant)
server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18765, log_level="error"))
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
for _ in range(100):
    if server.started:
        break
    time.sleep(.1)
class Client:
    def get(self, path, **kw):
        return requests.get("http://127.0.0.1:18765"+path, timeout=15, **kw)
    def post(self, path, **kw):
        return requests.post("http://127.0.0.1:18765"+path, timeout=15, **kw)
client = Client()
try:
    headers = {'X-Trial-Token': TOKEN}
    for model in ('M0', 'M1'):
        result = client.get('/flows/1', params={'model': model}, headers=headers)
        assert result.status_code == 200, result.text
        data = result.json()
        assert data['prediction'] is None and data['features']['Flow Byts/s'] is None
        assert data['invalid_features']['Flow Byts/s'] == 'Infinity'
        assert len(data['features']) == 78
        json.dumps(data, allow_nan=False)
        for method in ('shap', 'lime'):
            assert client.post(f'/flows/1/{method}', params={'model': model}, headers=headers).status_code == 422
        assert client.get('/flows', params={'model': model}, headers=headers).status_code == 200
        assert client.get('/flows/2', params={'model': model}, headers=headers).json()['prediction'] is not None
        assert client.get('/flows/999999', params={'model': model}, headers=headers).status_code == 404
        for flow_id in (3, 4, 5):
            response = client.get(f'/flows/{flow_id}', params={'model': model}, headers=headers)
            assert response.status_code == 200 and response.json()['prediction'] is None
            json.dumps(response.json(), allow_nan=False)
        print(model, 'invalid flow HTTP 200, rejected XAI HTTP 422, valid flow readable')
    assert client.get('/flows/1').status_code == 403
    print('PASS: original flow 108 reproduced; both model responses are strict JSON')
finally:
    server.should_exit = True
    thread.join(timeout=5)
