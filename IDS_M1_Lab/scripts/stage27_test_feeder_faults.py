"""Feeder boundary faults, temporary files; no API or production DB."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import feeder
from ingestion_checkpoint import save_checkpoint


class FeederFaults(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ids_feeder_fault_')
        self.csv = Path(self.tmp.name) / 'input.csv'
        self.csv.write_text('Dst Port\n443\n', encoding='utf-8')
        self.state = Path(str(self.csv) + '.feeder-state.json')
        self.keys = []

    def tearDown(self):
        self.tmp.cleanup()

    def response(self, *args, **kwargs):
        key = kwargs['headers']['Idempotency-Key']
        self.keys.append(key)
        return Mock(status_code=200, headers={'Idempotency-Key': key}, json=lambda: {
            'flow_id': 'confirmed-flow', 'predicted_label': 'Benign',
            'is_alert': False, 'explanation_status': None})

    def run_once(self, post):
        with patch('feeder.requests.post', side_effect=post), patch('feeder.time.sleep'):
            feeder.run_feeder(self.csv, 'http://127.0.0.1:1', .01, False, 1, '+07:00')

    def test_invalid_ack_retries_same_key(self):
        for body in ([], {}, {'flow_id': 'f', 'predicted_label': 'Benign'},
                     {'flow_id': 'f', 'predicted_label': 'Benign', 'is_alert': 'false', 'explanation_status': None}):
            def malformed(*a, **kw):
                result = self.response(*a, **kw)
                result.json = lambda: body
                return result
            self.run_once(malformed)
            self.assertEqual(json.loads(self.state.read_text())['acknowledged_rows'], 0)
        self.run_once(self.response)
        self.assertEqual(len(set(self.keys)), 1)
        self.assertEqual(json.loads(self.state.read_text())['acknowledged_rows'], 1)

    def test_transient_http_preserves_cursor(self):
        for status in (408, 425, 429, 500, 503):
            self.run_once(lambda *a, **kw: Mock(status_code=status))
            self.assertEqual(json.loads(self.state.read_text())['acknowledged_rows'], 0)
        self.run_once(self.response)
        self.assertEqual(json.loads(self.state.read_text())['acknowledged_rows'], 1)

    def test_checkpoint_failure_after_ack_reuses_key_on_restart(self):
        def fail_ack_save(path, state):
            if state['acknowledged_rows']:
                raise OSError('injected checkpoint disk failure')
            save_checkpoint(path, state)
        with patch('feeder.save_checkpoint', side_effect=fail_ack_save):
            with self.assertRaises(OSError):
                self.run_once(self.response)
        self.assertEqual(json.loads(self.state.read_text())['acknowledged_rows'], 0)
        self.run_once(self.response)
        self.assertEqual(len(set(self.keys)), 1)
        self.assertEqual(json.loads(self.state.read_text())['acknowledged_rows'], 1)

    def test_bad_idempotency_ack_stops_without_advancing(self):
        with self.assertRaises(RuntimeError):
            self.run_once(lambda *a, **kw: Mock(status_code=200, headers={}))
        self.assertEqual(json.loads(self.state.read_text())['acknowledged_rows'], 0)

    def test_invalid_poll_interval_rejected(self):
        for value in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                feeder.run_feeder(self.csv, 'http://127.0.0.1:1', value, False, 1)


class QueueLimits(unittest.TestCase):
    def test_recovery_does_not_starve_under_continuous_new_tasks(self):
        from explain_queue import ExplainQueue
        with patch('explain_queue.threading.Thread.start'):
            q = ExplainQueue(200, None, None, None, None)
        for i in range(20):
            q._q.put_nowait({'id': i})
        with patch.object(q, '_take_recovery', return_value={'id': 'recovery'}) as take:
            for _ in range(10):
                _, from_memory = q._next_task()
                self.assertTrue(from_memory)
                q._q.task_done()
            task, from_memory = q._next_task()
            self.assertEqual(task['id'], 'recovery')
            self.assertFalse(from_memory)
            self.assertEqual(q.qsize(), 10)
            self.assertEqual(take.call_count, 1)

    def test_unlimited_queue_configuration_refused(self):
        from explain_queue import ExplainQueue
        for size in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                ExplainQueue(size, None, None, None, None)

    def test_queue_200_marks_overflow_without_removing_accepted_tasks(self):
        from explain_queue import ExplainQueue
        with patch('explain_queue.threading.Thread.start'):
            q = ExplainQueue(200, None, None, None, None)
        states = {}
        with patch.object(q, '_set_status', side_effect=lambda key,status: states.update({key: status})):
            for i in range(200):
                self.assertEqual(q.submit(str(i), str(i), 'fixture', None), 'queued')
            self.assertEqual(q.submit('overflow', 'overflow', 'fixture', None), 'dropped_queue_full')
        self.assertEqual(q.qsize(), 200)
        self.assertEqual(q.n_dropped, 1)
        self.assertEqual(states['overflow'], 'dropped_queue_full')
        self.assertEqual(sum(v == 'queued' for v in states.values()), 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
