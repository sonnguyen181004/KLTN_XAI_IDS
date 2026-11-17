"""Read a Java CICFlowMeter CSV and run the frozen RQ1 M0 locally."""
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "RQ4_Retrain_Compare" / "scripts"))
from rq4_common import FEATURE_MAP  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output" / "m0_predictions.csv")
    args = parser.parse_args()
    model = joblib.load(ROOT / "RQ1_Model_Training_xboost" / "saved_models" / "best_xgboost_model.pkl")
    encoder = joblib.load(ROOT / "RQ1_Model_Training_xboost" / "saved_models" / "label_encoder.pkl")
    raw = pd.read_csv(args.csv, low_memory=False)
    features = list(model.feature_names_in_)
    missing = {name: FEATURE_MAP[name] for name in features if FEATURE_MAP[name] not in raw.columns}
    if missing:
        raise SystemExit("Missing Java columns: " + json.dumps(missing, ensure_ascii=False))
    x = raw[[FEATURE_MAP[name] for name in features]].copy()
    x.columns = features
    x = x.apply(pd.to_numeric, errors="coerce")
    bad = ~np.isfinite(x.to_numpy(dtype=float))
    if bad.any():
        raise SystemExit(f"Non-finite model inputs: {int(bad.sum())} cells; prediction refused")
    probabilities = model.predict_proba(x)
    idx = probabilities.argmax(axis=1)
    result = raw[[c for c in ("Flow ID", "Src IP", "Src Port", "Dst IP", "Dst Port", "Protocol", "Timestamp") if c in raw]].copy()
    result["predicted_label"] = encoder.classes_[idx]
    result["confidence"] = probabilities.max(axis=1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"M0 predicted {len(result)} Java flows -> {args.output}")
    print(result["predicted_label"].value_counts().to_string())


if __name__ == "__main__":
    main()
