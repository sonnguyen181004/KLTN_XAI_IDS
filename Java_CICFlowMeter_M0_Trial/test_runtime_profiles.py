"""Regression: per-model Java PCAP/CSV and optional real capture; no DB reset."""
import argparse, csv, io, json, os, shutil, time
import numpy as np
from pathlib import Path
os.environ.setdefault('JAVA_M0_TRIAL_TOKEN','profile-regression')
from service import manager
from run_java_live_m0 import list_interfaces
HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--live',action='store_true');a=ap.parse_args()
evidence={'passed':False,'models':{}}
imports=HERE/'output/imports';imports.mkdir(exist_ok=True)
shutil.copy2(HERE/'ss2.pcapng',imports/'profile_regression_ss2.pcapng')
try:
 for model in ('M0','M1'):
  result=manager.import_pcap('profile_regression_ss2.pcapng',model)
  assert result['rows']==6, result
  assert manager.status()['active_model']==model
  assert not any(r['prediction'] for r in manager.flows('M1' if model=='M0' else 'M0'))
  rows=manager.flows(model);valid=next(r for r in rows if r['prediction'])
  detail=manager.flow(valid['id'],model)
  shap=manager.explain_shap(valid['id'],model);lime=manager.explain_lime(valid['id'],model)
  assert shap['additivity_error']<1e-3
  evidence['models'][model]={'pcap_status':manager.status(model),'shap_error':shap['additivity_error'],'lime_status':lime['status']}
  buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=manager.names);w.writeheader();w.writerow(detail['features'])
  manager.import_csv('roundtrip.csv',buf.getvalue(),model=model)
  np.testing.assert_allclose(list(manager.flow(1,model)['features'].values()), list(detail['features'].values()), rtol=1e-12, atol=1e-12)
  assert manager.flow(1,model)['probabilities']==detail['probabilities']
  evidence['models'][model]['csv_roundtrip']='PASS'
  if a.live:
   devices=list_interfaces();iface=next(n for n,d in devices if 'WiFi' in d and 'Virtual' not in d)
   manager.start(iface,15,model)
   manager.thread.join(120)
   assert not manager.thread.is_alive(),manager.status(model)
   assert manager.phase=='finished' and manager.process.returncode==0,manager.status(model)
   assert manager.records,'No completed flows captured; cannot certify live prediction'
   assert any(r['prediction'] for r in manager.flows(model))
   evidence['models'][model]['live']=manager.status(model)
  print(model,evidence['models'][model],flush=True)
 evidence['passed']=True
finally:
 if manager.process and manager.process.poll() is None:
  manager.stop();manager.thread.join(60)
 (HERE/'java_runtime_integration_20261118.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
