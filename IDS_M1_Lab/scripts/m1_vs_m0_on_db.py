"""So M0 và M1 trên mọi flow đã lưu trong DB của lab (đọc từ bản sao, không sửa DB)."""
import sys, json, shutil, sqlite3, tempfile, collections
from pathlib import Path
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'IDS_M1_Lab' / 'app'))
from predict import Detector
M0 = Detector(REPO / 'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl', REPO / 'RQ1_Model_Training_xboost/saved_models/label_encoder.pkl')
M1 = Detector(REPO / 'IDS_M1_Lab/models/m1_xgboost_model.pkl', REPO / 'IDS_M1_Lab/models/m1_label_encoder.pkl')
assert M0.feature_names == M1.feature_names, 'hai model dùng khác tên/thứ tự đặc trưng'
tmp = Path(tempfile.mkdtemp()) / 'db.sqlite'
shutil.copy(REPO / 'IDS_M1_Lab/data/ids_system.db', tmp)
c = sqlite3.connect(tmp)
rows = c.execute("select f.flow_id,f.source,f.run_name,f.src_ip,f.dst_ip,f.received_at,f.features_json,p.predicted_label from FlowRecord f join Prediction p on p.flow_id=f.flow_id").fetchall()
X = pd.DataFrame([json.loads(r[6]) for r in rows])[M1.feature_names]
def run(det):
    pr = det.model.predict_proba(X); idx = pr.argmax(1)
    return [det.class_names[i] for i in idx], pr.max(1)
l0, c0 = run(M0); l1, c1 = run(M1)
df = pd.DataFrame(dict(flow_id=[r[0] for r in rows], source=[r[1] for r in rows], run=[r[2] for r in rows], src_ip=[r[3] for r in rows], dst_ip=[r[4] for r in rows], time=[r[5] for r in rows],
                       db_M1=[r[7] for r in rows], M0=l0, M0_conf=c0.round(3), M1=l1, M1_conf=c1.round(3),
                       proto=X['Protocol'].values, dst_port=X['Dst Port'].values))
assert (df.M1 == df.db_M1).all(), 'M1 tính lại khác nhãn đã lưu'
out = REPO / 'IDS_M1_Lab/data/m1_vs_m0_db.csv'; df.to_csv(out, index=False, encoding='utf-8-sig')
rt = df[df.source == 'feeder_live']
print(f'Tổng {len(df)} flow; realtime {len(rt)} flow')
for name, d in [('Realtime (feeder_live)', rt), ('CSV sạch', df[df.source == 'csv_upload']), ('PCAP', df[df.source == 'pcap_replay'])]:
    print(f'\n== {name} ({len(d)} flow) ==  cảnh báo M0: {(d.M0 != "Benign").sum()}  M1: {(d.M1 != "Benign").sum()}')
    print(pd.crosstab(d.M0, d.M1).to_string() if len(d) else '')
print('\n== Realtime: 57 flow M1=Infilteration, M0 nói gì ==')
inf = rt[rt.M1 == 'Infilteration']; print(inf.M0.value_counts().to_dict(), '| conf M0 trung vị', inf.M0_conf.median(), '| conf M1 trung vị', inf.M1_conf.median())
print('\n== Realtime: các flow M0 ≠ M1 theo cặp (M0 -> M1) ==')
dd = rt[rt.M0 != rt.M1]; print(len(dd), 'flow khác nhau'); print(dd.groupby(['M0', 'M1']).size().sort_values(ascending=False).to_string())
print('\nM0 cảnh báo realtime, theo giao thức/cổng:'); a = rt[rt.M0 != 'Benign']; print(a.groupby(['M0', 'proto']).size().to_string()); print('cổng đích hay gặp:', a.dst_port.value_counts().head(6).to_dict())
