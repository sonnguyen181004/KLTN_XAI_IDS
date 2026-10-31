"""Phép tính bổ sung cho bài báo: khoảng tin cậy, SHAP cùng lớp đầu ra, kiểm tra cộng dồn TreeSHAP, kiểm chứng vùng FIN theo phiên,
độ trễ và mã băm các tệp. Chỉ đọc dữ liệu và mô hình có sẵn; kết quả ghi vào results/paper_checks.json."""
import hashlib
import json
import platform
import sqlite3
import sys

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost
from scipy.stats import beta
from sklearn import __version__ as skl_version

from rq4_common import *

sys.path.insert(0, str(REPO / "RQ3_IDS_System" / "app"))
from explain_shap import ShapExplainer  # noqa: E402

out = {}


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(100 * (c - h) / d, 2), round(100 * (c + h) / d, 2)]


def clopper(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return [round(100 * lo, 3), round(100 * hi, 3)]


out["intervals_95"] = {name: dict(k=k, n=n, rate_pct=round(100 * k / n, 2), wilson=wilson(k, n), clopper_pearson=clopper(k, n))
                       for name, (k, n) in {"M0_alerts_on_784": (149, 784), "M0_hulk_alerts_on_784": (148, 784), "M1_alerts_on_784": (0, 784),
                                            "M0_hulk_on_web_browsing_21": (19, 21), "M1_alerts_on_web_browsing_21": (0, 21)}.items()}
print(json.dumps(out["intervals_95"]), flush=True)

R = hulk_zone_rule()


def in_zone(X):
    return ((X["FIN Flag Cnt"] >= R["min_fin_flag_cnt"]) & (X["Fwd Pkt Len Max"] >= R["min_fwd_pkt_len_max"]) & (X["Fwd Seg Size Min"] < R["below_fwd_seg_size_min"]))


M = {}
for name, mp, ep in [("M0", REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl", REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl"),
                     ("M1", MODELS / "m1_xgboost_model.pkl", MODELS / "m1_label_encoder.pkl")]:
    M[name] = (joblib.load(mp), list(joblib.load(ep).classes_))

# ---- tập 784 flow: nhóm theo phiên, vùng FIN, cảnh báo của M0
cand = pd.read_parquet(DATA / "t3_candidates.parquet")
log = pd.read_csv(RESULTS / "t3_session_log.csv")
t3 = pd.read_parquet(DATA / "t3_benign_confirmed.parquet")
cand = cand[cand.run.isin(log.loc[log.benign_confirmed == "yes", "run"])].reset_index(drop=True)
assert len(cand) == len(t3) == 784 and np.allclose(cand[FEATURES].to_numpy(dtype="float64"), t3[FEATURES].to_numpy(dtype="float64"), equal_nan=True)
X = t3[FEATURES]
m0, c0 = M["M0"]
pred0 = np.array(c0)[m0.predict(X)]
zone = in_zone(X).to_numpy()
alert = pred0 != "Benign"
cand["alert"], cand["zone"] = alert, zone
sess = cand.groupby("run").agg(start=("received_at", "min"), flows=("alert", "size"), alerts=("alert", "sum"), zone_flows=("zone", "sum")).sort_values("start")
sess["alerts_in_zone"] = cand[cand.alert & cand.zone].groupby("run").size().reindex(sess.index).fillna(0).astype(int)
out["live_sessions"] = json.loads(sess.reset_index().to_json(orient="records"))
out["live_zone"] = dict(flows=784, zone_flows=int(zone.sum()), alerts=int(alert.sum()), alerts_in_zone=int((alert & zone).sum()),
                        zone_flows_not_alerted=int((zone & ~alert).sum()))
print(sess.to_string(), flush=True)

# ---- kiểm chứng vùng FIN trên tập test của bộ đã sửa (682.100 dòng): M0 báo nhầm Benign nằm ở đâu
te = pd.read_parquet(DATA / "d2_test.parquet")
ben = te[te.Label == "Benign"]
Xb = ben[FEATURES]
pb = np.array(c0)[m0.predict(Xb)]
zb = in_zone(Xb).to_numpy()
out["corrected_test_benign"] = dict(benign=len(ben), alerts=int((pb != "Benign").sum()), zone_flows=int(zb.sum()), alerts_in_zone=int(((pb != "Benign") & zb).sum()),
                                    alerts_outside_zone=int(((pb != "Benign") & ~zb).sum()), alerts_hulk=int((pb == "DoS attacks-Hulk").sum()))
print(out["corrected_test_benign"], flush=True)

# ---- SHAP cùng lớp đầu ra (DoS-Hulk) cho hai mô hình trên cùng 148 flow trong vùng FIN, và cộng dồn TreeSHAP trên 784 flow
Z = X[zone].reset_index(drop=True)
for name in ("M0", "M1"):
    m, cls = M[name]
    h = cls.index("DoS attacks-Hulk")
    sv = shap.TreeExplainer(m).shap_values(Z)
    sv = np.stack(sv, axis=-1) if isinstance(sv, list) else sv
    s = pd.Series(sv[:, :, h].mean(axis=0), index=FEATURES)
    top = s.reindex(s.abs().sort_values(ascending=False).index).head(8)
    pz = np.array(cls)[m.predict(Z)]
    out[f"shap_hulk_class_{name}"] = dict(predicted_on_zone=pd.Series(pz).value_counts().to_dict(), top8={k: round(float(v), 3) for k, v in top.items()},
                                         fin_mean=round(float(s["FIN Flag Cnt"]), 3))
    print(name, out[f"shap_hulk_class_{name}"], flush=True)
for name in ("M0", "M1"):
    m, cls = M[name]
    ex = ShapExplainer(m, cls)
    pr = np.array(cls)[m.predict(X)]
    errs = [ex.explain(X.iloc[[i]], pr[i], top_k=5)["additivity_error"] for i in range(len(X))]
    out[f"treeshap_additivity_{name}"] = dict(flows=len(errs), max_abs_error=float(np.max(errs)), mean_abs_error=float(np.mean(errs)))
    print(name, out[f"treeshap_additivity_{name}"], flush=True)

# ---- độ trễ từ cơ sở dữ liệu lab M1 (chỉ đọc) và thời lượng flow
con = sqlite3.connect("file:" + str(REPO / "IDS_M1_Lab/data/ids_system.db") + "?mode=ro", uri=True)
t = pd.read_sql("select step, duration_ms from Timing", con)
out["latency_ms"] = {s: dict(n=int(len(g)), p50=round(float(g.duration_ms.quantile(.5)), 1), p95=round(float(g.duration_ms.quantile(.95)), 1), max=round(float(g.duration_ms.max()), 1))
                     for s, g in t.groupby("step")}
fj = pd.read_sql("select features_json from FlowRecord where source='feeder_live'", con)
dur = np.array([json.loads(x)["Flow Duration"] for x in fj.features_json]) / 1e6
out["live_flow_duration_s"] = dict(n=len(dur), p50=round(float(np.median(dur)), 2), p90=round(float(np.quantile(dur, .9)), 2), max=round(float(dur.max()), 1))
print(json.dumps(out["latency_ms"]), out["live_flow_duration_s"], flush=True)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            h.update(ch)
    return h.hexdigest()[:16]


arts = {"M0_model": REPO / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl", "M0_encoder": REPO / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl",
        "M1_model": MODELS / "m1_xgboost_model.pkl", "M1_encoder": MODELS / "m1_label_encoder.pkl", "original_train": TRAIN_OLD, "original_test": TEST_OLD,
        "corrected_train": DATA / "d2_train.parquet", "corrected_test": DATA / "d2_test.parquet", "live_784": DATA / "t3_benign_confirmed.parquet"}
out["sha256_16"] = {k: sha(p) for k, p in arts.items()}
out["versions"] = dict(python=platform.python_version(), xgboost=xgboost.__version__, shap=shap.__version__, scikit_learn=skl_version, pandas=pd.__version__)
print(out["sha256_16"], out["versions"], flush=True)
json.dump(out, open(RESULTS / "paper_checks.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("xong")
