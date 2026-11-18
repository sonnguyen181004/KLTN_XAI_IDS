"""Isolated Java directional-PSH fix; never changes the dashboard's upstream build."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT/'RQ4_Retrain_Compare/scripts'))
from rq4_common import FEATURE_MAP
from run_java_live_m0 import java_environment


def run(args, **kwargs):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=240, **kwargs)
    if p.returncode:
        raise RuntimeError(p.stdout[-3000:]+p.stderr[-3000:])
    return p.stdout


out = HERE/'output'/('psh_fix_'+uuid.uuid4().hex[:8])
out.mkdir(parents=True)
original = HERE/'upstream'
fixed = out/'java_psh_fixed'
shutil.copytree(original, fixed, ignore=shutil.ignore_patterns('.git', '.gradle', '.gradle-home', 'build', 'logs'))
relative = Path('src/main/java/cic/cs/unb/ca/jnetpcap/BasicFlow.java')
source_hash = hashlib.sha256((original/relative).read_bytes()).hexdigest()
source = (fixed/relative).read_text(encoding='utf-8')
anchor = 'public void addPacket(BasicPacketInfo packet){'
assert source.count(anchor) == 1
insertion = '''
        // Count subsequent packets; firstPacket already counts the first one.
        // Use the same direction rule as packet statistics in addPacket.
        if (packet.hasFlagPSH()) {
            if (!isBidirectional || Arrays.equals(this.src, packet.getSrc())) {
                this.fPSH_cnt++;
            } else {
                this.bPSH_cnt++;
            }
        }
'''
patched = source.replace(anchor, anchor+insertion)
(fixed/relative).write_text(patched, encoding='utf-8')
import difflib
(HERE/'directional_psh_fix.patch').write_text(''.join(difflib.unified_diff(
    source.splitlines(True), patched.splitlines(True), fromfile='a/'+relative.as_posix(),
    tofile='b/'+relative.as_posix())), encoding='utf-8')

fixture = out/'fixture.pcap'
run([ROOT/'RQ3_IDS_System/.venv_capture/Scripts/python.exe', HERE/'audit_lab_and_semantics.py', '--fixture', fixture])
pcap = out/'ss2.pcap'
run([r'C:\Program Files\Wireshark\editcap.exe', '-F', 'pcap', HERE/'ss2.pcapng', pcap])
report = {'scope': 'isolated experiment; runtime and model artifacts unchanged',
          'source_java_sha256': source_hash,
          'fixed_java_sha256': hashlib.sha256((fixed/relative).read_bytes()).hexdigest(),
          'pcap_sha256': hashlib.sha256((HERE/'ss2.pcapng').read_bytes()).hexdigest(),
          'artifacts': str(out.relative_to(ROOT)), 'cases': {}}
models = {}
for name, folder, filename, encoder in [
    ('M0', 'RQ1_Model_Training_xboost/saved_models', 'best_xgboost_model.pkl', 'label_encoder.pkl'),
    ('M1', 'IDS_M1_Lab/models', 'm1_xgboost_model.pkl', 'm1_label_encoder.pkl')]:
    path = ROOT/folder/filename
    models[name] = (joblib.load(path), joblib.load(path.with_name(encoder)).classes_)
    report[name+'_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()

for case, capture in [('fixture', fixture), ('ss2', pcap)]:
    frames = {}
    for version, project in [('original', original), ('fixed', fixed)]:
        dest = out/(case+'_'+version)
        dest.mkdir()
        log = run([project/'gradlew.bat', 'exeCMD', '-PtrialInput='+str(capture),
                   '-PtrialOutput='+str(dest), '--offline', '--no-daemon', '--console=plain'],
                  cwd=project, env=java_environment())
        (dest/'java.log').write_text(log, encoding='utf-8')
        frames[version] = pd.read_csv(dest/(capture.name+'_Flow.csv'))
    a, b = frames['original'], frames['fixed']
    identity = ['Src IP', 'Dst IP', 'Src Port', 'Dst Port', 'Protocol', 'Timestamp']
    assert a[identity].equals(b[identity]), 'Flow identity/order changed'
    changed = [n for n,c in FEATURE_MAP.items() if not np.allclose(a[c], b[c], equal_nan=True)]
    assert set(changed) <= {'Fwd PSH Flags', 'Bwd PSH Flags'}, changed
    item = {'rows': len(a), 'changed_features': changed, 'models': {}}
    if case == 'fixture':
        row = b[b['Src Port']==40001].iloc[0]
        assert row[FEATURE_MAP['Fwd PSH Flags']] == 3
        assert row[FEATURE_MAP['Bwd PSH Flags']] == 2
        assert row[FEATURE_MAP['PSH Flag Cnt']] == 5
        item['first_packet_psh_not_double_counted'] = True
    else:
        ssh = (b['Protocol']==6) & (b['Dst Port']==22)
        main = ssh & (b['Flow Duration'] > 1_000_000)
        assert int(main.sum()) == 3
        for feature, expected in [('Fwd PSH Flags', 16), ('Bwd PSH Flags', 15), ('PSH Flag Cnt',31)]:
            assert (b.loc[main, FEATURE_MAP[feature]] == expected).all(), feature
        item['psh_rows'] = b.loc[ssh, ['Src Port', 'Flow Duration']+[FEATURE_MAP[n] for n in
            ['Fwd PSH Flags','Bwd PSH Flags','PSH Flag Cnt']]].to_dict('records')
        for model_name, (model, classes) in models.items():
            item['models'][model_name] = {}
            for version, frame in frames.items():
                names = list(model.feature_names_in_)
                x = frame.loc[ssh, [FEATURE_MAP[n] for n in names]].copy()
                x.columns = names
                assert np.isfinite(x.to_numpy()).all()
                probs = model.predict_proba(x)
                labels = classes[probs.argmax(axis=1)]
                item['models'][model_name][version] = [dict(
                    src_port=int(frame.loc[idx,'Src Port']), duration_us=float(frame.loc[idx,'Flow Duration']),
                    label=str(label), confidence=float(p.max()),
                    ssh_probability=float(p[list(classes).index('SSH-Bruteforce')]))
                    for idx,label,p in zip(x.index,labels,probs)]
    report['cases'][case] = item
assert hashlib.sha256((original/relative).read_bytes()).hexdigest() == source_hash
report['checks_passed'] = True
(HERE/'directional_psh_fix_20261118.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
