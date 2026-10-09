# Trich so lieu THAT tu RQ1/RQ2 (run moi nhat RQ2/runs/<ngay>/) -> dist/data.js
# Chay lai khi co run RQ2 moi: python xai-ids-study-hub/tools/build_data.py
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def latest_run_dir() -> str:
    runs = sorted(glob.glob(os.path.join(ROOT, "RQ2", "runs", "*")))
    assert runs, "No RQ2/runs/<date> found"
    return runs[-1]


RUN = latest_run_dir()


def rd(rel: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(RUN, rel), encoding="utf-8-sig")


def rj(rel: str) -> dict:
    with open(os.path.join(RUN, rel), encoding="utf-8") as f:
        return json.load(f)


def r(x, n=4):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), n)


# ---------------------------------------------------------------------------
# RQ1 — classification report + confusion matrix (unchanged source, still valid)
# ---------------------------------------------------------------------------
rep = pd.read_csv(os.path.join(ROOT, "RQ1_Model_Training_xboost", "results", "bang_chi_tiet_15_lop_tan_cong.csv"), encoding="utf-8-sig")
rep = rep.rename(columns={rep.columns[0]: "cls"})
cm_raw = pd.read_csv(os.path.join(ROOT, "RQ1_Model_Training_xboost", "results", "confusion_matrix_values.csv"), encoding="utf-8-sig")
cm_raw = cm_raw.rename(columns={cm_raw.columns[0]: "cls"})
classes = [c for c in cm_raw["cls"] if c in rep["cls"].values]
M = cm_raw[classes].values.astype(int) if all(c in cm_raw.columns for c in classes) else cm_raw.iloc[:, 1:].values.astype(int)

# ---------------------------------------------------------------------------
# RQ2 — new pipeline, run RUN
# ---------------------------------------------------------------------------
gd2_top5 = rd("gd2_shap_global/rq2_shap_global_top5_by_class.csv")
gd3_cohort = rd("gd3_cohorts/cohort_ids.csv")
gd4_shap_long = rd("gd4_shap_per_flow/shap_per_flow_long.csv")
gd6_lime_long = rd("gd6_lime_per_flow/lime_per_flow_long.csv")
gd6_scores = rd("gd6_lime_per_flow/lime_sample_scores.csv")
gd7_by_class = rd("gd7_agreement/rq2_1_agreement_by_class.csv")
gd7_overall = rd("gd7_agreement/rq2_1_agreement_overall.csv")
gd7_baseline = rd("gd7_agreement/rq2_1_random_baseline.csv")
gd8_summary = rj("gd8_quality_gate/rq2_1_lime_quality_gate_summary.json")
gd9_summary = rj("gd9_stability_robustness/rq2_2_stability_summary.json")
gd9_stab_flow = rd("gd9_stability_robustness/rq2_2_stability_lime_per_flow.csv")
gd9_noise_overall = rd("gd9_stability_robustness/rq2_2_noise_robustness.csv")
gd10_per_flow = rd("gd10_faithfulness/rq2_3_per_flow_faithfulness.csv")
gd11_prec_detail = rd("gd11_domain_validation/rq2_4_domain_precision_detail.csv")
gd11_summary = rj("gd11_domain_validation/rq2_4_summary.json")
gd2_additivity = rj("gd2_shap_global/rq2_shap_global_additivity_report.json")
gd4_report = rj("gd4_shap_per_flow/shap_per_flow_report.json")

noise_by_class_path = os.path.join(RUN, "gd9_stability_robustness", "rq2_2_noise_by_class_for_hub.csv")
gd9b_by_class = pd.read_csv(noise_by_class_path, encoding="utf-8-sig") if os.path.exists(noise_by_class_path) else None
noise_overall_path = os.path.join(RUN, "gd9_stability_robustness", "rq2_2_noise_per_flow_for_hub.csv")
gd9b_per_flow = pd.read_csv(noise_overall_path, encoding="utf-8-sig") if os.path.exists(noise_overall_path) else None

import sys
sys.path.insert(0, os.path.join(ROOT, "RQ2", "scripts"))
from lib.domain_knowledge import DOMAIN_KNOWLEDGE, ENVIRONMENT_FINGERPRINT_FEATURES  # noqa: E402

cohort_flow_to_class = dict(zip(gd3_cohort["flow_id"], gd3_cohort["true_label"]))
gd4_by_flow = {fid: g for fid, g in gd4_shap_long.groupby("flow_id")}
gd6_by_flow = {fid: g for fid, g in gd6_lime_long.groupby("flow_id")}
gd6_scores_by_flow = dict(zip(gd6_scores["flow_id"], gd6_scores["local_r2"]))

out = {"classes": [], "cm": M.tolist(), "classOrder": classes}

for i, c in enumerate(classes):
    p = rep[rep.cls == c].iloc[0]
    d = {"name": c, "precision": r(p.precision), "recall": r(p.recall), "f1": r(p["f1-score"]), "support": int(p.support)}

    # ---- global SHAP top5 (split pos/neg by sign of mean_signed_shap) ----
    sub = gd2_top5[gd2_top5["class"] == c].sort_values("rank")
    if len(sub):
        pos = sub[sub["mean_signed_shap"] > 0]
        neg = sub[sub["mean_signed_shap"] <= 0]
        d["globalPos"] = [[a, r(b)] for a, b in zip(pos.feature, pos.mean_signed_shap)]
        d["globalNeg"] = [[a, r(b)] for a, b in zip(neg.feature, neg.mean_signed_shap)]

    # ---- domain knowledge signals (broad scope) ----
    dk = DOMAIN_KNOWLEDGE.get(c)
    d["domainSignals"] = dk["broad"] if dk else []

    # ---- agreement (k=5, by class) ----
    a = gd7_by_class[(gd7_by_class["class"] == c) & (gd7_by_class["k"] == 5)]
    if len(a):
        a = a.iloc[0]
        d["agree"] = {
            "jaccard_5_mean": r(a["jaccard_mean"]),
            "spearman_5_mean": r(a["spearman_full78_mean"]),
            "signed_agreement_5_mean": r(a["sign_agreement_mean"]),
        }

    # ---- domain precision@5 (broad scope) ----
    q = gd11_prec_detail[(gd11_prec_detail["class"] == c) & (gd11_prec_detail["scope"] == "broad")]
    if len(q):
        qs = q[q.method == "SHAP"]["precision_at_5"]
        ql = q[q.method == "LIME"]["precision_at_5"]
        n_cohort = int((gd3_cohort["true_label"] == c).sum())
        if len(qs) and len(ql):
            d["domainP5"] = {"shap": r(qs.iloc[0]), "lime": r(ql.iloc[0]), "n": n_cohort}

    # ---- stability (per-class mean of per-flow LIME seed-stability) ----
    flow_ids_c = gd3_cohort[gd3_cohort["true_label"] == c]["flow_id"]
    stab_sub = gd9_stab_flow[gd9_stab_flow["flow_id"].isin(flow_ids_c)]
    if len(stab_sub):
        d["stab"] = r(stab_sub["mean_pairwise_jaccard5"].mean(), 3)

    # ---- robustness to noise (per-class, from stage09b) ----
    if gd9b_by_class is not None:
        rb = gd9b_by_class[gd9b_by_class["true_label"] == c]
        if len(rb):
            rob = {}
            for row in rb.itertuples():
                pct_key = str(int(round(row.sigma_fraction * 100)))
                blended = (row.shap_jaccard5 + row.lime_jaccard5) / 2
                rob[pct_key] = [r(blended, 3), r(row.pred_changed_rate, 3)]
            d["rob"] = rob

    # ---- example flow: flow with MEDIAN local R2 among this class's cohort flows ----
    cand = gd3_cohort[(gd3_cohort["true_label"] == c) & (gd3_cohort["pred_label"] == c)]["flow_id"].tolist()
    cand_r2 = [(fid, gd6_scores_by_flow.get(fid)) for fid in cand if fid in gd6_scores_by_flow]
    cand_r2 = [x for x in cand_r2 if x[1] is not None]
    if cand_r2:
        cand_r2.sort(key=lambda x: x[1])
        fid, r2 = cand_r2[len(cand_r2) // 2]
        shap_g = gd4_by_flow.get(fid)
        lime_g = gd6_by_flow.get(fid)
        if shap_g is not None and lime_g is not None:
            prob_row = gd6_scores[gd6_scores["flow_id"] == fid]
            d["example"] = {
                "sample_id": int(fid),
                "prob": r(1.0),  # placeholder; see note below
                "r2": r(r2, 4),
                "shapSum": r(shap_g["shap_value"].sum(), 4),
                "shap": [[a, r(b, 5)] for a, b in zip(shap_g.feature, shap_g.shap_value)],
                "lime": [[a, r(b, 5)] for a, b in zip(lime_g.feature_desc, lime_g.lime_weight)],
                "jac5": None,
                "cohortN": len(cand_r2),
            }

    # ---- Local R2 median / pass-rate for this class (cohort) ----
    r2_c = gd6_scores[gd6_scores["pred_class"] == c]["local_r2"] if "pred_class" in gd6_scores.columns else pd.Series(dtype=float)
    if len(r2_c):
        d["r2med"] = r(r2_c.median(), 3)
        d["r2ge03"] = r((r2_c >= 0.3).mean(), 3)

    out["classes"].append(d)

# fix: get the real predicted probability for each example flow (from lime_sample_scores' local_pred is NOT the model proba; need from gd6_per_flow_topk or recompute). We stored intercept/local_pred for LIME not model proba — use lime_per_flow_topk's pred_proba column from GĐ4's topk SHAP file instead (base_value + sum = margin, not proba). Simplify: use GĐ6 lime_sample_scores local_pred as an approximation is wrong (that's LIME's own local linear prediction). Use GĐ4 topk's pred_proba column.
gd4_topk = rd("gd4_shap_per_flow/shap_per_flow_topk.csv")
proba_by_flow = dict(zip(gd4_topk[gd4_topk.k == 5]["flow_id"], gd4_topk[gd4_topk.k == 5]["pred_proba"]))
for d in out["classes"]:
    if "example" in d:
        fid = d["example"]["sample_id"]
        if fid in proba_by_flow:
            d["example"]["prob"] = r(proba_by_flow[fid])

# ---------------------------------------------------------------------------
# Global block
# ---------------------------------------------------------------------------
agreement_global = {}
for k in [3, 5, 10]:
    row = gd7_overall[gd7_overall["k"] == k].iloc[0]
    base = gd7_baseline[gd7_baseline["k"] == k].iloc[0]
    agreement_global[str(k)] = [r(row["jaccard_mean"]), r(row["spearman_full78_mean"]), r(row["sign_agreement_mean"])]

faith_global = {}
faith_table = {}
for k in [3, 5, 10]:
    sub = gd10_per_flow[(gd10_per_flow["baseline"] == "global_median") & (gd10_per_flow["k"] == k)]
    piv = sub.pivot(index="flow_id", columns="method", values="comprehensiveness_drop")
    shap_mean = r(piv["SHAP"].mean() * 100, 2)
    lime_mean = r(piv["LIME"].mean() * 100, 2)
    rand_mean = r(piv["Random"].mean() * 100, 2)
    win_shap = r((piv["SHAP"] > piv["LIME"]).mean() * 100, 1)
    win_lime = r((piv["LIME"] > piv["SHAP"]).mean() * 100, 1)
    faith_global[str(k)] = [win_shap, win_lime]
    faith_table[str(k)] = [shap_mean, rand_mean, lime_mean, rand_mean]

robust_global = []
if gd9b_per_flow is not None:
    for sigma in sorted(gd9b_per_flow["sigma_fraction"].unique()):
        sub = gd9b_per_flow[gd9b_per_flow["sigma_fraction"] == sigma]
        blended = (sub["shap_jaccard5"].mean() + sub["lime_jaccard5"].mean()) / 2
        robust_global.append([int(round(sigma * 100)), r(blended, 3), r(sub["pred_changed"].mean() * 100, 1)])

domain_macro = gd11_prec_detail[gd11_prec_detail["scope"] == "broad"].groupby("method")["precision_at_5"].mean()

r2_all = gd6_scores["local_r2"]
hist, _ = np.histogram(r2_all.clip(0, 0.999), bins=10, range=(0, 1))

out["global"] = {
    "agreement": agreement_global,
    "faith": faith_global,
    "faithCoverage10": 100.0,
    "domain": [r(domain_macro.get("SHAP")), r(domain_macro.get("LIME"))],
    "r2": {"median": r(r2_all.median(), 3), "mean": r(r2_all.mean(), 3), "share_ge03": r((r2_all >= 0.3).mean() * 100, 1)},
    "stability": r(gd9_summary["lime_mean_pairwise_jaccard5"], 3) if gd9_summary else None,
    "robust": robust_global,
    "additivity": f"{gd2_additivity['max_abs_error']:.2e}",
    "additivityCohort": f"{gd4_report['additivity_max_error']:.2e}",
    "rq1": {"acc": 97.91, "macroP": 90.84, "macroR": 83.99, "macroF1": 85.81, "fpr": 5.7481, "fp": 12071, "benign": 490000, "testN": 700000},
}
out["global"]["r2hist"] = [int(x) for x in hist]
out["global"]["r2n"] = int(len(r2_all))
out["global"]["r2medAll"] = r(r2_all.median(), 4)
out["global"]["r2ge03"] = r((r2_all >= 0.3).mean(), 4)
out["global"]["faithTable"] = faith_table
out["global"]["runId"] = os.path.basename(RUN)
out["global"]["cohortN"] = int(len(gd3_cohort))
out["global"]["envFingerprint"] = ENVIRONMENT_FINGERPRINT_FEATURES

js = "window.PROJECT=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
out_path = os.path.join(os.path.dirname(__file__), "..", "dist", "data.js")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(js)
print(len(js), "bytes, run =", RUN)
print(json.dumps(out["classes"][1], ensure_ascii=False)[:1500])
