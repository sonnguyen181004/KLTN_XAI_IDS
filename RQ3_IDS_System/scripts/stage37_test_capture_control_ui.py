"""Local control auth + UI button/refresh tests; no NIC or production DB."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from fastapi import FastAPI
import asyncio
import json
from urllib.parse import urlsplit
import requests
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]/'app'
sys.path.insert(0, str(APP))
from capture_routes import control_router
from capture_ui import local_browser

TOKEN = 'test-control-token-not-production-12345'


class TestClient:
    """Minimal ASGI harness: no optional HTTP client dependency."""
    def __init__(self, app, base_url='http://127.0.0.1', client=('127.0.0.1', 1234)):
        self.app, self.base, self.client = app, base_url, client
    def request(self, method, url, headers=None, json_body=None):
        parsed = urlsplit(url if url.startswith('http') else self.base+url)
        data = json.dumps(json_body).encode() if json_body is not None else b''
        merged = {'host': parsed.netloc, 'content-type': 'application/json',
                  **{k.lower(): v for k, v in (headers or {}).items()}}
        scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1', method=method,
                     scheme='http', path=parsed.path, raw_path=parsed.path.encode(), query_string=b'',
                     root_path='', headers=[(k.encode(), v.encode()) for k, v in merged.items()],
                     client=self.client, server=('127.0.0.1', 80))
        messages = []
        async def receive():
            return dict(type='http.request', body=data, more_body=False)
        async def send(message):
            messages.append(message)
        asyncio.run(self.app(scope, receive, send))
        response = requests.Response()
        response.status_code = next(m['status'] for m in messages if m['type'] == 'http.response.start')
        response._content = b''.join(m.get('body', b'') for m in messages if m['type'] == 'http.response.body')
        response.url = url
        return response
    def get(self, url, headers=None):
        return self.request('GET', url, headers)
    def post(self, url, headers=None, json=None):
        return self.request('POST', url, headers, json)
    def close(self):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class FakeSupervisor:
    def __init__(self):
        self.starts = 0
        self.stops = 0
        self.session = None
    def status(self):
        return dict(session=self.session, supervisor_error=None)
    def start(self, request_id, interface):
        self.starts += 1
        self.session = dict(run_id='a'*32, status='running', active=True, workers={}, acknowledged_rows=2)
        return self.status()
    def stop(self, run_id):
        self.stops += 1
        self.session.update(status='completed', active=False)
        return self.status()
    def reconcile(self, run_id):
        return self.status()


class ControlTests(unittest.TestCase):
    def test_local_listener_and_streamlit_none_ip(self):
        for address in ('127.0.0.1', '::1'):
            for browser in (None, '127.0.0.1', '::1', '192.168.1.2', '', 'invalid'):
                with self.subTest(address=address, browser=browser), patch('capture_ui.st.get_option', return_value=address), patch('capture_ui.st.context', SimpleNamespace(ip_address=browser)):
                    self.assertEqual(local_browser(), browser in (None, '127.0.0.1', '::1'))
        for address in (None, '', '0.0.0.0', '::', '192.168.1.2', 'localhost'):
            with self.subTest(address=address), patch('capture_ui.st.get_option', return_value=address), patch('capture_ui.st.context', SimpleNamespace(ip_address=None)):
                self.assertFalse(local_browser())

    def setUp(self):
        self.supervisor = FakeSupervisor()
        app = FastAPI()
        app.include_router(control_router(lambda: self.supervisor, TOKEN))
        self.client = TestClient(app, base_url='http://127.0.0.1', client=('127.0.0.1', 1234))
        self.headers = {'X-IDS-Control-Token': TOKEN}
    def tearDown(self):
        self.client.close()

    def test_auth_origin_host_and_schema(self):
        self.assertEqual(self.client.get('/capture/status').status_code, 403)
        for headers in ({'Origin': 'http://evil.example'}, {'Host': 'evil.example'},
                        {'X-IDS-Control-Token': 'wrong'}, {'Sec-Fetch-Site': 'cross-site'}):
            self.assertEqual(self.client.get('/capture/status', headers={**self.headers, **headers}).status_code, 403)
        self.assertEqual(self.client.get('/capture/status', headers=self.headers).status_code, 200)
        self.assertEqual(self.client.post('/capture/start', headers=self.headers,
            json=dict(request_id='x', interface='Wi-Fi', command='arbitrary')).status_code, 422)
        self.assertEqual(self.supervisor.starts, 0)

    def test_nonlocal_client_and_disabled(self):
        app = FastAPI()
        app.include_router(control_router(lambda: self.supervisor, TOKEN))
        with TestClient(app, base_url='http://127.0.0.1', client=('10.0.0.2', 2)) as client:
            self.assertEqual(client.get('/capture/status', headers=self.headers).status_code, 403)
        app = FastAPI()
        app.include_router(control_router(lambda: self.supervisor, ''))
        with TestClient(app) as client:
            self.assertEqual(client.get('/capture/status').status_code, 503)

    def test_ui_refresh_never_starts_and_buttons_send_commands(self):
        def get(url, **kwargs):
            return self.client.get(url, headers=kwargs.get('headers'))
        def post(url, **kwargs):
            return self.client.post(url, json=kwargs.get('json'), headers=kwargs.get('headers'))
        code = f'import sys; sys.path.insert(0,{str(APP)!r})\nfrom capture_ui import render_capture\nrender_capture("http://127.0.0.1")'
        code = f'''import sys
sys.path.insert(0, {str(APP)!r})
from unittest.mock import patch
from types import SimpleNamespace
import streamlit as st
from capture_ui import render_capture
original_option = st.get_option
def option(name):
    return '127.0.0.1' if name == 'server.address' else original_option(name)
with patch('capture_ui.st.get_option', side_effect=option), patch('capture_ui.st.context', SimpleNamespace(ip_address=None)):
    render_capture('http://127.0.0.1')
'''
        with patch.dict(os.environ, {'IDS_CAPTURE_CONTROL_TOKEN': TOKEN}), patch('requests.get', side_effect=get), patch('requests.post', side_effect=post):
            ui = AppTest.from_string(code).run(timeout=10)
            ui.run()
            self.assertFalse(ui.exception)
            self.assertEqual(self.supervisor.starts, 0)
            self.assertFalse(ui.error, [e.value for e in ui.error])
            next(b for b in ui.button if b.label == 'Bắt đầu capture').click().run()
            self.assertFalse(ui.exception)
            self.assertEqual(self.supervisor.starts, 1)
            ui.run()
            self.assertEqual(self.supervisor.starts, 1)
            next(b for b in ui.button if b.label == 'Dừng capture').click().run()
            self.assertFalse(ui.exception)
            self.assertEqual(self.supervisor.stops, 1)

    def test_remote_browser_ui_never_calls_controller(self):
        code = f'import sys; sys.path.insert(0,{str(APP)!r})\nfrom capture_ui import render_capture\nrender_capture("http://127.0.0.1")'
        with patch.dict(os.environ, {'IDS_CAPTURE_CONTROL_TOKEN': TOKEN}), patch('capture_ui.local_browser', return_value=False), patch('requests.get') as get:
            ui = AppTest.from_string(code).run()
            self.assertFalse(ui.exception)
            self.assertTrue(ui.error)
            get.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
