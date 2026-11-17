"""Read-only M0 audit of a labeled CSV and saved realtime capture CSVs."""
import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "RQ3_IDS_System" / "app"))
from feeder import row_to_payload  # noqa: E402

SOURCES = {
    "labeled_csv": ROOT / "RQ3_IDS_System/data/test_samples/test_sample100_15classes_with_label.csv",
    "live_review": ROOT / "RQ3_IDS_System/data/live_review_01.csv",
    "live_manual": ROOT / "RQ3_IDS_System/data/live_manual_01.csv",
    "live_phone": ROOT / "RQ3_IDS_System/data/live_phone_01.csv",
}


def main():
    model = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl")
    encoder = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")
    features = list(model.feature_names_in_)
    result = {}
    for name, path in SOURCES.items():
        raw = pd.read_csv(path, low_memory=False)
        if name == "labeled_csv":
            x = raw.reindex(columns=features).apply(pd.to_numeric, errors="coerce")
        else:
            rows = [row_to_payload(r, list(raw.columns), True) for r in raw.to_dict("records")]
            x = pd.DataFrame(rows).reindex(columns=features).apply(pd.to_numeric, errors="coerce")
        valid = np.isfinite(x.to_numpy(dtype=float)).all(axis=1)
        predicted = encoder.classes_[model.predict_proba(x.loc[valid]).argmax(axis=1)]
        labels = dict(Counter(str(v) for v in predicted))
        record = {"source": str(path.relative_to(ROOT)).replace('\\', '/'),
                  "rows": len(raw), "valid_rows": int(valid.sum()),
                  "rejected_rows": int((~valid).sum()), "predicted_labels": labels,
                  "attack_alerts": int(sum(v for k, v in labels.items() if k != "Benign"))}
        if "extractor_version" in raw:
            record["extractor_versions"] = dict(Counter(raw["extractor_version"].fillna("missing")))
        if name == "labeled_csv":
            truth = raw.loc[valid, "label_true"].astype(str).to_numpy()
            record["reference_labels"] = dict(Counter(truth))
            record["matches"] = int((truth == predicted).sum())
            record["sample_accuracy"] = float((truth == predicted).mean())
            record["benign_rows"] = int((truth == "Benign").sum())
            record["benign_alerts"] = int(((truth == "Benign") & (predicted != "Benign")).sum())
            record["attack_rows"] = int((truth != "Benign").sum())
            record["attack_detected_any_attack_label"] = int(((truth != "Benign") & (predicted != "Benign")).sum())
            record["exact_class_confusions"] = dict(Counter(f"{t} -> {p}" for t, p in zip(truth, predicted) if t != p))
        result[name] = record
    target = Path(__file__).parent / "csv_and_saved_live_m0_20261117.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
