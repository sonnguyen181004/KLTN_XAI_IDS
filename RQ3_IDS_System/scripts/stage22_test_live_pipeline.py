"""Bounded passive capture on an explicitly named interface and isolated API/DB.

Uses natural local host traffic only. No attack generation, no production DB
writes. Raw CSV is temporary; final JSON stores counters and checks, not IPs.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid

import requests

RQ3=Path(__file__).resolve().parents[1]


def main(interface,seconds,output):
    with tempfile.TemporaryDirectory(prefix='ids_live_validation_') as folder:
        target=Path(folder)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}'
        env={**os.environ,'IDS_DB_PATH':str(target/'live-test.db'),'IDS_API_URL':url,
             'PYTHONIOENCODING':'utf-8'}
        children=[]
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        result=dict(test_run_id=str(uuid.uuid4()),interface=interface,duration_seconds=seconds,
                    isolated_database=True,generated_network_traffic=False)
        def get(path):
            response=requests.get(url+path,timeout=10)
            response.raise_for_status()
            return response.json()
        try:
            with (target/'api.log').open('w',encoding='utf-8') as api_log, \
                 (target/'feeder.log').open('w',encoding='utf-8') as feeder_log, \
                 (target/'capture.log').open('w',encoding='utf-8') as capture_log:
                api=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
                    cwd=RQ3,env=env,stdout=api_log,stderr=subprocess.STDOUT,creationflags=creationflags)
                children.append(api)
                for _ in range(160):
                    try:
                        health=get('/health')
                        break
                    except requests.RequestException:
                        if api.poll() is not None:
                            raise RuntimeError((target/'api.log').read_text(encoding='utf-8'))
                        time.sleep(.25)
                else:
                    raise RuntimeError('Isolated API startup timeout')
                result['model_version']=health['model_version']
                csv_path=target/'live_validation.csv'
                feeder=subprocess.Popen([sys.executable,'-u','app/feeder.py','--watch',str(csv_path),
                    '--convert-units','--capture-timezone','+07:00'],cwd=RQ3,env=env,stdout=feeder_log,
                    stderr=subprocess.STDOUT,creationflags=creationflags)
                children.append(feeder)
                capture=subprocess.Popen([str(RQ3/'.venv_capture/Scripts/python.exe'),'-u',
                    str(RQ3/'scripts/run_live_capture.py'),'--interface',interface,'--seconds',str(seconds),
                    '--output',str(csv_path)],cwd=RQ3,env=env,stdout=capture_log,
                    stderr=subprocess.STDOUT,creationflags=creationflags)
                children.append(capture)
                deadline=time.monotonic()+seconds+30
                during=0
                while_sniffing=0
                last_progress=time.monotonic()
                while capture.poll() is None and time.monotonic()<deadline:
                    if feeder.poll() is not None:
                        raise RuntimeError('Feeder stopped during capture:\n'+(target/'feeder.log').read_text(encoding='utf-8',errors='replace'))
                    count=get('/flows?source=feeder_live&limit=1')['count']
                    during=max(during,count)
                    capture_text=(target/'capture.log').read_text(encoding='utf-8',errors='replace')
                    if '[capture] receiving_started' in capture_text and '[capture] receiving_stopped' not in capture_text:
                        while_sniffing=max(while_sniffing,count)
                    if time.monotonic()-last_progress>=15:
                        print(f'LIVE progress: {during} flows received while capture runs',flush=True)
                        last_progress=time.monotonic()
                    time.sleep(.5)
                if capture.poll() is None:
                    raise RuntimeError('Bounded capture failed to stop')
                if capture.returncode:
                    raise RuntimeError((target/'capture.log').read_text(encoding='utf-8'))
                result['flows_received_before_capture_exit']=during
                result['flows_received_while_sniffing']=while_sniffing
                with csv_path.open(encoding='utf-8-sig',newline='') as stream:
                    rows=list(csv.DictReader(stream))
                if not rows:
                    raise RuntimeError('No completed IPv4 TCP/UDP flows observed; live path not validated')
                deadline=time.monotonic()+max(30,len(rows)*.2)
                while time.monotonic()<deadline:
                    if feeder.poll() is not None:
                        raise RuntimeError('Feeder stopped after capture:\n'+(target/'feeder.log').read_text(encoding='utf-8',errors='replace'))
                    data=get('/flows?source=feeder_live&limit=1000')
                    if data['count']==len(rows):
                        break
                    time.sleep(.25)
                if data['count'] != len(rows):
                    raise RuntimeError(f"CSV/API mismatch: {len(rows)}/{data['count']}; feeder_exit={feeder.poll()}\n" +
                        (target/'feeder.log').read_text(encoding='utf-8',errors='replace')[-12000:])
                listed=list(data['flows'])
                while len(listed)<data['count']:
                    listed.extend(get(f'/flows?source=feeder_live&limit=1000&offset={len(listed)}')['flows'])
                details=[get('/flows/'+r['flow_id']) for r in listed]
                expected=sorted(float(r['flow_duration'])*1e6 for r in rows)
                observed=sorted(d['features']['Flow Duration'] for d in details)
                assert all(abs(a-b)<1e-5 for a,b in zip(expected,observed))
                assert all(len(d['probabilities'])==15 and len(d['features'])==78 for d in details)
                versions = {r['extractor_version'] for r in rows}
                assert versions == {'rq3-cfm-0.5.0-fixes-v2'}
                assert all(d['extractor_version'] in versions for d in details)
                assert all(d['src_ip'] and d['dst_ip'] for d in details)
                counters=re.search(r'accepted_packets=(\d+) exported_packets=(\d+) exported_flows=(\d+)',
                    (target/'capture.log').read_text(encoding='utf-8'))
                assert counters,'Capture counter missing'
                accepted,exported,flows=map(int,counters.groups())
                csv_packets=sum(int(r['tot_fwd_pkts'])+int(r['tot_bwd_pkts']) for r in rows)
                assert accepted==exported==csv_packets and flows==len(rows)
                from collections import Counter
                result.update(accepted_packets=accepted,exported_packets=exported,csv_packet_total=csv_packets,
                    csv_flows=len(rows),api_flows=data['count'],labels=dict(Counter(d['predicted_label'] for d in details)),
                    feature_columns=78,class_probabilities=15,metadata_version_and_ip_pass=True,
                    duration_unit_conversion_pass=True,queue=get('/explain_queue_status'))
                # This validates display logic with the actual live run via HTTP.
                from unittest.mock import patch
                from streamlit.testing.v1 import AppTest
                with patch.dict(os.environ,{'IDS_API_URL':url}):
                    app=AppTest.from_file(str(RQ3/'app/dashboard.py')).run(timeout=40)
                    assert not app.exception,app.exception
                    assert app.session_state['selected_flow'] in {d['flow_id'] for d in details}
                    assert any('Bộ trích xuất: rq3-cfm-0.5.0-fixes-v2' in c.value for c in app.caption)
                result['live_run_dashboard_app_test_pass']=True
                log=(target/'feeder.log').read_text(encoding='utf-8')
                assert 'KHÔNG GỬI ĐƯỢC' not in log and 'LỖI ' not in log,log
                result['feeder_error_count']=0
                print('PASS LIVE',json.dumps(result,ensure_ascii=False),flush=True)
        finally:
            for proc in reversed(children):
                if proc.poll() is None:
                    proc.terminate()
            for proc in children:
                proc.wait(timeout=15)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--interface',required=True)
    parser.add_argument('--seconds',type=int,default=20)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not 5<=args.seconds<=120:
        parser.error('Validation capture must be bounded to 5–120 seconds')
    main(args.interface,args.seconds,args.output)
