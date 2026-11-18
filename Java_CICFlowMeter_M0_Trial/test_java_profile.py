"""Positive bulk/URG/idle and UDP cases for the pinned Java dataset profile."""
import json
from pathlib import Path
import sys
import uuid

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent

if '--fixture-worker' in sys.argv:
    from scapy.all import Ether, IP, TCP, UDP, Raw, wrpcap
    from decimal import Decimal
    packets=[]
    def add(port,t,back=False,flags='A',size=0,udp=False):
        src,dst=('192.0.2.2','192.0.2.1') if back else ('192.0.2.1','192.0.2.2')
        sport,dport=(443,port) if back else (port,443)
        transport=UDP(sport=sport,dport=dport) if udp else TCP(sport=sport,dport=dport,flags=flags,window=2000 if back else 1000)
        p=Ether()/IP(src=src,dst=dst)/transport
        if size:p/=Raw(b'a'*size)
        p.time=Decimal('1700000000')+Decimal(str(t));packets.append(p)
    for i in range(4):add(41001,i/10,flags='PA',size=10)
    for i in range(4):add(41001,.5+i/10,True,'PA',20)
    add(41001,.9,flags='RA')
    add(41002,10,flags='S')
    add(41002,10.1,flags='PAUC',size=10)
    add(41002,10.2,True,'PAUE',20)
    add(41002,10.3,flags='RA')
    add(41003,20);add(41003,20.1,True);add(41003,26.1);add(41003,26.2,True,'RA')
    add(41004,30,size=10,udp=True);add(41004,30.1,True,size=20,udp=True)
    wrpcap(sys.argv[-1],packets)
    sys.exit(0)

import numpy as np
import pandas as pd
from extract_java_dataset import prepare,run
from run_java_live_m0 import java_environment

out=HERE/'output'/('profile_positive_'+uuid.uuid4().hex[:8]);out.mkdir()
pcap=out/'positive.pcap'
run([ROOT/'RQ3_IDS_System/.venv_capture/Scripts/python.exe',__file__,'--fixture-worker',pcap])
project,provenance=prepare()
log=run([project/'gradlew.bat','exeCMD','-PtrialInput='+str(pcap),'-PtrialOutput='+str(out),
         '--offline','--no-daemon','--console=plain'],cwd=project,env=java_environment())
(out/'java.log').write_text(log,encoding='utf-8')
d=pd.read_csv(out/'positive.pcap_Flow.csv')
expectations={41001:{'Fwd Bytes/Bulk Avg':40,'Fwd Packet/Bulk Avg':4,'Fwd Bulk Rate Avg':133,
                    'Bwd Bytes/Bulk Avg':80,'Bwd Packet/Bulk Avg':4,'Bwd Bulk Rate Avg':266},
              41002:{'Fwd URG Flags':1,'Bwd URG Flags':1,'URG Flag Count':2,
                     'Fwd PSH Flags':1,'Bwd PSH Flags':1,'PSH Flag Count':2,
                     'CWR Flag Count':1,'ECE Flag Count':1,'SYN Flag Count':1,'RST Flag Count':1},
              41003:{'Active Mean':100000,'Active Max':100000,'Idle Mean':6000000,'Idle Max':6000000},
              41004:{'Protocol':17,'Total Length of Fwd Packet':10,'Total Length of Bwd Packet':20,
                     'Fwd Header Length':8,'Bwd Header Length':8,'PSH Flag Count':0}}
checks=[]
for port,values in expectations.items():
    rows=d[d['Src Port']==port]
    if len(rows)!=1:raise AssertionError((port,len(rows)))
    r=rows.iloc[0]
    for name,wanted in values.items():
        actual=float(r[name]);checks.append({'port':port,'feature':name,'expected':wanted,'actual':actual,
                                            'pass':bool(np.isclose(actual,wanted,rtol=1e-6,atol=1e-6))})
result={'source_commit':provenance['commit'],'artifacts':str(out.relative_to(ROOT)),
        'checks':checks,'pass':all(c['pass'] for c in checks)}
(HERE/'java_profile_positive_tests_20261118.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
assert result['pass']
