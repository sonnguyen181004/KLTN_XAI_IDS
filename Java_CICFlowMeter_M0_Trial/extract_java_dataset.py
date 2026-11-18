"""Explicit offline Java profiles; never silently reinterpret CSV features.

m1-improved-2022 uses the author's pinned Java source. m0-current-unverified
retains the existing source, whose full historical M0 compatibility is unknown.
Output includes raw CSV, canonical finite features, rejected rows and manifest.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'RQ4_Retrain_Compare/scripts'))
from rq4_common import FEATURES, FEATURE_MAP
from run_java_live_m0 import java_environment

PIN='13a061520b862d605eea746c79ca4033b30d98fc'
URL='https://github.com/GintsEngelen/CICFlowMeter.git'


def run(args,**kwargs):
    p=subprocess.run([str(a) for a in args],capture_output=True,text=True,
                     encoding='utf-8',errors='replace',timeout=300,**kwargs)
    if p.returncode: raise RuntimeError(p.stdout[-2000:]+p.stderr[-2000:])
    return p.stdout


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def prepare():
    project=HERE/'output'/('profile_improved_'+PIN[:12]+'_win3')
    marker=project/'profile.json'
    if marker.exists():
        saved=json.loads(marker.read_text())
        if saved['commit']!=PIN:raise RuntimeError('Profile commit mismatch')
        for rel,h in saved['java_sha256'].items():
            if sha(project/rel)!=h:raise RuntimeError('Modified reference Java: '+rel)
        if sha(project/'build.gradle')!=saved['build_sha256']:raise RuntimeError('Modified reference build')
        if sha(project/'jnetpcap/win/jnetpcap-1.4.r1425/jnetpcap.jar')!=saved['native_jar_sha256']:raise RuntimeError('Modified jnetpcap jar')
        if sha(project/'jnetpcap/win/jnetpcap-1.4.r1500/jnetpcap.dll')!=saved['native_dll_sha256']:raise RuntimeError('Modified jnetpcap DLL')
        return project,saved
    if project.exists():raise RuntimeError('Incomplete profile exists; inspect before preparing again: '+str(project))
    repository=HERE/'output/improved_reference'
    if not (repository/'.git').exists():
        repository.parent.mkdir(parents=True,exist_ok=True)
        run(['git','clone',URL,repository])
    run(['git','-C',repository,'cat-file','-e',PIN+'^{commit}'])
    project.mkdir()
    archive=project/'source.tar'
    run(['git','-C',repository,'archive','--format=tar','-o',archive,PIN])
    with tarfile.open(archive) as f:f.extractall(project,filter='data')
    # Only packaging changes: local Windows jnetpcap jar and CLI args.
    build=(project/'build.gradle').read_text()
    dep="compile group: 'jnetpcap', name: 'jnetpcap', version:'1.4.r1425-1g'"
    assert build.count(dep)==1
    build=build.replace(dep,"compile files('jnetpcap/win/jnetpcap-1.4.r1425/jnetpcap.jar')")
    task="task exeCMD(type: JavaExec){"
    assert build.count(task)==1
    build=build.replace(task,task+"\n    args project.property('trialInput'), project.property('trialOutput')\n")
    build,count=re.subn(r'    args = \["/media/.*?\]', '', build, flags=re.S)
    assert count==1, 'Unexpected hard-coded upstream CLI arguments'
    (project/'build.gradle').write_text(build)
    saved={'repository':URL,'commit':PIN,'java_sha256':{p.relative_to(project).as_posix():sha(p) for p in (project/'src').rglob('*.java')},
           'build_sha256':sha(project/'build.gradle'),
           'native_jar_sha256':sha(project/'jnetpcap/win/jnetpcap-1.4.r1425/jnetpcap.jar'),
           'native_dll_sha256':sha(project/'jnetpcap/win/jnetpcap-1.4.r1500/jnetpcap.dll')}
    marker.write_text(json.dumps(saved,indent=2))
    return project,saved


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--profile',choices=['m1-improved-2022','m0-current-unverified'],required=True)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True,help='New directory to avoid overwriting a previous run')
    a=ap.parse_args();source=a.input.resolve();out=a.output_dir.resolve()
    if not source.is_file():raise SystemExit('PCAP not found: '+str(source))
    if out.exists():raise SystemExit('Output directory already exists; choose a new one')
    if a.profile=='m1-improved-2022':project,provenance=prepare()
    else:
        project=HERE/'upstream'
        provenance={'status':'not certified for historical M0 dataset',
                    'basic_flow_sha256':sha(project/'src/main/java/cic/cs/unb/ca/jnetpcap/BasicFlow.java')}
    out.mkdir(parents=True)
    converted=out/'input.pcap';rawdir=out/'raw';rawdir.mkdir()
    run([r'C:\Program Files\Wireshark\editcap.exe','-F','pcap',source,converted])
    log=run([project/'gradlew.bat','exeCMD','-PtrialInput='+str(converted),'-PtrialOutput='+str(rawdir),
             '--offline','--no-daemon','--console=plain'],cwd=project,env=java_environment())
    (out/'java.log').write_text(log,encoding='utf-8')
    raw=pd.read_csv(rawdir/'input.pcap_Flow.csv')
    missing=[n for n in FEATURES if FEATURE_MAP[n] not in raw]
    if missing:raise RuntimeError('Missing required columns: '+str(missing))
    x=raw[[FEATURE_MAP[n] for n in FEATURES]].copy();x.columns=FEATURES
    valid=np.isfinite(x.to_numpy()).all(axis=1)
    # No arbitrary NaN/inf imputation: dataset builder excludes nonfinite rows too.
    metadata=[n for n in ['Flow ID','Src IP','Src Port','Dst IP','Timestamp'] if n in raw]
    result=pd.concat([raw[metadata],x],axis=1)
    result.insert(0,'source_row',np.arange(1,len(result)+1))
    result.loc[valid].to_csv(out/'features.csv',index=False)
    result.loc[~valid].to_csv(out/'rejected.csv',index=False)
    manifest={'profile':a.profile,'provenance':provenance,'source':str(source),'source_sha256':sha(source),
              'raw_rows':len(raw),'accepted_rows':int(valid.sum()),'rejected_nonfinite_rows':int((~valid).sum()),
              'features':FEATURES,'time_units':'microseconds; no extra conversion',
              'limits':'2022 source provenance is known; exact dataset generation commit and rebuilt M1 training provenance are not certified',
              'runtime_modified':False}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('provenance','features')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
