"""HT4 durable lifecycle journal with explicit read-only OS reconciliation.

The future API supervisor alone owns this registry. It must obtain identities,
heartbeats and exit/flush/ACK evidence from owned workers, not HTTP payloads.
No PID kill, capture startup, or recovery auto-restart is implemented here.
Persist begin_launch before spawn; attach only after verifying OS identity.
"""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
import uuid

from ingestion_checkpoint import checkpoint_lock
from process_identity import probe_identity


class CaptureConflict(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


class CaptureRegistry:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.folder.mkdir(parents=True, exist_ok=True)
        self._guard = threading.RLock()
        self._closed = False
        self._ownership = checkpoint_lock(self.folder/'api-owner')
        try:
            self._ownership.__enter__()
        except RuntimeError as exc:
            raise CaptureConflict('Another supervisor owns this registry') from exc
        self.path = self.folder/'sessions.sqlite3'
        self.owner_epoch = uuid.uuid4().hex
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    run_id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
                    active INTEGER NOT NULL CHECK(active IN (0,1)), payload TEXT NOT NULL)''')
                conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS one_active ON sessions(active) WHERE active=1')
                row = conn.execute('SELECT run_id,payload FROM sessions WHERE active=1').fetchone()
                if row:
                    state = json.loads(row[1])
                    state.update(status='unknown', reason='supervisor_restarted_requires_reconciliation', updated_at=now())
                    self._save(conn, state, active=True)
        except BaseException:
            self.close()
            raise

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def _check(self):
        if self._closed:
            raise RuntimeError('Registry is closed')

    def _save(self, conn, state, active=True):
        state['updated_at'] = now()
        conn.execute('UPDATE sessions SET active=?,payload=? WHERE run_id=?',
                     (int(active), json.dumps(state), state['run_id']))

    def _load(self, conn, run_id):
        row = conn.execute('SELECT active,payload FROM sessions WHERE run_id=?', (run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        return bool(row[0]), json.loads(row[1])

    def reserve(self, request_id, interface):
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise ValueError('request_id must be 1–128 characters')
        if not isinstance(interface, str) or not interface.strip() or len(interface) > 256:
            raise ValueError('Invalid interface name')
        with self._guard, closing(self._connect()) as conn, conn:
            self._check()
            conn.execute('BEGIN IMMEDIATE')
            previous = conn.execute('SELECT payload FROM sessions WHERE request_id=?', (request_id,)).fetchone()
            if previous:
                state = json.loads(previous[0])
                if state['interface'] != interface:
                    raise CaptureConflict('Request ID already used with different parameters')
                return dict(state, start_granted=False)  # Never spawn on a retry.
            if conn.execute('SELECT 1 FROM sessions WHERE active=1').fetchone():
                raise CaptureConflict('A session is active or requires reconciliation')
            state = dict(run_id=uuid.uuid4().hex, request_id=request_id, interface=interface,
                         owner_epoch=self.owner_epoch, status='starting', reason=None,
                         created_at=now(), updated_at=now(), workers={}, capture_result=None,
                         feeder_result=None, launch_journal_version=1, launch_intents={})
            conn.execute('INSERT INTO sessions VALUES (?,?,1,?)',
                         (state['run_id'], request_id, json.dumps(state)))
            return dict(deepcopy(state), start_granted=True)

    def read(self, run_id):
        with self._guard, closing(self._connect()) as conn:
            self._check()
            return self._load(conn, run_id)[1]

    def _mutate(self, run_id, action):
        with self._guard, closing(self._connect()) as conn, conn:
            self._check()
            conn.execute('BEGIN IMMEDIATE')
            active, state = self._load(conn, run_id)
            if not active:
                raise CaptureConflict('Session already finalized')
            if state['owner_epoch'] != self.owner_epoch or state['status'] == 'unknown':
                raise CaptureConflict('Session requires explicit process reconciliation')
            action(state)
            self._save(conn, state)
            return deepcopy(state)

    def attach(self, run_id, role, pid, birth_token, worker_token):
        if role not in ('capture', 'feeder') or type(pid) is not int or pid <= 0 or not birth_token or not worker_token:
            raise ValueError('Need role, PID, creation identity and worker token')
        def action(state):
            if state['status'] != 'starting' or role in state['workers']:
                raise CaptureConflict('Worker cannot be replaced or attached after startup')
            intent = state.get('launch_intents', {}).get(role)
            if not intent or intent['worker_token'] != worker_token:
                raise CaptureConflict('Persist matching launch intent before creating a worker')
            state['workers'][role] = dict(pid=pid, birth_token=birth_token, worker_token=worker_token,
                                          heartbeat_at=None, ready=False, exit_code=None)
            del state['launch_intents'][role]
        return self._mutate(run_id, action)

    def begin_launch(self, run_id, role, worker_token):
        """Must commit BEFORE spawn. Unresolved intent blocks recovery after crash."""
        if role not in ('capture', 'feeder') or not isinstance(worker_token, str) or not worker_token:
            raise ValueError('Need worker role and token')
        def action(state):
            if (state['status'] != 'starting' or role in state['workers'] or
                    role in state.get('launch_intents', {})):
                raise CaptureConflict('Launch already attempted or startup closed')
            state.setdefault('launch_intents', {})[role] = dict(worker_token=worker_token, at=now())
        return self._mutate(run_id, action)

    def active(self):
        with self._guard, closing(self._connect()) as conn:
            self._check()
            row = conn.execute('SELECT payload FROM sessions WHERE active=1').fetchone()
            return json.loads(row[0]) if row else None

    def cancel_unspawned(self, run_id, role):
        """Trusted launcher only: Popen raised without returning a process handle."""
        def action(state):
            if role in state['workers']:
                raise CaptureConflict('Cannot cancel attached worker')
            state['launch_intents'].pop(role, None)
        return self._mutate(run_id, action)

    def fail(self, run_id, reason):
        def action(state):
            state.update(status='failed', reason=state.get('reason') or str(reason))
        return self._mutate(run_id, action)

    def finalize_failed_start(self, run_id):
        with self._guard, closing(self._connect()) as conn, conn:
            self._check()
            active, state = self._load(conn, run_id)
            if not active:
                return state
            if (state['owner_epoch'] != self.owner_epoch or state['status'] != 'failed' or
                    state.get('launch_intents') or any(w['exit_code'] is None for w in state['workers'].values())):
                raise CaptureConflict('Startup failure still has unresolved processes')
            self._save(conn, state, active=False)
            return state

    def reconcile(self, run_id):
        """Explicit read-only OS reconciliation; never accepts HTTP-supplied evidence.

        Releases only as FAILED when all recorded identities are gone and no
        unresolved spawn window exists. Cannot recover success from exit absence.
        """
        with self._guard, closing(self._connect()) as conn, conn:
            self._check()
            conn.execute('BEGIN IMMEDIATE')
            active, state = self._load(conn, run_id)
            if not active:
                return state
            if state['status'] != 'unknown':
                raise CaptureConflict('Reconciliation requires an unknown session')
            evidence = {role: probe_identity(worker) for role, worker in state['workers'].items()}
            state['reconciliation'] = dict(at=now(), workers=evidence)
            # Old journals lack a pre-spawn record; a missing worker is ambiguous.
            ambiguous = bool(state.get('launch_intents')) or (
                state.get('launch_journal_version') != 1 and len(state['workers']) != 2)
            gone = all(item['status'] in ('absent', 'reused') for item in evidence.values())
            if not ambiguous and gone:
                state.update(status='failed', reason='reconciled_workers_gone_outcome_unverified')
                self._save(conn, state, active=False)
            else:
                state['reason'] = ('unresolved_launch_requires_manual_reconciliation' if ambiguous
                                   else 'worker_alive_or_identity_unverifiable')
                self._save(conn, state, active=True)
            return deepcopy(state)

    @staticmethod
    def _worker(state, role, identity):
        worker = state['workers'].get(role)
        if not worker or any(worker[k] != identity.get(k) for k in ('pid', 'birth_token', 'worker_token')):
            raise CaptureConflict('Worker identity mismatch; PID alone is not sufficient')
        return worker

    def heartbeat(self, run_id, role, identity, ready=False):
        def action(state):
            worker = self._worker(state, role, identity)
            if worker['exit_code'] is not None:
                raise CaptureConflict('Worker has already exited')
            worker.update(heartbeat_at=now(), ready=bool(ready))
            if state['status'] == 'starting' and len(state['workers']) == 2 and all(w['ready'] for w in state['workers'].values()):
                state['status'] = 'running'
        return self._mutate(run_id, action)

    def request_stop(self, run_id):
        def action(state):
            if state['status'] in ('starting', 'running'):
                state['status'] = 'stopping'
            # Repeated stop is harmless; never changes failed/draining to running.
        return self._mutate(run_id, action)

    def mark_unknown(self, run_id, reason):
        if not reason:
            raise ValueError('Unknown state requires an explicit reason')
        def action(state):
            state.update(status='unknown', reason=str(reason))
        return self._mutate(run_id, action)

    def observe_exit(self, run_id, role, identity, exit_code, *, flushed=False, rows=None, acknowledged=None):
        if type(exit_code) is not int:
            raise ValueError('Exit code must come from process reaping')
        for count in (rows, acknowledged):
            if count is not None and (type(count) is not int or count < 0):
                raise ValueError('Row counters must be nonnegative integers')
        def action(state):
            worker = self._worker(state, role, identity)
            if worker['exit_code'] is not None:
                raise CaptureConflict('Exit evidence already recorded')
            worker['exit_code'] = exit_code
            if role == 'capture':
                state['capture_result'] = dict(flushed=flushed is True, rows=rows)
                if exit_code == 0 and flushed is True and rows is not None and state['status'] == 'stopping':
                    state['status'] = 'draining'
                else:
                    state.update(status='failed', reason=state.get('reason') or 'capture_exit_without_safe_stop_flush')
            else:
                state['feeder_result'] = dict(acknowledged=acknowledged)
                if exit_code != 0 or state['status'] != 'draining':
                    state.update(status='failed', reason=state.get('reason') or 'feeder_exit_before_drain_or_with_error')
        return self._mutate(run_id, action)

    def finalize(self, run_id):
        with self._guard, closing(self._connect()) as conn, conn:
            self._check()
            active, state = self._load(conn, run_id)
            if not active:
                return state
            if state['owner_epoch'] != self.owner_epoch or state['status'] == 'unknown':
                raise CaptureConflict('Unreconciled session cannot be finalized')
            if len(state['workers']) != 2 or any(w['exit_code'] is None for w in state['workers'].values()):
                raise CaptureConflict('Both owned workers must be reaped first')
            capture, feeder = state['capture_result'], state['feeder_result']
            complete = (state['status'] == 'draining' and capture and feeder and capture['flushed'] and
                        capture['rows'] is not None and capture['rows'] == feeder['acknowledged'] and
                        all(w['exit_code'] == 0 for w in state['workers'].values()))
            state.update(status='completed' if complete else 'failed',
                         reason=None if complete else (state['reason'] or 'csv_ack_mismatch'))
            self._save(conn, state, active=False)
            return state

    def close(self):
        with self._guard:
            if not self._closed:
                self._closed = True
                self._ownership.__exit__(None, None, None)
