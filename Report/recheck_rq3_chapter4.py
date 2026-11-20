"""Run isolated regression checks and offline PCAP replay for report evidence."""
from pathlib import Path
import subprocess,sys,json,time
R=Path(__file__).resolve().parents[1]; O=R/'Report/chapter4_assets'; O.mkdir(exist_ok=True)
tests=[('stage26_test_capture_lifecycle.py',True),('stage27_test_feeder_faults.py',False),('stage29_test_capture_limits.py',True),('stage15_test_lime_validity.py',False),('stage14_test_dashboard_redesign.py',False),('stage36_test_capture_supervisor.py',False),('stage37_test_capture_control_ui.py',False)]
results=json.loads((O/'rq3_test_results.json').read_text()) if (O/'rq3_test_results.json').exists() else []
for name,capture in tests:
    if any(r['script']==name and r['exit_code']==0 for r in results): continue
    exe=str(R/'RQ3_IDS_System/.venv_capture/Scripts/python.exe') if capture else sys.executable
    start=time.perf_counter()
    p=subprocess.run([exe,'-X','utf8',str(R/'RQ3_IDS_System/scripts'/name)],cwd=R,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    (O/(name+'.log')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
    results.append({'script':name,'exit_code':p.returncode,'seconds':time.perf_counter()-start})
    (O/'rq3_test_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(results[-1],flush=True)
if (O/'pcap_recheck.json').exists():
    print('Existing PCAP evidence retained; no duplicate run',flush=True)
    sys.exit(0)
p=subprocess.run([sys.executable,'-X','utf8',str(R/'RQ3_IDS_System/scripts/stage21_compare_capture_versions.py'),'--output',str(O/'pcap_recheck.json'),'--baseline','project-v2','--candidate','project-v3'],cwd=R,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
(O/'pcap_recheck.log').write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
print('PCAP exit',p.returncode,flush=True)
