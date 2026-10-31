"""Figures for the IEEE paper. Grayscale only. Every number is read from a result file or typed from paper_checks.json."""
import json
import sqlite3

import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

R4 = r"C:\Users\LOQ\Downloads\SELF_KLTN\RQ4_Retrain_Compare\results"
OUT = r"C:\Users\LOQ\Downloads\SELF_KLTN\Paper_IEEE\figures"
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 8})
checks = json.load(open(R4 + r"\paper_checks.json", encoding="utf-8"))


def save(fig, name):
    fig.savefig(f"{OUT}\\{name}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUT}\\{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


def bx(ax, x, y, w, h, t, fs=6.9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.8", fc="white", ec="black", lw=0.9))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, weight="bold" if bold else "normal", linespacing=1.3)


def ar(ax, p, q):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="->", lw=0.9, color="black"))


# ---------- Fig. 1: evidence chain ----------
fig, ax = plt.subplots(figsize=(7.1, 2.9), dpi=300)
ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off")
live = checks["intervals_95"]["M0_alerts_on_784"]
texts = [
    f"1. Observation\nM0 alerts on 149 of\n784 confirmed-benign\nflows ({live['rate_pct']}%, 95% CI\n{live['wilson'][0]} to {live['wilson'][1]})",
    "2. SHAP\nFIN Flag Cnt adds +5.87\nlog-odds on average,\n2.3 times the next\nfeature",
    "3. Decision path\nA false alert passes\ntree 38. All 100 Hulk\ntrees split on\nFIN Flag Cnt",
    "4. FIN zone\nFIN count at least 1,\nforward packet at\nleast 66 B, forward\nheader below 32 B",
    "5. Intervention tests\nSetting FIN Flag Cnt\nto 0 changes 148 of\n148 zone labels",
    "6. Training data check\nOriginal zone: 445\nHulk, 0 benign.\nCorrected zone: 405,347\nbenign, 330 Hulk",
    "7. Retrained model M1\n0 of 784 alerts\n(95% upper bound\n0.47%)",
]
W, H = 22.5, 16
xs1 = [0.5, 25.8, 51.1, 76.4]
xs2 = [0.5, 25.8, 51.1]
for t, x in zip(texts[:4], xs1):
    bx(ax, x, 25, W, H, t, fs=6.6)
for t, x in zip(texts[4:], xs2):
    bx(ax, x, 2, W, H, t, fs=6.6)
for x in xs1[:-1]:
    ar(ax, (x + W + 0.3, 33), (x + 3.0 + W, 33))
for x in xs2[:-1]:
    ar(ax, (x + W + 0.3, 10), (x + 3.0 + W, 10))
ax.plot([87.6, 87.6], [25, 21.5], color="black", lw=0.9)
ax.plot([87.6, 11.7], [21.5, 21.5], color="black", lw=0.9)
ar(ax, (11.7, 21.5), (11.7, 18.3))
save(fig, "fig1_chain")

# ---------- Fig. 2: system pipeline (no diagonal links) ----------
fig, ax = plt.subplots(figsize=(7.1, 2.0), dpi=300)
ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")
top = [("Network traffic\n(live or PCAP)", 0.5), ("Packet capture\n(Npcap, Scapy)", 25.8), ("Flow extractor\n(CICFlowMeter,\n78 features)", 51.1), ("Feeder and\nREST API", 76.4)]
bot = [("Analyst dashboard\n(SHAP; LIME\non request)", 0.5), ("Reliability flags\n(environment,\nrare class)", 25.8), ("TreeSHAP\nexplanation", 51.1), ("XGBoost\ndetector", 76.4)]
for t, x in top:
    bx(ax, x, 17, W, 10, t, fs=7.2)
for t, x in bot:
    bx(ax, x, 2, W, 10, t, fs=7.2)
for x in (0.5, 25.8, 51.1):
    ar(ax, (x + W + 0.3, 22), (x + 3.0 + W, 22))
ar(ax, (87.6, 17), (87.6, 12.3))
for x in (25.8, 51.1, 76.4):
    ar(ax, (x - 0.3, 7), (x - 3.0, 7))
save(fig, "fig2_pipeline")

# ---------- Fig. 3: absolute counts in the FIN zone ----------
fig, ax = plt.subplots(figsize=(3.4, 2.1), dpi=300)
cats = ["Original\ntraining set", "Corrected\ntraining set"]
ben = [0, 405347]; hulk = [445, 330]
x = np.arange(2); w = 0.34
ax.bar(x - w / 2, [max(v, 0.6) for v in ben], w, color="white", edgecolor="black", hatch="///", label="Benign")
ax.bar(x + w / 2, hulk, w, color="0.35", edgecolor="black", label="DoS-Hulk")
ax.set_yscale("log"); ax.set_ylim(0.5, 3e6)
for xi, v in zip(x - w / 2, ben):
    ax.text(xi, max(v, 0.6) * 1.5, f"{v:,}", ha="center", fontsize=7)
for xi, v in zip(x + w / 2, hulk):
    ax.text(xi, v * 1.5, f"{v:,}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=7.5)
ax.set_ylabel("Flows in the FIN zone (log scale)", fontsize=7.5)
ax.legend(frameon=False, fontsize=7, loc="upper left")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
save(fig, "fig3_zone")

# ---------- Fig. 4: SHAP of the Hulk output for both models on the same 148 flows ----------
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.3), dpi=300)
for ax, key, title in ((axes[0], "shap_hulk_class_M0", "(a) M0, DoS-Hulk output"), (axes[1], "shap_hulk_class_M1", "(b) M1, DoS-Hulk output")):
    d = checks[key]["top8"]
    names = list(d.keys())[::-1]; vals = [d[n] for n in names]
    ax.barh(range(len(vals)), vals, color=["0.35" if v > 0 else "white" for v in vals], edgecolor="black", height=0.62)
    ax.set_yticks(range(len(vals))); ax.set_yticklabels(names, fontsize=7)
    ax.axvline(0, color="black", lw=0.7)
    ax.set_title(title, fontsize=8); ax.set_xlabel("Mean SHAP value (log-odds)", fontsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
fig.tight_layout()
save(fig, "fig4_shap")

# ---------- Fig. 5: blocked evaluation of M1 ----------
b = pd.read_csv(R4 + r"\blocked_cv_m1.csv")
full = b[b.bo == "khoi_thoi_gian"].sort_values("fold"); ded = b[b.bo == "khoi_thoi_gian_sach"].sort_values("fold")
fig, ax = plt.subplots(figsize=(3.4, 2.0), dpi=300)
x = np.arange(5); w = 0.36
ax.bar(x - w / 2, full.macro_f1, w, color="0.35", edgecolor="black", label="All test flows")
ax.bar(x + w / 2, ded.macro_f1, w, color="white", edgecolor="black", hatch="///", label="Duplicates removed")
ax.set_ylim(96, 100.4); ax.set_xticks(x); ax.set_xticklabels([f"Block {i + 1}" for i in range(5)], fontsize=7)
ax.set_ylabel("Macro F1 (%)", fontsize=7.5); ax.legend(frameon=False, fontsize=6.8, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
save(fig, "fig5_blocked")

# ---------- Fig. 6: LIME validity ----------
keep = ["windows_live", "lab_WEB-B01", "lab_A07", "lab_B03"]
a = pd.read_csv(R4 + r"\lab_m1\lime_validity_M0_nen_cu.csv"); a = a[a.source.isin(keep)]
c = pd.read_csv(R4 + r"\lab_m1\lime_validity_M1_nen_M1.csv"); c = c[c.source.isin(keep)]
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.2), dpi=300, gridspec_kw={"width_ratios": [1.1, 1]})
ax = axes[0]
labels = ["RQ2 test cohort,\nall classes (1,339)", "RQ2 test cohort,\nbenign flows (100)", "Real flows, M0 and\noriginal background (313)", "Real flows, M1 and\ncorrected background (313)"]
vals = [85.96, 23.0, 100 * a["pass_r2_0.3"].mean(), 100 * c["pass_r2_0.3"].mean()]
ax.barh(range(4), vals[::-1], color=["white", "white", "0.35", "0.35"], edgecolor="black", height=0.6)
ax.set_yticks(range(4)); ax.set_yticklabels(labels[::-1], fontsize=6.8)
for i, v in enumerate(vals[::-1]):
    ax.text(v + 1.5, i, f"{v:.1f}%", va="center", fontsize=7)
ax.set_xlim(0, 105); ax.set_xlabel("Flows with local fit R$^2$ at least 0.3 (%)", fontsize=7.5)
ax.set_title("(a) Share of valid LIME fits", fontsize=8)
ax = axes[1]
bins = np.logspace(0, np.log10(250), 26)
ax.hist(a.ess, bins=bins, histtype="stepfilled", color="0.75", edgecolor="black", label="M0, original background")
ax.hist(c.ess, bins=bins, histtype="step", color="black", hatch="///", label="M1, corrected background", lw=1.0)
ax.axvline(2, color="black", ls="--", lw=0.9)
ax.set_xscale("log"); ax.set_xlabel("Effective sample size of the perturbed samples", fontsize=7.5); ax.set_ylabel("Real flows", fontsize=7.5)
ax.text(2.2, ax.get_ylim()[1] * 0.55, "validity limit", fontsize=6.8, rotation=90, va="center")
ax.legend(frameon=False, fontsize=6.8, loc="upper right"); ax.set_title("(b) Neighborhood size on real flows", fontsize=8)
for ax in axes:
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
fig.tight_layout()
save(fig, "fig6_lime")

# ---------- Fig. 7: latency ----------
con = sqlite3.connect(r"file:C:\Users\LOQ\Downloads\SELF_KLTN\IDS_M1_Lab\data\ids_system.db?mode=ro", uri=True)
t = pd.read_sql("select step, duration_ms from Timing", con)
order = [("normalize", "Validation"), ("predict", "XGBoost"), ("shap", "TreeSHAP"), ("reliability", "Flags"), ("total", "Request total")]
fig, ax = plt.subplots(figsize=(3.4, 2.0), dpi=300)
data = [t[t.step == s].duration_ms.to_numpy() for s, _ in order]
bp = ax.boxplot(data, vert=False, whis=(5, 95), showfliers=False, patch_artist=True, widths=0.55)
for p in bp["boxes"]:
    p.set_facecolor("0.8"); p.set_edgecolor("black")
for m in bp["medians"]:
    m.set_color("black")
ax.set_yticklabels([f"{n} (n={len(d)})" for (_, n), d in zip(order, data)], fontsize=6.8)
ax.set_xscale("log"); ax.set_xlabel("Time per flow or alert (ms, log scale)", fontsize=7.5); ax.invert_yaxis()
ax.set_xticks([2, 5, 10, 20, 50, 100]); ax.set_xticklabels(["2", "5", "10", "20", "50", "100"], fontsize=7)
ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
save(fig, "fig7_latency")
print("ok")
