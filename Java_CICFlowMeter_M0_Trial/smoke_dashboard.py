"""Exercise Java CSV -> M0 -> SHAP/LIME without opening a network capture."""
import csv
import os
from pathlib import Path

os.environ.setdefault("JAVA_M0_TRIAL_TOKEN", "offline-smoke")
from service import manager  # noqa: E402

path = Path(__file__).parent / "output" / "test.pcap_Flow.csv"
with path.open(encoding="utf-8", newline="") as source:
    rows = list(csv.DictReader(source))
for row in rows:
    manager._accept_row(row)
status = manager.status()
alerts = [flow for flow in manager.flows() if flow["prediction"] not in (None, "Benign")]
assert status["rows"] == len(rows)
assert alerts and alerts[0]["shap"] is not None
assert alerts[0]["shap"]["class_explained"] == alerts[0]["prediction"]
lime = manager.explain_lime(alerts[0]["id"])
assert lime["status"] in ("ok", "insufficient_neighborhood", "zero_coefficients", "undefined_fit")
print({"rows": status["rows"], "labels": status["labels"],
       "shap_class": alerts[0]["shap"]["class_explained"],
       "shap_additivity_error": alerts[0]["shap"]["additivity_error"],
       "lime_status": lime["status"],
       "lime_ess": lime["diagnostics"]["effective_sample_size"]})
