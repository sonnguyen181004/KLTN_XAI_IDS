"""Offline Java CSV -> isolated M0/M1 model, SHAP, LIME and CSV import check."""
import csv
import io
import os
from pathlib import Path

os.environ.setdefault("JAVA_M0_TRIAL_TOKEN", "offline-dual-smoke")
from service import TrialManager  # noqa: E402

source = Path(__file__).parent / "output" / "test.pcap_Flow.csv"
manager = TrialManager()
text = source.read_text(encoding="utf-8-sig")
rows = list(csv.DictReader(io.StringIO(text)))
assert manager.import_csv(source.name, text)["rows"] == len(rows)

for name, count in (("M0", 15), ("M1", 13)):
    status = manager.status(name)
    assert status["rows"] == len(rows) and status["n_classes"] == count
    valid = next(r for r in manager.flows(name) if r["prediction"])
    detail = manager.flow(valid["id"], name)
    assert len(detail["probabilities"]) == count
    shap = manager.explain_shap(valid["id"], name)
    assert shap["class_explained"] == detail["prediction"]
    assert shap["additivity_error"] < 1e-3
    lime = manager.explain_lime(valid["id"], name)
    assert lime["status"] in ("ok", "insufficient_neighborhood", "zero_coefficients", "undefined_fit")
    print(name, status["labels"], "shap_error", shap["additivity_error"], "lime", lime["status"])

# A CSV with canonical model column names must enter the same feature vector.
original = manager.flow(1, "M0")
buffer = io.StringIO()
writer = csv.DictWriter(buffer, fieldnames=list(original["features"]))
writer.writeheader()
writer.writerow(original["features"])
assert manager.import_csv("canonical.csv", buffer.getvalue())["rows"] == 1
assert manager.flow(1, "M0")["features"] == original["features"]
assert manager.flow(1, "M1")["probabilities"]
print("canonical_csv", "ok")

from normalize import TIME_COLUMNS  # noqa: E402
seconds_row = original["features"].copy()
for name in TIME_COLUMNS:
    if name in seconds_row:
        seconds_row[name] /= 1_000_000
buffer = io.StringIO()
writer = csv.DictWriter(buffer, fieldnames=list(seconds_row))
writer.writeheader()
writer.writerow(seconds_row)
manager.import_csv("seconds.csv", buffer.getvalue(), convert_seconds=True)
assert abs(manager.flow(1, "M0")["features"]["Flow Duration"] - original["features"]["Flow Duration"]) < 1e-5
print("seconds_to_microseconds", "ok")
