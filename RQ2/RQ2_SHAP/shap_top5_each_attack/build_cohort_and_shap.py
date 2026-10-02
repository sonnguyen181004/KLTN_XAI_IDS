"""Dung chung mot lan cho ca SHAP va LIME: dung cohort ghep cap va tinh SHAP per-flow.

Muc dich: tao ra dung file con thieu de LIME co the ghep cap voi SHAP theo tung flow
(Sub-RQ 2.1). Khac voi shap_top5_each_attack.py (chi xuat trung binh theo lop), script
nay xuat vector SHAP 78 chieu cho TUNG FLOW trong mot cohort nho (khong phai toan bo
700k dong), nen chay rat nhanh.

Quy uoc dong bo voi cac script SHAP da co trong shap_top5_each_attack/:
  - TreeExplainer(model_output='raw', feature_perturbation='tree_path_dependent')
  - Kiem tra additivity bang np.testing.assert_allclose
  - Ghi checksum SHA256 cho model/encoder/test_set va chinh script nay
  - Ghi run_info.json de tai lap

Quy uoc rieng cho phan ghep cap voi LIME:
  - SHAP giai thich dung LOP MA MODEL DA DU DOAN cho flow do (predicted_label),
    KHONG PHAI true_label. LIME sau nay cung phai giai thich dung predicted_label
    cua chinh flow do de hai ben so sanh duoc.
  - Cohort chinh (main cohort) = flow ma XGBoost du doan DUNG (predicted == true),
    toi da CAP=100 flow moi lop, seed co dinh 42; lop nao co it hon CAP flow dung
    thi giu toan bo. Day la nen tang de tinh Sub-RQ 2.1/2.2/2.4 (theo dung tinh
    than "chi dung flow model du doan dung" da ghi trong ke hoach RQ2).
  - Ngoai ra xuat them mot "error cohort" (toi da 20 flow sai moi lop, uu tien
    cac lop kho: Infilteration, SlowHTTPTest, SQL Injection) de dung lam case
    study rieng, KHONG trong vao trung binh chinh.

Chay tu thu muc goc du an (noi co RQ1_Model_Training_xboost/ va dataset/):
    python build_cohort_and_shap.py
hoac chi dinh goc du an neu dat script noi khac:
    python build_cohort_and_shap.py --project "C:\\Users\\LOQ\\Downloads\\SELF_KLTN"

Output (thu muc moi, khong ghi de):
  rq2_paired_cohort/<timestamp>/manifest_main.csv        - cohort chinh
  rq2_paired_cohort/<timestamp>/manifest_error_cases.csv - case loi (rieng)
  rq2_paired_cohort/<timestamp>/shap_per_flow_long.csv   - sample_id, feature, shap_value (cohort chinh)
  rq2_paired_cohort/<timestamp>/run_info.json            - checksum + cau hinh de tai lap
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
import shap
import xgboost


CAP_MAIN = 100        # so flow dung toi da moi lop cho cohort chinh
CAP_ERROR = 20         # so flow sai toi da moi lop cho error cohort
SEED = 42              # seed lay mau, dong bo voi cac script SHAP/LIME khac trong du an


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent,
                        help="Thu muc goc du an (co RQ1_Model_Training_xboost/ va dataset/)")
    parser.add_argument("--output", type=Path, help="Thu muc ket qua MOI hoac rong")
    parser.add_argument("--cap-main", type=int, default=CAP_MAIN)
    parser.add_argument("--cap-error", type=int, default=CAP_ERROR)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    root = args.project.resolve()
    model_path = root / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl"
    encoder_path = model_path.with_name("label_encoder.pkl")
    test_path = root / "dataset/CICID-2018_processed/test_set.parquet"
    for p in (model_path, encoder_path, test_path):
        if not p.is_file():
            raise FileNotFoundError(f"Khong tim thay: {p}. Dung --project tro dung goc du an.")

    out = (args.output or root / "RQ2_SHAP" / "rq2_paired_cohort" /
           datetime.now().strftime("%Y%m%d_%H%M%S_%f")).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Thu muc da co du lieu: {out}. Dung --output khac.")
    out.mkdir(parents=True, exist_ok=True)

    print("[1/5] Nap model, encoder, danh sach feature...", flush=True)
    model, encoder = joblib.load(model_path), joblib.load(encoder_path)
    features = model.get_booster().feature_names
    labels = encoder.classes_.astype(str).tolist()
    if not features or len(features) != len(set(features)):
        raise ValueError("Model khong co danh sach feature hop le.")
    if not np.array_equal(model.classes_, np.arange(len(labels))):
        raise ValueError("Anh xa lop model va label_encoder khong khop.")

    source = pq.ParquetFile(test_path)
    if set(source.schema_arrow.names) != set(features) | {"Label"}:
        raise ValueError("Cot du lieu test khong khop feature cua model va Label.")

    print(f"[2/5] Doc toan bo test set va du doan ({source.metadata.num_rows:,} dong)...", flush=True)
    frame = pd.read_parquet(test_path)
    X_all = frame[features].astype(float)
    if not np.isfinite(X_all.to_numpy()).all():
        raise ValueError("Co NaN/Infinity trong test set.")
    true_all = frame["Label"].astype(str).to_numpy()
    true_code_all = encoder.transform(true_all)
    proba_all = model.predict_proba(X_all)
    pred_code_all = proba_all.argmax(axis=1)
    pred_label_all = np.asarray(labels)[pred_code_all]
    pred_proba_all = proba_all[np.arange(len(X_all)), pred_code_all]
    is_correct_all = pred_label_all == true_all

    print("[3/5] Dung cohort chinh (flow du doan dung, phan tang theo lop) va error cohort...", flush=True)
    rng = np.random.default_rng(args.seed)
    row_pos = np.arange(len(frame))
    main_rows, error_rows = [], []
    for label in labels:
        class_mask = true_all == label
        correct_idx = row_pos[class_mask & is_correct_all]
        wrong_idx = row_pos[class_mask & ~is_correct_all]
        if len(correct_idx) > args.cap_main:
            chosen = rng.choice(correct_idx, size=args.cap_main, replace=False)
        else:
            chosen = correct_idx
        main_rows.append(np.sort(chosen))
        if len(wrong_idx) > args.cap_error:
            chosen_wrong = rng.choice(wrong_idx, size=args.cap_error, replace=False)
        else:
            chosen_wrong = wrong_idx
        error_rows.append(np.sort(chosen_wrong))
    main_ids = np.concatenate(main_rows) if main_rows else np.array([], dtype=int)
    error_ids = np.concatenate(error_rows) if error_rows else np.array([], dtype=int)
    if len(set(main_ids)) != len(main_ids):
        raise ValueError("Trung sample_id trong cohort chinh.")

    def build_manifest(ids):
        return pd.DataFrame({
            "sample_id": ids,
            "true_label": true_all[ids],
            "predicted_label": pred_label_all[ids],
            "predicted_probability": pred_proba_all[ids],
            "is_correct": is_correct_all[ids],
            "seed": args.seed,
        }).sort_values("sample_id").reset_index(drop=True)

    manifest_main = build_manifest(main_ids)
    manifest_error = build_manifest(error_ids)
    manifest_main.to_csv(out / "manifest_main.csv", index=False, encoding="utf-8-sig")
    manifest_error.to_csv(out / "manifest_error_cases.csv", index=False, encoding="utf-8-sig")
    print(manifest_main.groupby("true_label").size().to_string())
    print(f"-> Cohort chinh: {len(manifest_main)} flow | Error cohort: {len(manifest_error)} flow")

    print("[4/5] Tinh SHAP cho tung flow trong cohort chinh (dung predicted_label)...", flush=True)
    X_cohort = X_all.loc[manifest_main["sample_id"]].reset_index(drop=True)
    raw_margin = model.predict(X_cohort, output_margin=True)
    explainer = shap.TreeExplainer(model, model_output="raw", feature_perturbation="tree_path_dependent")
    explanation = explainer(X_cohort, check_additivity=True, approximate=False)
    values = explanation.values
    if values.shape != (len(X_cohort), len(features), len(labels)):
        raise ValueError(f"Kich thuoc SHAP khong dung: {values.shape}")
    reconstructed = explanation.base_values + values.sum(axis=1)
    np.testing.assert_allclose(reconstructed, raw_margin, atol=1e-4, rtol=1e-4)
    max_additivity_error = float(np.max(np.abs(reconstructed - raw_margin)))

    pred_code_cohort = encoder.transform(manifest_main["predicted_label"].to_numpy())
    phi = values[np.arange(len(X_cohort)), :, pred_code_cohort]  # (n_flow, n_feature) cho dung predicted class

    long_rows = []
    sample_ids = manifest_main["sample_id"].to_numpy()
    for i, sid in enumerate(sample_ids):
        for f_idx, feat in enumerate(features):
            long_rows.append((int(sid), feat, float(phi[i, f_idx])))
    shap_long = pd.DataFrame(long_rows, columns=["sample_id", "feature", "shap_value"])
    shap_long["abs_shap_value"] = shap_long["shap_value"].abs()
    shap_long.to_csv(out / "shap_per_flow_long.csv", index=False, encoding="utf-8-sig")

    print("[5/5] Ghi checksum va run_info.json...", flush=True)
    info = dict(
        status="complete",
        protocol="per_flow_shap_predicted_class_paired_cohort_v1",
        project=str(root),
        seed=args.seed,
        cap_main=args.cap_main,
        cap_error=args.cap_error,
        n_main=int(len(manifest_main)),
        n_error=int(len(manifest_error)),
        max_additivity_error=max_additivity_error,
        input_sha256={str(p): sha256(p) for p in (model_path, encoder_path, test_path)},
        script_sha256=sha256(Path(__file__)),
        features=features,
        classes=labels,
        shap_settings=dict(model_output="raw", feature_perturbation="tree_path_dependent", approximate=False),
        explained_output="predicted_label of each flow (NOT true_label) -- must match LIME's convention",
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                      shap=shap.__version__, xgboost=xgboost.__version__),
    )
    save_json(out / "run_info.json", info)
    print(f"HOAN TAT. Max additivity error = {max_additivity_error:.6g}")
    print(f"Ket qua: {out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
