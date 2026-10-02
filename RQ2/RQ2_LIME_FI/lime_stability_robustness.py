"""BUOC 4 - Sub-RQ 2.3: Stability va Robustness cua LIME tren mot tap con cohort.

STABILITY: chay lai LIME voi 8 seed khac nhau (random_state cua LimeTabularExplainer,
background va flow giu nguyen) tren mot tap con 20 flow/lop (toi da 300 flow, it hon
neu lop hiem hon 20). Voi moi flow, tinh Jaccard Top-5 GIUA TAT CA CAP seed, lay trung
binh -> mot diem stability/flow; bao cao MEDIAN diem nay theo tung lop.

ROBUSTNESS: ap dung DUNG co che nhieu thoi gian ma SHAP da dung (xem shap_noise_robustness.py,
phuc dung tu Bao_cao_RQ_SHAP_XGBoost.docx): moi mau duoc co gian cac dai luong thoi gian
khong am boi he so s = 1 + a*U (U ~ Uniform[-1,1]), a in {1%, 5%, 10%}, toc do tuong ung
chia cho s; 3 seed [42, 123, 2026] cho moi muc nhieu. Lop giai thich duoc GIU CO DINH la
lop du doan TRUOC nhieu (dung quy uoc voi SHAP). Do Jaccard Top-5 truoc/sau nhieu va ty
le doi predicted_label sau nhieu.

GIOI HAN so voi ban SHAP full-test 700k: vi LIME ton chi phi tinh toan lon hon SHAP rat
nhieu (perturb + fit Ridge cho tung mau), robustness LIME o day chi chay tren CUNG tap
con 20 flow/lop (toi da 300 flow) dung cho stability, KHONG phai toan bo 1.339 flow hay
700k flow cua SHAP. Day la mot gioi han pham vi duoc ghi ro, khong suy rong sang toan
tap.

Chay tu goc du an:
    python RQ2_LIME/lime_stability_robustness.py

Output (RQ2_LIME/rq2_stability_robustness/<timestamp>/):
  subset_manifest.csv               - 20 flow/lop dung cho ca hai phep thu
  per_flow_stability.csv            - stability_jaccard5 trung binh cac cap seed, theo flow
  summary_stability_by_class.csv    - median/mean/N theo lop
  per_flow_robustness.csv           - jaccard5 truoc/sau nhieu + prediction_changed, theo flow/level/seed
  summary_robustness_by_class.csv   - mean Jaccard5 va ty le doi nhan theo lop x muc nhieu
  summary_robustness_overall.csv    - gop toan tap con theo muc nhieu
  run_info.json
"""
from pathlib import Path
from datetime import datetime
from itertools import combinations
import argparse
import hashlib
import json
import platform
import sys
import time

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "RQ2_SHAP" / "shap_top5_each_attack"))
from run_lime_paired_cohort import stratified_background_positions, extract_rows, build_explainer  # noqa: E402
from shap_noise_robustness import rescale_time  # noqa: E402


N_PER_CLASS = 20
STABILITY_SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]
NOISE_LEVELS = [0.01, 0.05, 0.10]
NOISE_SEEDS = [42, 123, 2026]
NUM_FEATURES = 78
NUM_SAMPLES = 5000
BASE_SEED = 42
BACKGROUND_SIZE = 8000


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


def top5_from_exp(exp, code):
    local_exp = dict(exp.local_exp[code])
    ranked = sorted(local_exp.items(), key=lambda kv: -abs(kv[1]))[:5]
    return ranked


def jaccard(set_a, set_b):
    union = set_a | set_b
    return len(set_a & set_b) / len(union) if union else np.nan


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--cohort", type=Path, default=None)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--n-per-class", type=int, default=N_PER_CLASS)
    parser.add_argument("--background-size", type=int, default=BACKGROUND_SIZE)
    parser.add_argument("--num-samples", type=int, default=NUM_SAMPLES)
    parser.add_argument("--seed", type=int, default=BASE_SEED)
    args = parser.parse_args()

    root = args.project.resolve()
    cohort_dir = (args.cohort or latest_subdir(root / "RQ2_SHAP" / "rq2_paired_cohort")).resolve()
    manifest_path = cohort_dir / "manifest_main.csv"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Khong thay {manifest_path}")

    out = (args.output or Path(__file__).resolve().parent / "rq2_stability_robustness" /
           datetime.now().strftime("%Y%m%d_%H%M%S_%f")).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Thu muc da co du lieu: {out}. Dung --output khac.")
    out.mkdir(parents=True, exist_ok=True)

    model_path = root / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl"
    encoder_path = model_path.with_name("label_encoder.pkl")
    test_path = root / "dataset/CICID-2018_processed/test_set.parquet"
    train_path = root / "dataset/CICID-2018_processed/train_set.parquet"

    print("[1/7] Nap model, encoder, manifest cohort...", flush=True)
    model, encoder = joblib.load(model_path), joblib.load(encoder_path)
    features = model.get_booster().feature_names
    labels = encoder.classes_.astype(str).tolist()
    manifest = pd.read_csv(manifest_path)

    print(f"[2/7] Lay tap con {args.n_per_class} flow/lop (seed {args.seed})...", flush=True)
    rng_subset = np.random.default_rng(args.seed)
    pieces = []
    for label, group in manifest.groupby("true_label"):
        n = min(args.n_per_class, len(group))
        idx = rng_subset.choice(group.index.to_numpy(), size=n, replace=False)
        pieces.append(group.loc[idx])
    subset = pd.concat(pieces).sort_values("sample_id").reset_index(drop=True)
    subset.to_csv(out / "subset_manifest.csv", index=False, encoding="utf-8-sig")
    print(f"  Tap con: {len(subset)} flow tu {subset['true_label'].nunique()} lop.", flush=True)

    print("[3/7] Lay feature va DOI CHIEU predicted_probability cho tap con...", flush=True)
    frame = pd.read_parquet(test_path)
    sample_ids = subset["sample_id"].to_numpy()
    X_subset = frame.iloc[sample_ids][features].reset_index(drop=True).astype(float)
    proba_now = model.predict_proba(X_subset)
    pred_code_now = proba_now.argmax(axis=1)
    pred_label_now = np.asarray(labels)[pred_code_now]
    if (pred_label_now != subset["predicted_label"].to_numpy()).any():
        raise ValueError("DUNG: predicted_label hien tai lech voi manifest tren tap con.")
    pred_codes = pred_code_now

    print(f"[4/7] Dung background phan tang (~{args.background_size} flow, seed {args.seed}) - dong bo voi Buoc 1...", flush=True)
    bg_positions, _ = stratified_background_positions(train_path, args.seed, args.background_size)
    background_X = extract_rows(train_path, features, bg_positions).astype(float)
    kernel_width = 0.75 * np.sqrt(len(features))
    predict_fn = lambda arr: model.predict_proba(pd.DataFrame(np.asarray(arr), columns=features))

    # ============================== STABILITY ==============================
    print(f"[5/7] STABILITY: {len(STABILITY_SEEDS)} seed x {len(subset)} flow...", flush=True)
    top5_by_seed = {}
    t0 = time.perf_counter()
    for si, seed in enumerate(STABILITY_SEEDS):
        explainer = build_explainer(background_X, features, labels, kernel_width, True, seed)
        top5s = []
        for i in range(len(subset)):
            row = X_subset.iloc[i].to_numpy(dtype=float)
            code = int(pred_codes[i])
            exp = explainer.explain_instance(row, predict_fn, labels=[code],
                                              num_features=NUM_FEATURES, num_samples=args.num_samples)
            ranked = top5_from_exp(exp, code)
            top5s.append(set(f for f, _ in ranked))
        top5_by_seed[seed] = top5s
        print(f"  seed {seed} ({si + 1}/{len(STABILITY_SEEDS)}) xong | {time.perf_counter() - t0:.1f}s", flush=True)

    stability_rows = []
    pairs = list(combinations(STABILITY_SEEDS, 2))
    for i in range(len(subset)):
        jaccards = [jaccard(top5_by_seed[a][i], top5_by_seed[b][i]) for a, b in pairs]
        stability_rows.append(dict(
            sample_id=int(subset.loc[i, "sample_id"]), true_label=subset.loc[i, "true_label"],
            stability_jaccard5_mean=float(np.nanmean(jaccards)),
            stability_jaccard5_min=float(np.nanmin(jaccards)),
            n_seed_pairs=len(pairs),
        ))
    per_flow_stability = pd.DataFrame(stability_rows)
    per_flow_stability.to_csv(out / "per_flow_stability.csv", index=False, encoding="utf-8-sig")
    summary_stability = per_flow_stability.groupby("true_label")["stability_jaccard5_mean"].agg(
        ["median", "mean", "std", "count"]).reset_index().rename(columns={"count": "N"})
    summary_stability.to_csv(out / "summary_stability_by_class.csv", index=False, encoding="utf-8-sig")
    print(f"  Stability median Jaccard@5 toan tap con: {per_flow_stability['stability_jaccard5_mean'].median():.4f}", flush=True)

    # ============================== ROBUSTNESS ==============================
    print(f"[6/7] ROBUSTNESS: nhieu {NOISE_LEVELS} x seed {NOISE_SEEDS}, giu co dinh explainer seed={args.seed}...", flush=True)
    baseline_explainer = build_explainer(background_X, features, labels, kernel_width, True, args.seed)
    top5_clean = []
    for i in range(len(subset)):
        row = X_subset.iloc[i].to_numpy(dtype=float)
        code = int(pred_codes[i])
        exp = baseline_explainer.explain_instance(row, predict_fn, labels=[code],
                                                    num_features=NUM_FEATURES, num_samples=args.num_samples)
        top5_clean.append(set(f for f, _ in top5_from_exp(exp, code)))
    print(f"  Da co Top-5 sach (khong nhieu) cho {len(subset)} flow.", flush=True)

    robustness_rows = []
    t0 = time.perf_counter()
    combo_i = 0
    for level in NOISE_LEVELS:
        for seed in NOISE_SEEDS:
            combo_i += 1
            rng_noise = np.random.default_rng(seed)
            factors = 1 + level * rng_noise.uniform(-1, 1, len(subset))
            X_noisy = rescale_time(X_subset, factors)
            if not np.isfinite(X_noisy.to_numpy()).all():
                raise ValueError("Nhieu tao gia tri khong huu han.")
            proba_noisy = model.predict_proba(X_noisy)
            pred_code_noisy = proba_noisy.argmax(axis=1)
            for i in range(len(subset)):
                row = X_noisy.iloc[i].to_numpy(dtype=float)
                code = int(pred_codes[i])  # giu co dinh lop du doan TRUOC nhieu
                exp = baseline_explainer.explain_instance(row, predict_fn, labels=[code],
                                                            num_features=NUM_FEATURES, num_samples=args.num_samples)
                top5_noisy = set(f for f, _ in top5_from_exp(exp, code))
                robustness_rows.append(dict(
                    sample_id=int(subset.loc[i, "sample_id"]), true_label=subset.loc[i, "true_label"],
                    noise_percent=level * 100, seed=seed,
                    jaccard5_before_after=jaccard(top5_clean[i], top5_noisy),
                    prediction_changed=bool(pred_code_noisy[i] != code),
                ))
            print(f"  muc {level * 100:.0f}% seed {seed} ({combo_i}/{len(NOISE_LEVELS) * len(NOISE_SEEDS)}) xong | "
                  f"{time.perf_counter() - t0:.1f}s", flush=True)
    per_flow_robustness = pd.DataFrame(robustness_rows)
    per_flow_robustness.to_csv(out / "per_flow_robustness.csv", index=False, encoding="utf-8-sig")

    print("[7/7] Tong hop robustness theo lop x muc nhieu, va toan tap con...", flush=True)
    summary_by_class = per_flow_robustness.groupby(["true_label", "noise_percent"]).agg(
        N=("sample_id", "nunique"),
        mean_jaccard5=("jaccard5_before_after", "mean"),
        median_jaccard5=("jaccard5_before_after", "median"),
        prediction_changed_rate=("prediction_changed", "mean"),
    ).reset_index()
    summary_by_class.to_csv(out / "summary_robustness_by_class.csv", index=False, encoding="utf-8-sig")
    summary_overall = per_flow_robustness.groupby("noise_percent").agg(
        N=("sample_id", "nunique"),
        mean_jaccard5=("jaccard5_before_after", "mean"),
        median_jaccard5=("jaccard5_before_after", "median"),
        prediction_changed_rate=("prediction_changed", "mean"),
    ).reset_index()
    summary_overall.to_csv(out / "summary_robustness_overall.csv", index=False, encoding="utf-8-sig")
    print(summary_overall.to_string(index=False))

    info = dict(
        status="complete",
        protocol="sub_rq_2_3_lime_stability_robustness_v1",
        cohort_dir=str(cohort_dir),
        n_per_class=args.n_per_class, n_subset=len(subset),
        stability_seeds=STABILITY_SEEDS, noise_levels=NOISE_LEVELS, noise_seeds=NOISE_SEEDS,
        num_features=NUM_FEATURES, num_samples=args.num_samples, kernel_width=kernel_width,
        background_size=len(background_X), base_seed=args.seed,
        limitation="Robustness chi chay tren tap con (toi da 20 flow/lop), KHONG phai toan bo "
                   "1.339 flow hay 700k flow nhu ban SHAP full-test, do chi phi tinh toan LIME lon hon.",
        input_sha256={str(p): sha256(p) for p in (model_path, encoder_path, test_path, train_path, manifest_path)},
        script_sha256=sha256(Path(__file__)),
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
    )
    save_json(out / "run_info.json", info)
    print(f"\nHOAN TAT. Ket qua: {out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
