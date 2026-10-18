"""Re-extract both user PCAPs into isolated runs; compare model/SHAP/LIME in memory.

No API requests or production DB writes. Full CSVs are temporary. JSON output
contains per-run totals and matched-flow changes; no packet payloads or IPs.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

import numpy as np
import yaml

RQ3=Path(__file__).resolve().parents[1]
ROOT=RQ3.parent
sys.path.insert(0,str(RQ3/'app'))
from predict import Detector
from feeder import row_to_payload
from normalize import normalize_flow
from explain_shap import ShapExplainer
from explain_lime import LimeExplainer


def key(row):
    return tuple(row[n] for n in ('src_ip','dst_ip','src_port','dst_port','protocol','timestamp'))


def main(output, baseline='legacy', candidate='project'):
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite evidence: {output}')
    if baseline == candidate:
        raise ValueError('Choose different baseline and candidate modes')
    cfg=yaml.safe_load((RQ3/'config.yaml').read_text(encoding='utf-8'))
    detector=Detector(ROOT/cfg['paths']['model'],ROOT/cfg['paths']['label_encoder'])
    shap=ShapExplainer(detector.model,detector.class_names)
    lime=LimeExplainer(detector.model,detector.feature_names,detector.class_names,
        np.load(RQ3/'data/lime_background.npy'),cfg['lime'],cfg['seed'])
    report=dict(model_version=detector.model_version, baseline_mode=baseline, candidate_mode=candidate,
        warning='No confirmed ground truth; changes are not accuracy/FPR measurements. LIME uses identical per-pair diagnostic seed, not saved DB alert IDs.',runs=[])
    report['code_sha256'] = {name: hashlib.sha256((RQ3/name).read_bytes()).hexdigest() for name in
        ('app/capture_adapter.py', 'app/capture_lifecycle.py', 'scripts/run_live_capture.py',
         'scripts/stage21_compare_capture_versions.py')}
    with tempfile.TemporaryDirectory(prefix='ids_capture_comparison_') as folder:
        for name in ('tesst2.pcapng','test.pcapng'):
            path=ROOT/name
            if not path.exists():
                report['runs'].append(dict(file=name,skipped='PCAP not found'))
                continue
            variants={}
            for mode in (baseline,candidate):
                target=Path(folder)/(name+'.'+mode+'.csv')
                proc=subprocess.run([str(RQ3/'.venv_capture/Scripts/python.exe'),
                    str(RQ3/'scripts/run_live_capture.py'),'--pcap-input',str(path),
                    '--output',str(target),'--extractor',mode],capture_output=True,
                    text=True,encoding='utf-8',errors='replace',timeout=120,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if proc.returncode:
                    raise RuntimeError(proc.stdout+proc.stderr)
                # Exact repeat with a fresh output, not a feeder/checkpoint replay.
                repeat = target.with_suffix('.repeat.csv')
                command = [str(RQ3/'.venv_capture/Scripts/python.exe'),
                    str(RQ3/'scripts/run_live_capture.py'),'--pcap-input',str(path),
                    '--output',str(repeat),'--extractor',mode]
                check = subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                    errors='replace', timeout=120, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if check.returncode or target.read_bytes() != repeat.read_bytes():
                    raise AssertionError(f'Non-reproducible extraction: {name}/{mode}: {check.stderr}')
                with target.open(encoding='utf-8-sig',newline='') as stream:
                    records=list(csv.DictReader(stream))
                samples=[]
                for row in records:
                    x=normalize_flow(row_to_payload(row,list(row),True),detector.feature_names)
                    prediction=detector.predict_flow(x)
                    sample = dict(key=key(row),row=row,x=x,prediction=prediction)
                    label = prediction['predicted_label']
                    result = dict(predicted_label=label, probability=prediction['probabilities'][label])
                    if label != 'Benign':
                        token = hashlib.sha256(json.dumps(sample['key']).encode()).hexdigest()[:16]
                        s = shap.explain(x, label)
                        l = lime.explain(x, label, int(token[:8],16))
                        result.update(shap_top5=s['top_k'], shap_additivity_error=s['additivity_error'],
                                      lime_status=l['status'], lime_diagnostics=l['diagnostics'])
                    sample['explanation'] = result
                    samples.append(sample)
                variants[mode]=samples
            def summarize(samples):
                return dict(flow_count=len(samples), labels=dict(Counter(s['prediction']['predicted_label'] for s in samples)),
                    packet_total=sum(float(s['row']['tot_fwd_pkts'])+float(s['row']['tot_bwd_pkts']) for s in samples),
                    repeat_csv_identical=True,
                    end_reasons=dict(Counter(s['row'].get('flow_end_reason','not_recorded') for s in samples)),
                    alert_xai=[dict(flow_index=i, **s['explanation']) for i,s in enumerate(samples) if s['prediction']['predicted_label'] != 'Benign'],
                    extractor_versions=sorted({s['row'].get('extractor_version','python-cicflowmeter-0.5.0-legacy') for s in samples}))
            run=dict(file=name,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                comparison_run_id=str(uuid.uuid4()),baseline=summarize(variants[baseline]),
                candidate=summarize(variants[candidate]),matched_flows=[],ambiguous_or_unmatched_keys=0)
            if baseline != 'legacy' and candidate != 'legacy':
                oracle = subprocess.run([str(RQ3/'.venv_capture/Scripts/python.exe'), '-c',
                    'import sys; from scapy.all import PcapReader,IP,TCP,UDP; r=PcapReader(sys.argv[1]); print(sum(IP in p and (TCP in p or UDP in p) for p in r)); r.close()', str(path)],
                    capture_output=True,text=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                oracle.check_returncode()
                run['supported_packet_oracle'] = int(oracle.stdout.strip())
                if not run['baseline']['packet_total'] == run['candidate']['packet_total'] == run['supported_packet_oracle']:
                    raise AssertionError(f'Packet conservation failed for {name}')
            groups={}
            for mode,samples in variants.items():
                groups[mode]=defaultdict(list)
                for sample in samples:
                    groups[mode][sample['key']].append(sample)
            for k in groups[baseline].keys() | groups[candidate].keys():
                old,new=groups[baseline].get(k,[]),groups[candidate].get(k,[])
                if len(old)!=1 or len(new)!=1:
                    run['ambiguous_or_unmatched_keys']+=1
                    continue
                old,new=old[0],new[0]
                token=hashlib.sha256(json.dumps(k).encode()).hexdigest()[:16]
                seed=int(token[:8],16)
                changed=[n for n in detector.feature_names
                         if not np.isclose(float(old['x'][n].iloc[0]),float(new['x'][n].iloc[0]),rtol=1e-10,atol=1e-8)]
                pair=dict(pair_id=token,changed_features=changed)
                for mode,sample in [('baseline',old),('candidate',new)]:
                    pair[mode]=sample['explanation']
                pair['label_changed']=pair['baseline']['predicted_label']!=pair['candidate']['predicted_label']
                run['matched_flows'].append(pair)
            run['matched_flows'].sort(key=lambda x:x['pair_id'])
            run['matched_count']=len(run['matched_flows'])
            run['changed_labels']=sum(p['label_changed'] for p in run['matched_flows'])
            run['changed_vectors']=sum(bool(p['changed_features']) for p in run['matched_flows'])
            report['runs'].append(run)
            print(name,run['baseline']['labels'],'=>',run['candidate']['labels'],
                  'matched',run['matched_count'],'label changes',run['changed_labels'],flush=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WROTE',output,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    modes = ['legacy','project-v1','project-v2','project-v3','project','train-candidate']
    parser.add_argument('--baseline',choices=modes,default='legacy')
    parser.add_argument('--candidate',choices=modes,default='project')
    args=parser.parse_args()
    main(args.output,args.baseline,args.candidate)
