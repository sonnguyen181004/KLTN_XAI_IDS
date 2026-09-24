"""Create PNG charts from the completed SHAP CSV outputs.

Run:
    py -3.14 RQ2_SHAP/create_shap_charts.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "RQ2_SHAP" / "outputs"
FIG = ROOT / "RQ2_SHAP" / "figures"
BLUE = "#17365D"
ORANGE = "#C65D15"
GRID = "#D9E2F3"


def save(fig, name: str) -> None:
    fig.savefig(FIG / name, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def label(value: str) -> str:
    return value.replace(" attacks-", "-").replace(" attack-", "-").replace("Brute Force -", "BF-")


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    prediction = pd.read_csv(DATA / "rq2_shap_sample_predictions.csv")
    ranking = pd.read_csv(DATA / "rq2_shap_ranking_all_features.csv")
    class_top5 = pd.read_csv(DATA / "rq2_shap_top5_by_class.csv")

    # 1. Accuracy per true class in the shared XAI cohort.
    rates = prediction.groupby("true_label")["is_correct"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh([label(x) for x in rates.index], rates.values * 100, color=BLUE)
    ax.set_xlim(0, 108)
    ax.set_xlabel("Tỷ lệ XGBoost dự đoán đúng trên tập XAI (%)")
    ax.set_title("Kết quả XGBoost theo lớp trên 1.363 flow SHAP")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for y, value in enumerate(rates.values * 100):
        ax.text(value + 1.0, y, f"{value:.1f}%", va="center", fontsize=8)
    save(fig, "01_xgboost_accuracy_by_class.png")

    # 2. The most frequent Top-1 feature, with its frequency in the class.
    top1 = ranking[ranking["rank"] == 1].groupby(["true_label", "feature"]).size().reset_index(name="count")
    top1 = top1.sort_values(["true_label", "count"], ascending=[True, False]).groupby("true_label").head(1)
    top1["total"] = top1["true_label"].map(prediction.groupby("true_label").size())
    top1["percent"] = top1["count"] / top1["total"] * 100
    top1 = top1.sort_values("percent")
    fig, ax = plt.subplots(figsize=(10.5, 7.3))
    bars = ax.barh([label(x) for x in top1["true_label"]], top1["percent"], color=BLUE)
    ax.set_xlim(0, 114)
    ax.set_xlabel("Tỷ lệ flow có cùng Top-1 SHAP (%)")
    ax.set_title("Feature Top-1 SHAP xuất hiện nhiều nhất theo lớp")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for bar, (_, row) in zip(bars, top1.iterrows()):
        ax.text(row.percent + 1.0, bar.get_y() + bar.get_height() / 2, f"{row.feature} ({row.percent:.0f}%)", va="center", fontsize=7.6)
    save(fig, "02_shap_top1_frequency_by_class.png")

    # 3. Mean-absolute SHAP Top-5, one small multiple per class, correct predictions only.
    current = class_top5[class_top5["is_correct"] == True].sort_values(["true_label", "class_rank"])
    labels = list(current["true_label"].drop_duplicates())
    fig, axes = plt.subplots(5, 3, figsize=(15.5, 18))
    for ax, class_name in zip(axes.flat, labels):
        part = current[current["true_label"] == class_name].sort_values("mean_abs_shap")
        ax.barh(part["feature"], part["mean_abs_shap"], color=BLUE)
        ax.set_title(label(class_name), fontsize=10, fontweight="bold")
        ax.set_xlabel("Mean |SHAP|", fontsize=8)
        ax.tick_params(axis="y", labelsize=7.3)
        ax.tick_params(axis="x", labelsize=7.3)
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
    for ax in axes.flat[len(labels):]:
        ax.axis("off")
    fig.suptitle("Top-5 SHAP trung bình theo lớp trên các flow XGBoost dự đoán đúng", fontsize=15, fontweight="bold", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    save(fig, "03_shap_top5_mean_by_class.png")

    # 4. Signed local SHAP explanation for one correctly predicted representative flow in each core class.
    core = [
        "DDOS attack-HOIC",
        "DDoS attacks-LOIC-HTTP",
        "DoS attacks-SlowHTTPTest",
        "DoS attacks-Slowloris",
        "SSH-Bruteforce",
        "Infilteration",
        "SQL Injection",
    ]
    representatives = prediction[prediction["is_correct"]].groupby("true_label").head(1).set_index("true_label")
    fig, axes = plt.subplots(4, 2, figsize=(14, 16))
    for ax, class_name in zip(axes.flat, core):
        if class_name not in representatives.index:
            ax.axis("off")
            continue
        sample_id = int(representatives.loc[class_name, "sample_id"])
        part = ranking[(ranking["sample_id"] == sample_id) & (ranking["rank"] <= 5)].sort_values("shap_value")
        colors = [BLUE if value >= 0 else ORANGE for value in part["shap_value"]]
        ax.barh(part["feature"], part["shap_value"], color=colors)
        ax.axvline(0, color="#5B6573", linewidth=0.8)
        ax.set_title(f"{label(class_name)} | sample_id={sample_id}", fontsize=9.5, fontweight="bold")
        ax.set_xlabel("SHAP value cho lớp XGBoost dự đoán", fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
    for ax in axes.flat[len(core):]:
        ax.axis("off")
    fig.suptitle("Giải thích Top-5 SHAP cho các flow đại diện", fontsize=15, fontweight="bold", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    save(fig, "04_shap_local_top5_representatives.png")

    readme = """# Biểu đồ SHAP

1. `01_xgboost_accuracy_by_class.png`: tỷ lệ XGBoost dự đoán đúng theo lớp trong tập 1.363 flow.
2. `02_shap_top1_frequency_by_class.png`: feature Top-1 xuất hiện nhiều nhất và tỷ lệ xuất hiện của nó.
3. `03_shap_top5_mean_by_class.png`: Top-5 mean absolute SHAP của các flow dự đoán đúng theo từng lớp.
4. `04_shap_local_top5_representatives.png`: giải thích có dấu của một flow đại diện. Xanh dương đẩy model về lớp dự đoán, cam kéo model ra khỏi lớp đó.

Biểu đồ 3 dùng để đọc xu hướng theo lớp. Biểu đồ 4 dùng để giải thích một cảnh báo cụ thể. Không dùng biểu đồ 4 để kết luận cho toàn bộ lớp.
"""
    (FIG / "README_figures.md").write_text(readme, encoding="utf-8")
    print(FIG)


if __name__ == "__main__":
    main()
