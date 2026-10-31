"""Hình cho bản tiếng Việt của bài báo. Chỉ dùng thang xám. Số liệu đọc từ file kết quả hoặc paper_checks.json."""
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
OUT = r"C:\Users\LOQ\Downloads\SELF_KLTN\Paper_IEEE\figures_vi"
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 8})
checks = json.load(open(R4 + r"\paper_checks.json", encoding="utf-8"))


def vn(x, nd=2):
    return f"{x:.{nd}f}".replace(".", ",")


def save(fig, name):
    fig.savefig(f"{OUT}\\{name}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUT}\\{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


def bx(ax, x, y, w, h, t, fs=6.9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.8", fc="white", ec="black", lw=0.9))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, linespacing=1.3)


def ar(ax, p, q):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="->", lw=0.9, color="black"))


# ---------- Hình 1: chuỗi bằng chứng ----------
fig, ax = plt.subplots(figsize=(7.1, 2.9), dpi=300)
ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off")
live = checks["intervals_95"]["M0_alerts_on_784"]
texts = [
    f"1. Quan sát\nM0 báo tấn công trên\n149 trên 784 flow bình\nthường ({vn(live['rate_pct'])}%, KTC 95%\n{vn(live['wilson'][0])} đến {vn(live['wilson'][1])})",
    "2. SHAP\nFIN Flag Cnt đóng góp\n+5,87 log-odds trung\nbình, gấp 2,3 lần đặc\ntrưng kế tiếp",
    "3. Đường đi quyết định\nMột cảnh báo sai đi qua\ncây 38. Cả 100 cây của\nlớp Hulk đều tách theo\nFIN Flag Cnt",
    "4. Vùng FIN\nSố cờ FIN từ 1 trở lên,\ngói forward lớn nhất từ\n66 B, header forward\nnhỏ hơn 32 B",
    "5. Thử can thiệp\nĐặt FIN Flag Cnt về 0\nđổi nhãn của 148 trên\n148 flow trong vùng",
    "6. Kiểm tra dữ liệu\nVùng ở tập gốc: 445\nHulk, 0 Benign. Vùng ở\ntập đã sửa: 405.347\nBenign, 330 Hulk",
    "7. M1 huấn luyện lại\n0 trên 784 cảnh báo\n(cận trên 95%\nlà 0,47%)",
]
W, H = 22.5, 16
xs1 = [0.5, 25.8, 51.1, 76.4]
xs2 = [0.5, 25.8, 51.1]
for t, x in zip(texts[:4], xs1):
    bx(ax, x, 25, W, H, t, fs=6.4)
for t, x in zip(texts[4:], xs2):
    bx(ax, x, 2, W, H, t, fs=6.4)
for x in xs1[:-1]:
    ar(ax, (x + W + 0.3, 33), (x + 3.0 + W, 33))
for x in xs2[:-1]:
    ar(ax, (x + W + 0.3, 10), (x + 3.0 + W, 10))
ax.plot([87.6, 87.6], [25, 21.5], color="black", lw=0.9)
ax.plot([87.6, 11.7], [21.5, 21.5], color="black", lw=0.9)
ar(ax, (11.7, 21.5), (11.7, 18.3))
save(fig, "fig1_chain")

# ---------- Hình 2: sơ đồ hệ thống ----------
fig, ax = plt.subplots(figsize=(7.1, 2.0), dpi=300)
ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")
top = [("Lưu lượng mạng\n(trực tiếp hoặc PCAP)", 0.5), ("Bắt gói tin\n(Npcap, Scapy)", 25.8), ("Trích xuất flow\n(CICFlowMeter,\n78 đặc trưng)", 51.1), ("Bộ nạp flow\nvà REST API", 76.4)]
bot = [("Bảng điều khiển\n(SHAP; LIME theo\nyêu cầu)", 0.5), ("Cờ độ tin cậy\n(môi trường,\nlớp hiếm)", 25.8), ("Giải thích\nTreeSHAP", 51.1), ("Bộ phát hiện\nXGBoost", 76.4)]
for t, x in top:
    bx(ax, x, 17, W, 10, t, fs=7.0)
for t, x in bot:
    bx(ax, x, 2, W, 10, t, fs=7.0)
for x in (0.5, 25.8, 51.1):
    ar(ax, (x + W + 0.3, 22), (x + 3.0 + W, 22))
ar(ax, (87.6, 17), (87.6, 12.3))
for x in (25.8, 51.1, 76.4):
    ar(ax, (x - 0.3, 7), (x - 3.0, 7))
save(fig, "fig2_pipeline")

# ---------- Hình 3: số flow trong vùng FIN ----------
fig, ax = plt.subplots(figsize=(3.4, 2.1), dpi=300)
cats = ["Tập huấn luyện\ngốc", "Tập huấn luyện\nđã sửa"]
ben = [0, 405347]; hulk = [445, 330]
x = np.arange(2); w = 0.34
ax.bar(x - w / 2, [max(v, 0.6) for v in ben], w, color="white", edgecolor="black", hatch="///", label="Benign")
ax.bar(x + w / 2, hulk, w, color="0.35", edgecolor="black", label="DoS-Hulk")
ax.set_yscale("log"); ax.set_ylim(0.5, 3e6)
for xi, v in zip(x - w / 2, ben):
    ax.text(xi, max(v, 0.6) * 1.5, f"{v:,}".replace(",", "."), ha="center", fontsize=7)
for xi, v in zip(x + w / 2, hulk):
    ax.text(xi, v * 1.5, f"{v:,}".replace(",", "."), ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=7.5)
ax.set_ylabel("Số flow trong vùng FIN (thang log)", fontsize=7.5)
ax.legend(frameon=False, fontsize=7, loc="upper left")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
save(fig, "fig3_zone")

# ---------- Hình 4: SHAP của đầu ra Hulk cho hai mô hình trên cùng 148 flow ----------
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.3), dpi=300)
for ax, key, title in ((axes[0], "shap_hulk_class_M0", "(a) M0, đầu ra DoS-Hulk"), (axes[1], "shap_hulk_class_M1", "(b) M1, đầu ra DoS-Hulk")):
    d = checks[key]["top8"]
    names = list(d.keys())[::-1]; vals = [d[n] for n in names]
    ax.barh(range(len(vals)), vals, color=["0.35" if v > 0 else "white" for v in vals], edgecolor="black", height=0.62)
    ax.set_yticks(range(len(vals))); ax.set_yticklabels(names, fontsize=7)
    ax.axvline(0, color="black", lw=0.7)
    ax.set_title(title, fontsize=8); ax.set_xlabel("Giá trị SHAP trung bình (log-odds)", fontsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
fig.tight_layout()
save(fig, "fig4_shap")

# ---------- Hình 5: đánh giá theo khối thời gian của M1 ----------
b = pd.read_csv(R4 + r"\blocked_cv_m1.csv")
full = b[b.bo == "khoi_thoi_gian"].sort_values("fold"); ded = b[b.bo == "khoi_thoi_gian_sach"].sort_values("fold")
fig, ax = plt.subplots(figsize=(3.4, 2.0), dpi=300)
x = np.arange(5); w = 0.36
ax.bar(x - w / 2, full.macro_f1, w, color="0.35", edgecolor="black", label="Toàn bộ flow kiểm thử")
ax.bar(x + w / 2, ded.macro_f1, w, color="white", edgecolor="black", hatch="///", label="Đã loại flow trùng")
ax.set_ylim(96, 100.4); ax.set_xticks(x); ax.set_xticklabels([f"Khối {i + 1}" for i in range(5)], fontsize=7)
ax.set_ylabel("Macro F1 (%)", fontsize=7.5); ax.legend(frameon=False, fontsize=6.6, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
save(fig, "fig5_blocked")

# ---------- Hình 6: độ hợp lệ của LIME ----------
sw = pd.read_csv(R4 + r"\lab_m1\lime_kernel_sweep.csv")
a = sw[(sw.model == "M0_nen_goc") & (sw.kernel_width == 3.312)]
c = sw[(sw.model == "M1_nen_da_sua") & (sw.kernel_width == 3.312)]
fig, axes = plt.subplots(1, 3, figsize=(7.1, 2.2), dpi=300, gridspec_kw={"width_ratios": [1.1, 0.9, 1.0]})
ax = axes[0]
labels = ["Nhóm RQ2 (1.339)", "RQ2, Benign (100)", "Flow thật, M0 (313)", "Flow thật, M1 (313)"]
vals = [85.96, 23.0, 100 * a["passed"].mean(), 100 * c["passed"].mean()]
ax.barh(range(4), vals[::-1], color=["white", "white", "0.35", "0.35"], edgecolor="black", height=0.6)
ax.set_yticks(range(4)); ax.set_yticklabels(labels[::-1], fontsize=6.6)
for i, v in enumerate(vals[::-1]):
    ax.text(v + 1.5, i, f"{vn(v, 1)}%", va="center", fontsize=6.8)
ax.set_xlim(0, 112); ax.set_xlabel("Flow có R$^2$ từ 0,3 (%)", fontsize=7)
ax.set_title("(a) Khớp hợp lệ, kernel 3,312", fontsize=7.6)
ax = axes[1]
bins = np.logspace(0, np.log10(250), 26)
ax.hist(a.ess, bins=bins, histtype="stepfilled", color="0.75", edgecolor="black", label="M0, nền gốc")
ax.hist(c.ess, bins=bins, histtype="step", color="black", hatch="///", label="M1, nền đã sửa", lw=1.0)
ax.axvline(2, color="black", ls="--", lw=0.9)
ax.set_xscale("log"); ax.set_xlabel("Cỡ mẫu hiệu dụng", fontsize=7); ax.set_ylabel("Flow thật", fontsize=7)
ax.legend(frameon=False, fontsize=6.4, loc="upper right"); ax.set_title("(b) Kích thước lân cận", fontsize=7.6)
ax = axes[2]
for model, style, lab in (("M0_nen_goc", "--", "M0, nền gốc"), ("M1_nen_da_sua", "-", "M1, nền đã sửa")):
    g = sw[sw.model == model].groupby("kernel_width").passed.mean() * 100
    ax.plot(g.index, g.values, style, marker="o", color="black", ms=3, lw=1.0, label=lab)
ax.set_xscale("log"); ax.set_ylim(-3, 108)
ax.set_xlabel("Độ rộng kernel", fontsize=7); ax.set_ylabel("Flow thật có R$^2$ từ 0,3 (%)", fontsize=6.8)
ax.legend(frameon=False, fontsize=6.4, loc="center right"); ax.set_title("(c) Kernel rộng hơn", fontsize=7.6)
for ax in axes:
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
fig.tight_layout()
save(fig, "fig6_lime")

# ---------- Hình 7: độ trễ ----------
con = sqlite3.connect(r"file:C:\Users\LOQ\Downloads\SELF_KLTN\IDS_M1_Lab\data\ids_system.db?mode=ro", uri=True)
t = pd.read_sql("select step, duration_ms from Timing", con)
order = [("normalize", "Kiểm tra dữ liệu"), ("predict", "XGBoost"), ("shap", "TreeSHAP"), ("reliability", "Cờ"), ("total", "Cả yêu cầu")]
fig, ax = plt.subplots(figsize=(3.4, 2.0), dpi=300)
data = [t[t.step == s].duration_ms.to_numpy() for s, _ in order]
bp = ax.boxplot(data, orientation="horizontal", whis=(5, 95), showfliers=False, patch_artist=True, widths=0.55)
for p in bp["boxes"]:
    p.set_facecolor("0.8"); p.set_edgecolor("black")
for m in bp["medians"]:
    m.set_color("black")
ax.set_yticklabels([f"{n} (n={len(d)})" for (_, n), d in zip(order, data)], fontsize=6.8)
ax.set_xscale("log"); ax.set_xlabel("Thời gian cho mỗi flow hoặc cảnh báo (ms, thang log)", fontsize=7.2); ax.invert_yaxis()
ax.set_xticks([2, 5, 10, 20, 50, 100]); ax.set_xticklabels(["2", "5", "10", "20", "50", "100"], fontsize=7)
ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
save(fig, "fig7_latency")
print("ok")
