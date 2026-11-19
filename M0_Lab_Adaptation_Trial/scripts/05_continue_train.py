"""Bước 6: huấn luyện tiếp XGBoost từ M0 bằng flow tấn công lab thuộc các lượt train.

Nạp bản sao booster M0, thêm extra_rounds vòng theo configs/continue_v1.yaml. Cây cũ giữ nguyên; chỉ thêm cây mới.
Giữ 78 đặc trưng theo thứ tự M0 và encoder 15 lớp gốc. Lưu bản chính (cờ presence) và bản đối chứng (cờ raw).
"""
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
cfg = yaml.safe_load(open(HERE / "configs/continue_v1.yaml", encoding="utf-8"))
base = joblib.load(ROOT / cfg["base_model"])
enc_path = ROOT / cfg["base_encoder"]
classes = list(joblib.load(enc_path).classes_)
feats = list(base.feature_names_in_)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


for tag, data_key in (("primary", "primary"), ("control", "control")):
    df = pd.read_parquet(HERE / cfg["data"][data_key])
    tr = df[df.split == cfg["data"]["use_split"]].reset_index(drop=True)
    y = np.array([classes.index(c) for c in tr.label])
    n = tr.label.value_counts()
    w = tr.label.map(len(tr) / (len(n) * n)).to_numpy()
    d = xgb.DMatrix(tr[feats], label=y, weight=w, feature_names=feats)
    booster = base.get_booster().copy()
    p = dict(cfg["params"])
    new = xgb.train(p, d, num_boost_round=cfg["extra_rounds"], xgb_model=booster)
    assert new.num_boosted_rounds() == base.get_booster().num_boosted_rounds() + cfg["extra_rounds"]
    out = HERE / cfg["outputs"][tag]
    out.mkdir(parents=True, exist_ok=True)
    new.save_model(out / "model.json")
    shutil.copy(enc_path, out / "label_encoder.pkl")
    json.dump(feats, open(out / "feature_order.json", "w", encoding="utf-8"), indent=0)
    meta = dict(base_model=cfg["base_model"], base_sha256=sha(ROOT / cfg["base_model"]), base_rounds=base.get_booster().num_boosted_rounds(),
                extra_rounds=cfg["extra_rounds"], total_rounds=new.num_boosted_rounds(), params=p, weights=cfg["weights"],
                data=cfg["data"][data_key], runs_used=sorted(tr.run_id.unique()), rows_per_class=n.to_dict(),
                weight_per_class={k: float(len(tr) / (len(n) * v)) for k, v in n.items()}, classes=classes,
                benign_in_continued_training=False, model_sha256=sha(out / "model.json"),
                libraries=dict(xgboost=xgb.__version__, sklearn=sklearn.__version__, pandas=pd.__version__, python=sys.version.split()[0]))
    json.dump(meta, open(out / "training_info.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(tag, out.name, meta["total_rounds"], meta["rows_per_class"], flush=True)
