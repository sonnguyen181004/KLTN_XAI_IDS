"""Read-only capacity reporting and non-overwriting SQLite snapshot bundles.

No retention deletion, CSV copy, DB migration, model changes or live restore.
"""
import hashlib
from contextlib import closing
from itertools import zip_longest
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
from datetime import datetime, timezone

TABLES = ('FlowRecord', 'DataError', 'Prediction', 'AlertRecord', 'Reliability', 'Timing')


def storage_status(db_path, warning_free_bytes=1073741824):
    """Shallow inventory only; no opening SQLite or reading packet content."""
    db_path = Path(db_path).resolve()
    folder = db_path.parent
    disk = shutil.disk_usage(folder)
    groups = dict(database=0, csv=0, log=0, checkpoint=0, other=0)
    count = 0
    errors = 0
    for path in folder.iterdir():
        try:
            if path.is_symlink() or not path.is_file():
                continue
            size = path.stat().st_size
            name = path.name
            group = ('database' if name.endswith(('.db', '.db-wal', '.db-shm')) else
                     'checkpoint' if '.feeder-state.json' in name else
                     'csv' if path.suffix.lower() == '.csv' else
                     'log' if path.suffix.lower() == '.log' else 'other')
            groups[group] += size
            count += 1
        except OSError:
            errors += 1
    return dict(free_bytes=disk.free, total_bytes=disk.total,
                warning_free_bytes=warning_free_bytes,
                low_space=disk.free < warning_free_bytes, file_count=count,
                bytes_by_group=groups, scan_errors=errors,
                scope='DB parent directory, direct files only; excludes subdirectories/backups elsewhere',
                automatic_deletion=False)


def readonly(path, immutable=False):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro' +
                           ('&immutable=1' if immutable else ''), uri=True, timeout=5)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inspect_db(conn):
    if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('SQLite integrity_check failed')
    if conn.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise ValueError('SQLite foreign_key_check failed')
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not set(TABLES) <= tables:
        raise ValueError('Not an IDS database: missing required tables')
    counts = {name: conn.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] for name in TABLES}
    versions = [r[0] for r in conn.execute('SELECT DISTINCT model_version FROM Prediction ORDER BY model_version')]
    return dict(table_counts=counts, model_versions=versions)


def backup_db(source, bundle, timeout_seconds=30):
    source, bundle = Path(source).resolve(), Path(bundle).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if timeout_seconds <= 0:
        raise ValueError('Backup timeout must be positive')
    # Exclusive directory: no replacement, existing bundle or partial retry.
    bundle.mkdir(parents=True, exist_ok=False)
    target = bundle/'snapshot.db'
    started = time.monotonic()
    try:
        with closing(readonly(source)) as src:
            try:
                pages = src.execute('PRAGMA page_count').fetchone()[0]
                page_size = src.execute('PRAGMA page_size').fetchone()[0]
                if shutil.disk_usage(bundle).free < pages * page_size + 268435456:
                    raise OSError('Insufficient free space for snapshot plus 256 MiB safety margin')
                with closing(sqlite3.connect(target)) as dst:
                    try:
                        def progress(status, remaining, total):
                            if time.monotonic() - started > timeout_seconds:
                                raise TimeoutError('Backup deadline exceeded; partial bundle is not valid')
                        src.backup(dst, pages=256, progress=progress, sleep=.05)
                        dst.execute('PRAGMA journal_mode=DELETE')
                        metadata = inspect_db(dst)
                    finally:
                        dst.close()
            finally:
                src.close()
        with target.open('rb+') as stream:
            os.fsync(stream.fileno())
        manifest = dict(format_version=1, status='complete',
                        created_at=datetime.now(timezone.utc).isoformat(),
                        database='snapshot.db', sha256=digest(target),
                        size_bytes=target.stat().st_size, **metadata,
                        includes='SQLite only; no CSV/checkpoint/log/model/pending capture RAM')
        # Manifest is the completion marker, written only after validation.
        temp = bundle/'manifest.pending'
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temp.rename(bundle/'manifest.json')
        return manifest
    except Exception:
        # Leave partial artifacts for diagnosis; never delete user data.
        raise


def verify_bundle(bundle):
    bundle = Path(bundle).resolve()
    manifest = json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format_version') != 1 or manifest.get('status') != 'complete' or manifest.get('database') != 'snapshot.db':
        raise ValueError('Incomplete or unsupported snapshot bundle')
    target = bundle/'snapshot.db'
    if target.is_symlink() or any(Path(str(target)+suffix).exists() for suffix in ('-wal', '-shm', '-journal')):
        raise ValueError('Snapshot must be standalone, not linked or open for WAL writes')
    if target.stat().st_size != manifest['size_bytes'] or digest(target) != manifest['sha256']:
        raise ValueError('Snapshot checksum/size mismatch')
    conn = readonly(target, immutable=True)
    try:
        metadata = inspect_db(conn)
    finally:
        conn.close()
    if any(metadata[key] != manifest[key] for key in metadata):
        raise ValueError('Snapshot metadata mismatch')
    return manifest


def restore_bundle(bundle, destination):
    """Materialize a checked snapshot into a NEW bundle; never swap a live DB."""
    verified = verify_bundle(bundle)
    result = backup_db(Path(bundle)/'snapshot.db', destination)
    if result['table_counts'] != verified['table_counts'] or result['sha256'] != verified['sha256']:
        # SQLite backup may normalize header bytes: semantic comparison suffices
        # only when contents compare as identical ordered SQL dumps.
        left, right = readonly(Path(bundle)/'snapshot.db', True), readonly(Path(destination)/'snapshot.db', True)
        try:
            if any(a != b for a, b in zip_longest(left.iterdump(), right.iterdump())):
                raise ValueError('Restored database differs from snapshot')
        finally:
            left.close()
            right.close()
    return verify_bundle(destination)
