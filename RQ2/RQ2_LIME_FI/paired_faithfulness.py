"""BUOC 5 - Sub-RQ 2.4 (quan trong nhat): Faithfulness ghep cap SHAP vs LIME.

Ap DUNG protocol donor-substitution ma RQ2_SHAP/shap_top5_each_attack/shap_faithfulness_full_test.py
da dung tren 700.000 flow (donor_seed=173, control_seed=2026, 10 donor tu train, 20 lan
lap doi chung ngau nhien, k in {3,5,10}, nguong thang 1e-6, nguong duong 1e-8), nhung
chay CHO CA SHAP VA LIME tren CUNG 1.339 flow cua cohort (khong phai 700k). Muc dich la
mot cap win-rate so sanh truc tiep duoc giua hai phuong phap tren CUNG mot tap flow.

QUAN TRONG: KHONG duoc tron ket qua nay voi con so 99,31% da cong bo (do tren 700.000
flow, pham vi khac - toan bo test set, khong phai cohort ghep cap). Ket qua 99,31% chi
duoc trich dan lam bang chung global BO SUNG, giu rieng khoi bang so sanh SHAP-LIME o day.

Quy trinh cho MOI phuong phap (SHAP dung shap_value, LIME dung weight, ca hai da giai
thich DUNG predicted_label):
  - pool duong = feature co attribution > 1e-8 (day la huong "day diem ve lop du doan").
  - Top-k that su = k feature attribution lon nhat trong pool.
  - Doi chung ngau nhien = chon k feature NGAU NHIEN tu CUNG pool duong, lap 20 lan,
    seed rieng cho tung (method, k, sample_id) de tai lap duoc.
  - Voi ca Top-k va moi lan doi chung: thay gia tri k feature do bang gia tri tu 10 dong
    "donor" lay tu train set (seed 173, DUNG CHUNG donor cho SHAP va LIME de cong bang).
  - Do muc giam raw margin cua lop du doan (trung binh tren 10 donor); SHAP/LIME THANG
    khi muc giam cua Top-k that su > muc giam trung binh cua 20 lan doi chung, chenh
    lech qua nguong 1e-6.
  - Flow duoc tinh (eligible) chi khi so feature duong > k (du de doi chung ngau nhien
    khac Top-k that su).

Chay tu goc du an:
    python RQ2_LIME/paired_faithfulness.py

Output (RQ2_LIME/rq2_faithfulness/<timestamp>/):
  per_flow_faithfulness.csv         - sample_id, true_label, method, k, status, margin_drop*, win/tie
  summary_by_class.csv              - N, coverage, win_rate SHAP vs LIME theo lop x k
  summary_overall.csv               - gop toan cohort theo k, SHAP vs LIME
  run_info.json
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import platform
import sys

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "RQ2_SHAP" / "shap_top5_each_attack"))
from shap_faithfulness_full_test import training_donors, softmax, digest  # noqa: E402


KS = (3, 5, 10)
N_DONORS = 10
REPEATS = 20
DONOR_SEED = 173
CONTROL_SEED = 2026
POSITIVE_THRESHOLD = 1e-8
WIN_TOLERANCE = 1e-6


def sha256(path):
    return digest(path)


def save_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def latest_subdir(root):
    candidates = sorted([p for p in root.iterdir() if p.is_dir()])
    if not candidates:
        raise FileNotFoundError(f"Khong tim thay thu muc con trong {root}")
    return candidates[-1]


def long_to_matrix(long_df, sample_ids, features, value_col):
    """Chuyen bang dai (sample_id, feature, value) thanh ma tran (n_flow, n_feature) dung
    thu tu sample_ids va features da cho."""
    pivot = long_df.pivot(index="sample_id", columns="feature", values=value_col)
    pivot = pivot.loc[sample_ids, features]
    return pivot.to_numpy(dtype=float)


def run_method(method_name, phi, model, features, target, X_cohort, raw_margin, probs, donors, sample_ids):
    n, n_feat = phi.shape
    positive = (phi > POSITIVE_THRESHOLD).sum(axis=1)
    order = np.argsort(-phi, axis=1, kind="stable")
    donors_np = donors.to_numpy(dtype=float)
    results = []
    for k in KS:
        eligible_mask = positive > k
        status = np.where(eligible_mask, "eligible", np.where(positive == k, "exactly_k_no_distinct_control", "fewer_than_k"))
        eligible = np.flatnonzero(eligible_mask)
        table = pd.DataFrame(dict(
            sample_id=sample_ids, method=method_name, k=k, status=status, n_positive=positive,
            shap_margin_drop=np.nan, random_margin_drop=np.nan, margin_drop_advantage=np.nan,
            shap_probability_drop_pp=np.nan, random_probability_drop_pp=np.nan,
            shap_beats_random=np.nan, tie=np.nan,
        ))
        if len(eligible):
            m = len(eligible)
            selections = np.empty((REPEATS + 1, m, k), dtype=int)
            selections[0] = order[eligible, :k]
            for j, i in enumerate(eligible):
                rng = np.random.default_rng(np.random.SeedSequence([CONTROL_SEED, k, hash(method_name) % (2**31), int(sample_ids[i])]))
                pool = np.flatnonzero(phi[i] > POSITIVE_THRESHOLD)
                for r in range(REPEATS):
                    selections[r + 1, j] = rng.choice(pool, k, replace=False)
            indices = selections.reshape(-1, k)
            original = np.tile(X_cohort.iloc[eligible].to_numpy(dtype=float), (REPEATS + 1, 1))
            targets = np.tile(target[eligible], REPEATS + 1)
            old_margin = np.tile(raw_margin[eligible, target[eligible]], REPEATS + 1)
            old_prob = np.tile(probs[eligible, target[eligible]], REPEATS + 1)
            rr = np.arange(len(original))
            scores = np.zeros((REPEATS + 1, m, 2))
            for donor in donors_np:
                masked = original.copy()
                masked[rr[:, None], indices] = donor[indices]
                altered = np.concatenate([
                    model.predict(pd.DataFrame(masked[s:s + 8192], columns=features), output_margin=True)
                    for s in range(0, len(masked), 8192)
                ])
                altered_probs = softmax(altered)
                values = np.column_stack([old_margin - altered[rr, targets],
                                           100 * (old_prob - altered_probs[rr, targets])])
                scores += values.reshape(REPEATS + 1, m, 2) / N_DONORS
            top, random = scores[0], scores[1:].mean(axis=0)
            table.loc[eligible, "shap_margin_drop"] = top[:, 0]
            table.loc[eligible, "random_margin_drop"] = random[:, 0]
            table.loc[eligible, "shap_probability_drop_pp"] = top[:, 1]
            table.loc[eligible, "random_probability_drop_pp"] = random[:, 1]
            gap = top[:, 0] - random[:, 0]
            table.loc[eligible, "margin_drop_advantage"] = gap
            table.loc[eligible, "shap_beats_random"] = (gap > WIN_TOLERANCE).astype(float)
            table.loc[eligible, "tie"] = (np.abs(gap) <= WIN_TOLERANCE).astype(float)
        results.append(table)
    return pd.concat(results, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--shap-dir", type=Path, default=None)
    parser.add_argument("--lime-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.project.resolve()
    shap_dir = (args.shap_dir or latest_subdir(root / "RQ2_SHAP" / "rq2_paired_cohort")).resolve()
    lime_dir = (args.lime_dir or latest_subdir(root / "RQ2_LIME" / "rq2_lime_paired")).resolve()
    manifest_path = shap_dir / "manifest_main.csv"
    shap_long_path = shap_dir / "shap_per_flow_long.csv"
    lime_long_path = lime_dir / "lime_per_flow_long.csv"
    for p in (manifest_path, shap_long_path, lime_long_path):
        if not p.is_file():
            raise FileNotFoundError(f"Khong thay {p}")

    out = (args.output or Path(__file__).resolve().parent / "rq2_faithfulness" /
           datetime.now().strftime("%Y%m%d_%H%M%S_%f")).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Thu muc da co du lieu: {out}. Dung --output khac.")
    out.mkdir(parents=True, exist_ok=True)

    model_path = root / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl"
    encoder_path = model_path.with_name("label_encoder.pkl")
    test_path = root / "dataset/CICID-2018_processed/test_set.parquet"
    train_path = root / "dataset/CICID-2018_processed/train_set.parquet"

    print("[1/6] Nap model, encoder, manifest, SHAP/LIME long...", flush=True)
    model, encoder = joblib.load(model_path), joblib.load(encoder_path)
    features = model.get_booster().feature_names
    labels = encoder.classes_.astype(str).tolist()
    manifest = pd.read_csv(manifest_path)
    sample_ids = manifest["sample_id"].to_numpy()
    shap_long = pd.read_csv(shap_long_path)
    lime_long = pd.read_csv(lime_long_path)

    print("[2/6] Lay feature cohort, du doan, raw margin va xac suat...", flush=True)
    frame = pd.read_parquet(test_path)
    X_cohort = frame.iloc[sample_ids][features].reset_index(drop=True).astype(float)
    raw_margin = model.predict(X_cohort, output_margin=True)
    probs = model.predict_proba(X_cohort)
    np.testing.assert_allclose(softmax(raw_margin), probs, atol=1e-5, rtol=1e-4)
    target = encoder.transform(manifest["predicted_label"].to_numpy())
    if not np.array_equal(np.asarray(labels)[target], manifest["predicted_label"].to_numpy()):
        raise ValueError("Ma lop du doan khong khop predicted_label trong manifest")

    print(f"[3/6] Lay {N_DONORS} donor tu train set (seed {DONOR_SEED}) - DUNG CHUNG cho SHAP va LIME...", flush=True)
    donors = training_donors(train_path, features, N_DONORS)
    if not np.isfinite(donors.to_numpy()).all():
        raise ValueError("Donor co gia tri khong huu han")

    print("[4/6] Chuyen SHAP/LIME long thanh ma tran (n_flow, 78) dung thu tu sample_id/feature...", flush=True)
    phi_shap = long_to_matrix(shap_long, sample_ids, features, "shap_value")
    phi_lime = long_to_matrix(lime_long, sample_ids, features, "weight")

    print("[5/6] Chay donor-substitution faithfulness cho SHAP...", flush=True)
    table_shap = run_method("shap", phi_shap, model, features, target, X_cohort, raw_margin, probs, donors, sample_ids)
    print("  Chay donor-substitution faithfulness cho LIME...", flush=True)
    table_lime = run_method("lime", phi_lime, model, features, target, X_cohort, raw_margin, probs, donors, sample_ids)
    per_flow = pd.concat([table_shap, table_lime], ignore_index=True)
    per_flow = per_flow.merge(manifest[["sample_id", "true_label", "predicted_label"]], on="sample_id", how="left")
    per_flow.to_csv(out / "per_flow_faithfulness.csv", index=False, encoding="utf-8-sig")

    print("[6/6] Tong hop win-rate theo lop va toan cohort, SHAP vs LIME, k=3/5/10...", flush=True)
    per_flow["n_original"] = 1
    per_flow["n_eligible"] = per_flow["status"].eq("eligible").astype(int)

    def summarize(group_cols):
        g = per_flow.groupby(group_cols)
        out_rows = []
        for keys, sub in g:
            n_original = len(sub)
            n_eligible = int(sub["n_eligible"].sum())
            eligible_sub = sub[sub["status"] == "eligible"]
            row = dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,)))
            row["N"] = n_original
            row["n_eligible"] = n_eligible
            row["coverage_percent"] = 100 * n_eligible / n_original if n_original else np.nan
            row["win_rate_percent"] = 100 * eligible_sub["shap_beats_random"].mean() if n_eligible else np.nan
            row["tie_rate_percent"] = 100 * eligible_sub["tie"].mean() if n_eligible else np.nan
            row["mean_margin_drop_method"] = eligible_sub["shap_margin_drop"].mean() if n_eligible else np.nan
            row["mean_margin_drop_random"] = eligible_sub["random_margin_drop"].mean() if n_eligible else np.nan
            out_rows.append(row)
        return pd.DataFrame(out_rows)

    summary_by_class = summarize(["true_label", "method", "k"]).sort_values(["true_label", "k", "method"])
    summary_by_class.to_csv(out / "summary_by_class.csv", index=False, encoding="utf-8-sig")
    summary_overall = summarize(["method", "k"]).sort_values(["k", "method"])
    summary_overall.to_csv(out / "summary_overall.csv", index=False, encoding="utf-8-sig")
    print(summary_overall.to_string(index=False))

    info = dict(
        status="complete",
        protocol="sub_rq_2_4_paired_faithfulness_shap_vs_lime_v1",
        note_scope="Chay tren 1.339 flow cohort, KHONG PHAI 700.000 flow cua ban SHAP full-test goc "
                   "(99,31%). Hai con so KHONG duoc tron; con so 99,31% chi la bang chung global bo sung.",
        shap_dir=str(shap_dir), lime_dir=str(lime_dir),
        n_flow=len(manifest), n_donors=N_DONORS, repeats=REPEATS,
        donor_seed=DONOR_SEED, control_seed=CONTROL_SEED, ks=list(KS),
        positive_threshold=POSITIVE_THRESHOLD, win_tolerance=WIN_TOLERANCE,
        train_donor_positions=donors.index.tolist(),
        input_sha256={str(p): sha256(p) for p in (model_path, encoder_path, test_path, train_path,
                                                    manifest_path, shap_long_path, lime_long_path)},
        script_sha256=sha256(Path(__file__)),
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
    )
    save_json(out / "run_info.json", info)
    print(f"\nHOAN TAT. Ket qua: {out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
