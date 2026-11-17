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


def java_environment():
    env = os.environ.copy()
    env["JAVA_HOME"] = r"C:\Program Files\Java\jdk1.8.0_431"
    env["GRADLE_USER_HOME"] = str(TRIAL / "upstream" / ".gradle-home")
    return env


def list_interfaces():
    command = [str(TRIAL / "upstream" / "gradlew.bat"), "liveTrial",
               "-PtrialArgs=--list", "--offline", "--no-daemon", "--console=plain"]
    proc = subprocess.run(command, cwd=TRIAL / "upstream", env=java_environment(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise SystemExit("Cannot list Java/Npcap interfaces:\n" + proc.stdout + proc.stderr)
    devices = []
    for line in proc.stdout.splitlines():
        if line.startswith("\\Device\\NPF_") and " | " in line:
            name, description = line.split(" | ", 1)
            devices.append((name, description))
    if not devices:
        raise SystemExit("Java/Npcap returned no interfaces. Run this terminal with capture permission.")
    return devices


def choose_interface(devices):
    print("Chọn card mạng để Java bắt traffic:")
    for number, (_, description) in enumerate(devices, 1):
        print(f"  {number}. {description}")
    while True:
        answer = input("Nhập số card mạng (Enter để hủy): ").strip()
        if not answer:
            raise SystemExit("Đã hủy; chưa bắt traffic.")
        if answer.isdigit() and 1 <= int(answer) <= len(devices):
            return devices[int(answer) - 1][0]
        print("Số không hợp lệ, hãy chọn lại.")


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
    parser.add_argument("--interface", help="Exact Npcap name/description; omit to choose from menu")
    parser.add_argument("--list", action="store_true", help="Show interfaces and exit")
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        parser.error("--seconds must be 1..120")
    if args.list:
        for number, (name, description) in enumerate(list_interfaces(), 1):
            print(f"{number}. {description} [{name}]")
        return
    interface = args.interface or choose_interface(list_interfaces())
    model = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl")
    encoder = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")
    features = list(model.feature_names_in_)
    output = TRIAL / "output" / f"java_live_{uuid.uuid4().hex[:12]}.csv"
    output.parent.mkdir(exist_ok=True)
    cmd = [str(TRIAL / "upstream" / "gradlew.bat"), "liveTrial",
           f"-PtrialArgs={interface}|{args.seconds}|{output}", "--offline", "--no-daemon"]
    env = java_environment()
    log = output.with_suffix(".log")
    log_file = log.open("w", encoding="utf-8")
    process = subprocess.Popen(cmd, cwd=TRIAL / "upstream", env=env,
                               stdout=log_file, stderr=subprocess.STDOUT)
    log_file.close()
    print(f"Java capture started on {interface}; {args.seconds}s; CSV: {output}", flush=True)
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
        print(f"Java log: {log}")
        raise SystemExit(code)


if __name__ == "__main__":
    main()
