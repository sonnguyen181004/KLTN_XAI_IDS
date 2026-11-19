"""Bước 6, lần 2: huấn luyện tiếp M0 bằng flow tấn công lab trộn với mẫu ôn lại từ train gốc (configs/continue_v2.yaml)."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
import yaml

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
cfg = yaml.safe_load(open(HERE / "configs/continue_v2.yaml", encoding="utf-8"))
base = joblib.load(ROOT / cfg["base_model"])
enc_path = ROOT / cfg["base_encoder"]
classes = list(joblib.load(enc_path).classes_)
feats = list(base.feature_names_in_)
D, W = cfg["data"], cfg["weights"]

lab = pd.read_parquet(HERE / D["lab"])
lab = lab[lab.split == "train"]
n = lab.label.value_counts()
lab_w = lab.label.map(lambda c: min(W["lab_class_total"] / n[c], W["lab_row_cap"])).to_numpy()

tr = pd.read_parquet(ROOT / D["replay"])
frac = D["replay_rows"] / len(tr)
idx = [g.sample(max(1, round(len(g) * frac)), random_state=D["replay_seed"]).index for _, g in tr.groupby("Label")]
rep = tr.loc[np.concatenate(idx)]
assert rep.Label.nunique() == len(classes)

X = pd.concat([rep[feats], lab[feats]], ignore_index=True)
y = np.array([classes.index(c) for c in list(rep.Label) + list(lab.label)])
w = np.concatenate([np.full(len(rep), float(W["replay"])), lab_w])
d = xgb.DMatrix(X, label=y, weight=w, feature_names=feats)
new = xgb.train(dict(cfg["params"]), d, num_boost_round=cfg["extra_rounds"], xgb_model=base.get_booster().copy())

out = HERE / cfg["output"]
out.mkdir(parents=True, exist_ok=True)
new.save_model(out / "model.json")
shutil.copy(enc_path, out / "label_encoder.pkl")
json.dump(feats, open(out / "feature_order.json", "w", encoding="utf-8"), indent=0)
meta = dict(config="configs/continue_v2.yaml", base_rounds=base.get_booster().num_boosted_rounds(), total_rounds=new.num_boosted_rounds(),
            replay_rows=len(rep), replay_per_class=rep.Label.value_counts().to_dict(), lab_rows_per_class=n.to_dict(),
            lab_weight_per_row={c: min(W["lab_class_total"] / n[c], W["lab_row_cap"]) for c in n.index},
            lab_runs=sorted(lab.run_id.unique()), params=cfg["params"],
            model_sha256=hashlib.sha256((out / "model.json").read_bytes()).hexdigest(),
            libraries=dict(xgboost=xgb.__version__, sklearn=sklearn.__version__, pandas=pd.__version__, python=sys.version.split()[0]))
json.dump(meta, open(out / "training_info.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(meta["total_rounds"], meta["replay_rows"], meta["lab_weight_per_row"])
