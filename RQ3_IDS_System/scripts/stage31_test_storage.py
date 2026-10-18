"""Storage regression, temporary IDS databases only. No live data mutation."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RQ3/'app'))
import db
from storage import backup_db, verify_bundle, restore_bundle, storage_status


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ids_storage_test_')
        self.root = Path(self.temp.name)
        self.path = self.root/'source.db'
        self.conn = db.init_db(self.path)
        self.conn.execute("INSERT INTO FlowRecord(flow_id,received_at,source,features_json,ingestion_key,ingestion_hash,ingestion_response_json) VALUES ('f1','now','api','{}','key','hash','{}')")
        self.conn.execute("INSERT INTO Prediction VALUES ('f1','Benign','{}','fixture','now')")
        self.conn.execute("INSERT INTO AlertRecord(alert_id,flow_id,group_key,predicted_label,created_at,explanation_status) VALUES ('a1','f1','g','Bot','now','recovery_pending')")
        self.conn.execute("INSERT INTO Reliability(alert_id,shap_top5_json,lime_top5_json) VALUES ('a1','[]','[]')")
        self.conn.execute("INSERT INTO Timing(flow_id,step,duration_ms,recorded_at) VALUES ('f1','predict',1,'now')")
        self.conn.execute("INSERT INTO DataError(flow_id,occurred_at,error_code,reason) VALUES ('bad','now',422,'fixture')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_online_wal_snapshot_restore_and_source_preserved(self):
        self.assertTrue(Path(str(self.path)+'-wal').exists())
        self.conn.execute("INSERT INTO FlowRecord(flow_id,received_at,source,features_json) VALUES ('uncommitted','now','api','{}')")
        bundle = self.root/'backup'
        manifest = backup_db(self.path, bundle)
        self.assertEqual(manifest['table_counts']['FlowRecord'], 1)
        self.assertEqual(verify_bundle(bundle), manifest)
        self.assertEqual(restore_bundle(bundle, self.root/'restored')['table_counts'], manifest['table_counts'])
        with closing(sqlite3.connect(self.root/'restored/snapshot.db')) as restored:
            self.assertEqual(restored.execute('SELECT ingestion_key FROM FlowRecord').fetchone()[0], 'key')
            self.assertEqual(restored.execute('SELECT explanation_status FROM AlertRecord').fetchone()[0], 'recovery_pending')
            self.assertEqual(restored.execute('SELECT lime_top5_json FROM Reliability').fetchone()[0], '[]')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM FlowRecord').fetchone()[0], 2)
        self.conn.rollback()

    def test_never_overwrites_existing_backup_or_restore(self):
        bundle = self.root/'backup'
        backup_db(self.path, bundle)
        before = (bundle/'snapshot.db').read_bytes()
        with self.assertRaises(FileExistsError):
            backup_db(self.path, bundle)
        with self.assertRaises(FileExistsError):
            restore_bundle(bundle, self.root)
        self.assertEqual((bundle/'snapshot.db').read_bytes(), before)

    def test_corrupt_checksum_and_incomplete_bundle_refused(self):
        bundle = self.root/'backup'
        backup_db(self.path, bundle)
        with (bundle/'snapshot.db').open('ab') as stream:
            stream.write(b'corrupt')
        with self.assertRaises(ValueError):
            restore_bundle(bundle, self.root/'restore')
        self.assertFalse((self.root/'restore').exists())
        with self.assertRaises(FileNotFoundError):
            verify_bundle(self.root/'missing')

    def test_manifest_path_and_wal_sidecar_refused(self):
        bundle = self.root/'backup'
        backup_db(self.path, bundle)
        sidecar = bundle/'snapshot.db-wal'
        sidecar.touch()
        with self.assertRaises(ValueError):
            verify_bundle(bundle)
        sidecar.unlink()
        path = bundle/'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['database'] = '../source.db'
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            verify_bundle(bundle)

    def test_low_space_and_deadline_do_not_mark_complete(self):
        with patch('storage.shutil.disk_usage', return_value=SimpleNamespace(free=0)):
            with self.assertRaises(OSError):
                backup_db(self.path, self.root/'low')
        self.assertFalse((self.root/'low/manifest.json').exists())
        with patch('storage.time.monotonic', side_effect=[0, 100]):
            with self.assertRaises(TimeoutError):
                backup_db(self.path, self.root/'timeout', timeout_seconds=1)
        self.assertFalse((self.root/'timeout/manifest.json').exists())

    def test_inventory_warning_does_not_modify_csv_or_checkpoint(self):
        csv = self.root/'active.csv'
        checkpoint = self.root/'active.csv.feeder-state.json'
        csv.write_bytes(b'header\npartial')
        checkpoint.write_bytes(b'{"offset":7}')
        with patch('storage.shutil.disk_usage', return_value=SimpleNamespace(free=20, total=100)):
            status = storage_status(self.path, 30)
        self.assertTrue(status['low_space'])
        self.assertFalse(status['automatic_deletion'])
        self.assertEqual(status['bytes_by_group']['csv'], 14)
        self.assertEqual(csv.read_bytes(), b'header\npartial')
        self.assertEqual(checkpoint.read_bytes(), b'{"offset":7}')

    def test_missing_or_non_ids_source_not_accepted(self):
        with self.assertRaises(FileNotFoundError):
            backup_db(self.root/'missing.db', self.root/'missingbackup')
        self.assertFalse((self.root/'missing.db').exists())
        plain = self.root/'plain.db'
        with closing(sqlite3.connect(plain)) as conn:
            conn.execute('CREATE TABLE example(x)')
        with self.assertRaises(ValueError):
            backup_db(plain, self.root/'invalid')
        self.assertFalse((self.root/'invalid/manifest.json').exists())

    def test_broken_foreign_key_not_marked_complete(self):
        self.conn.execute('PRAGMA foreign_keys=OFF')
        self.conn.execute("INSERT INTO Prediction VALUES ('orphan','Benign','{}','fixture','now')")
        self.conn.commit()
        with self.assertRaises(ValueError):
            backup_db(self.path, self.root/'broken')
        self.assertFalse((self.root/'broken/manifest.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
