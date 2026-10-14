"""Tầng 6 (phần API) — FastAPI, ghép tầng 2 (chuẩn hóa) + tầng 3 (dự đoán) + ghi DB.

Chạy thử: uvicorn app.main:app --reload --port 8000  (chạy từ thư mục RQ3_IDS_System/)
"""
from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
from normalize import normalize_flow, FlowValidationError  # noqa: E402
from predict import Detector  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
RQ3_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(RQ3_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Khởi tạo 1 lần lúc server bật lên --------------------------------------------
cfg = load_config()
detector = Detector(REPO_ROOT / cfg["paths"]["model"], REPO_ROOT / cfg["paths"]["label_encoder"])
DB_PATH = REPO_ROOT / cfg["paths"]["sqlite_db"]
db.init_db(DB_PATH)  # chạy 1 lần lúc khởi động để chắc chắn đủ bảng

app = FastAPI(title="RQ3 IDS System API")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": detector.model is not None,
        "model_version": detector.model_version,
        "n_features_expected": len(detector.feature_names),
        "n_classes": len(detector.class_names),
    }


@app.post("/predict")
def predict(flow: Dict[str, float]):
    flow_id = str(uuid.uuid4())
    t_start = time.perf_counter()
    # Mở 1 connection RIÊNG cho request này (xem lý do trong app/db.py::get_connection).
    conn = db.get_connection(DB_PATH)
    try:
        # ---- Tầng 2: chuẩn hóa ------------------------------------------------------
        # Lỗi (422) thì KHÔNG ghi FlowRecord/Timing — flow coi như chưa vào hệ thống,
        # chỉ ghi vào DataError.
        t0 = time.perf_counter()
        try:
            normalized = normalize_flow(flow, detector.feature_names, convert_seconds_to_microseconds=False)
        except FlowValidationError as e:
            db.insert_error(conn, flow_id, now_iso(), 422, e.reason, flow)
            raise HTTPException(status_code=422, detail={"reason": e.reason, **e.details})
        t_normalize_ms = (time.perf_counter() - t0) * 1000

        # Phải ghi FlowRecord TRƯỚC Timing, vì Timing.flow_id tham chiếu khóa ngoại
        # tới FlowRecord.flow_id — ghi ngược thứ tự sẽ vi phạm FOREIGN KEY constraint.
        db.insert_flow(conn, flow_id, now_iso(), "api", flow, label_true=None)
        db.insert_timing(conn, flow_id, "normalize", t_normalize_ms, now_iso())

        # ---- Tầng 3: dự đoán ---------------------------------------------------------
        t0 = time.perf_counter()
        result = detector.predict_flow(normalized)
        t_predict_ms = (time.perf_counter() - t0) * 1000
        db.insert_timing(conn, flow_id, "predict", t_predict_ms, now_iso())

        db.insert_prediction(
            conn, flow_id, result["predicted_label"], result["probabilities"],
            result["model_version"], now_iso(),
        )

        # ---- Luật tạo cảnh báo: nhãn khác Benign thì tạo Alert ngay ------------------
        alert_id = None
        if result["predicted_label"] != "Benign":
            alert_id = str(uuid.uuid4())
            db.insert_alert(
                conn, alert_id, flow_id,
                group_key=result["predicted_label"],  # chưa có IP/port để gộp theo cặp IP, dùng tạm nhãn dự đoán
                predicted_label=result["predicted_label"],
                created_at=now_iso(),
            )

        t_total_ms = (time.perf_counter() - t_start) * 1000
        db.insert_timing(conn, flow_id, "total", t_total_ms, now_iso())
    finally:
        conn.close()

    return JSONResponse({
        "flow_id": flow_id,
        "predicted_label": result["predicted_label"],
        "probabilities": result["probabilities"],
        "model_version": result["model_version"],
        "is_alert": alert_id is not None,
        "alert_id": alert_id,
        "timing_ms": {
            "normalize": round(t_normalize_ms, 3),
            "predict": round(t_predict_ms, 3),
            "total": round(t_total_ms, 3),
        },
    })
