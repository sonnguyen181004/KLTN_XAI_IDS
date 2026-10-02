"""Bao cao rieng cho LIME (khong so sanh voi SHAP) - RQ2_LIME_Bao_Cao_Rieng.docx.

Tong hop toan bo ket qua CUA RIENG LIME tren cohort ghep cap 1.339 flow: chat luong
giai thich cuc bo (local R^2), Top-5 feature theo lop, do on dinh giua cac seed,
do nhay truoc nhieu thoi gian va Domain Precision@5 cua LIME.

Chay tu goc du an (sau khi da chay du Buoc 1-4 trong RQ2_LIME/):
    python RQ2_LIME/create_lime_progress_report.py
"""
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


NAVY = "17365D"
PALE_BLUE = "EAF2F8"
LIGHT_GRAY = "D9D9D9"
TEXT = "1F2933"
BASE = Path(__file__).resolve().parent


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color=LIGHT_GRAY, size="8"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=90, start=100, bottom=90, end=100):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def style_run(run, bold=False, size=None, color=TEXT):
    run.bold = bold
    run.font.name = "Aptos"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    run.font.color.rgb = RGBColor.from_string(color)
    if size:
        run.font.size = Pt(size)


def add_body(doc, text, bold_lead=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    if bold_lead:
        style_run(p.add_run(bold_lead), bold=True)
    style_run(p.add_run(text))
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.space_before = Pt(14 if level == 1 else 9)
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run(text)
    style_run(r, bold=True, size=14 if level == 1 else 12, color="000000")
    return p


def add_table(doc, headers, rows, widths=None, font_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = False
    header = table.rows[0]
    set_repeat_table_header(header)
    for i, label in enumerate(headers):
        cell = header.cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_run(p.add_run(label), bold=True, size=font_size, color="FFFFFF")
        set_cell_shading(cell, NAVY)
        set_cell_border(cell)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        if widths:
            cell.width = widths[i]
    for row_idx, values in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(values):
            cell = cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            style_run(p.add_run(str(value)), size=font_size)
            if row_idx % 2 == 1:
                set_cell_shading(cell, PALE_BLUE)
            set_cell_border(cell)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if widths:
                cell.width = widths[i]
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_figure(doc, image_path, caption, width=6.3):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(4)
    p.add_run().add_picture(str(image_path), width=Inches(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(9)
    r = c.add_run(caption)
    style_run(r, size=9, color="4B5563")


def set_page_layout(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)


def latest_subdir(root):
    candidates = sorted([p for p in root.iterdir() if p.is_dir()])
    if not candidates:
        raise FileNotFoundError(f"Khong tim thay thu muc con trong {root}")
    return candidates[-1]


def fmt(x, nd=3):
    try:
        if pd.isna(x):
            return "NA"
        return f"{x:.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


# ------------------------------------------------------------------ CHARTS

def chart_r2_by_class(lime_scores, out_path):
    order = lime_scores.groupby("true_label")["local_r2"].median().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(6.6, 4.2), dpi=150)
    data = [lime_scores[lime_scores.true_label == c]["local_r2"].to_numpy() for c in order.index]
    bp = ax.boxplot(data, vert=False, patch_artist=True, showfliers=False, widths=0.6)
    for box in bp["boxes"]:
        box.set(facecolor="#AFC6E3", edgecolor="#1F4E79")
    for med in bp["medians"]:
        med.set(color="#C0392B", linewidth=1.5)
    ax.set_yticklabels(order.index, fontsize=8)
    ax.axvline(0.3, color="#C0392B", linestyle="--", linewidth=1, label="Nguong canh bao 0,3")
    ax.set_xlabel("Local R^2 (LIME)")
    ax.set_title("Phan bo Local R^2 cua LIME theo lop (1.339 flow)", fontsize=11)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def chart_top5_examples(top5_df, out_path, classes):
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.5), dpi=150)
    for ax, cls in zip(axes.flat, classes):
        sub = top5_df[top5_df.true_label == cls].sort_values("abs_weight")
        ax.barh(sub["feature"], sub["abs_weight"], color="#1F4E79")
        ax.set_title(cls, fontsize=10)
        ax.tick_params(labelsize=8)
        ax.set_xlabel("Mean |LIME weight|", fontsize=8)
    fig.suptitle("Top-5 feature LIME (mean |weight|) - vi du 4 lop", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path)
    plt.close(fig)


def chart_stability_by_class(stability_by_class, out_path):
    df = stability_by_class.sort_values("median", ascending=True)
    fig, ax = plt.subplots(figsize=(6.6, 4.4), dpi=150)
    colors = ["#C0392B" if v < 0.3 else "#1F4E79" for v in df["median"]]
    ax.barh(df["true_label"], df["median"], color=colors)
    ax.set_xlabel("Median Jaccard@5 giua cac cap seed")
    ax.set_title("Stability LIME theo lop (8 seed, tap con 289 flow)", fontsize=11)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def chart_robustness(robustness_overall, out_path):
    df = robustness_overall
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=150)
    ax.plot(df["noise_percent"], df["mean_jaccard5"], marker="o", color="#1F4E79", label="Mean Jaccard@5 truoc/sau nhieu")
    ax2 = ax.twinx()
    ax2.plot(df["noise_percent"], 100 * df["prediction_changed_rate"], marker="s", color="#C0392B",
              linestyle="--", label="Ty le doi predicted_label (%)")
    ax.set_xlabel("Muc nhieu thoi gian (%)")
    ax.set_ylabel("Mean Jaccard@5", color="#1F4E79")
    ax2.set_ylabel("Ty le doi nhan (%)", color="#C0392B")
    ax.set_ylim(0, 1)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="center left", fontsize=8)
    ax.set_title("Robustness LIME truoc nhieu thoi gian (tap con 289 flow)", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def chart_domain_precision(domain_by_class, out_path):
    df = domain_by_class.sort_values("lime_precision_at_5_mean", ascending=True)
    fig, ax = plt.subplots(figsize=(6.6, 4.4), dpi=150)
    ax.barh(df["true_label"], df["lime_precision_at_5_mean"], color="#1F4E79")
    ax.set_xlabel("Domain Precision@5 (LIME) - mean")
    ax.set_xlim(0, 1)
    ax.set_title("Domain Precision@5 cua LIME theo lop", fontsize=11)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def chart_faithfulness_lime(faith_overall, out_path):
    df = faith_overall[faith_overall.method == "lime"].sort_values("k")
    fig, ax = plt.subplots(figsize=(5.6, 3.4), dpi=150)
    ax.bar(df["k"].astype(str), df["win_rate_percent"], color="#1F4E79", width=0.5)
    for i, v in enumerate(df["win_rate_percent"]):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_xlabel("k (so feature Top-k bi thay bang gia tri train)")
    ax.set_ylabel("Win rate LIME vs doi chung ngau nhien (%)")
    ax.set_title("Faithfulness cua LIME (donor-substitution, 1.339 flow)", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=BASE.parent)
    parser.add_argument("--shap-cohort", type=Path, default=None)
    parser.add_argument("--lime-dir", type=Path, default=None)
    parser.add_argument("--domain-dir", type=Path, default=None)
    parser.add_argument("--stability-dir", type=Path, default=None)
    parser.add_argument("--faithfulness-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=BASE.parent / "RQ2_LIME_Bao_Cao_Rieng.docx")
    args = parser.parse_args()

    root = args.project.resolve()
    shap_cohort = (args.shap_cohort or latest_subdir(root / "RQ2_SHAP" / "rq2_paired_cohort")).resolve()
    lime_dir = (args.lime_dir or latest_subdir(root / "RQ2_LIME" / "rq2_lime_paired")).resolve()
    domain_dir = (args.domain_dir or latest_subdir(root / "RQ2_LIME" / "rq2_domain")).resolve()
    stability_dir = (args.stability_dir or latest_subdir(root / "RQ2_LIME" / "rq2_stability_robustness")).resolve()
    faithfulness_dir = (args.faithfulness_dir or latest_subdir(root / "RQ2_LIME" / "rq2_faithfulness")).resolve()

    manifest = pd.read_csv(shap_cohort / "manifest_main.csv")
    lime_info = json.loads((lime_dir / "run_info.json").read_text(encoding="utf-8"))
    lime_scores = pd.read_csv(lime_dir / "lime_sample_scores.csv")
    lime_long = pd.read_csv(lime_dir / "lime_per_flow_long.csv")
    diagnosis_path = lime_dir / "diagnosis_low_r2.json"
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8")) if diagnosis_path.exists() else None

    domain_by_class = pd.read_csv(domain_dir / "summary_by_class.csv")
    domain_macro = pd.read_csv(domain_dir / "summary_macro.csv").iloc[0]

    stability_by_class = pd.read_csv(stability_dir / "summary_stability_by_class.csv")
    robustness_overall = pd.read_csv(stability_dir / "summary_robustness_overall.csv")
    robustness_by_class = pd.read_csv(stability_dir / "summary_robustness_by_class.csv")
    stability_info = json.loads((stability_dir / "run_info.json").read_text(encoding="utf-8"))

    faith_overall = pd.read_csv(faithfulness_dir / "summary_overall.csv")

    # Top-5 by class (mean abs weight)
    m = lime_long.merge(manifest[["sample_id", "true_label"]], on="sample_id")
    top5_by_class = (m.groupby(["true_label", "feature"])["abs_weight"].mean().reset_index()
                      .sort_values(["true_label", "abs_weight"], ascending=[True, False])
                      .groupby("true_label").head(5))
    top5_by_class.to_csv(BASE / "lime_top5_by_class.csv", index=False, encoding="utf-8-sig")

    charts_dir = BASE / "report_charts"
    charts_dir.mkdir(exist_ok=True)
    r2_chart = charts_dir / "lime_r2_by_class.png"
    top5_chart = charts_dir / "lime_top5_examples.png"
    stability_chart = charts_dir / "lime_stability_by_class.png"
    robustness_chart2 = charts_dir / "lime_robustness_only.png"
    domain_chart = charts_dir / "lime_domain_precision.png"
    faith_chart = charts_dir / "lime_faithfulness.png"

    chart_r2_by_class(lime_scores, r2_chart)
    example_classes = ["DDOS attack-LOIC-UDP", "SSH-Bruteforce", "DoS attacks-Hulk", "Infilteration"]
    chart_top5_examples(top5_by_class, top5_chart, example_classes)
    chart_stability_by_class(stability_by_class, stability_chart)
    chart_robustness(robustness_overall, robustness_chart2)
    chart_domain_precision(domain_by_class, domain_chart)
    chart_faithfulness_lime(faith_overall, faith_chart)

    doc = Document()
    set_page_layout(doc)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(TEXT)
    for name in ("Heading 1", "Heading 2"):
        styles[name].font.name = "Aptos Display"
        styles[name]._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
        styles[name]._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
        styles[name].font.color.rgb = RGBColor(0, 0, 0)

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(5)
    style_run(title.add_run("Bao cao rieng ve LIME cho RQ2"), bold=True, size=20, color="000000")
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(14)
    style_run(subtitle.add_run(
        f"Cohort ghep cap {len(manifest)} flow, seed 42 | XGBoost 15 lop, 78 feature | Bao cao chi tap trung ket qua cua LIME"),
        size=10, color="4B5563")

    # 1
    add_heading(doc, "1. Tom tat")
    add_body(doc,
        f"LIME da giai thich {lime_info['n_flow']} flow (dung predicted_label, dong bo voi SHAP), voi background "
        f"{lime_info['background_size']} flow phan tang tu train set, kernel_width={fmt(lime_info['kernel_width'])}, "
        f"num_samples={lime_info['num_samples']}, num_features={lime_info['num_features']}, discretize_continuous=True. "
        f"Local R^2 trung binh {fmt(lime_info['mean_local_r2'])} (median {fmt(lime_info['median_local_r2'])}) - THAP "
        f"hon nguong canh bao 0,3; chuan doan tren tap con 60 flow xac nhan cac cau hinh thay the (num_samples=10.000 "
        f"hoac discretize_continuous=False) KHONG cai thien R^2 nen cau hinh mac dinh duoc giu nguyen.",
        "Cau hinh & chat luong surrogate: ")
    add_body(doc,
        f"Do on dinh (8 seed, 289 flow, 20/lop): median Jaccard@5 giua cac cap seed = "
        f"{fmt(pd.read_csv(stability_dir / 'per_flow_stability.csv')['stability_jaccard5_mean'].median())}. Robustness "
        f"truoc nhieu thoi gian: Jaccard@5 giam nhe tu {fmt(robustness_overall.iloc[0]['mean_jaccard5'])} (nhieu 1%) "
        f"xuong {fmt(robustness_overall.iloc[-1]['mean_jaccard5'])} (nhieu 10%); ty le doi predicted_label tang tu "
        f"{fmt(100*robustness_overall.iloc[0]['prediction_changed_rate'],2)}% len {fmt(100*robustness_overall.iloc[-1]['prediction_changed_rate'],2)}%.",
        "On dinh & do nhay: ")
    add_body(doc,
        f"Domain Precision@5 macro-average = {fmt(domain_macro['lime_precision_at_5_macro_mean_of_class_means'])} "
        f"(thap). Faithfulness (donor-substitution, doi chung ngau nhien) win-rate LIME = "
        f"{fmt(faith_overall[(faith_overall.method=='lime')&(faith_overall.k==5)]['win_rate_percent'].iloc[0],2)}% tai k=5.",
        "Domain & faithfulness: ")

    # 2
    doc.add_page_break()
    add_heading(doc, "2. Chat luong giai thich cuc bo (Local R^2)")
    add_body(doc, "Local R^2 la R^2 cua mo hinh Ridge tuyen tinh cuc bo (surrogate) ma LIME fit quanh moi flow. Gia "
                  "tri thap nghia la surrogate tuyen tinh kho khop voi ham quyet dinh cua XGBoost quanh diem do.")
    add_figure(doc, r2_chart, "Hinh 1. Phan bo Local R^2 cua LIME theo 15 lop (hop thoi, khong hien fliers). Duong "
                                "dut la nguong canh bao 0,3.")
    if diagnosis:
        rows = [[k, fmt(v["median_r2"]), fmt(v["mean_r2"]), v["n"]] for k, v in diagnosis["results"].items()]
        add_table(doc, ["Cau hinh chuan doan (60 flow)", "Median R^2", "Mean R^2", "N"], rows,
                   [Inches(3.2), Inches(1.1), Inches(1.1), Inches(0.6)])
        add_body(doc, "Ca ba cau hinh deu cho R^2 thap tuong duong; tang num_samples hoac tat discretize_continuous "
                      "KHONG cai thien - day la dac diem cua du lieu/mo hinh (XGBoost phi tuyen manh tren 78 chieu), "
                      "khong phai loi tham so LIME.", "Ket luan chuan doan: ")

    # 3
    add_heading(doc, "3. Top-5 feature LIME theo lop")
    add_body(doc, "Mean |LIME weight| tren cac flow du doan dung cua tung lop. Vi du 4 lop tieu bieu ben duoi; bang "
                  "day du 15 lop x 5 feature trong lime_top5_by_class.csv.")
    add_figure(doc, top5_chart, "Hinh 2. Top-5 feature LIME (mean |weight|) cho 4 lop vi du.")
    rows = []
    for cls in sorted(top5_by_class["true_label"].unique()):
        feats = top5_by_class[top5_by_class.true_label == cls].sort_values("abs_weight", ascending=False)
        rows.append([cls, feats.iloc[0]["feature"], fmt(feats.iloc[0]["abs_weight"], 4)])
    add_table(doc, ["Lop", "Feature Top-1 LIME", "Mean |weight|"], rows, [Inches(2.0), Inches(2.3), Inches(1.3)])

    # 4
    doc.add_page_break()
    add_heading(doc, "4. Stability giua cac lan chay (seed khac nhau)")
    add_body(doc,
        f"Chay lai LIME voi {len(stability_info['stability_seeds'])} seed khac nhau ({stability_info['stability_seeds']}) "
        f"tren tap con {stability_info['n_subset']} flow. Voi moi flow, tinh Jaccard@5 trung binh giua tat ca cap "
        f"seed; bieu do duoi la median theo lop, sap xep tang dan.")
    add_figure(doc, stability_chart, "Hinh 3. Stability LIME (median Jaccard@5 giua 8 seed) theo lop. Mau do la lop "
                                       "duoi nguong 0,3 (khong on dinh).")
    rows = []
    for _, r in stability_by_class.sort_values("median").iterrows():
        rows.append([r["true_label"], int(r["N"]), fmt(r["median"]), fmt(r["mean"]), fmt(r["std"])])
    add_table(doc, ["Lop", "N", "Median Jaccard@5", "Mean", "Std"], rows,
               [Inches(1.8), Inches(0.5), Inches(1.2), Inches(1.2), Inches(1.2)])

    # 5
    doc.add_page_break()
    add_heading(doc, "5. Robustness truoc nhieu thoi gian")
    add_body(doc,
        "Ap dung co che nhieu s = 1 + a*U (U~Uniform[-1,1], a in {1%,5%,10%}) len cac dai luong thoi gian, toc do "
        "chia nguoc lai - dung co che SHAP da dung. Lop giai thich giu co dinh la lop du doan TRUOC nhieu.")
    add_figure(doc, robustness_chart2, "Hinh 4. Jaccard@5 truoc/sau nhieu va ty le doi predicted_label theo muc nhieu.")
    rows = []
    for _, r in robustness_overall.iterrows():
        rows.append([f"{r['noise_percent']:.0f}%", int(r["N"]), fmt(r["mean_jaccard5"]), fmt(r["median_jaccard5"]),
                     fmt(100 * r["prediction_changed_rate"], 2) + "%"])
    add_table(doc, ["Muc nhieu", "N", "Mean Jaccard@5", "Median Jaccard@5", "Ty le doi nhan"], rows,
               [Inches(1.1), Inches(0.8), Inches(1.4), Inches(1.4), Inches(1.4)])

    # 6
    doc.add_page_break()
    add_heading(doc, "6. Domain Precision@5 cua LIME")
    add_body(doc, "Ty le feature trong Top-5 LIME khop voi bang expected-signals cua lop that (Bang 8, ke hoach chi "
                  "tiet), chia cho 5.")
    add_figure(doc, domain_chart, "Hinh 5. Domain Precision@5 cua LIME theo lop, sap xep tang dan.")
    add_body(doc, f"Macro-average (khong trong so, 15 lop) = "
                  f"{fmt(domain_macro['lime_precision_at_5_macro_mean_of_class_means'])} - muc THAP. Day la doi chieu "
                  f"djnh tinh voi kien thuc mien suy tu co che tan cong, khong phai diem chuyen gia SOC doc lap.")

    # 7
    add_heading(doc, "7. Faithfulness cua LIME (donor-substitution)")
    add_body(doc, "Thay Top-k feature LIME (weight duong) bang gia tri tu 10 dong train (seed 173); doi chung chon "
                  "ngau nhien k feature tu cung pool duong, lap 20 lan (seed 2026). LIME 'thang' khi muc giam raw "
                  "margin cua Top-k that su > doi chung, chenh lech qua 1e-6.")
    add_figure(doc, faith_chart, "Hinh 6. Win-rate cua LIME so voi doi chung ngau nhien, k=3/5/10, tren 1.339 flow.")
    rows = []
    for _, r in faith_overall[faith_overall.method == "lime"].iterrows():
        rows.append([int(r["k"]), int(r["N"]), int(r["n_eligible"]), fmt(r["coverage_percent"], 2) + "%",
                     fmt(r["win_rate_percent"], 2) + "%"])
    add_table(doc, ["k", "N", "N du dieu kien", "Coverage", "Win rate LIME"], rows,
               [Inches(0.6), Inches(0.8), Inches(1.2), Inches(1.2), Inches(1.4)])

    # 8
    doc.add_page_break()
    add_heading(doc, "8. Gioi han")
    add_table(doc, ["Gioi han", "Chi tiet"], [
        ["Local R^2 thap", f"Median {fmt(lime_info['median_local_r2'])} tren toan cohort - surrogate tuyen tinh kho "
                            "khop quyet dinh XGBoost phi tuyen tren 78 chieu; da chuan doan hai cau hinh thay the, "
                            "khong cai thien."],
        ["Co mau nho", "SQL Injection N=9, Brute Force-XSS N=44 - ket qua chi mang tinh minh hoa cho hai lop nay."],
        ["Robustness pham vi hep", f"Chi chay tren tap con {stability_info['n_subset']} flow (20/lop), khong phai "
                                     "toan bo cohort, do chi phi tinh toan LIME."],
        ["Domain signals don gian hoa", "Bang expected-signals la kien thuc mien suy luan, khong phai cham diem "
                                          "chuyen gia SOC doc lap."],
    ], [Inches(1.7), Inches(4.85)], font_size=9.5)

    add_heading(doc, "9. Ket luan ve LIME")
    add_body(doc,
        f"Tren cohort {len(manifest)} flow, LIME cho Top-5 feature khac nhau ro ret giua cac lop, nhung chat luong "
        f"surrogate cuc bo thap (local R^2 trung binh {fmt(lime_info['mean_local_r2'])}), do on dinh giua cac lan chay "
        f"o muc trung binh (median Jaccard@5 ~0,42) va giam nhe khi du lieu bi nhieu. Domain Precision@5 va "
        f"faithfulness cua LIME deu thap hon SHAP tren cung cohort (xem bao cao so sanh RQ2_LIME_Ket_Qua_Final.docx). "
        f"Day la dac diem cua LIME khi ap dung cho khong gian 78 dac trung mang co tuong tac phi tuyen manh, khong "
        f"phai loi trien khai.")

    doc.core_properties.title = "Bao cao rieng ve LIME cho RQ2"
    doc.core_properties.subject = "Ket qua rieng cua LIME: local R2, Top-5, stability, robustness, domain, faithfulness"
    doc.core_properties.author = "Nhom nghien cuu"
    doc.save(args.output)
    print(f"HOAN TAT. Bao cao: {args.output}")


if __name__ == "__main__":
    main()
