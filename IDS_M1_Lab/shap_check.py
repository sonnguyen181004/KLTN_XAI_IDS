# -*- coding: utf-8 -*-
"""Phan tich SHAP vi sao flow tan cong THAT bi gan Benign.

Chay trong CHINH moi truong Python da chay run_ids.ps1 (co xgboost/shap):
    cd C:\\Users\\LOQ\\Downloads\\SELF_KLTN\\IDS_M1_Lab
    python shap_check.py

Lay flow moi nhat cho CA port 22 (SSH-brute) va port 80 (DoS/web) toi 192.168.11.134,
in: nhan du doan, xac suat Benign, va top-5 dac trung keo ve Benign (SHAP).
"""
import sys, json, sqlite3
sys.path.insert(0, ".")
import joblib
from app.normalize import normalize_flow
from app.explain_shap import ShapExplainer

model = joblib.load("models/m1_xgboost_model.pkl")
le = joblib.load("models/m1_label_encoder.pkl")
feature_names = list(model.feature_names_in_)
class_names = list(le.classes_)
explainer = ShapExplainer(model, class_names)

# DB dang bi IDS song giu lock -> mo read-only immutable
con = sqlite3.connect("file:data/ids_system.db?mode=ro&immutable=1", uri=True)

def latest(dst_port, n=3):
    q = """select f.flow_id,f.received_at,f.features_json,p.predicted_label,p.probabilities_json
           from FlowRecord f join Prediction p using(flow_id)
           where f.dst_ip='192.168.11.134'
             and json_extract(f.features_json,'$."Dst Port"')=?
           order by f.received_at desc limit ?"""
    return con.execute(q,(dst_port,n)).fetchall()

for tag, port in [("SSH-Bruteforce (port 22)",22), ("DoS/web hulk-rs (port 80)",80)]:
    rows = latest(port)
    print("#"*72)
    print(f"# {tag} — {len(rows)} flow moi nhat")
    print("#"*72)
    for fid,rec,fj,lab,pj in rows:
        feat = json.loads(fj); prob = json.loads(pj)
        df = normalize_flow(feat, feature_names, convert_seconds_to_microseconds=False)
        # Luu y: features_json DA la gia tri sau normalize (micro giay) -> KHONG doi don vi nua.
        res = explainer.explain(df, lab, top_k=8)
        pben = prob.get("Benign",0.0)
        # xac suat cao nhat cho mot nhan TAN CONG bat ky
        atk = {k:v for k,v in prob.items() if k!="Benign"}
        top_atk = max(atk.items(), key=lambda x:x[1]) if atk else ("-",0)
        print(f"\nflow {fid[:8]} | {rec} | du doan={lab} | P(Benign)={pben:.4f} | nhan tan cong cao nhat: {top_atk[0]}={top_atk[1]:.4f}")
        print(f"  base={res['base_value']:.4f}  additivity_err={res['additivity_error']:.2e}")
        print(f"  Top-8 dac trung keo ve '{lab}':")
        for it in res["top_k"]:
            print(f"    {it['feature']:24s} value={it['value']:>14.2f}  phi={it['phi']:+.4f}")
    print()
