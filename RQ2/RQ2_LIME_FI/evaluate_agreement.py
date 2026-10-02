"""BUOC 2 - Sub-RQ 2.1: Do do tuong dong SHAP-LIME tren dung cohort ghep cap.

Ghep shap_per_flow_long.csv (RQ2_SHAP) voi lime_per_flow_long.csv (RQ2_LIME) theo
sample_id + feature. Voi moi flow va moi k trong {3, 5, 10}:
  - Jaccard@k     = |Top-k SHAP giao Top-k LIME| / |Top-k SHAP hop Top-k LIME|
  - Spearman      = spearman(shap_value, weight) CHI tren cac feature CHUNG giua
                    hai Top-k (NA neu <2 feature chung)
  - Signed agreement = ti le feature chung ma dau (sign) cua shap_value va weight
                    giong nhau (NA neu 0 feature chung)

Gop theo true_label (median, mean, std, N), roi macro-average khong trong so tren
15 lop. SQL Injection chi co N=9 flow trong cohort chinh - duoc ghi ro rang trong
output, KHONG gop im lang voi cac lop khac.

Chay tu goc du an:
    python RQ2_LIME/evaluate_agreement.py
hoac chi dinh thu muc SHAP/LIME neu co nhieu ban chay:
    python RQ2_LIME/evaluate_agreement.py --shap-dir <...> --lime-dir <...>

Output (RQ2_LIME/rq2_agreement/<timestamp>/):
  per_flow_agreement.csv   - sample_id, true_label, jaccard_k, spearman_k, signed_agreement_k, n_common_k (k=3,5,10)
  summary_by_class.csv     - mean/median/std/N theo 15 lop cho tung chi so va tung k
  summary_macro.csv        - macro-average khong trong so tren 15 lop
  run_info.json
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import platform
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


KS = (3, 5, 10)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def latest_subdir(root):
    candidates = sorted([p for p in root.iterdir() if p.is_dir()])
    if not candidates:
        raise FileNotFoundError(f"Khong tim thay thu muc con trong {root}")
    return candidates[-1]


def per_flow_metrics(group, ks=KS):
    g_shap = group.sort_values("abs_shap_value", ascending=False)
    g_lime = group.sort_values("abs_weight", ascending=False)
    by_feature = group.set_index("feature")
    out = {}
    for k in ks:
        top_shap = list(g_shap["feature"].iloc[:k])
        top_lime = list(g_lime["feature"].iloc[:k])
        set_shap, set_lime = set(top_shap), set(top_lime)
        inter = set_shap & set_lime
        union = set_shap | set_lime
        out[f"jaccard_{k}"] = len(inter) / len(union) if union else np.nan
        out[f"n_common_{k}"] = len(inter)
        if len(inter) >= 2:
            common = by_feature.loc[list(inter)]
            if common["shap_value"].nunique() > 1 and common["weight"].nunique() > 1:
                rho, _ = spearmanr(common["shap_value"], common["weight"])
            else:
                rho = np.nan  # spearman khong xac dinh khi mot chuoi hang so
            out[f"spearman_{k}"] = rho
        else:
            out[f"spearman_{k}"] = np.nan
        if len(inter) > 0:
            common = by_feature.loc[list(inter)]
            same_sign = np.sign(common["shap_value"]) == np.sign(common["weight"])
            out[f"signed_agreement_{k}"] = float(same_sign.mean())
        else:
            out[f"signed_agreement_{k}"] = np.nan
    return pd.Series(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--shap-dir", type=Path, default=None, help="Thu muc cohort SHAP (co shap_per_flow_long.csv)")
    parser.add_argument("--lime-dir", type=Path, default=None, help="Thu muc ket qua LIME (co lime_per_flow_long.csv)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.project.resolve()
    shap_dir = (args.shap_dir or latest_subdir(root / "RQ2_SHAP" / "rq2_paired_cohort")).resolve()
    lime_dir = (args.lime_dir or latest_subdir(root / "RQ2_LIME" / "rq2_lime_paired")).resolve()

    shap_long_path = shap_dir / "shap_per_flow_long.csv"
    lime_long_path = lime_dir / "lime_per_flow_long.csv"
    manifest_path = shap_dir / "manifest_main.csv"
    for p in (shap_long_path, lime_long_path, manifest_path):
        if not p.is_file():
            raise FileNotFoundError(f"Khong thay {p}")

    out = (args.output or Path(__file__).resolve().parent / "rq2_agreement" /
           datetime.now().strftime("%Y%m%d_%H%M%S_%f")).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Thu muc da co du lieu: {out}. Dung --output khac.")
    out.mkdir(parents=True, exist_ok=True)

    print("[1/4] Nap manifest, SHAP long, LIME long...", flush=True)
    manifest = pd.read_csv(manifest_path)
    shap_long = pd.read_csv(shap_long_path)
    lime_long = pd.read_csv(lime_long_path)

    shap_ids = set(shap_long["sample_id"].unique())
    lime_ids = set(lime_long["sample_id"].unique())
    manifest_ids = set(manifest["sample_id"].unique())
    if shap_ids != manifest_ids:
        raise ValueError(f"SHAP sample_id khong khop manifest: chi co trong SHAP {shap_ids - manifest_ids}, "
                          f"chi co trong manifest {manifest_ids - shap_ids}")
    if lime_ids != manifest_ids:
        raise ValueError(f"LIME sample_id khong khop manifest: chi co trong LIME {lime_ids - manifest_ids}, "
                          f"chi co trong manifest {manifest_ids - lime_ids}")

    print("[2/4] Ghep SHAP va LIME theo sample_id + feature...", flush=True)
    combined = pd.merge(
        shap_long[["sample_id", "feature", "shap_value", "abs_shap_value"]],
        lime_long[["sample_id", "feature", "weight", "abs_weight"]],
        on=["sample_id", "feature"], how="inner",
    )
    expected_rows = len(manifest) * 78
    if len(combined) != expected_rows:
        raise ValueError(f"So dong sau ghep ({len(combined)}) khac ky vong ({expected_rows}). "
                          f"Kiem tra feature co dong bo giua SHAP va LIME khong.")

    print("[3/4] Tinh Jaccard/Spearman/signed agreement theo tung flow, k = 3, 5, 10...", flush=True)
    per_flow = combined.groupby("sample_id").apply(per_flow_metrics, include_groups=False).reset_index()
    per_flow = per_flow.merge(manifest[["sample_id", "true_label", "predicted_label"]], on="sample_id", how="left")
    cols_order = ["sample_id", "true_label", "predicted_label"] + [c for c in per_flow.columns
                  if c not in ("sample_id", "true_label", "predicted_label")]
    per_flow = per_flow[cols_order]
    per_flow.to_csv(out / "per_flow_agreement.csv", index=False, encoding="utf-8-sig")

    print("[4/4] Gop theo lop va macro-average tren 15 lop...", flush=True)
    metric_cols = [c for c in per_flow.columns if c.startswith(("jaccard_", "spearman_", "signed_agreement_"))]
    class_sizes = manifest.groupby("true_label").size().rename("N")

    rows = []
    for label, group in per_flow.groupby("true_label"):
        row = {"true_label": label, "N": class_sizes.loc[label]}
        for col in metric_cols:
            vals = group[col].dropna()
            row[f"{col}_mean"] = vals.mean() if len(vals) else np.nan
            row[f"{col}_median"] = vals.median() if len(vals) else np.nan
            row[f"{col}_std"] = vals.std() if len(vals) > 1 else np.nan
            row[f"{col}_n_valid"] = len(vals)
        rows.append(row)
    summary_by_class = pd.DataFrame(rows).sort_values("true_label").reset_index(drop=True)
    summary_by_class.to_csv(out / "summary_by_class.csv", index=False, encoding="utf-8-sig")

    # Macro-average: trung binh KHONG trong so tren 15 dong lop cua summary_by_class (moi lop dong gop = nhau,
    # bat ke N lon hay nho - vi du SQL Injection N=9 van co trong so bang Benign N=100).
    macro = {"n_classes": len(summary_by_class)}
    for col in metric_cols:
        macro[f"{col}_macro_mean_of_class_means"] = summary_by_class[f"{col}_mean"].mean()
        macro[f"{col}_macro_mean_of_class_medians"] = summary_by_class[f"{col}_median"].mean()
    macro_df = pd.DataFrame([macro])
    macro_df.to_csv(out / "summary_macro.csv", index=False, encoding="utf-8-sig")

    small_n_classes = class_sizes[class_sizes < 30].to_dict()
    print("Kich co mau nho (N<30) can ghi ro khi bao cao, KHONG gop im lang:")
    for label, n in small_n_classes.items():
        print(f"  - {label}: N={n}")

    print("\nTom tat macro-average (khong trong so, 15 lop):")
    for k in KS:
        print(f"  k={k}: Jaccard mean-of-class-mean={macro[f'jaccard_{k}_macro_mean_of_class_means']:.4f} | "
              f"Spearman mean-of-class-mean={macro[f'spearman_{k}_macro_mean_of_class_means']:.4f} | "
              f"Signed agreement mean-of-class-mean={macro[f'signed_agreement_{k}_macro_mean_of_class_means']:.4f}")

    info = dict(
        status="complete",
        protocol="sub_rq_2_1_shap_lime_agreement_v1",
        shap_dir=str(shap_dir), lime_dir=str(lime_dir),
        n_flow=len(manifest), ks=list(KS),
        small_n_classes=small_n_classes,
        input_sha256={str(p): sha256(p) for p in (shap_long_path, lime_long_path, manifest_path)},
        script_sha256=sha256(Path(__file__)),
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
    )
    save_json(out / "run_info.json", info)
    print(f"\nHOAN TAT. Ket qua: {out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
