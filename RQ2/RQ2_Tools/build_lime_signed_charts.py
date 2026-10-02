"""Bieu do rieng cho LIME co DAU (duong/am): huong anh huong cua feature.
Chay tu thu muc goc: python RQ2_Tools/build_lime_signed_charts.py
"""
from pathlib import Path
import glob
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parent.parent
OUT = R / "RQ2_LIME_FI" / "report_charts"
latest = lambda pat: sorted(glob.glob(str(R / pat)))[-1]
lime = pd.read_csv(latest("RQ2_LIME_FI/rq2_lime_paired/*/lime_per_flow_long.csv"))
sc = pd.read_csv(latest("RQ2_LIME_FI/rq2_lime_paired/*/lime_sample_scores.csv"))
shap = pd.read_csv(latest("RQ2_SHAP/rq2_paired_cohort/*/shap_per_flow_long.csv"))
lime = lime.merge(sc[["sample_id", "true_label"]], on="sample_id")
shap = shap.merge(sc[["sample_id", "true_label"]], on="sample_id")
POS, NEG = "#C0392B", "#2471A3"   # duong = day ve lop du doan, am = keo di
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

def top_signed(df, col, cls, k=5):
    g = df[df.true_label == cls].groupby("feature")[col]
    mean, absm = g.mean(), g.apply(lambda s: s.abs().mean())
    top = absm.nlargest(k).index
    return mean[top][::-1]

classes = sorted(sc.true_label.unique())
# 1) LIME co dau: luoi 15 lop
fig, axes = plt.subplots(5, 3, figsize=(15, 15))
for ax, c in zip(axes.ravel(), classes):
    s = top_signed(lime, "weight", c)
    ax.barh(s.index, s.values, color=[POS if v > 0 else NEG for v in s.values])
    ax.axvline(0, color="k", lw=.6); ax.set_title(c, fontsize=10, fontweight="bold")
for ax in axes.ravel()[len(classes):]: ax.axis("off")
fig.suptitle("LIME - Top-5 feature theo lop, trung binh CO DAU (do = duong, day ve lop du doan; xanh = am, keo di)", y=.995)
fig.tight_layout(); fig.savefig(OUT / "lime_signed_top5_all_classes.png", dpi=150); plt.close(fig)

# 2) SHAP vs LIME co dau, 4 lop dai dien
reps = [c for c in ["Bot", "DDOS attack-HOIC", "DoS attacks-Hulk", "SSH-Bruteforce"] if c in classes]
fig, axes = plt.subplots(len(reps), 2, figsize=(11, 3 * len(reps)))
for i, c in enumerate(reps):
    for j, (name, df, col) in enumerate([("SHAP", shap, "shap_value"), ("LIME", lime, "weight")]):
        s = top_signed(df, col, c); ax = axes[i, j]
        ax.barh(s.index, s.values, color=[POS if v > 0 else NEG for v in s.values])
        ax.axvline(0, color="k", lw=.6); ax.set_title(f"{c} - {name}", fontsize=10)
fig.suptitle("Cung lop, cung flow: huong (duong/am) cua SHAP va LIME", y=.999)
fig.tight_layout(); fig.savefig(OUT / "shap_vs_lime_signed_representative.png", dpi=150); plt.close(fig)

# 3) Ty le dong y dau tren cac feature Top-10 cua LIME theo lop
a = lime.merge(shap[["sample_id", "feature", "shap_value"]], on=["sample_id", "feature"])
a["same"] = np.sign(a.weight) == np.sign(a.shap_value)
a["r"] = a.groupby("sample_id").abs_weight.rank(ascending=False, method="first")
ag = a[a.r <= 10].groupby("true_label").same.mean().reindex(classes) * 100
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(ag.index[::-1], ag.values[::-1], color="#5D6D7E"); ax.set_xlim(0, 100)
ax.set_xlabel("% feature Top-10 cua LIME co cung dau voi SHAP"); ax.set_title("Dong y ve HUONG anh huong SHAP - LIME theo lop")
for y, v in enumerate(ag.values[::-1]): ax.text(v + 1, y, f"{v:.0f}%", va="center", fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "lime_sign_agreement_by_class.png", dpi=150); plt.close(fig)
ag.round(1).to_csv(OUT / "lime_sign_agreement_by_class.csv", header=["pct_same_sign"], encoding="utf-8-sig")

# 4) Phan bo Local R2
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(sc.local_r2, bins=40, color="#7F8C8D"); ax.axvline(0.3, color=POS, ls="--", label="nguong 0,3")
ax.axvline(sc.local_r2.median(), color=NEG, label=f"trung vi {sc.local_r2.median():.3f}")
ax.set_xlabel("Local R2"); ax.set_ylabel("So flow"); ax.legend(); ax.set_title("Phan bo Local R2 cua LIME (1.339 flow)")
fig.tight_layout(); fig.savefig(OUT / "lime_r2_histogram.png", dpi=150); plt.close(fig)

# 5) Vi du 1 flow: waterfall kieu LIME (co dau)
sid = sc.sort_values("local_r2").iloc[-1].sample_id
f = lime[lime.sample_id == sid].nlargest(10, "abs_weight")[::-1]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.barh(f.feature, f.weight, color=[POS if v > 0 else NEG for v in f.weight]); ax.axvline(0, color="k", lw=.6)
lab = sc[sc.sample_id == sid].iloc[0]
ax.set_title(f"Vi du 1 flow (id {sid}, {lab.true_label}, R2={lab.local_r2:.2f}) - LIME Top-10 co dau")
fig.tight_layout(); fig.savefig(OUT / "lime_single_flow_example.png", dpi=150); plt.close(fig)
print(ag.round(0).to_string())
