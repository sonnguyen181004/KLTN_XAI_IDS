"""Bounded Java Wi-Fi capture with local M0 prediction as CSV flows close."""
import argparse
import csv
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TRIAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "RQ4_Retrain_Compare" / "scripts"))
from rq4_common import FEATURE_MAP  # noqa: E402


def complete_rows(path):
    if not path.exists():
        return []
    data = path.read_bytes()
    if not data.endswith(b"\n"):
        data = data[: data.rfind(b"\n") + 1]
    if not data:
        return []
    return list(csv.DictReader(data.decode("utf-8", errors="replace").splitlines()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", required=True, help="Exact Npcap device name or description from Java --list")
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        parser.error("--seconds must be 1..120")
    model = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl")
    encoder = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")
    features = list(model.feature_names_in_)
    output = TRIAL / "output" / f"java_live_{uuid.uuid4().hex[:12]}.csv"
    output.parent.mkdir(exist_ok=True)
    cmd = [str(TRIAL / "upstream" / "gradlew.bat"), "liveTrial",
           f"-PtrialArgs={args.interface}|{args.seconds}|{output}", "--offline", "--no-daemon"]
    env = os.environ.copy()
    env["JAVA_HOME"] = r"C:\Program Files\Java\jdk1.8.0_431"
    env["GRADLE_USER_HOME"] = str(TRIAL / "upstream" / ".gradle-home")
    process = subprocess.Popen(cmd, cwd=TRIAL / "upstream", env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    print(f"Java capture started; CSV: {output}", flush=True)
    seen = 0
    counts = {}
    while process.poll() is None or len(complete_rows(output)) > seen:
        rows = complete_rows(output)
        for row in rows[seen:]:
            values = pd.to_numeric(pd.Series({name: row.get(FEATURE_MAP[name]) for name in features}), errors="coerce")
            x = pd.DataFrame([values], columns=features)
            if not np.isfinite(x.to_numpy(dtype=float)).all():
                print(f"flow {seen + 1}: skipped (missing/NaN/Inf)", flush=True)
            else:
                proba = model.predict_proba(x)[0]
                label = str(encoder.classes_[int(proba.argmax())])
                counts[label] = counts.get(label, 0) + 1
                print(f"flow {seen + 1}: {label} ({proba.max():.1%})", flush=True)
            seen += 1
        if process.poll() is None:
            time.sleep(0.5)
    code = process.wait()
    print(f"Java exit={code}; CSV rows={seen}; M0 labels={counts}")
    if code:
        raise SystemExit(code)


if __name__ == "__main__":
    main()
