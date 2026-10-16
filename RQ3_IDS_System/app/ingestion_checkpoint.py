"""Durable append-only CSV cursor; one feeder per checkpoint, no feature data stored."""
import csv
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import uuid


@contextmanager
def checkpoint_lock(path):
    lock_path = Path(str(path) + '.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Checkpoint đang được feeder khác sử dụng.') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def save_checkpoint(path, state):
    """Replace only after fsync; interruption retains old or complete new state."""
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(state, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def identity(stream):
    stat = os.fstat(stream.fileno())
    return [stat.st_dev, stat.st_ino]


def anchor(stream, offset):
    position = stream.tell()
    try:
        stream.seek(max(0, offset - 512))
        return hashlib.sha256(stream.read(min(offset, 512))).hexdigest()
    finally:
        stream.seek(position)


def validate_file(stream, state):
    if identity(stream) != state['identity'] or os.fstat(stream.fileno()).st_size < state['offset']:
        raise RuntimeError('CSV đã bị thay thế/cắt ngắn. Dùng tên CSV và checkpoint mới cho lượt capture mới.')
    if anchor(stream, state['offset']) != state['anchor']:
        raise RuntimeError('CSV đã đổi nội dung tại checkpoint; dừng để tránh gửi sai hoặc bỏ flow.')


def read_record(stream):
    """Read a complete newline-terminated CSV record, including quoted newlines.

    Return None and rewind on partial write. Refuse malformed records; never skip.
    """
    start = stream.tell()
    chunks = []
    while True:
        line = stream.readline(1024 * 1024 + 1)
        if len(line) > 1024 * 1024:
            raise ValueError('Một dòng CSV vượt 1 MiB; kiểm tra file đầu vào.')
        if not line or not line.endswith(b'\n'):
            stream.seek(start)
            return None
        chunks.append(line)
        if sum(map(len, chunks)) > 1024 * 1024:
            raise ValueError('Một dòng CSV vượt 1 MiB; kiểm tra file đầu vào.')
        try:
            text = b''.join(chunks).decode('utf-8-sig' if start == 0 else 'utf-8')
            # Upstream CICFlowMeter opens CSV without newline='', producing
            # CR CR LF on Windows. csv.reader exposes the extra CR as an empty
            # row; accept those empty rows just as the old feeder did.
            rows = [row for row in csv.reader(io.StringIO(text, newline=''), strict=True) if row]
        except csv.Error as exc:
            if str(exc) == 'unexpected end of data':
                continue
            raise ValueError(f'CSV sai định dạng tại byte {start}: {exc}') from exc
        if len(rows) == 1:
            return rows[0]
        if not rows:
            return []
        raise ValueError(f'CSV không phải một record tại byte {start}')


def open_state(path, watch_path, api_url, convert_units, zone):
    config = dict(watch_path=os.path.normcase(str(watch_path.resolve())),
                  api_url=api_url.rstrip('/'), convert_units=bool(convert_units))
    if path.exists():
        state = json.loads(path.read_text(encoding='utf-8'))
        if state.get('version') != 1 or any(state.get(k) != v for k,v in config.items()):
            raise RuntimeError('Checkpoint khác file/API/quy tắc đổi đơn vị; dùng checkpoint mới cho lượt mới.')
        if zone is not None and state['capture_zone'] != zone:
            raise RuntimeError('Múi giờ khác checkpoint; giữ cấu hình cũ khi tiếp tục một lượt.')
        return state
    return dict(version=1, **config, run_id=str(uuid.uuid4()), capture_zone=zone,
                header=None, identity=None, offset=0, acknowledged_rows=0, anchor=None)
