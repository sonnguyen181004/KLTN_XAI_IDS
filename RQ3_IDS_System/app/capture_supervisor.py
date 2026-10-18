"""Single-owner, bounded local capture supervisor. No shell or arbitrary PID kill."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
from ipaddress import ip_address
from urllib.parse import urlsplit

from capture_registry import CaptureRegistry, CaptureConflict
from process_identity import birth_of, probe_identity, parent_of
from worker_control import write_control, read_control

ROOT = Path(__file__).resolve().parents[1]


class CaptureSupervisor:
    def __init__(self, folder, api_url, *, capture_python=None, capture_script=None):
        parsed = urlsplit(api_url)
        host = parsed.hostname
        if (parsed.scheme != 'http' or not host or parsed.username or parsed.password or
                parsed.path not in ('', '/') or parsed.query or parsed.fragment or
                (host != 'localhost' and not ip_address(host).is_loopback)):
            raise ValueError('Managed feeder requires a loopback HTTP API URL')
        self.registry = CaptureRegistry(folder)
        self.folder = self.registry.folder
        self.api_url = api_url
        self.capture_python = Path(capture_python or ROOT/'.venv_capture/Scripts/python.exe')
        self.capture_script = Path(capture_script or ROOT/'scripts/run_live_capture.py')
        self.guard = threading.RLock()
        self.thread = None
        self.stop_event = threading.Event()
        self.last_run = None
        self.error = None
        self.closed = False

    def status(self):
        with self.guard:
            state = self.registry.active()
            if state is None and self.last_run:
                state = self.registry.read(self.last_run)
            if state:
                state = json.loads(json.dumps(state))
                for worker in state['workers'].values():
                    worker.pop('worker_token', None)
                state['unresolved_launches'] = list(state.pop('launch_intents', {}))
                state['active'] = self.registry.active() is not None
                state['telemetry'] = {}
                for role in ('capture', 'feeder'):
                    try:
                        telemetry = json.loads((self.folder/state['run_id']/role/'status.json').read_text(encoding='utf-8'))
                        state['telemetry'][role] = {k: telemetry.get(k) for k in
                            ('state', 'error_message', 'accepted_packets', 'exported_flows', 'buffered_packets', 'acknowledged')}
                    except (OSError, ValueError):
                        pass
                checkpoint = self.folder/state['run_id']/'flows.csv.feeder-state.json'
                try:
                    saved = json.loads(checkpoint.read_text(encoding='utf-8'))
                    state['prediction_run_id'] = saved['run_id']
                    state['acknowledged_rows'] = saved['acknowledged_rows']
                except (OSError, ValueError, KeyError):
                    state['acknowledged_rows'] = None
            return dict(session=state, supervisor_error=self.error)

    def start(self, request_id, interface):
        with self.guard:
            if self.closed:
                raise CaptureConflict('Supervisor shutting down')
            if not self.capture_python.is_file():
                raise ValueError('Missing capture Python environment')
            state = self.registry.reserve(request_id, interface)
            if not state['start_granted']:
                return self.status()
            self.last_run = state['run_id']
            self.stop_event = threading.Event()
            self.error = None
            self.thread = threading.Thread(target=self._run, args=(state,), daemon=True)
            self.thread.start()
            return self.status()

    def stop(self, run_id):
        with self.guard:
            state = self.registry.read(run_id)
            if state['status'] in ('completed', 'failed') and self.registry.active() is None:
                return self.status()
            if run_id != self.last_run or state['status'] == 'unknown':
                raise CaptureConflict('Reconcile old session; not owned by current worker loop')
            self.stop_event.set()
            return self.status()

    def reconcile(self, run_id):
        with self.guard:
            self.registry.reconcile(run_id)
            self.last_run = run_id
            return self.status()

    @staticmethod
    def _report(worker):
        report = read_control(worker['folder']/'status.json')
        if report.get('worker_token') != worker['token'] or report.get('role') != worker['role']:
            raise RuntimeError('Worker status identity mismatch')
        return report

    @staticmethod
    def _send(worker, action, **extra):
        write_control(worker['folder']/'command.json', dict(worker_token=worker['token'], action=action, **extra))

    @staticmethod
    def _lease(worker):
        write_control(worker['folder']/'lease.json', dict(worker_token=worker['token'], monotonic=time.monotonic()))

    def _run(self, state):
        run = state['run_id']
        workers = {}
        logs = []
        try:
            folder = self.folder/run
            folder.mkdir()
            csv = folder/'flows.csv'
            for role in ('capture', 'feeder'):
                worker = dict(role=role, folder=folder/role, token=uuid.uuid4().hex,
                              process=None, identity=None, reaped=False)
                worker['folder'].mkdir()
                self._lease(worker)
                python = str(self.capture_python) if role == 'capture' else sys.executable
                command = ([str(self.capture_script), '--interface', state['interface'], '--output', str(csv)]
                           if role == 'capture' else [str(ROOT/'app/feeder.py'), '--watch', str(csv), '--convert-units'])
                log = (folder/(role+'.log')).open('wb')
                logs.append(log)
                self.registry.begin_launch(run, role, worker['token'])
                try:
                    worker['process'] = subprocess.Popen([python, str(ROOT/'scripts/managed_worker.py'),
                        '--role', role, '--control-dir', str(worker['folder']), '--worker-token', worker['token'], *command],
                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        env={**os.environ, 'IDS_API_URL': self.api_url, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'},
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                except OSError:
                    self.registry.cancel_unspawned(run, role)
                    raise
                workers[role] = worker
                launcher_birth = birth_of(worker['process'].pid)
                deadline = time.monotonic()+20
                while True:
                    try:
                        report = self._report(worker)
                        identity = {key: report[key] for key in ('pid', 'birth_token', 'worker_token')}
                        related = (identity['pid'] == worker['process'].pid or
                                   parent_of(identity['pid']) == worker['process'].pid)
                        if (not related or launcher_birth is None or
                                birth_of(worker['process'].pid) != launcher_birth or
                                probe_identity(identity)['status'] != 'alive'):
                            raise RuntimeError('Cannot verify owned worker OS identity')
                        worker['identity'] = identity
                        self.registry.attach(run, role, **identity)
                        break
                    except FileNotFoundError:
                        if worker['process'].poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError('Worker startup handshake failed')
                        time.sleep(.1)
            for worker in workers.values():
                if self.stop_event.is_set():
                    raise RuntimeError('Capture cancelled during startup')
                write_control(worker['folder']/'go.json', dict(worker_token=worker['token']))
            deadline = time.monotonic()+45
            stopping_at = None
            while True:
                current = self.registry.read(run)
                if self.stop_event.is_set() and current['status'] in ('starting', 'running'):
                    self.registry.request_stop(run)
                    stopping_at = time.monotonic()
                for role in ('capture', 'feeder'):
                    worker = workers[role]
                    if worker['reaped']:
                        continue
                    self._lease(worker)
                    current = self.registry.read(run)
                    if current['status'] in ('stopping', 'failed'):
                        if role == 'capture':
                            self._send(worker, 'stop')
                        elif current['status'] == 'failed':
                            self._send(worker, 'abort')
                    report = self._report(worker)
                    if any(report.get(k) != v for k, v in worker['identity'].items()):
                        raise RuntimeError('Worker changed identity')
                    code = worker['process'].poll()
                    if code is not None:
                        if probe_identity(worker['identity'])['status'] not in ('absent', 'reused'):
                            raise RuntimeError('Launcher exited but worker not proven gone')
                        # The last report must be read AFTER exit, not before poll:
                        # the worker may have finished between those two reads.
                        report = self._report(worker)
                        if any(report.get(k) != v for k, v in worker['identity'].items()):
                            raise RuntimeError('Final report identity mismatch')
                        good = report.get('state') == 'finished'
                        if not good and report.get('error_message'):
                            self.registry.fail(run, f"{role}: {report['error_message']}")
                        self.registry.observe_exit(run, role, worker['identity'], code,
                            flushed=good and report.get('flushed') is True,
                            rows=report.get('rows') if good else None,
                            acknowledged=report.get('acknowledged') if good else None)
                        worker['reaped'] = True
                        if role == 'capture' and self.registry.read(run)['status'] == 'draining':
                            size = report.get('csv_size')
                            if type(size) is not int or size != csv.stat().st_size:
                                raise RuntimeError('Capture CSV size evidence mismatch')
                            self._send(workers['feeder'], 'drain', rows=report['rows'], csv_size=size)
                            stopping_at = time.monotonic()
                        continue
                    observed = probe_identity(worker['identity'])['status']
                    if observed in ('absent', 'reused'):
                        # Normal exit may race Popen.poll (especially venv launcher).
                        worker.setdefault('gone_since', time.monotonic())
                        if time.monotonic()-worker['gone_since'] > 5:
                            raise RuntimeError('Worker gone but launcher not reaped')
                        continue
                    if observed != 'alive':
                        raise RuntimeError('Live worker OS identity unavailable')
                    worker.pop('gone_since', None)
                    age = time.monotonic()-report['heartbeat_monotonic']
                    if not 0 <= age < 90:
                        raise RuntimeError('Worker heartbeat stale')
                    self.registry.heartbeat(run, role, worker['identity'], ready=report['state'] in
                                            ('capturing', 'sending', 'waiting_input'))
                current = self.registry.read(run)
                if all(w['reaped'] for w in workers.values()):
                    self.registry.finalize(run)
                    return
                if current['status'] == 'starting' and time.monotonic() > deadline:
                    raise RuntimeError('Worker readiness timeout')
                if stopping_at and time.monotonic()-stopping_at > 120:
                    raise RuntimeError('Stop/drain timeout; outcome incomplete')
                time.sleep(.25)
        except BaseException as exc:
            self.error = f'{type(exc).__name__}: {exc}'
            try:
                write_control(self.folder/run/'supervisor_error.json', dict(error=self.error))
                self.registry.fail(run, self.error)
                # Cooperative rollback only; no terminate/kill by PID.
                for role, worker in workers.items():
                    self._send(worker, 'stop' if role == 'capture' else 'abort')
                until = time.monotonic()+65
                while time.monotonic() < until:
                    pending = False
                    for role, worker in workers.items():
                        if worker['reaped']:
                            continue
                        code = worker['process'].poll()
                        if code is None:
                            pending = True
                            continue  # No lease renewal: abandoned workers must fail closed.
                        if worker['identity'] and probe_identity(worker['identity'])['status'] in ('absent', 'reused'):
                            self.registry.observe_exit(run, role, worker['identity'], code)
                            worker['reaped'] = True
                    if not pending:
                        break
                    time.sleep(.25)
                self.registry.finalize_failed_start(run)
            except BaseException:
                try:
                    self.registry.mark_unknown(run, self.error+'; unresolved workers/launch')
                except Exception:
                    pass
        finally:
            for log in logs:
                log.close()

    def close(self):
        with self.guard:
            self.closed = True
            self.stop_event.set()
            thread = self.thread
        if thread:
            thread.join(timeout=140)
        if thread and thread.is_alive():
            # Do not release ownership while the loop may still mutate it.
            return False
        self.registry.close()
        return True
