"""Bước 7: so M0 và hai bản huấn luyện tiếp trên lượt lab và trên tập test gốc, kèm phép thử đường tắt.

Model: M0 (100 vòng), v1 (cờ presence, 120 vòng), v1_rawflags (cờ raw, 120 vòng, đối chứng).
Đầu vào lab: M0 và v1 nhận bảng presence, v1_rawflags nhận bảng raw (đúng quy ước lúc train của từng bản).
Tập test gốc đã là 0/1 ở cột cờ nên cả ba nhận cùng bảng.
Phép thử đường tắt trên Benign của test gốc (chỉ đo độ nhạy, không phải traffic thật):
  S1 đặt Init Fwd Win Byts = 64240 (giá trị SYN của Kali trong mọi lượt lab);
  S2 đổi mọi cột cờ đang bằng 1 thành 2 (giống số đếm Java ở một kết nối đóng bình thường).
Ghi results/adaptation/*.csv và summary.json.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
OUT = HERE / "results/adaptation"
OUT.mkdir(parents=True, exist_ok=True)
FLAGS = ["Fwd PSH Flags", "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags", "FIN Flag Cnt", "SYN Flag Cnt", "RST Flag Cnt",
         "PSH Flag Cnt", "ACK Flag Cnt", "URG Flag Cnt", "CWE Flag Count", "ECE Flag Cnt"]

m0 = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl")
feats = list(m0.feature_names_in_)
classes = np.array(joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl").classes_)
B = classes.tolist().index("Benign")
MODELS = {"M0": m0.get_booster()}
for name, folder in (("v1", "m0_continued_v1"), ("v1_rawflags", "m0_continued_v1_rawflags"), ("v2", "m0_continued_v2")):
    if (HERE / "models" / folder / "model.json").exists():
        b = xgb.Booster(); b.load_model(HERE / "models" / folder / "model.json"); MODELS[name] = b
INPUT = {"M0": "presence", "v1": "presence", "v1_rawflags": "raw", "v2": "presence"}


def predict(name, X):
    return classes[MODELS[name].predict(xgb.DMatrix(X[feats], feature_names=feats)).argmax(axis=1)]


# 1. Lượt lab
lab = {k: pd.read_parquet(HERE / f"data/labeled/lab_flows_{k}.parquet") for k in ("presence", "raw")}
meta = lab["presence"][["run_id", "split", "label", "short_flow", "starts_from_attacker"]].copy()
for name in MODELS:
    meta["pred_" + name] = predict(name, lab[INPUT[name]])
meta["subset"] = np.where(meta.short_flow | ~meta.starts_from_attacker, "fragment", "main")
meta.drop(columns=[]).to_parquet(OUT / "lab_predictions.parquet", index=False)

rows = []
for (run, split, label), g in meta.groupby(["run_id", "split", "label"], sort=False):
    for subset, gg in (("all", g), ("main", g[g.subset == "main"])):
        for name in MODELS:
            p = gg["pred_" + name]
            rows.append(dict(run_id=run, split=split, label=label, subset=subset, model=name, flows=len(gg),
                             correct=int((p == label).sum()), to_benign=int((p == "Benign").sum()),
                             to_other_attack=int(((p != label) & (p != "Benign")).sum()),
                             top_wrong=(p[p != label].value_counts().head(2).to_dict() if (p != label).any() else {})))
labres = pd.DataFrame(rows)
labres.to_csv(OUT / "lab_by_run.csv", index=False)

# 2. Tập test gốc
te = pd.read_parquet(ROOT / "dataset/CICID-2018_processed/test_set.parquet")
y = te["Label"].to_numpy()
orig = {}
for name in MODELS:
    p = predict(name, te)
    pr, rc, f1, sup = precision_recall_fscore_support(y, p, labels=classes, zero_division=0)
    pd.DataFrame(dict(cls=classes, precision=pr, recall=rc, f1=f1, support=sup)).to_csv(OUT / f"orig_test_per_class_{name}.csv", index=False)
    pd.DataFrame(confusion_matrix(y, p, labels=classes), index=classes, columns=classes).to_csv(OUT / f"orig_test_confusion_{name}.csv")
    ben = y == "Benign"
    orig[name] = dict(rows=len(y), accuracy=float((p == y).mean()), macro_f1=float(f1.mean()),
                      benign=int(ben.sum()), benign_alerts=int((p[ben] != "Benign").sum()),
                      attacks=int((~ben).sum()), attacks_to_benign=int((p[~ben] == "Benign").sum()),
                      changed_vs_M0=None)
    orig[name]["pred"] = p
p0 = orig["M0"]["pred"]
for name in MODELS:
    orig[name]["changed_vs_M0"] = int((orig[name].pop("pred") != p0).sum())

# 3. Phép thử đường tắt trên Benign của test gốc
ben = te[te["Label"] == "Benign"]
s1 = ben.copy(); s1["Init Fwd Win Byts"] = 64240
s2 = ben.copy(); s2[FLAGS] = s2[FLAGS].replace(1, 2)
shortcut = {}
for tag, X in (("S1_init_fwd_win_64240", s1), ("S2_flags_1_to_2", s2)):
    shortcut[tag] = {name: dict(benign=len(X), alerts=int((predict(name, X) != "Benign").sum())) for name in MODELS}
shortcut["benign_rows_with_init_fwd_win_64240_in_test"] = int((ben["Init Fwd Win Byts"] == 64240).sum())

json.dump(dict(original_test=orig, shortcut=shortcut), open(OUT / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250)
print(labres[labres.subset == "all"].drop(columns=["subset"]).to_string(index=False))
print(json.dumps(orig, indent=0))
print(json.dumps(shortcut, indent=0))
