"""Local API owning the isolated Java capture process and M0 explanations."""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

TRIAL = Path(__file__).resolve().parent
ROOT = TRIAL.parent
sys.path.insert(0, str(ROOT / "RQ4_Retrain_Compare" / "scripts"))
sys.path.insert(0, str(ROOT / "RQ3_IDS_System" / "app"))
from rq4_common import FEATURE_MAP  # noqa: E402
from explain_shap import ShapExplainer  # noqa: E402
from explain_lime import LimeExplainer  # noqa: E402
from run_java_live_m0 import java_environment, list_interfaces  # noqa: E402

TOKEN = os.environ.get("JAVA_M0_TRIAL_TOKEN", "")
if not TOKEN:
    raise RuntimeError("JAVA_M0_TRIAL_TOKEN must be set by launch_dashboard.py")


def authorized(x_trial_token: str | None = Header(None)):
    if x_trial_token != TOKEN:
        raise HTTPException(403, "Invalid local trial token")


class StartRequest(BaseModel):
    interface: str
    seconds: int = 0  # 0 = until Stop is pressed


class TrialManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.process = None
        self.thread = None
        self.phase = "idle"
        self.run_id = None
        self.interface = None
        self.csv_path = None
        self.log_path = None
        self.stop_path = None
        self.records = []
        self.error = None
        self.packet_summary = None
        self.model = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl")
        self.encoder = joblib.load(ROOT / "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl")
        self.names = list(self.model.feature_names_in_)
        self.classes = list(self.encoder.classes_)
        self.shap = ShapExplainer(self.model, self.classes)
        cfg = yaml.safe_load((ROOT / "RQ3_IDS_System/config.yaml").read_text(encoding="utf-8"))
        background = np.load(ROOT / "RQ3_IDS_System/data/lime_background.npy")
        self.lime = LimeExplainer(self.model, self.names, self.classes, background, cfg["lime"], cfg["seed"])

    def start(self, interface: str, seconds: int):
        if not 0 <= seconds <= 3600:
            raise HTTPException(422, "seconds must be 0..3600")
        devices = list_interfaces()
        matches = [name for name, desc in devices if interface in (name, desc)]
        if not matches:
            raise HTTPException(422, "Interface is not in Java/Npcap device list")
        with self.lock:
            if self.phase in ("capturing", "stopping"):
                raise HTTPException(409, "A capture is already running")
            self.run_id = uuid.uuid4().hex[:12]
            self.interface = matches[0]
            output = TRIAL / "output"
            output.mkdir(exist_ok=True)
            self.csv_path = output / f"dashboard_{self.run_id}.csv"
            self.log_path = output / f"dashboard_{self.run_id}.log"
            self.stop_path = output / f"dashboard_{self.run_id}.stop"
            self.records = []
            self.error = None
            self.packet_summary = None
            cmd = [str(TRIAL / "upstream/gradlew.bat"), "liveTrial",
                   f"-PtrialArgs={self.interface}~{seconds}~{self.csv_path}~{self.stop_path}",
                   "--offline", "--no-daemon", "--console=plain"]
            with self.log_path.open("w", encoding="utf-8") as log:
                self.process = subprocess.Popen(cmd, cwd=TRIAL / "upstream",
                                                env=java_environment(), stdout=log, stderr=subprocess.STDOUT)
            self.phase = "capturing"
            self.thread = threading.Thread(target=self._monitor, daemon=True)
            self.thread.start()
            return self.status()

    def stop(self):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                raise HTTPException(409, "No active capture")
            self.stop_path.write_text("stop", encoding="ascii")
            self.phase = "stopping"
            return self.status()

    def _monitor(self):
        proc = self.process
        csv_path = self.csv_path
        offset = 0
        pending = b""
        header = None
        while proc.poll() is None or (csv_path.exists() and csv_path.stat().st_size > offset):
            try:
                if csv_path.exists():
                    with csv_path.open("rb") as source:
                        source.seek(offset)
                        chunk = source.read()
                        offset = source.tell()
                    pending += chunk
                    lines = pending.split(b"\n")
                    pending = lines.pop()
                    for line in lines:
                        decoded = line.decode("utf-8-sig", errors="replace").rstrip("\r")
                        if not decoded:
                            continue
                        if header is None:
                            header = next(csv.reader([decoded]))
                            continue
                        values = next(csv.reader([decoded]))
                        if len(values) != len(header):
                            raise ValueError(f"Java CSV row has {len(values)} fields; expected {len(header)}")
                        try:
                            self._accept_row(dict(zip(header, values)))
                        except Exception as exc:
                            with self.lock:
                                self.error = f"CSV/prediction row: {exc}"
            except Exception as exc:
                with self.lock:
                    self.error = f"CSV/prediction: {exc}"
            if proc.poll() is None:
                time.sleep(0.5)
        code = proc.wait()
        log = self.log_path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"accepted_packets=\d+ closed_flows=\d+ flushed_flows=\d+", log)
        with self.lock:
            self.packet_summary = match.group(0) if match else None
            if code:
                self.error = self.error or f"Java exit={code}; see {self.log_path.name}"
            self.phase = "finished" if code == 0 and not self.error else "error"

    def _accept_row(self, row):
        values = pd.to_numeric(pd.Series({n: row.get(FEATURE_MAP[n]) for n in self.names}), errors="coerce")
        x = pd.DataFrame([values], columns=self.names)
        record = {"id": len(self.records) + 1, "time": row.get("Timestamp"),
                  "src_ip": row.get("Src IP"), "src_port": row.get("Src Port"),
                  "dst_ip": row.get("Dst IP"), "dst_port": row.get("Dst Port"),
                  "protocol": row.get("Protocol"), "features": values.to_dict(),
                  "prediction": None, "confidence": None, "shap": None, "lime": None,
                  "error": None}
        if not np.isfinite(x.to_numpy(dtype=float)).all():
            record["error"] = "NaN/Inf or missing feature; no prediction"
        else:
            proba = self.model.predict_proba(x)[0]
            record["prediction"] = self.classes[int(proba.argmax())]
            record["confidence"] = float(proba.max())
        with self.lock:
            self.records.append(record)
        if record["prediction"] not in (None, "Benign"):
            try:
                result = self.shap.explain(x, record["prediction"], top_k=5)
                with self.lock:
                    record["shap"] = result
            except Exception as exc:
                with self.lock:
                    record["error"] = f"SHAP: {exc}"

    def explain_lime(self, flow_id: int):
        with self.lock:
            record = next((r for r in self.records if r["id"] == flow_id), None)
            if record is None:
                raise HTTPException(404, "Flow not found")
            if record["prediction"] is None:
                raise HTTPException(422, "Flow has no valid prediction")
            if record["lime"] is not None:
                return record["lime"]
            x = pd.DataFrame([record["features"]], columns=self.names)
            label = record["prediction"]
        result = self.lime.explain(x, label, flow_id, top_k=5)
        with self.lock:
            record["lime"] = result
        return result

    def status(self):
        with self.lock:
            labels = pd.Series([r["prediction"] for r in self.records if r["prediction"]]).value_counts().to_dict()
            return {"phase": self.phase, "run_id": self.run_id,
                    "interface": self.interface, "rows": len(self.records),
                    "labels": labels, "error": self.error, "packet_summary": self.packet_summary}

    def flows(self):
        with self.lock:
            return [{k: v for k, v in r.items() if k != "features"} for r in self.records]

    def flow(self, flow_id: int):
        with self.lock:
            record = next((r for r in self.records if r["id"] == flow_id), None)
            if record is None:
                raise HTTPException(404, "Flow not found")
            return record.copy()


manager = TrialManager()
app = FastAPI(title="Isolated Java CICFlowMeter + M0 trial")


@app.get("/interfaces", dependencies=[Depends(authorized)])
def interfaces():
    return [{"name": n, "description": d} for n, d in list_interfaces()]


@app.get("/status", dependencies=[Depends(authorized)])
def status():
    return manager.status()


@app.post("/start", dependencies=[Depends(authorized)])
def start(req: StartRequest):
    return manager.start(req.interface, req.seconds)


@app.post("/stop", dependencies=[Depends(authorized)])
def stop():
    return manager.stop()


@app.get("/flows", dependencies=[Depends(authorized)])
def flows():
    return manager.flows()


@app.get("/flows/{flow_id}", dependencies=[Depends(authorized)])
def flow(flow_id: int):
    return manager.flow(flow_id)


@app.post("/flows/{flow_id}/lime", dependencies=[Depends(authorized)])
def lime(flow_id: int):
    return manager.explain_lime(flow_id)
