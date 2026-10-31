"""Supervisor tests: real subprocess workers, synthetic NIC, temporary ACK server."""
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
from capture_supervisor import CaptureSupervisor
from capture_registry import CaptureConflict
from process_identity import probe_identity
from stage34_test_worker_control import Handler


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ids_supervisor_')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.http_thread = threading.Thread(target=self.server.serve_forever)
        self.http_thread.start()
        self.supervisor = CaptureSupervisor(self.temp.name, f'http://127.0.0.1:{self.server.server_port}',
            capture_script=ROOT/'scripts/stage34_capture_fixture.py')

    def tearDown(self):
        self.assertTrue(self.supervisor.close())
        self.server.shutdown()
        self.server.server_close()
        self.http_thread.join()
        self.temp.cleanup()

    def wait(self, states, timeout=25):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            status = self.supervisor.status()
            if status['session'] and status['session']['status'] in states:
                return status['session']
            time.sleep(.1)
        self.fail(str(self.supervisor.status()))

    def test_start_retry_conflict_stop_drain_complete(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            starts = list(pool.map(lambda _: self.supervisor.start('one', 'fixture'), range(4)))
        self.assertEqual(len({s['session']['run_id'] for s in starts}), 1)
        with self.assertRaises(CaptureConflict):
            self.supervisor.start('two', 'fixture')
        state = self.wait({'running', 'failed', 'unknown'})
        self.assertEqual(state['status'], 'running', self.supervisor.status())
        self.assertNotIn('worker_token', state['workers']['capture'])
        self.supervisor.stop(state['run_id'])
        self.supervisor.stop(state['run_id'])
        result = self.wait({'completed', 'failed', 'unknown'})
        self.assertEqual(result['status'], 'completed', self.supervisor.status())
        self.assertGreater(result['capture_result']['rows'], 0)
        self.assertEqual(result['capture_result']['rows'], result['feeder_result']['acknowledged'])
        self.assertFalse(self.supervisor.start('one', 'fixture')['session']['active'])

    def test_worker_script_failure_does_not_leave_feeder_running(self):
        self.supervisor.capture_script = Path(self.temp.name)/'missing-script.py'
        self.supervisor.start('bad', 'fixture')
        self.wait({'failed', 'unknown'})
        self.supervisor.thread.join(timeout=25)
        self.assertFalse(self.supervisor.thread.is_alive())
        result = self.supervisor.status()['session']
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['active'])
        self.assertTrue(all(w['exit_code'] is not None for w in result['workers'].values()))

    def test_missing_interpreter_has_no_reservation(self):
        self.supervisor.capture_python = Path(self.temp.name)/'missing-python.exe'
        with self.assertRaises(ValueError):
            self.supervisor.start('bad', 'fixture')
        self.assertIsNone(self.supervisor.registry.active())

    def test_popen_failure_clears_only_unspawned_intent(self):
        with patch('capture_supervisor.subprocess.Popen', side_effect=OSError('fixture spawn failure')):
            self.supervisor.start('spawn-failure', 'fixture')
            self.supervisor.thread.join(timeout=10)
        self.assertFalse(self.supervisor.thread.is_alive())
        self.assertIsNone(self.supervisor.registry.active())
        self.assertEqual(self.supervisor.status()['session']['status'], 'failed')

    def test_second_spawn_failure_rolls_back_first_worker(self):
        real_spawn = subprocess.Popen
        count = 0
        def spawn(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('fixture second spawn failed')
            return real_spawn(*args, **kwargs)
        with patch('capture_supervisor.subprocess.Popen', side_effect=spawn):
            self.supervisor.start('partial', 'fixture')
            self.supervisor.thread.join(timeout=20)
        self.assertFalse(self.supervisor.thread.is_alive())
        state = self.supervisor.status()['session']
        self.assertEqual(state['status'], 'failed')
        self.assertFalse(state['active'])
        self.assertIsNotNone(state['workers']['capture']['exit_code'])

    def test_close_cooperatively_stops_owned_session(self):
        self.supervisor.start('shutdown', 'fixture')
        state = self.wait({'running', 'failed', 'unknown'})
        self.assertEqual(state['status'], 'running')
        self.assertTrue(self.supervisor.close())
        self.assertFalse(self.supervisor.thread.is_alive())

    def test_os_exit_poll_race_does_not_falsely_fail_stop(self):
        self.supervisor.start('exit-race', 'fixture')
        state = self.wait({'running', 'failed', 'unknown'})
        self.assertEqual(state['status'], 'running')
        injected = []
        def probe(identity):
            actual = probe_identity(identity)
            if self.supervisor.stop_event.is_set() and not injected and actual['status'] == 'alive':
                injected.append(True)
                return dict(status='absent')
            return actual
        with patch('capture_supervisor.probe_identity', side_effect=probe):
            self.supervisor.stop(state['run_id'])
            result = self.wait({'completed', 'failed', 'unknown'})
        self.assertTrue(injected)
        self.assertEqual(result['status'], 'completed', self.supervisor.status())


if __name__ == '__main__':
    unittest.main(verbosity=2)
