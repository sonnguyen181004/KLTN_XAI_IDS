"""HT4.1 registry fixtures; no NIC, no process launch, no production DB."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import subprocess
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1]/'app'
sys.path.insert(0, str(APP))
from capture_registry import CaptureRegistry, CaptureConflict


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ids_registry_test_')
        self.registry = CaptureRegistry(self.temp.name)

    def tearDown(self):
        self.registry.close()
        self.temp.cleanup()

    def ready(self):
        run = self.registry.reserve('request', 'fixture-interface')['run_id']
        identities = {}
        for role, pid in [('capture', 100), ('feeder', 101)]:
            identities[role] = dict(pid=pid, birth_token='birth-'+role, worker_token='token-'+role)
            self.registry.attach(run, role, **identities[role])
            self.registry.heartbeat(run, role, identities[role], ready=True)
        self.assertEqual(self.registry.read(run)['status'], 'running')
        return run, identities

    def drain(self, run, identities, rows=10, acknowledged=10):
        self.registry.request_stop(run)
        self.registry.observe_exit(run, 'capture', identities['capture'], 0, flushed=True, rows=rows)
        self.assertEqual(self.registry.read(run)['status'], 'draining')
        self.registry.observe_exit(run, 'feeder', identities['feeder'], 0, acknowledged=acknowledged)
        return self.registry.finalize(run)

    def test_stop_drain_complete_and_idempotency(self):
        run, identities = self.ready()
        self.registry.request_stop(run)
        self.registry.request_stop(run)
        self.assertEqual(self.drain(run, identities)['status'], 'completed')
        retry = self.registry.reserve('request', 'fixture-interface')
        self.assertEqual(retry['run_id'], run)
        self.assertFalse(retry['start_granted'])
        self.assertEqual(self.registry.finalize(run)['status'], 'completed')
        self.assertTrue(self.registry.reserve('next', 'fixture-interface')['start_granted'])

    def test_simultaneous_different_starts_only_one_reserved(self):
        def start(i):
            try:
                return self.registry.reserve(str(i), 'fixture-interface')['start_granted']
            except CaptureConflict:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(start, range(8))), 1)

    def test_simultaneous_same_request_only_one_start_grant(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.registry.reserve('same', 'fixture-interface'), range(8)))
        self.assertEqual(sum(r['start_granted'] for r in results), 1)
        self.assertEqual(len({r['run_id'] for r in results}), 1)
        with self.assertRaises(CaptureConflict):
            self.registry.reserve('same', 'different-interface')

    def test_registry_lock_across_real_processes(self):
        code = "import sys; sys.path.insert(0,sys.argv[1]); from capture_registry import CaptureRegistry,CaptureConflict\ntry: CaptureRegistry(sys.argv[2])\nexcept CaptureConflict: sys.exit(23)\nsys.exit(0)"
        result = subprocess.run([sys.executable, '-c', code, str(APP), self.temp.name], timeout=10, capture_output=True)
        self.assertEqual(result.returncode, 23, result.stderr)

    def test_restart_blocks_until_reconciled_not_auto_running(self):
        run, identities = self.ready()
        self.registry.close()
        self.registry = CaptureRegistry(self.temp.name)
        self.assertEqual(self.registry.read(run)['status'], 'unknown')
        self.assertFalse(self.registry.reserve('request', 'fixture-interface')['start_granted'])
        with self.assertRaises(CaptureConflict):
            self.registry.reserve('next', 'fixture-interface')
        with self.assertRaises(CaptureConflict):
            self.registry.heartbeat(run, 'capture', identities['capture'], ready=True)
        with self.assertRaises(CaptureConflict):
            self.registry.finalize(run)

    def test_pid_reuse_or_wrong_token_rejected(self):
        run, identities = self.ready()
        for field in ('birth_token', 'worker_token', 'pid'):
            wrong = {**identities['capture'], field: 'different'}
            with self.assertRaises(CaptureConflict):
                self.registry.observe_exit(run, 'capture', wrong, 0, flushed=True, rows=0)
        self.assertEqual(self.registry.read(run)['status'], 'running')

    def test_heartbeat_not_completion_and_stale_state_blocks(self):
        run, identities = self.ready()
        self.registry.request_stop(run)
        with self.assertRaises(CaptureConflict):
            self.registry.finalize(run)
        self.registry.mark_unknown(run, 'heartbeat_unverified')
        with self.assertRaises(CaptureConflict):
            self.registry.reserve('new', 'fixture-interface')

    def test_capture_crash_never_completes_or_releases_live_feeder(self):
        run, identities = self.ready()
        self.registry.observe_exit(run, 'capture', identities['capture'], 1)
        with self.assertRaises(CaptureConflict):
            self.registry.finalize(run)
        with self.assertRaises(CaptureConflict):
            self.registry.reserve('new', 'fixture-interface')
        self.registry.observe_exit(run, 'feeder', identities['feeder'], 1)
        self.assertEqual(self.registry.finalize(run)['status'], 'failed')

    def test_ack_mismatch_not_completed(self):
        run, identities = self.ready()
        self.assertEqual(self.drain(run, identities, rows=10, acknowledged=9)['status'], 'failed')

    def test_unexpected_clean_capture_exit_not_completed(self):
        run, identities = self.ready()
        self.registry.observe_exit(run, 'capture', identities['capture'], 0, flushed=True, rows=0)
        self.assertEqual(self.registry.read(run)['status'], 'failed')

    def test_write_failure_preserves_previous_durable_state(self):
        run, identities = self.ready()
        with patch.object(self.registry, '_save', side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):
                self.registry.request_stop(run)
        self.assertEqual(self.registry.read(run)['status'], 'running')

    def test_completed_history_survives_restart_without_blocking_new_run(self):
        run, identities = self.ready()
        self.drain(run, identities)
        self.registry.close()
        self.registry = CaptureRegistry(self.temp.name)
        self.assertEqual(self.registry.read(run)['status'], 'completed')
        self.assertTrue(self.registry.reserve('new', 'fixture-interface')['start_granted'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
