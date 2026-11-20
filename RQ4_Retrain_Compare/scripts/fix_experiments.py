# -*- coding: utf-8 -*-
"""THU NGHIEM CACH SUA (khong ghi report chinh) — chay tren Windows co xgboost.
    cd C:\\Users\\LOQ\\Downloads\\SELF_KLTN\\RQ4_Retrain_Compare\\scripts
    python fix_experiments.py

Tach 3 nhom flow THAT:
  - SSH-Bruteforce : port 22 (hydra/brutespray)            -> nhom TAN CONG
  - DoS Hulk       : port 80, Flow Duration >= 1s (hulk-rs keep-alive) -> nhom TAN CONG
  - Benign         : port 80, Flow Duration < 1s (baseline curl)       -> nhom BINH THUONG
Do tren tung model: RECALL o 2 nhom tan cong (cang cao cang bat duoc),
va FPR o nhom Benign (cang thap cang it bao nham). Cho thay danh doi M0 (on ao) vs M1 (mu).
"""
import json, sqlite3
from pathlib import Path
import numpy as np, pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import f1_score
from xgboost import XGBClassifier
from rq4_common import FEATURES, SEED, REPO, DATA, MODELS, RESULTS

IDS_DB = REPO / "IDS_M1_Lab" / "data" / "ids_system.db"
ENV = ["Dst Port", "Protocol", "Init Fwd Win Byts", "Init Bwd Win Byts", "Fwd Seg Size Min"]
VICTIM = "192.168.11.134"

con = sqlite3.connect(f"file:{IDS_DB}?mode=ro&immutable=1", uri=True)
def load(dst_port, limit=400):
    q = """select f.features_json from FlowRecord f join Prediction p using(flow_id)
           where f.dst_ip=? and json_extract(f.features_json,'$."Dst Port"')=?
           order by f.received_at desc limit ?"""
    return [json.loads(fj) for (fj,) in con.execute(q, (VICTIM, dst_port, limit))]

ssh = pd.DataFrame(load(22)); ssh["__true__"] = "SSH-Bruteforce"
web = pd.DataFrame(load(80))
web["__dur_s__"] = web["Flow Duration"].astype(float) / 1e6
web["__true__"] = np.where(web["__dur_s__"] >= 1.0, "DoS attacks-Hulk", "Benign")
real = pd.concat([ssh, web], ignore_index=True)

n_ssh = int((real["__true__"]=="SSH-Bruteforce").sum())
n_hulk= int((real["__true__"]=="DoS attacks-Hulk").sum())
n_ben = int((real["__true__"]=="Benign").sum())
print("="*80)
print("(A) FLOW THAT (da tach benign/attack theo thoi luong flow port80)")
print(f"    SSH-Bruteforce(22): {n_ssh}   DoS-Hulk(80 dai>=1s): {n_hulk}   Benign(80 ngan<1s): {n_ben}")
miss=[c for c in FEATURES if c not in real.columns]; print(f"    Du 78 dac trung? {'du 78' if not miss else miss}")

def report(pred, tag):
    real["__pred__"] = pred
    r = {}
    for grp, kind in [("SSH-Bruteforce","recall"),("DoS attacks-Hulk","recall"),("Benign","fpr")]:
        m = (real["__true__"]==grp).values
        if m.sum()==0: continue
        pr = real["__pred__"].values[m]
        if kind=="recall":
            val=(pr==grp).mean()*100
            r[grp]=dict(n=int(m.sum()),recall_pct=round(float(val),2),top=pd.Series(pr).value_counts().head(3).to_dict())
            print(f"    [{tag}] {grp:18s} n={int(m.sum()):4d}  RECALL={val:6.2f}%  pred: {r[grp]['top']}")
        else:
            fpr=(pr!="Benign").mean()*100
            r[grp]=dict(n=int(m.sum()),fpr_pct=round(float(fpr),2),top=pd.Series(pr).value_counts().head(3).to_dict())
            print(f"    [{tag}] {grp:18s} n={int(m.sum()):4d}  FPR   ={fpr:6.2f}% (bao nham benign thanh tan cong)  pred: {r[grp]['top']}")
    return r

out={"n_ssh":n_ssh,"n_hulk":n_hulk,"n_benign":n_ben}
print("\n"+"="*80); print("(B) MODEL HIEN TAI"); print("="*80)
def run(pkl,enc,tag):
    mdl=joblib.load(pkl); le=joblib.load(enc)
    pred=np.array(le.classes_)[mdl.predict(real[list(mdl.feature_names_in_)].astype(float))]
    print(f"\n-- {tag} ({len(le.classes_)} lop) --"); return report(pred,tag)
out["M0"]=run(REPO/"RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl",
              REPO/"RQ1_Model_Training_xboost/saved_models/label_encoder.pkl","M0")
out["M0b"]=run(MODELS/"m0b_xgboost_model.pkl",MODELS/"m0b_label_encoder.pkl","M0b")
out["M1"]=run(MODELS/"m1_xgboost_model.pkl",MODELS/"m1_label_encoder.pkl","M1")

print("\n"+"="*80); print("(C) CACH 2: train lai M1 BO 5 dac trung moi truong (dang train ~1-2 phut)"); print("="*80)
tr=pd.read_parquet(DATA/"d2_train.parquet"); feats=[f for f in FEATURES if f not in ENV]
le=LabelEncoder(); y=le.fit_transform(tr.Label)
m=XGBClassifier(n_estimators=100,max_depth=8,learning_rate=0.08,tree_method="hist",random_state=SEED,n_jobs=-1).fit(tr[feats],y)
pred=np.array(le.classes_)[m.predict(real[feats].astype(float))]
print("\n-- M1-bo-moi-truong --"); out["M1_noenv"]=report(pred,"M1-noenv")
te=pd.read_parquet(DATA/"d2_test.parquet"); pte=np.array(le.classes_)[m.predict(te[feats])]
out["M1_noenv_indist"]=dict(accuracy=round(float((pte==te.Label).mean()*100),3),
                            macro_f1=round(float(f1_score(te.Label,pte,average='macro',zero_division=0)*100),3))
print(f"    (sanity trong phan phoi: acc={out['M1_noenv_indist']['accuracy']}%  macroF1={out['M1_noenv_indist']['macro_f1']}%)")

print("\n"+"="*80); print("TOM TAT — RECALL tan cong (cao=tot) va FPR benign (thap=tot)"); print("="*80)
print(f"{'model':16s}{'SSH recall':>12s}{'Hulk recall':>13s}{'Benign FPR':>13s}")
def gr(d,k): return d.get(k,{}).get('recall_pct',float('nan'))
def gf(d,k): return d.get(k,{}).get('fpr_pct',float('nan'))
for k,name in [("M0","M0 15lop"),("M0b","M0b 13lop"),("M1","M1 (live)"),("M1_noenv","M1 bo m.truong")]:
    print(f"{name:16s}{gr(out[k],'SSH-Bruteforce'):>11.2f}%{gr(out[k],'DoS attacks-Hulk'):>12.2f}%{gf(out[k],'Benign'):>12.2f}%")
RESULTS.mkdir(exist_ok=True)
json.dump(out,open(RESULTS/"fix_experiments.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
print(f"\nDa luu: {RESULTS/'fix_experiments.json'}")
