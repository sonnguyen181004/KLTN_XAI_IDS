"""Generate reproducible SHAP Top-k files for RQ2.

Run in the VS Code terminal from the project root:
    py -3.14 RQ2_SHAP/run_rq2_shap_topk.py

First validate only the shared cohort and feature schema:
    py -3.14 RQ2_SHAP/run_rq2_shap_topk.py --dry-run

This is the SHAP phase only. It deliberately does not calculate Jaccard or
overlap until LIME reuses the saved rq2_shared_samples.csv manifest.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TEST_SET = ROOT / "dataset" / "CICID-2018_processed" / "test_set.parquet"
MODEL_FILE = ROOT / "RQ1_Model_Training_xboost" / "saved_models" / "best_xgboost_model.pkl"
ENCODER_FILE = ROOT / "RQ1_Model_Training_xboost" / "saved_models" / "label_encoder.pkl"
OUTPUT_DIR = ROOT / "RQ2_SHAP" / "outputs"


def feature_key(name: str) -> str:
    """Join key for a later SHAP-LIME comparison; display names stay unchanged."""
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create SHAP Top-1, Top-3, Top-5 files for RQ2.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-per-class", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Thư mục kết quả. Dùng thư mục mới nếu outputs đang bị Excel hoặc VS Code khóa.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Create only schema and shared sample manifest.")
    return parser.parse_args()


def require(path: Path, name: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy {name}: {path}")


def model_features(model, data_features: list[str]) -> list[str]:
    if hasattr(model, "feature_names_in_") and len(model.feature_names_in_):
        return [str(x) for x in model.feature_names_in_]
    try:
        names = model.get_booster().feature_names
        if names:
            return [str(x) for x in names]
    except AttributeError:
        pass
    return data_features


def verify_schema(expected: list[str], received: list[str]) -> None:
    missing = [x for x in expected if x not in received]
    extra = [x for x in received if x not in expected]
    if missing or extra:
        details = []
        if missing:
            details.append(f"Thiếu feature: {missing}")
        if extra:
            details.append(f"Feature dư: {extra}")
        raise ValueError("Schema feature của dữ liệu không khớp model.\n" + "\n".join(details))


def make_manifest(labels: pd.Series, class_names: list[str], seed: int, max_per_class: int) -> pd.DataFrame:
    """Use original test-row positions as stable sample_id values."""
    rng = np.random.default_rng(seed)
    values = labels.astype(str).to_numpy()
    result: list[dict[str, object]] = []
    for name in class_names:
        positions = np.flatnonzero(values == name)
        if not len(positions):
            raise ValueError(f"Nhãn {name!r} không có trong test set.")
        chosen = positions if len(positions) <= max_per_class else rng.choice(positions, max_per_class, replace=False)
        result.extend({"sample_id": int(pos), "true_label": name} for pos in np.sort(chosen))
    return pd.DataFrame(result).sort_values(["true_label", "sample_id"], kind="stable").reset_index(drop=True)


def choose_predicted_class_values(raw_values, predicted_codes: np.ndarray, feature_count: int) -> np.ndarray:
    """Support both SHAP multiclass result layouts used by common SHAP versions."""
    values = np.stack(raw_values, axis=-1) if isinstance(raw_values, list) else np.asarray(raw_values)
    if values.ndim != 3 or values.shape[0] != len(predicted_codes):
        raise ValueError(f"SHAP output đa lớp không hợp lệ: shape={values.shape}")
    rows = np.arange(len(predicted_codes))
    if values.shape[1] == feature_count:  # samples, features, classes
        return values[rows, :, predicted_codes]
    if values.shape[2] == feature_count:  # samples, classes, features
        return values[rows, predicted_codes, :]
    raise ValueError(f"Không xác định được trục feature trong SHAP output: shape={values.shape}")


def base_for_predicted_class(expected_value, predicted_codes: np.ndarray) -> np.ndarray:
    base = np.asarray(expected_value)
    if base.ndim == 0:
        return np.full(len(predicted_codes), float(base))
    if base.ndim == 1:
        return base[predicted_codes]
    raise ValueError(f"SHAP expected_value không hỗ trợ shape={base.shape}")


def create_ranking(meta: pd.DataFrame, values: np.ndarray, features: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for row, (_, data) in enumerate(meta.iterrows()):
        order = np.argsort(-np.abs(values[row]), kind="stable")
        for rank, column in enumerate(order, start=1):
            name = features[column]
            records.append(
                {
                    "sample_id": int(data.sample_id),
                    "true_label": data.true_label,
                    "predicted_label": data.predicted_label,
                    "is_correct": bool(data.is_correct),
                    "rank": rank,
                    "feature": name,
                    "feature_key": feature_key(name),
                    "shap_value": float(values[row, column]),
                    "abs_shap_value": float(abs(values[row, column])),
                }
            )
    return records


def make_class_top5(ranking: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        ranking.groupby(["true_label", "is_correct", "feature", "feature_key"], as_index=False)
        .agg(
            mean_abs_shap=("abs_shap_value", "mean"),
            mean_signed_shap=("shap_value", "mean"),
            sample_count=("sample_id", "nunique"),
        )
    )
    grouped["class_rank"] = grouped.groupby(["true_label", "is_correct"])["mean_abs_shap"].rank(
        method="first", ascending=False
    ).astype(int)
    return grouped[grouped.class_rank <= 5].sort_values(["true_label", "is_correct", "class_rank"], kind="stable")


def write_summary(output: Path, manifest: pd.DataFrame, meta: pd.DataFrame | None, ranking: pd.DataFrame | None) -> None:
    lines = ["# RQ2 SHAP Top-k", "", f"Shared cohort: **{len(manifest):,}** flows.", "", "## Samples per true class", "", "| Class | Samples |", "|---|---:|"]
    lines.extend(f"| {label} | {count} |" for label, count in manifest.groupby("true_label").size().sort_index().items())
    if meta is None or ranking is None:
        lines.extend(["", "This is a dry run. SHAP has not been calculated yet."])
    else:
        top1 = ranking[ranking["rank"] == 1].groupby("true_label")["feature"].value_counts().groupby(level=0).head(1)
        lines.extend(["", "## Prediction summary", "", f"Correct predictions: **{int(meta.is_correct.sum()):,}/{len(meta):,}**.", "", "## Most frequent SHAP Top-1 feature", "", "| True class | Feature | Count |", "|---|---|---:|"])
        lines.extend(f"| {label} | {feature} | {count} |" for (label, feature), count in top1.items())
        lines.extend(["", "## Next step", "", "Run LIME on exactly `rq2_shared_samples.csv`. Use `feature_key` to normalize LIME condition names before calculating Overlap and Jaccard for k = 1, 3, 5."])
    (output / "README_results.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    for path, name in [(TEST_SET, "test_set.parquet"), (MODEL_FILE, "mô hình XGBoost"), (ENCODER_FILE, "LabelEncoder")]:
        require(path, name)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[1/5] Nạp dataset, model và LabelEncoder...")
    test_df = pd.read_parquet(TEST_SET)
    if "Label" not in test_df:
        raise ValueError("test_set.parquet không có cột Label.")
    model = joblib.load(MODEL_FILE)
    encoder = joblib.load(ENCODER_FILE)
    raw_x = test_df.drop(columns="Label")
    features = model_features(model, list(raw_x.columns))
    verify_schema(features, list(raw_x.columns))
    x = raw_x.loc[:, features]

    schema = {"feature_count": len(features), "features": [{"feature": name, "feature_key": feature_key(name)} for name in features]}
    (output_dir / "rq2_feature_schema.json").write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[2/5] Tạo danh sách flow dùng chung cho SHAP và LIME...")
    names = [str(name) for name in encoder.classes_]
    manifest = make_manifest(test_df.Label, names, args.seed, args.max_per_class)
    manifest.to_csv(output_dir / "rq2_shared_samples.csv", index=False, encoding="utf-8-sig")
    print(f"       {len(manifest):,} flow | seed={args.seed} | tối đa {args.max_per_class} flow/lớp")
    if args.dry_run:
        write_summary(output_dir, manifest, None, None)
        print("Dry run hoàn tất. Đã tạo rq2_shared_samples.csv và rq2_feature_schema.json.")
        return

    try:
        import shap
    except ModuleNotFoundError as error:
        raise SystemExit("Chưa cài SHAP. Chạy trong VS Code: py -3.14 -m pip install shap") from error

    print("[3/5] Dự đoán XGBoost và tính SHAP theo batch...")
    ids = manifest.sample_id.to_numpy(dtype=int)
    x_selected = x.iloc[ids].reset_index(drop=True)
    predicted_codes = np.asarray(model.predict(x_selected), dtype=int)
    probabilities = np.asarray(model.predict_proba(x_selected))[np.arange(len(ids)), predicted_codes]
    meta = manifest.copy()
    meta["predicted_label"] = encoder.inverse_transform(predicted_codes).astype(str)
    meta["predicted_probability"] = probabilities.astype(float)
    meta["is_correct"] = meta.true_label.eq(meta.predicted_label)
    meta.to_csv(output_dir / "rq2_shap_sample_predictions.csv", index=False, encoding="utf-8-sig")

    explainer = shap.TreeExplainer(model, model_output="raw", feature_perturbation="tree_path_dependent")
    all_ranks: list[dict[str, object]] = []
    additivity_rows: list[dict[str, object]] = []
    for start in range(0, len(x_selected), args.batch_size):
        end = min(start + args.batch_size, len(x_selected))
        batch_x = x_selected.iloc[start:end]
        batch_codes = predicted_codes[start:end]
        values = choose_predicted_class_values(explainer.shap_values(batch_x, check_additivity=False), batch_codes, len(features))
        batch_meta = meta.iloc[start:end].reset_index(drop=True)
        all_ranks.extend(create_ranking(batch_meta, values, features))
        margins = np.asarray(model.predict(batch_x, output_margin=True))
        margins = margins if margins.ndim == 1 else margins[np.arange(len(batch_codes)), batch_codes]
        reconstructed = base_for_predicted_class(explainer.expected_value, batch_codes) + values.sum(axis=1)
        additivity_rows.extend({"sample_id": int(batch_meta.iloc[i].sample_id), "predicted_label": batch_meta.iloc[i].predicted_label, "raw_margin": float(margins[i]), "shap_reconstructed_margin": float(reconstructed[i]), "absolute_error": float(abs(margins[i] - reconstructed[i]))} for i in range(len(batch_meta)))
        print(f"       Đã xử lý {end:,}/{len(x_selected):,} flow")

    print("[4/5] Lưu ranking Top-1, Top-3, Top-5...")
    ranking = pd.DataFrame(all_ranks)
    ranking.to_csv(output_dir / "rq2_shap_ranking_all_features.csv", index=False, encoding="utf-8-sig")
    for k in (1, 3, 5):
        ranking[ranking["rank"] <= k].to_csv(output_dir / f"rq2_shap_top{k}.csv", index=False, encoding="utf-8-sig")
    additivity = pd.DataFrame(additivity_rows)
    additivity.to_csv(output_dir / "rq2_shap_additivity_check.csv", index=False, encoding="utf-8-sig")

    print("[5/5] Tổng hợp Top-5 theo từng lớp...")
    class_top5 = make_class_top5(ranking)
    class_top5.to_csv(output_dir / "rq2_shap_top5_by_class.csv", index=False, encoding="utf-8-sig")
    metadata = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "seed": args.seed, "max_per_class": args.max_per_class, "shared_sample_count": int(len(manifest)), "feature_count": len(features), "shap_version": shap.__version__, "mean_additivity_absolute_error": float(additivity.absolute_error.mean()), "max_additivity_absolute_error": float(additivity.absolute_error.max()), "next_step": "Run LIME on rq2_shared_samples.csv, then calculate Top-k overlap and Jaccard."}
    (output_dir / "rq2_shap_run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    write_summary(output_dir, manifest, meta, ranking)
    print(f"Hoàn tất. Mở {output_dir / 'README_results.md'} trong VS Code để xem tóm tắt.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nLỖI: {exc}", file=sys.stderr)
        raise
