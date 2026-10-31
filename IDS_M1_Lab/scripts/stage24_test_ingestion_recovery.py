"""Real HTTP/model/SQLite recovery tests with isolated temporary files and API.

Faults: lost ACK, network outage, failed transaction, concurrent duplicate POST,
process restart, partial CSV, schema error, replaced input and conflicting key.
Never uses the demo database or transmits capture traffic.
"""
import csv
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from unittest.mock import patch

import requests

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RQ3/'app'))
from feeder import run_feeder
from ingestion_checkpoint import checkpoint_lock, read_record


def main():
    with tempfile.TemporaryDirectory(prefix='ids_ingestion_recovery_') as folder:
        root = Path(folder)
        target = root/'isolated.db'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port = sock.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        env = {**os.environ,'IDS_DB_PATH':str(target),'PYTHONIOENCODING':'utf-8'}
        log = (root/'api.log').open('w',encoding='utf-8')
        proc = None
        def start():
            child = subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
                cwd=RQ3,env=env,stdout=log,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                for _ in range(160):
                    try:
                        if requests.get(url+'/health',timeout=1).json().get('ingestion_idempotency'):
                            return child
                    except (requests.RequestException,ValueError):
                        pass
                    if child.poll() is not None:
                        break
                    time.sleep(.25)
                raise RuntimeError((root/'api.log').read_text(encoding='utf-8'))
            except BaseException:
                child.terminate(); child.wait(timeout=20)
                raise
        def count(table='FlowRecord'):
            with closing(sqlite3.connect(target)) as conn:
                return conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
        try:
            proc = start()
            try:
                with checkpoint_lock(str(target)+'.worker'):
                    raise AssertionError('Active API must own the DB worker lock')
            except RuntimeError:
                pass
            with (RQ3/'data/clean_holdout_set.csv').open(encoding='utf-8-sig',newline='') as stream:
                source = list(csv.DictReader(stream))
            row = next(r for r in source if r['label_true']=='DoS attacks-Hulk')
            payload = {k:float(v) for k,v in row.items() if k not in ('flow_id','label_true')}
            def post(key, data=None):
                return requests.post(url+'/predict',json=payload if data is None else data,
                    headers={'Idempotency-Key':key},timeout=30)
            with ThreadPoolExecutor(max_workers=8) as pool:
                responses = list(pool.map(lambda _:post('concurrent-key'),range(8)))
            assert all(r.status_code==200 for r in responses),[r.text for r in responses]
            assert len({r.json()['flow_id'] for r in responses})==1
            assert sum(r.headers['Idempotency-Replayed']=='false' for r in responses)==1
            assert count()==count('Prediction')==count('AlertRecord')==1
            with closing(sqlite3.connect(target)) as conn:
                assert conn.execute('SELECT p.predicted_at > f.received_at FROM Prediction p JOIN FlowRecord f USING(flow_id)').fetchone()[0]
            assert requests.get(url+'/explain_queue_status',timeout=10).json()['n_queued']==1
            assert post('concurrent-key',{**payload,'Dst Port':12345}).status_code==409
            assert count()==1
            print('PASS concurrent duplicate, one prediction/alert/SHAP admission, key conflict',flush=True)

            # Abort in the middle of the DB bundle: no orphan flow/prediction.
            with closing(sqlite3.connect(target)) as conn, conn:
                conn.execute("CREATE TRIGGER fail_timing BEFORE INSERT ON Timing WHEN NEW.step='normalize' BEGIN SELECT RAISE(ABORT,'injected failure'); END")
            before=count()
            assert post('rollback-key').status_code==500
            assert count()==before and count('Prediction')==before
            with closing(sqlite3.connect(target)) as conn, conn:
                conn.execute('DROP TRIGGER fail_timing')
            assert post('rollback-key').status_code==200
            print('PASS atomic rollback and same-key retry',flush=True)

            watch = root/'live.csv'
            fields = list(payload)
            with watch.open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerow(payload)
            checkpoint=Path(str(watch)+'.feeder-state.json')
            def run(iterations=1):
                run_feeder(watch,url,.01,False,max_iterations=iterations,capture_timezone='+07:00')
            before=count()
            with patch('feeder.requests.post',side_effect=requests.ConnectionError('injected offline')):
                run()
            assert count()==before
            assert json.loads(checkpoint.read_text())['acknowledged_rows']==0
            original_post=requests.post
            sent=[]
            def lost_ack(*args,**kwargs):
                response=original_post(*args,**kwargs)
                response.raise_for_status(); sent.append(response.json()['flow_id'])
                raise requests.Timeout('injected lost ACK after commit')
            with patch('feeder.requests.post',side_effect=lost_ack):
                run()
            assert count()==before+1
            assert json.loads(checkpoint.read_text())['acknowledged_rows']==0
            # Actual API restart: receipt lives in DB, not process memory.
            proc.terminate(); proc.wait(timeout=20); proc=None
            # Model an interrupted queue/dispatch after the process has stopped.
            # No running worker can race with these isolated fixture changes.
            with closing(sqlite3.connect(target)) as conn, conn:
                interrupted_ids = [responses[0].json()['flow_id'], sent[0]]
                for fid,status in zip(interrupted_ids,['queued','pending_dispatch']):
                    conn.execute('DELETE FROM Reliability WHERE alert_id IN (SELECT alert_id FROM AlertRecord WHERE flow_id=?)',(fid,))
                    conn.execute('UPDATE AlertRecord SET explanation_status=? WHERE flow_id=?',(status,fid))
                conn.execute("UPDATE AlertRecord SET explanation_status='dropped_queue_full' WHERE flow_id IN (SELECT flow_id FROM FlowRecord WHERE ingestion_key='rollback-key')")
                conn.execute("DELETE FROM Reliability WHERE alert_id IN (SELECT a.alert_id FROM AlertRecord a JOIN FlowRecord f ON f.flow_id=a.flow_id WHERE f.ingestion_key='rollback-key')")
            proc=start()
            for _ in range(120):
                with closing(sqlite3.connect(target)) as conn:
                    recovered=conn.execute("SELECT COUNT(*) FROM AlertRecord WHERE flow_id IN (?,?) AND explanation_status='processed'",interrupted_ids).fetchone()[0]
                if recovered==2:
                    break
                time.sleep(.1)
            assert recovered==2
            recovery=requests.get(url+'/explain_queue_status',timeout=10).json()
            assert recovery['n_recovered']==2 and recovery['recovery_pending']==0
            with closing(sqlite3.connect(target)) as conn:
                assert conn.execute("SELECT COUNT(*) FROM AlertRecord WHERE explanation_status='dropped_queue_full'").fetchone()[0]==1
            print('PASS interrupted SHAP recovery after actual API restart, dropped policy preserved',flush=True)
            run()
            assert count()==before+1
            assert json.loads(checkpoint.read_text())['acknowledged_rows']==1
            with patch('feeder.requests.post',wraps=original_post) as wrapped:
                run(); assert wrapped.call_count==0
            print('PASS offline retry, lost ACK, API/feeder restart, durable cursor and deduplication',flush=True)

            output=io.StringIO(newline=''); csv.writer(output).writerow([payload[k] for k in fields])
            record=output.getvalue()
            with watch.open('a',encoding='utf-8',newline='') as stream:
                stream.write('\n'+record.rstrip('\r\n'))
            run(); assert count()==before+1
            with watch.open('a',encoding='utf-8',newline='') as stream:
                stream.write('\r\n')
            run(); assert count()==before+2  # Identical feature row is a new captured flow.
            assert json.loads(checkpoint.read_text())['acknowledged_rows']==2
            with checkpoint_lock(checkpoint):
                try:
                    run()
                    raise AssertionError('Second feeder must be refused')
                except RuntimeError as exc:
                    assert 'feeder khác' in str(exc)
            print('PASS partial row, blank line, identical distinct flow, exclusive checkpoint lock',flush=True)

            # Complete bad row cannot be silently skipped to later valid rows.
            with watch.open('a',encoding='utf-8',newline='') as stream:
                csv.writer(stream).writerow(['bad']*len(fields))
            try:
                run()
                raise AssertionError('422 must stop with cursor unchanged')
            except RuntimeError as exc:
                assert '422' in str(exc)
            assert json.loads(checkpoint.read_text())['acknowledged_rows']==2
            assert count()==before+2
            invalid=root/'nonfinite.csv'
            with invalid.open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader(); writer.writerow({**payload,'Dst Port':'nan'})
            try:
                run_feeder(invalid,url,.01,False,max_iterations=1)
                raise AssertionError('Non-finite input must not be retried forever')
            except ValueError as exc:
                assert 'NaN/Infinity' in str(exc)
            assert json.loads(Path(str(invalid)+'.feeder-state.json').read_text())['acknowledged_rows']==0
            watch.write_text('replacement\n',encoding='utf-8')
            try:
                run()
                raise AssertionError('Truncated source must be refused')
            except RuntimeError as exc:
                assert 'cắt ngắn' in str(exc)
            # Parser supports quoted multiline and waits for a terminating newline.
            stream=io.BytesIO(b'a,"b\nc"\nnext,partial')
            assert read_record(stream)==['a','b\nc']
            cursor=stream.tell(); assert read_record(stream) is None and stream.tell()==cursor
            stream=io.BytesIO(b'a,b\r\r\n1,2\r\r\n')
            assert read_record(stream)==['a','b'] and read_record(stream)==['1','2']
            print('PASS permanent validation error, truncation detection, multiline CSV parser',flush=True)
            print('ALL INGESTION RECOVERY CHECKS PASS',flush=True)
        finally:
            if proc is not None:
                proc.terminate(); proc.wait(timeout=20)
            log.close()


if __name__=='__main__':
    main()
