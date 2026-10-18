"""Worker protocol tests with real child processes, temporary files and HTTP ACK fixture.
No Wi-Fi, model predictions or production DB writes.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RQ3/'app'))
from worker_control import WorkerControl, read_control, write_control as save_checkpoint


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers['Content-Length']))
        self.send_response(200)
        self.send_header('Idempotency-Key', self.headers['Idempotency-Key'])
        self.end_headers()
        self.wfile.write(json.dumps(dict(flow_id=uuid.uuid4().hex, predicted_label='Benign',
                                        is_alert=False, explanation_status=None)).encode())

    def log_message(self, *args):
        pass


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ids_worker_test_')
        self.root = Path(self.temp.name)
        self.token = uuid.uuid4().hex

    def tearDown(self):
        self.temp.cleanup()

    def folder(self, name):
        folder = self.root/name
        folder.mkdir()
        save_checkpoint(folder/'lease.json', dict(worker_token=self.token, monotonic=time.monotonic()))
        return folder

    @contextmanager
    def lease(self, folder):
        stop = threading.Event()
        errors = []
        def update():
            try:
                while not stop.wait(.5):
                    save_checkpoint(folder/'lease.json', dict(worker_token=self.token, monotonic=time.monotonic()))
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=update)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=3)
            self.assertFalse(errors, errors)

    def test_control_write_retries_bounded_permission_error(self):
        with patch('worker_control.save_checkpoint', side_effect=[PermissionError(), None]) as write:
            save_checkpoint(self.root/'unused', {})
            self.assertEqual(write.call_count, 2)
        with patch('worker_control.save_checkpoint', side_effect=PermissionError()) as write:
            with self.assertRaises(PermissionError):
                save_checkpoint(self.root/'unused', {})
            self.assertEqual(write.call_count, 6)
        with patch('worker_control.Path.read_text', side_effect=[PermissionError(), '{}']) as read:
            self.assertEqual(read_control(self.root/'unused'), {})
            self.assertEqual(read.call_count, 2)
        with patch('worker_control.Path.read_text', side_effect=PermissionError()) as read:
            with self.assertRaises(PermissionError):
                read_control(self.root/'unused')
            self.assertEqual(read.call_count, 6)

    def test_lease_renewed_during_read_is_not_future(self):
        worker = WorkerControl(self.folder('renew'), self.token, 'capture')
        with patch('worker_control.time.monotonic', return_value=10) as clock:
            def renewed(name):
                clock.return_value = 12
                return {'worker_token': self.token, 'monotonic': 11}
            with patch.object(worker, '_read', side_effect=renewed):
                worker.tick('capturing')

    def command(self, folder, action, **fields):
        save_checkpoint(folder/'command.json', dict(worker_token=self.token, action=action, **fields))

    def feeder(self, folder, csv, env=None):
        return subprocess.run([sys.executable, str(RQ3/'app/feeder.py'), '--watch', str(csv),
                               '--control-dir', str(folder), '--worker-token', self.token],
                              env={**os.environ, **(env or {}), 'PYTHONIOENCODING': 'utf-8'},
                              capture_output=True, timeout=30,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    def test_control_identity_sequence_and_wrong_token(self):
        folder = self.folder('identity')
        worker = WorkerControl(folder, self.token, 'capture')
        self.assertEqual(worker.identity['pid'], os.getpid())
        self.assertTrue(worker.identity['birth_token'])
        worker.tick('capturing', force=True)
        report = json.loads((folder/'status.json').read_text())
        self.assertEqual(report['sequence'], 2)
        save_checkpoint(folder/'command.json', dict(worker_token='wrong', action='stop'))
        with self.assertRaises(RuntimeError):
            worker.tick('capturing')

    def test_stale_or_future_lease_is_not_healthy(self):
        folder = self.folder('expired')
        for offset in (-100, 100):
            save_checkpoint(folder/'lease.json', dict(worker_token=self.token, monotonic=time.monotonic()+offset))
            with self.assertRaises(RuntimeError):
                WorkerControl(folder, self.token, 'capture')

    def test_real_capture_pcap_then_real_feeder_drains_ack_fixture(self):
        folder = self.folder('capture')
        csv = self.root/'flows.csv'
        with self.lease(folder):
            proc = subprocess.run([str(RQ3/'.venv_capture/Scripts/python.exe'),
                str(RQ3/'scripts/run_live_capture.py'), '--pcap-input', str(RQ3.parent/'test.pcapng'),
                '--output', str(csv), '--control-dir', str(folder), '--worker-token', self.token],
                capture_output=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        capture = json.loads((folder/'status.json').read_text())
        self.assertEqual(capture['state'], 'finished')
        self.assertTrue(capture['flushed'])
        self.assertGreater(capture['rows'], 0)
        self.assertEqual(capture['rows'], capture['exported_flows'])
        self.assertEqual(capture['buffered_packets'], 0)
        self.assertEqual(capture['csv_size'], csv.stat().st_size)
        self.assertNotEqual(capture['pid'], os.getpid())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            folder = self.folder('feeder')
            self.command(folder, 'drain', csv_size=capture['csv_size'], rows=capture['rows'])
            with self.lease(folder):
                proc = self.feeder(folder, csv, {'IDS_API_URL': f'http://127.0.0.1:{server.server_port}'})
            self.assertEqual(proc.returncode, 0, (proc.stdout, proc.stderr))
            feeder = json.loads((folder/'status.json').read_text())
            self.assertEqual(feeder['state'], 'finished')
            self.assertEqual(feeder['acknowledged'], capture['rows'])
            self.assertEqual(feeder['offset'], capture['csv_size'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_abort_while_waiting_for_csv_fails(self):
        folder = self.folder('abort')
        self.command(folder, 'abort')
        proc = self.feeder(folder, self.root/'missing.csv')
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(json.loads((folder/'status.json').read_text())['state'], 'failed')

    def test_empty_csv_can_drain_zero_and_mismatch_fails(self):
        csv = self.root/'empty.csv'
        csv.touch()
        for expected in (0, 1):
            folder = self.folder('zero'+str(expected))
            self.command(folder, 'drain', csv_size=0, rows=expected)
            proc = self.feeder(folder, csv)
            report = json.loads((folder/'status.json').read_text())
            self.assertEqual(proc.returncode == 0, expected == 0, proc.stderr)
            self.assertEqual(report['state'], 'finished' if expected == 0 else 'failed')

    def test_partial_csv_not_success(self):
        csv = self.root/'partial.csv'
        csv.write_bytes(b'Dst Port\n443')
        folder = self.folder('partial')
        self.command(folder, 'drain', csv_size=csv.stat().st_size, rows=1)
        proc = self.feeder(folder, csv)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(json.loads((folder/'status.json').read_text())['state'], 'failed')

    def test_stop_command_flushes_running_capture_without_ctrl_c(self):
        folder = self.folder('stop')
        csv = self.root/'synthetic.csv'
        with self.lease(folder):
            proc = subprocess.Popen([str(RQ3/'.venv_capture/Scripts/python.exe'),
                str(RQ3/'scripts/stage34_capture_fixture.py'), '--interface', 'fixture-no-nic',
                '--output', str(csv), '--control-dir', str(folder), '--worker-token', self.token],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                deadline = time.monotonic()+10
                while time.monotonic() < deadline:
                    if (folder/'status.json').exists():
                        status = json.loads((folder/'status.json').read_text())
                        if status['state'] == 'capturing':
                            break
                    if proc.poll() is not None:
                        self.fail('Capture fixture exited before ready')
                    time.sleep(.1)
                else:
                    self.fail('Capture fixture readiness timeout')
                started = time.monotonic()
                self.command(folder, 'stop')
                stdout, stderr = proc.communicate(timeout=15)
                self.assertEqual(proc.returncode, 0, stderr)
                self.assertLess(time.monotonic()-started, 5)
                status = json.loads((folder/'status.json').read_text())
                self.assertEqual(status['state'], 'finished')
                self.assertTrue(status['flushed'])
                self.assertGreater(status['rows'], 0)
                self.assertIn(b'receiving_stopped', stdout)
            finally:
                # Fixture self-exits after 8s; never terminate arbitrary PIDs.
                if proc.poll() is None:
                    proc.communicate(timeout=15)


if __name__ == '__main__':
    unittest.main(verbosity=2)
