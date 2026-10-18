"""HT4 worker-local control protocol. Private per-worker directories only.

Not an HTTP API or supervisor. A trusted owner renews lease.json and writes
command.json; the worker writes status.json. Tokens bind all messages.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import time
from ingestion_checkpoint import save_checkpoint


def write_control(path, value):
    """Bound Windows reader/replace contention; never suppress persistent errors."""
    for attempt in range(6):
        try:
            save_checkpoint(path, value)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.02 * (attempt + 1))


def process_birth():
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        values = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(kernel.GetCurrentProcess(), *(ctypes.byref(v) for v in values)):
            raise ctypes.WinError(ctypes.get_last_error())
        return str((values[0].dwHighDateTime << 32) | values[0].dwLowDateTime)
    # Explicit OS creation identity, not a random replacement for process birth.
    stat = Path('/proc/self/stat').read_text()
    return stat[stat.rfind(')') + 2:].split()[19]


class WorkerControl:
    def __init__(self, folder, token, role, lease_timeout=45):
        self.folder = Path(folder).resolve()
        if not self.folder.is_dir() or not isinstance(token, str) or len(token) < 32:
            raise ValueError('Managed worker needs an existing private directory and token >=32 chars')
        self.token, self.role = token, role
        self.lease_timeout = lease_timeout
        self.identity = dict(pid=os.getpid(), birth_token=process_birth(), worker_token=token)
        self.last_write = 0.
        self.report = dict(role=role, **self.identity, state='starting', sequence=0)
        self.tick('starting', force=True)

    def _read(self, name):
        value = json.loads((self.folder/name).read_text(encoding='utf-8'))
        if not isinstance(value, dict) or value.get('worker_token') != self.token:
            raise RuntimeError('Worker control token mismatch')
        return value

    def tick(self, state, force=False, **values):
        lease = self._read('lease.json')
        # Sample after reading: the owner may renew while the file is read.
        stamp = time.monotonic()
        age = stamp - float(lease['monotonic'])
        if not 0 <= age <= self.lease_timeout:
            raise RuntimeError('Supervisor lease expired or invalid; session must not report success')
        command = self._read('command.json') if (self.folder/'command.json').exists() else {}
        allowed = ('stop',) if self.role == 'capture' else ('drain', 'abort')
        if command and command.get('action') not in allowed:
            raise RuntimeError('Unsupported worker command')
        if force or stamp - self.last_write >= 1:
            self.report.update(state=state, heartbeat_monotonic=stamp, **values)
            self.report['sequence'] += 1
            write_control(self.folder/'status.json', self.report)
            self.last_write = stamp
        return command

    def finish(self, success, **values):
        self.report.update(state='finished' if success else 'failed', **values,
                           heartbeat_monotonic=time.monotonic())
        self.report['sequence'] += 1
        write_control(self.folder/'status.json', self.report)


def control_args(parser):
    parser.add_argument('--control-dir', type=Path, help='Internal HT4 worker directory; not for manual sessions')
    parser.add_argument('--worker-token', help='Internal HT4 identity token')


def from_args(args, role):
    if bool(args.control_dir) != bool(args.worker_token):
        raise ValueError('--control-dir and --worker-token must be supplied together')
    return WorkerControl(args.control_dir, args.worker_token, role) if args.control_dir else None
