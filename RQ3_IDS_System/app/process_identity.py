"""Read-only OS identity checks. Never signals, adopts or restarts a process."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path


def birth_of(pid):
    """Creation identity or None if absent/exited; errors remain unknown to caller."""
    if type(pid) is not int or pid <= 0 or (os.name == 'nt' and pid > 0xffffffff):
        raise ValueError('PID must be a positive integer')
    if os.name != 'nt':
        try:
            fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        except FileNotFoundError:
            return None
        return None if fields[0] == 'Z' else fields[19]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)  # limited query + synchronize
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:  # ERROR_INVALID_PARAMETER: PID absent (PID 0 rejected above).
            return None
        raise ctypes.WinError(error)
    try:
        result = kernel.WaitForSingleObject(handle, 0)
        if result == 0:
            return None
        if result != 258:  # WAIT_TIMEOUT means still running.
            raise OSError('Cannot establish process liveness')
        values = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(v) for v in values)):
            raise ctypes.WinError(ctypes.get_last_error())
        return str((values[0].dwHighDateTime << 32) | values[0].dwLowDateTime)
    finally:
        kernel.CloseHandle(handle)


def probe_identity(identity):
    """alive/reused/absent/unknown, with no inference of successful flush or ACK."""
    try:
        expected = identity.get('birth_token')
        if not isinstance(expected, str) or not expected:
            raise ValueError('Missing creation identity')
        actual = birth_of(identity.get('pid'))
        return dict(status='absent' if actual is None else ('alive' if actual == expected else 'reused'),
                    observed_birth=actual)
    except (OSError, ValueError, IndexError) as exc:
        return dict(status='unknown', error_type=type(exc).__name__)
