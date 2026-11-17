"""Local API owning the isolated Java capture process and M0 explanations."""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
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
from normalize import TIME_COLUMNS  # noqa: E402
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


class CsvRequest(BaseModel):
    name: str
    content: str
    convert_seconds: bool = False


class PcapRequest(BaseModel):
    filename: str


def model_name(value: str) -> str:
    if value not in ("M0", "M1"):
        raise HTTPException(422, "model must be M0 or M1")
    return value


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
        self.models = {}
        for name, base, model_path, encoder_path in (
            ("M0", "RQ3_IDS_System", "RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl",
             "RQ1_Model_Training_xboost/saved_models/label_encoder.pkl"),
            ("M1", "IDS_M1_Lab", "IDS_M1_Lab/models/m1_xgboost_model.pkl",
             "IDS_M1_Lab/models/m1_label_encoder.pkl"),
        ):
            model = joblib.load(ROOT / model_path)
            encoder = joblib.load(ROOT / encoder_path)
            names = list(model.feature_names_in_)
            classes = list(encoder.classes_)
            if model.n_classes_ != len(classes) or len(names) != 78:
                raise RuntimeError(f"{name} model/encoder/features do not match")
            cfg = yaml.safe_load((ROOT / base / "config.yaml").read_text(encoding="utf-8"))
            background = np.load(ROOT / base / "data/lime_background.npy")
            stats = json.loads((ROOT / base / "data/train_stats.json").read_text(encoding="utf-8"))
            if background.ndim != 2 or background.shape[1] != len(names):
                raise RuntimeError(f"{name} LIME background does not match features")
            self.models[name] = {"model": model, "classes": classes, "names": names,
                                 "shap": ShapExplainer(model, classes),
                                 "lime": LimeExplainer(model, names, classes, background, cfg["lime"], cfg["seed"]),
                                 "cfg": cfg, "stats": stats}
        self.model = self.models["M0"]["model"]  # legacy offline smoke compatibility
        self.names = self.models["M0"]["names"]
        self.classes = self.models["M0"]["classes"]

    def start(self, interface: str, seconds: int):
        if not 0 <= seconds <= 3600:
            raise HTTPException(422, "seconds must be 0..3600")
        devices = list_interfaces()
        matches = [name for name, desc in devices if interface in (name, desc)]
        if not matches:
            raise HTTPException(422, "Interface is not in Java/Npcap device list")
        with self.lock:
            if self.phase in ("capturing", "stopping", "importing"):
                raise HTTPException(409, "A capture or import is already running")
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

    def _accept_row(self, row, convert_seconds: bool = False):
        values = pd.to_numeric(pd.Series({n: row.get(FEATURE_MAP[n], row.get(n)) for n in self.names}),
                               errors="coerce")
        if convert_seconds:
            values.loc[[n for n in TIME_COLUMNS if n in values.index]] *= 1_000_000
        record = {"id": len(self.records) + 1, "time": row.get("Timestamp"),
                  "src_ip": row.get("Src IP"), "src_port": row.get("Src Port"),
                  "dst_ip": row.get("Dst IP"), "dst_port": row.get("Dst Port"),
                  "protocol": row.get("Protocol"), "features": values.to_dict(),
                  "models": {}, "error": None}
        valid = np.isfinite(values.to_numpy(dtype=float)).all()
        if not valid:
            record["error"] = "NaN/Inf or missing feature; no prediction"
        for name, bundle in self.models.items():
            result = {"prediction": None, "confidence": None, "probabilities": {},
                      "shap": None, "lime": None, "error": record["error"],
                      "branch": None, "env_fingerprint_count": 0, "rare_class_flag": False}
            if valid:
                x = pd.DataFrame([{n: values[n] for n in bundle["names"]}], columns=bundle["names"])
                proba = bundle["model"].predict_proba(x)[0]
                result["prediction"] = bundle["classes"][int(proba.argmax())]
                result["confidence"] = float(proba.max())
                result["probabilities"] = dict(zip(bundle["classes"], map(float, proba)))
                if result["prediction"] != "Benign":
                    try:
                        result["shap"] = bundle["shap"].explain(x, result["prediction"], top_k=5)
                    except Exception as exc:
                        result["error"] = f"SHAP: {exc}"
                    if result["shap"]:
                        env = set(bundle["cfg"].get("environment_fingerprint_features", []))
                        result["env_fingerprint_count"] = sum(
                            item["feature"] in env for item in result["shap"]["top_k"])
                    samples = bundle["stats"]["train_samples_per_class"].get(result["prediction"])
                    result["rare_class_flag"] = samples is not None and samples < bundle["cfg"].get(
                        "rare_class_min_train_samples", 100)
                    threshold = bundle["cfg"].get("environment_fingerprint_flag_threshold", 2)
                    result["branch"] = ("B" if result["env_fingerprint_count"] >= threshold
                                        or result["rare_class_flag"] else "A")
            record["models"][name] = result
        record.update(record["models"]["M0"])  # keep previous M0 read contract
        with self.lock:
            self.records.append(record)

    def explain_lime(self, flow_id: int, name: str = "M0"):
        name = model_name(name)
        with self.lock:
            record = next((r for r in self.records if r["id"] == flow_id), None)
            if record is None:
                raise HTTPException(404, "Flow not found")
            result = record["models"][name]
            if result["prediction"] is None:
                raise HTTPException(422, "Flow has no valid prediction")
            if result["lime"] is not None:
                return result["lime"]
            bundle = self.models[name]
            x = pd.DataFrame([record["features"]], columns=bundle["names"])
            label = result["prediction"]
        explanation = bundle["lime"].explain(x, label, flow_id, top_k=5)
        with self.lock:
            result["lime"] = explanation
            if name == "M0":
                record["lime"] = explanation
        return explanation

    def explain_shap(self, flow_id: int, name: str = "M0"):
        name = model_name(name)
        with self.lock:
            record = next((r for r in self.records if r["id"] == flow_id), None)
            if record is None:
                raise HTTPException(404, "Flow not found")
            result = record["models"][name]
            if result["prediction"] is None:
                raise HTTPException(422, "Flow has no valid prediction")
            if result["shap"] is not None:
                return result["shap"]
            bundle = self.models[name]
            x = pd.DataFrame([record["features"]], columns=bundle["names"])
            label = result["prediction"]
        explanation = bundle["shap"].explain(x, label, top_k=5)
        with self.lock:
            result["shap"] = explanation
            if name == "M0":
                record["shap"] = explanation
        return explanation

    def status(self, name: str = "M0"):
        name = model_name(name)
        with self.lock:
            labels = pd.Series([r["models"][name]["prediction"] for r in self.records
                                if r["models"][name]["prediction"]]).value_counts().to_dict()
            return {"phase": self.phase, "run_id": self.run_id,
                    "interface": self.interface, "rows": len(self.records),
                    "labels": labels, "error": self.error, "packet_summary": self.packet_summary,
                    "model": name, "n_classes": len(self.models[name]["classes"])}

    def model_info(self, name: str):
        name = model_name(name)
        bundle = self.models[name]
        return {"classes": bundle["classes"],
                "global_median": bundle["stats"]["global_median"],
                "train_samples_per_class": bundle["stats"]["train_samples_per_class"],
                "environment_features": bundle["cfg"].get("environment_fingerprint_features", []),
                "environment_threshold": bundle["cfg"].get("environment_fingerprint_flag_threshold", 2)}

    def flows(self, name: str = "M0"):
        name = model_name(name)
        with self.lock:
            return [self._view(r, name, False) for r in self.records]

    @staticmethod
    def _view(record, name, detail):
        shared = {k: record[k] for k in ("id", "time", "src_ip", "src_port", "dst_ip", "dst_port", "protocol")}
        if detail:
            shared["features"] = record["features"].copy()
        shared.update(record["models"][name].copy())
        return shared

    def flow(self, flow_id: int, name: str = "M0"):
        name = model_name(name)
        with self.lock:
            record = next((r for r in self.records if r["id"] == flow_id), None)
            if record is None:
                raise HTTPException(404, "Flow not found")
            return self._view(record, name, True)

    def import_csv(self, name: str, content: str, convert_seconds: bool = False, internal: bool = False):
        with self.lock:
            if self.phase in ("capturing", "stopping") or (self.phase == "importing" and not internal):
                raise HTTPException(409, "Stop capture/import before importing CSV")
        if len(content.encode("utf-8")) > 20_000_000:
            raise HTTPException(413, "CSV is larger than 20 MB")
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames or any(n not in reader.fieldnames and FEATURE_MAP[n] not in reader.fieldnames
                                        for n in self.names):
            raise HTTPException(422, "CSV needs all 78 feature columns (Java or model names)")
        rows = list(reader)
        if len(rows) > 10_000:
            raise HTTPException(413, "CSV is limited to 10,000 flows per import")
        with self.lock:
            if self.phase in ("capturing", "stopping") or (self.phase == "importing" and not internal):
                raise HTTPException(409, "Stop capture/import before importing CSV")
            self.phase = "importing"
            self.records = []
            self.run_id = "csv:" + name[:80]
            self.error = None
            self.packet_summary = None
        for row in rows:
            self._accept_row(row, convert_seconds=convert_seconds)
        with self.lock:
            self.phase = "finished"
        return {"rows": len(rows), "status": self.status()}

    def import_pcap(self, filename: str):
        with self.lock:
            if self.phase in ("capturing", "stopping", "importing"):
                raise HTTPException(409, "Stop capture/import before importing PCAP")
        imports = (TRIAL / "output" / "imports").resolve()
        path = (imports / filename).resolve()
        if path.parent != imports or path.suffix.lower() not in (".pcap", ".pcapng") or not path.is_file():
            raise HTTPException(422, "Select an uploaded PCAP/PCAPNG in trial imports")
        if path.stat().st_size > 100_000_000:
            raise HTTPException(413, "PCAP is larger than 100 MB")
        with self.lock:
            self.phase = "importing"
        try:
            return self._import_pcap_file(path)
        except Exception as exc:
            with self.lock:
                self.phase = "error"
                self.error = str(exc)
            raise

    def _import_pcap_file(self, path: Path):
        if path.suffix.lower() == ".pcapng":
            editcap = shutil.which("editcap") or r"C:\Program Files\Wireshark\editcap.exe"
            if not Path(editcap).is_file():
                raise HTTPException(422, "Wireshark editcap is needed for PCAPNG")
            converted = path.with_suffix(".pcap")
            conversion = subprocess.run([editcap, "-F", "pcap", str(path), str(converted)],
                                        capture_output=True, text=True, timeout=180)
            if conversion.returncode:
                raise HTTPException(422, "editcap failed: " + conversion.stderr[-300:])
            path = converted
        out = (TRIAL / "output" / "imports" / (path.stem + "_java"))
        out.mkdir(exist_ok=True)
        proc = subprocess.run([str(TRIAL / "upstream/gradlew.bat"), "exeCMD",
                               f"-PtrialInput={path}", f"-PtrialOutput={out}",
                               "--offline", "--no-daemon", "--console=plain"],
                              cwd=TRIAL / "upstream", env=java_environment(),
                              capture_output=True, text=True, timeout=300)
        if proc.returncode:
            raise HTTPException(422, "Java PCAP extraction failed: " + (proc.stdout + proc.stderr)[-500:])
        csv_path = out / f"{path.name}_Flow.csv"
        if not csv_path.is_file():
            raise HTTPException(422, "Java finished without a flow CSV")
        return self.import_csv(path.name, csv_path.read_text(encoding="utf-8-sig"), internal=True)


manager = TrialManager()
app = FastAPI(title="Isolated Java CICFlowMeter + M0/M1 trial")


@app.get("/interfaces", dependencies=[Depends(authorized)])
def interfaces():
    return [{"name": n, "description": d} for n, d in list_interfaces()]


@app.get("/status", dependencies=[Depends(authorized)])
def status(model: str = "M0"):
    return manager.status(model)


@app.get("/model-info", dependencies=[Depends(authorized)])
def model_info(model: str = "M0"):
    return manager.model_info(model)


@app.post("/start", dependencies=[Depends(authorized)])
def start(req: StartRequest):
    return manager.start(req.interface, req.seconds)


@app.post("/stop", dependencies=[Depends(authorized)])
def stop():
    return manager.stop()


@app.get("/flows", dependencies=[Depends(authorized)])
def flows(model: str = "M0"):
    return manager.flows(model)


@app.get("/flows/{flow_id}", dependencies=[Depends(authorized)])
def flow(flow_id: int, model: str = "M0"):
    return manager.flow(flow_id, model)


@app.post("/flows/{flow_id}/lime", dependencies=[Depends(authorized)])
def lime(flow_id: int, model: str = "M0"):
    return manager.explain_lime(flow_id, model)


@app.post("/flows/{flow_id}/shap", dependencies=[Depends(authorized)])
def shap(flow_id: int, model: str = "M0"):
    return manager.explain_shap(flow_id, model)


@app.post("/import/csv", dependencies=[Depends(authorized)])
def import_csv(req: CsvRequest):
    return manager.import_csv(req.name, req.content, req.convert_seconds)


@app.post("/import/pcap", dependencies=[Depends(authorized)])
def import_pcap(req: PcapRequest):
    return manager.import_pcap(req.filename)
