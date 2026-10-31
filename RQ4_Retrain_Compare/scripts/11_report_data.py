"""Gom mọi số liệu của báo cáo RQ4 vào results/report_data.json và vẽ hình. Mọi con số trong báo cáo đi qua tệp này,
đọc từ các tệp kết quả đã commit, không gõ tay."""
import glob
import json
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from rq4_common import *

D = {}


# --- chỉ số kiểu RQ1 của ba mô hình
def parse_summary(path):
    s = pd.read_csv(path)
    num = lambda i: float(re.match(r"[\d.]+", str(s.iloc[i, 1])).group())
    m = re.search(r"FP=(\d+), TN=(\d+)", str(s.iloc[4, 1]))
    n = re.search(r"FN=(\d+), TP=(\d+)", str(s.iloc[5, 1]))
    return dict(acc=num(0), prec=num(1), rec=num(2), f1=num(3), fpr=num(4), fp=int(m[1]), tn=int(m[2]), fnr=num(5), fn=int(n[1]), tp=int(n[2]))


D["rq1"] = {"M0": parse_summary(REPO / "RQ1_Model_Training_xboost/results/bang_2_ket_qua_chinh_thuc_rq1.csv"),
            "M0b": parse_summary(RESULTS / "m0b/bang_2_ket_qua_chinh_thuc.csv"), "M1": parse_summary(RESULTS / "m1/bang_2_ket_qua_chinh_thuc.csv")}
D["rq1_hulk"] = {}
old = pd.read_csv(REPO / "RQ1_Model_Training_xboost/results/bang_chi_tiet_15_lop_tan_cong.csv", index_col=0)
D["rq1_hulk"]["M0"] = old.loc["DoS attacks-Hulk"].to_dict()
for m in ("m0b", "m1"):
    D["rq1_hulk"][m] = pd.read_csv(RESULTS / m / "bang_chi_tiet_lop.csv", index_col=0).loc["DoS attacks-Hulk"].to_dict()

# --- đánh giá chéo
ce = pd.read_csv(RESULTS / "cross_evaluation.csv")
D["cross"] = json.loads(ce.to_json(orient="records"))

# --- so sánh hai bộ train (cũ và improved)
D["train_cmp"] = json.load(open(RESULTS / "compare_train_sets.json", encoding="utf-8"))
D["scan"] = json.load(open(RESULTS / "improved_scan_summary.json", encoding="utf-8"))
D["perclass"] = {m: json.loads(pd.read_csv(RESULTS / m / "bang_chi_tiet_lop.csv", index_col=0)["f1-score"].to_json()) for m in ("m0b", "m1")}
D["standalone"] = json.load(open(RESULTS / "m1_standalone_audit.json", encoding="utf-8"))
D["blocked"] = json.loads(pd.read_csv(RESULTS / "blocked_cv_m1.csv").to_json(orient="records"))
D["srcip"] = json.loads(pd.read_csv(RESULTS / "srcip_per_class.csv").to_json(orient="records"))

# --- thành phần, rò rỉ, chẩn đoán, realtime
D["composition"] = json.loads(pd.read_csv(RESULTS / "dataset_composition.csv", index_col=0).to_json(orient="index"))
D["leak"] = json.load(open(RESULTS / "leakage_report.json", encoding="utf-8"))
D["diag"] = json.load(open(RESULTS / "diagnose_m1.json", encoding="utf-8"))
D["t3"] = json.load(open(RESULTS / "t3_explain.json", encoding="utf-8"))

# --- XAI: M0 (RQ2) và M1 (RQ4)
x0 = json.load(open(REPO / "RQ2/runs/20261009/gd13_report/rq2_master_summary.json", encoding="utf-8"))
x1 = json.load(open(glob.glob(str(RQ4 / "xai_runs/m1/runs/*/gd13_report/rq2_master_summary.json"))[0], encoding="utf-8"))


def xai(x):
    g = lambda lst, **kw: next(r for r in lst if all(r[k] == v for k, v in kw.items()))
    k5 = g(x["gd7_agreement_overall"], k=5)
    return dict(cohort=x["gd3_cohorts"]["cohort_size"], errors=x["gd3_cohorts"]["error_cohort_size"], additivity_max=x["gd2_additivity"]["max_abs_error"],
                lime_median_r2=x["gd6_lime_per_flow"]["median_local_r2"], lime_pass=x["gd6_lime_per_flow"]["frac_r2_pass_gate"],
                jacc5=g(x["gd7_random_baseline"], k=5)["observed_jaccard_mean"], jacc5_random=g(x["gd7_random_baseline"], k=5)["random_jaccard_mean"],
                sign5=k5["sign_agreement_mean"],
                comp_shap=g(x["gd10_auc_summary"], baseline="global_median", method="SHAP")["comprehensiveness_auc"],
                comp_lime=g(x["gd10_auc_summary"], baseline="global_median", method="LIME")["comprehensiveness_auc"],
                comp_rand=g(x["gd10_auc_summary"], baseline="global_median", method="Random")["comprehensiveness_auc"],
                win5=g(x["gd10_winrate"], baseline="global_median")["shap_win_rate_vs_lime"],
                dom_shap_strict=g(x["gd11_domain_summary"], scope="strict", method="SHAP")["f1"],
                dom_lime_strict=g(x["gd11_domain_summary"], scope="strict", method="LIME")["f1"],
                dom_shap_broad=g(x["gd11_domain_summary"], scope="broad", method="SHAP")["f1"],
                dom_lime_broad=g(x["gd11_domain_summary"], scope="broad", method="LIME")["f1"],
                err_env=x["gd12_error_comparison"]["error_env_fraction_in_top5_mean"],
                top5_hulk=[(r["feature"], r["mean_abs_shap"]) for r in x["gd2_shap_global_top5"] if r["class"] == "DoS attacks-Hulk"],
                top5_benign=[(r["feature"], r["mean_abs_shap"]) for r in x["gd2_shap_global_top5"] if r["class"] == "Benign"])


D["xai"] = {"M0": xai(x0), "M1": xai(x1)}
json.dump(D, open(RESULTS / "report_data.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)

# ---------- hình 1: Benign bị báo thành tấn công
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
BLUE, ORANGE, AQUA, INK = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b"
sets = [("T1_test_cu_sach", "Bộ kiểm thử cũ\nđã bỏ trùng"), ("T2a_improved_stratified_sach", "Bộ kiểm thử improved\nđã bỏ trùng"),
        ("T3_realtime_benign", "784 flow Benign\nthực tế")]
labels = {"M0": "M0 (mô hình cũ, 15 lớp)", "M0b": "M0b (dữ liệu cũ, 13 lớp)", "M1": "M1 (dữ liệu improved)"}
fig, ax = plt.subplots(figsize=(8.2, 4.1), dpi=200)
w = 0.26
for k, (m, col) in enumerate([("M0", BLUE), ("M0b", ORANGE), ("M1", AQUA)]):
    vals = [float(ce[(ce.model == m) & (ce.test == s)].fpr_pct.iloc[0]) for s, _ in sets]
    xs = [j + (k - 1) * (w + 0.02) for j in range(len(sets))]
    ax.bar(xs, vals, width=w, color=col, label=labels[m], edgecolor="white", linewidth=1.2)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.5, (f"{v:.1f}".replace(".", ",") if v >= 0.05 else "0"), ha="center", va="bottom", fontsize=8.5, color=INK)
ax.set_xticks(range(len(sets)))
ax.set_xticklabels([n for _, n in sets], color=INK)
ax.set_ylabel("Benign bị báo thành tấn công (%)", color=INK)
ax.set_ylim(0, 33)
ax.yaxis.grid(True, color="#e5e4e0", linewidth=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(RQ4 / "report" / "hinh1_benign_bao_nham.png")
plt.close(fig)

# ---------- hình 2: FIN trong Benign TCP của hai bộ train
tc = D["train_cmp"]
ob, ib = tc["cu"]["benign"], tc["moi"]["benign"]
cats = ["Mang cờ FIN", "FIN và có dữ liệu", "FIN và dữ liệu từ 66 byte"]
ov = [100 * ob[k] / ob["tcp_rows"] for k in ("fin", "fin_data_gt0", "fin_data_ge_min")]
iv = [100 * ib[k] / ib["tcp_rows"] for k in ("fin", "fin_data_gt0", "fin_data_ge_min")]
fig, ax = plt.subplots(figsize=(8.2, 3.7), dpi=200)
for k, (vals, col, lab) in enumerate([(ov, BLUE, f"Train cũ ({ob['tcp_rows']/1e6:.2f} triệu flow Benign TCP)".replace(".", ",")),
                                      (iv, ORANGE, f"Train improved ({ib['tcp_rows']/1e6:.2f} triệu flow Benign TCP)".replace(".", ","))]):
    xs = [j + (k - 0.5) * 0.33 for j in range(3)]
    ax.bar(xs, vals, width=0.31, color=col, label=lab, edgecolor="white", linewidth=1.2)
    for x, v in zip(xs, vals):
        ax.text(x, v + 1, f"{v:.2f}".replace(".", ",") + "%", ha="center", va="bottom", fontsize=9, color=INK)
ax.set_xticks(range(3))
ax.set_xticklabels(cats, color=INK)
ax.set_ylim(0, 70)
ax.set_ylabel("Tỷ lệ flow Benign TCP (%)", color=INK)
ax.yaxis.grid(True, color="#e5e4e0", linewidth=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(RQ4 / "report" / "hinh2_fin_benign.png")
plt.close(fig)
print("ok", list(D))
