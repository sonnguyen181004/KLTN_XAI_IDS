"""HT4.3a: read-only OS checks + durable startup recovery; no NIC or IDS DB."""
import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]/'app'
sys.path.insert(0, str(APP))
from capture_registry import CaptureRegistry, CaptureConflict
from process_identity import birth_of, probe_identity
from worker_control import process_birth


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ids_reconcile_')
        self.registry = CaptureRegistry(self.temp.name)
        self.run = self.registry.reserve('request', 'fixture-no-nic')['run_id']
        self.children = []

    def tearDown(self):
        for child in self.children:
            child.communicate(timeout=10)
        self.registry.close()
        self.temp.cleanup()

    def child(self):
        code = ('import sys,os,json; sys.path.insert(0,sys.argv[1]); '
                'from worker_control import process_birth; '
                'print(json.dumps(dict(pid=os.getpid(),birth_token=process_birth(),worker_token="test-token")),flush=True); '
                'sys.stdin.read()')
        child = subprocess.Popen([sys.executable, '-c', code, str(APP)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.children.append(child)
        identity = json.loads(child.stdout.readline())
        return child, identity

    def attach(self, identity, role='capture'):
        self.registry.begin_launch(self.run, role, identity['worker_token'])
        self.registry.attach(self.run, role, **identity)

    def restart(self):
        self.registry.close()
        self.registry = CaptureRegistry(self.temp.name)

    def test_os_creation_identity_matches_worker_self_report(self):
        self.assertEqual(birth_of(os.getpid()), process_birth())
        child, identity = self.child()
        self.assertEqual(probe_identity(identity)['status'], 'alive')
        self.assertEqual(probe_identity({**identity, 'birth_token': 'different'})['status'], 'reused')
        child.communicate(timeout=10)
        self.assertEqual(probe_identity(identity)['status'], 'absent')

    def test_live_child_blocks_restart_recovery_then_exit_releases_as_failed(self):
        child, identity = self.child()
        self.attach(identity)
        self.restart()
        self.assertEqual(self.registry.active()['run_id'], self.run)
        result = self.registry.reconcile(self.run)
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(child.poll())
        with self.assertRaises(CaptureConflict):
            self.registry.reserve('second', 'fixture-no-nic')
        child.communicate(timeout=10)
        result = self.registry.reconcile(self.run)
        self.assertEqual(result['status'], 'failed')
        self.assertIsNone(result['capture_result'])
        self.assertIsNone(self.registry.active())
        self.assertTrue(self.registry.reserve('second', 'fixture-no-nic')['start_granted'])
        self.assertFalse(self.registry.reserve('request', 'fixture-no-nic')['start_granted'])

    def test_reused_pid_never_killed_or_marked_completed(self):
        child, identity = self.child()
        self.attach({**identity, 'birth_token': 'old-creation'})
        self.restart()
        result = self.registry.reconcile(self.run)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reconciliation']['workers']['capture']['status'], 'reused')
        self.assertIsNone(child.poll())

    def test_spawn_gap_blocks_even_without_attached_workers(self):
        self.registry.begin_launch(self.run, 'capture', 'token')
        self.restart()
        result = self.registry.reconcile(self.run)
        self.assertEqual(result['status'], 'unknown')
        self.assertIn('unresolved_launch', result['reason'])
        self.assertIsNotNone(self.registry.active())

    def test_no_spawn_attempt_can_be_cancelled_after_restart(self):
        self.restart()
        self.assertEqual(self.registry.reconcile(self.run)['status'], 'failed')
        self.assertIsNone(self.registry.active())

    def test_attach_requires_matching_durable_intent_and_clears_it(self):
        identity = dict(pid=os.getpid(), birth_token=process_birth(), worker_token='token')
        with self.assertRaises(CaptureConflict):
            self.registry.attach(self.run, 'capture', **identity)
        self.registry.begin_launch(self.run, 'capture', 'token')
        with self.assertRaises(CaptureConflict):
            self.registry.begin_launch(self.run, 'capture', 'token')
        with self.assertRaises(CaptureConflict):
            self.registry.attach(self.run, 'capture', **{**identity, 'worker_token': 'wrong'})
        self.registry.attach(self.run, 'capture', **identity)
        self.assertEqual(self.registry.read(self.run)['launch_intents'], {})

    def test_access_denied_probe_is_unknown_not_absent(self):
        with patch('process_identity.birth_of', side_effect=PermissionError()):
            self.assertEqual(probe_identity(dict(pid=123, birth_token='x'))['status'], 'unknown')
        self.assertEqual(probe_identity(dict(pid=-1, birth_token='x'))['status'], 'unknown')
        if os.name == 'nt':
            self.assertEqual(probe_identity(dict(pid=2**32 + os.getpid(), birth_token='x'))['status'], 'unknown')

    def test_unverifiable_worker_keeps_registry_locked(self):
        self.attach(dict(pid=123, birth_token='x', worker_token='token'))
        self.restart()
        with patch('capture_registry.probe_identity', return_value=dict(status='unknown')):
            self.assertEqual(self.registry.reconcile(self.run)['status'], 'unknown')
        self.assertIsNotNone(self.registry.active())

    def test_legacy_partial_journal_not_assumed_safe(self):
        with closing(sqlite3.connect(self.registry.path)) as conn, conn:
            state = self.registry.read(self.run)
            del state['launch_journal_version']
            del state['launch_intents']
            conn.execute('UPDATE sessions SET payload=? WHERE run_id=?', (json.dumps(state), self.run))
        self.restart()
        self.assertEqual(self.registry.reconcile(self.run)['status'], 'unknown')

    def test_reconcile_write_error_does_not_unlock(self):
        self.restart()
        with patch.object(self.registry, '_save', side_effect=OSError('fixture write failure')):
            with self.assertRaises(OSError):
                self.registry.reconcile(self.run)
        self.assertEqual(self.registry.active()['status'], 'unknown')

    def test_launch_intent_write_error_prevents_permission_to_spawn(self):
        with patch.object(self.registry, '_save', side_effect=OSError('fixture write failure')):
            with self.assertRaises(OSError):
                self.registry.begin_launch(self.run, 'capture', 'token')
        self.assertEqual(self.registry.read(self.run)['launch_intents'], {})

    def test_normal_active_session_cannot_be_reconciled(self):
        with self.assertRaises(CaptureConflict):
            self.registry.reconcile(self.run)


if __name__ == '__main__':
    unittest.main(verbosity=2)
