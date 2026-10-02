"""BUOC 1 - LIME per-flow tren dung cohort ghep cap voi SHAP (Sub-RQ 2.1-2.4).

Doc RQ2_SHAP/rq2_paired_cohort/<timestamp>/manifest_main.csv (1.339 flow, CAP=100/lop,
seed 42, flow XGBoost du doan DUNG), lay dung sample_id + predicted_label da luu, roi
giai thich TUNG flow bang LIME cho DUNG lop du doan do (khong phai true_label) - dong bo
quy uoc voi SHAP de hai ben so sanh duoc theo tung flow.

Truoc khi chay: doi chieu model.predict_proba HIEN TAI voi predicted_probability da ghi
trong manifest; neu lech qua 0.001 o bat ky flow nao thi DUNG NGAY (sai model hoac sai
thu tu feature).

Cau hinh LIME mac dinh (theo yeu cau):
  - Background: 5.000-10.000 flow phan tang tu train_set.parquet, seed 42.
  - LimeTabularExplainer(mode='classification', discretize_continuous=True,
    kernel_width=0.75*sqrt(78), random_state=42).
  - num_features=78 (lay du, khong chi Top-5) de tinh linh hoat Top-3/5/10 sau.
  - num_samples=5000.

Sau khi chay xong tren toan bo cohort, in median/mean local_r2. Neu median < 0.3, chay
CHUAN DOAN (khong tu dong doi cau hinh chinh) tren mot tap con 50 flow voi hai cau hinh
thay the (num_samples=10000; discretize_continuous=False) va in ket qua so sanh -
KHONG duoc chon cau hinh dua vao do giong SHAP, chi dua vao local_r2 co cai thien hay
khong. Neu chuan doan cho thay mot cau hinh tot ro ret hon, chay lai TOAN BO cohort voi
cau hinh do vao mot thu muc rieng va ghi ro trong run_info.

Chay tu goc du an:
    python RQ2_LIME/run_lime_paired_cohort.py
hoac chi dinh cohort neu co nhieu ban chay SHAP:
    python RQ2_LIME/run_lime_paired_cohort.py --cohort "RQ2_SHAP/rq2_paired_cohort/20260929_073435_637739"

Output (thu muc moi, khong ghi de):
  RQ2_LIME/rq2_lime_paired/<timestamp>/lime_per_flow_long.csv   - sample_id, feature, weight, abs_weight
  RQ2_LIME/rq2_lime_paired/<timestamp>/lime_sample_scores.csv   - sample_id, local_r2, ...
  RQ2_LIME/rq2_lime_paired/<timestamp>/run_info.json            - checksum + cau hinh de tai lap
  RQ2_LIME/rq2_lime_paired/<timestamp>/diagnosis_low_r2.json    - (chi neu median r2 < 0.3)
"""
from pathlib import Path
from datetime import datetime
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
import lime
from lime.lime_tabular import LimeTabularExplainer


BACKGROUND_SIZE = 8000   # trong khoang 5.000-10.000 theo yeu cau
SEED = 42
NUM_FEATURES = 78        # lay du 78 feature, khong chi Top-5
NUM_SAMPLES = 5000
R2_ALERT_THRESHOLD = 0.3
PILOT_N_PER_CLASS = 4    # ~50 flow chuan doan khi can (15 lop x ~3-4 flow)


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


def stratified_background_positions(train_path, seed, target_total):
    """Phan tang theo Label, ti le thuan voi kich thuoc lop trong train set, seed co dinh."""
    label_series = pd.read_parquet(train_path, columns=["Label"])["Label"].astype(str)
    counts = label_series.value_counts()
    n_total = len(label_series)
    rng = np.random.default_rng(seed)
    row_pos = np.arange(n_total)
    chosen = []
    for label, count in counts.items():
        n_i = max(1, round(target_total * count / n_total))
        n_i = min(n_i, count)
        class_idx = row_pos[label_series.to_numpy() == label]
        chosen.append(rng.choice(class_idx, size=n_i, replace=False))
    positions = np.sort(np.concatenate(chosen))
    return positions, counts.to_dict()


def extract_rows(path, features, positions, batch_size=65536):
    """Doc dung cac dong tai 'positions' (thu tu goc trong parquet) theo streaming batch."""
    source = pq.ParquetFile(path)
    positions = np.sort(np.asarray(positions))
    parts, offset = [], 0
    for batch in source.iter_batches(batch_size=batch_size, columns=features):
        local = positions[(positions >= offset) & (positions < offset + batch.num_rows)] - offset
        if len(local):
            parts.append(batch.take(local.tolist()).to_pandas()[features])
        offset += batch.num_rows
        if len(positions) and offset > positions[-1]:
            break
    frame = pd.concat(parts, ignore_index=True)
    frame.index = pd.Index(positions, name="train_row_position")
    assert len(frame) == len(positions), "Thieu dong khi trich xuat theo positions"
    return frame


def build_explainer(background_X, features, labels, kernel_width, discretize_continuous, seed):
    return LimeTabularExplainer(
        training_data=background_X.to_numpy(dtype=float),
        mode="classification",
        feature_names=features,
        class_names=labels,
        discretize_continuous=discretize_continuous,
        kernel_width=kernel_width,
        random_state=seed,
    )


def explain_cohort(explainer, predict_fn, X_cohort, sample_ids, true_labels, pred_labels,
                    pred_codes, pred_proba, features, num_features, num_samples, log_every=100):
    long_rows, score_rows = [], []
    t0 = time.perf_counter()
    for i, sid in enumerate(sample_ids):
        row = X_cohort.iloc[i].to_numpy(dtype=float)
        code = int(pred_codes[i])
        exp = explainer.explain_instance(
            row, predict_fn, labels=[code], num_features=num_features, num_samples=num_samples,
        )
        local_exp = dict(exp.local_exp[code])
        if len(local_exp) != len(features):
            missing = set(range(len(features))) - set(local_exp)
            for m in missing:
                local_exp[m] = 0.0
        for f_idx, w in local_exp.items():
            long_rows.append((int(sid), features[f_idx], float(w)))
        score_rows.append((int(sid), true_labels[i], pred_labels[i], float(pred_proba[i]), float(exp.score)))
        if (i + 1) % log_every == 0 or (i + 1) == len(sample_ids):
            elapsed = time.perf_counter() - t0
            rate = (i + 1) / elapsed
            remaining = (len(sample_ids) - i - 1) / rate if rate > 0 else float("nan")
            print(f"  {i + 1}/{len(sample_ids)} flow | {elapsed:.1f}s da qua | uoc con {remaining:.1f}s", flush=True)
    long_df = pd.DataFrame(long_rows, columns=["sample_id", "feature", "weight"])
    long_df["abs_weight"] = long_df["weight"].abs()
    score_df = pd.DataFrame(score_rows, columns=["sample_id", "true_label", "predicted_label",
                                                  "predicted_probability", "local_r2"])
    return long_df, score_df


def run_pilot_diagnosis(model, encoder, features, labels, background_X, X_all_cohort,
                         manifest, predict_fn, seed):
    """Chuan doan tren ~50 flow: so sanh local_r2 giua cau hinh mac dinh va hai cau hinh thay the.
    CHI dung de kiem tra local_r2 co cai thien khong; KHONG duoc chon dua vao do giong SHAP."""
    rng = np.random.default_rng(seed)
    pieces = []
    for label, group in manifest.groupby("true_label"):
        n = min(PILOT_N_PER_CLASS, len(group))
        pieces.append(group.sample(n=n, random_state=seed))
    pilot = pd.concat(pieces).sort_values("sample_id").reset_index(drop=True)
    print(f"[Chuan doan] {len(pilot)} flow lay tu {pilot['true_label'].nunique()} lop", flush=True)

    kernel_width_default = 0.75 * np.sqrt(len(features))
    configs = {
        "baseline_5000_discretize_true": dict(num_samples=NUM_SAMPLES, discretize_continuous=True),
        "num_samples_10000": dict(num_samples=10000, discretize_continuous=True),
        "discretize_false": dict(num_samples=NUM_SAMPLES, discretize_continuous=False),
    }
    results = {}
    X_pilot = X_all_cohort.loc[pilot["sample_id"]].reset_index(drop=True)
    pred_codes_pilot = encoder.transform(pilot["predicted_label"].to_numpy())
    for name, cfg in configs.items():
        explainer = build_explainer(background_X, features, labels, kernel_width_default,
                                     cfg["discretize_continuous"], seed)
        r2s = []
        for i in range(len(pilot)):
            row = X_pilot.iloc[i].to_numpy(dtype=float)
            code = int(pred_codes_pilot[i])
            exp = explainer.explain_instance(row, predict_fn, labels=[code],
                                              num_features=NUM_FEATURES, num_samples=cfg["num_samples"])
            r2s.append(float(exp.score))
        results[name] = dict(median_r2=float(np.median(r2s)), mean_r2=float(np.mean(r2s)),
                              min_r2=float(np.min(r2s)), max_r2=float(np.max(r2s)), n=len(r2s))
        print(f"  {name}: median_r2={results[name]['median_r2']:.4f} mean_r2={results[name]['mean_r2']:.4f}", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Thu muc goc du an (co RQ1_Model_Training_xboost/ va dataset/)")
    parser.add_argument("--cohort", type=Path, default=None,
                        help="Thu muc cohort SHAP (co manifest_main.csv). Mac dinh: ban chay moi nhat.")
    parser.add_argument("--output", type=Path, help="Thu muc ket qua MOI hoac rong")
    parser.add_argument("--background-size", type=int, default=BACKGROUND_SIZE)
    parser.add_argument("--num-samples", type=int, default=NUM_SAMPLES)
    parser.add_argument("--num-features", type=int, default=NUM_FEATURES)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--tolerance", type=float, default=0.001)
    parser.add_argument("--skip-diagnosis", action="store_true",
                        help="Bo qua buoc chuan doan tu dong ngay ca khi median r2 < 0.3")
    args = parser.parse_args()

    root = args.project.resolve()
    if args.cohort is None:
        cohort_root = root / "RQ2_SHAP" / "rq2_paired_cohort"
        candidates = sorted([p for p in cohort_root.iterdir() if p.is_dir()])
        if not candidates:
            raise FileNotFoundError(f"Khong tim thay cohort nao trong {cohort_root}")
        cohort_dir = candidates[-1]
    else:
        cohort_dir = args.cohort.resolve()
    manifest_path = cohort_dir / "manifest_main.csv"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Khong thay {manifest_path}")

    out = (args.output or Path(__file__).resolve().parent / "rq2_lime_paired" /
           datetime.now().strftime("%Y%m%d_%H%M%S_%f")).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Thu muc da co du lieu: {out}. Dung --output khac.")
    out.mkdir(parents=True, exist_ok=True)

    model_path = root / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl"
    encoder_path = model_path.with_name("label_encoder.pkl")
    test_path = root / "dataset/CICID-2018_processed/test_set.parquet"
    train_path = root / "dataset/CICID-2018_processed/train_set.parquet"
    for p in (model_path, encoder_path, test_path, train_path):
        if not p.is_file():
            raise FileNotFoundError(f"Khong tim thay: {p}")

    print("[1/6] Nap model, encoder, manifest cohort...", flush=True)
    model, encoder = joblib.load(model_path), joblib.load(encoder_path)
    features = model.get_booster().feature_names
    labels = encoder.classes_.astype(str).tolist()
    manifest = pd.read_csv(manifest_path)
    print(f"  Cohort: {manifest_path} | {len(manifest)} flow", flush=True)

    print("[2/6] Lay flow cohort tu test_set.parquet va DOI CHIEU predicted_probability...", flush=True)
    frame = pd.read_parquet(test_path)
    sample_ids = manifest["sample_id"].to_numpy()
    X_cohort = frame.iloc[sample_ids][features].reset_index(drop=True).astype(float)
    if not np.isfinite(X_cohort.to_numpy()).all():
        raise ValueError("Co NaN/Infinity trong cohort.")
    proba_now = model.predict_proba(X_cohort)
    pred_code_now = proba_now.argmax(axis=1)
    pred_label_now = np.asarray(labels)[pred_code_now]
    pred_proba_now = proba_now[np.arange(len(X_cohort)), pred_code_now]

    label_mismatch = pred_label_now != manifest["predicted_label"].to_numpy()
    proba_diff = np.abs(pred_proba_now - manifest["predicted_probability"].to_numpy())
    if label_mismatch.any() or (proba_diff > args.tolerance).any():
        bad = manifest.loc[label_mismatch | (proba_diff > args.tolerance)]
        raise ValueError(
            f"DUNG: predicted_label/predicted_probability HIEN TAI lech so voi manifest o "
            f"{len(bad)} flow (nguong {args.tolerance}). Kiem tra dung model/dataset/thu tu feature. "
            f"Vi du sample_id lech: {bad['sample_id'].head(5).tolist()}"
        )
    print(f"  Doi chieu OK: {len(manifest)} flow khop predicted_label va predicted_probability (nguong {args.tolerance}).", flush=True)
    pred_codes = encoder.transform(manifest["predicted_label"].to_numpy())

    print(f"[3/6] Dung background phan tang tu train_set.parquet (~{args.background_size} flow, seed {args.seed})...", flush=True)
    bg_positions, train_class_counts = stratified_background_positions(train_path, args.seed, args.background_size)
    background_X = extract_rows(train_path, features, bg_positions).astype(float)
    if not np.isfinite(background_X.to_numpy()).all():
        raise ValueError("Co NaN/Infinity trong background.")
    print(f"  Background: {len(background_X)} flow tu {len(train_class_counts)} lop.", flush=True)

    kernel_width = 0.75 * np.sqrt(len(features))
    print(f"[4/6] Khoi tao LimeTabularExplainer (kernel_width={kernel_width:.4f}, "
          f"discretize_continuous=True, num_features={args.num_features}, num_samples={args.num_samples})...", flush=True)
    explainer = build_explainer(background_X, features, labels, kernel_width, True, args.seed)
    predict_fn = lambda arr: model.predict_proba(pd.DataFrame(np.asarray(arr), columns=features))

    print(f"[5/6] Giai thich {len(manifest)} flow bang LIME (dung predicted_label)...", flush=True)
    long_df, score_df = explain_cohort(
        explainer, predict_fn, X_cohort, sample_ids,
        manifest["true_label"].to_numpy(), manifest["predicted_label"].to_numpy(),
        pred_codes, manifest["predicted_probability"].to_numpy(),
        features, args.num_features, args.num_samples,
    )
    long_df.to_csv(out / "lime_per_flow_long.csv", index=False, encoding="utf-8-sig")
    score_df.to_csv(out / "lime_sample_scores.csv", index=False, encoding="utf-8-sig")

    median_r2 = float(score_df["local_r2"].median())
    mean_r2 = float(score_df["local_r2"].mean())
    print(f"[6/6] local_r2: median={median_r2:.4f} mean={mean_r2:.4f} min={score_df['local_r2'].min():.4f} "
          f"max={score_df['local_r2'].max():.4f}", flush=True)

    diagnosis = None
    if median_r2 < R2_ALERT_THRESHOLD and not args.skip_diagnosis:
        print(f"[Canh bao] median_r2={median_r2:.4f} < {R2_ALERT_THRESHOLD}. Chay CHUAN DOAN tren tap con...", flush=True)
        X_cohort_by_sid = X_cohort.copy()
        X_cohort_by_sid.index = sample_ids
        diagnosis = run_pilot_diagnosis(model, encoder, features, labels, background_X, X_cohort_by_sid,
                                         manifest.assign(sample_id=sample_ids), predict_fn, args.seed)
        save_json(out / "diagnosis_low_r2.json", dict(
            trigger_median_r2=median_r2, threshold=R2_ALERT_THRESHOLD, results=diagnosis,
            note="Chuan doan chi de kiem tra local_r2; KHONG chon cau hinh dua vao do giong SHAP. "
                 "Xem run_info.json de biet cau hinh cuoi cung da dung cho ket qua chinh."))

    info = dict(
        status="complete",
        protocol="per_flow_lime_predicted_class_paired_cohort_v1",
        project=str(root),
        cohort_dir=str(cohort_dir),
        seed=args.seed,
        n_flow=len(manifest),
        background_size=len(background_X),
        background_target=args.background_size,
        tolerance_predicted_probability=args.tolerance,
        num_features=args.num_features,
        num_samples=args.num_samples,
        kernel_width=kernel_width,
        discretize_continuous=True,
        median_local_r2=median_r2,
        mean_local_r2=mean_r2,
        r2_alert_threshold=R2_ALERT_THRESHOLD,
        diagnosis_triggered=diagnosis is not None,
        input_sha256={str(p): sha256(p) for p in (model_path, encoder_path, test_path, train_path, manifest_path)},
        script_sha256=sha256(Path(__file__)),
        features=features,
        classes=labels,
        explained_output="predicted_label of each flow (NOT true_label) -- dong bo voi SHAP",
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                      lime=getattr(lime, "__file__", "unknown")),
    )
    save_json(out / "run_info.json", info)
    print(f"HOAN TAT. Ket qua: {out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
