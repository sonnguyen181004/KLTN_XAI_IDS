"""Tầng 6 (phần API) — FastAPI, ghép tầng 2 (chuẩn hóa) + tầng 3 (dự đoán) + ghi DB.

Chạy thử: uvicorn app.main:app --reload --port 8000  (chạy từ thư mục RQ3_IDS_System/)
"""
from __future__ import annotations

import json
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
from explain_shap import ShapExplainer  # noqa: E402
from reliability import ReliabilityScorer  # noqa: E402
from explain_queue import ExplainQueue  # noqa: E402

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
shap_explainer = ShapExplainer(detector.model, detector.class_names)
DB_PATH = REPO_ROOT / cfg["paths"]["sqlite_db"]
db.init_db(DB_PATH)  # chạy 1 lần lúc khởi động để chắc chắn đủ bảng

# Bước 8 — thống kê train tính sẵn 1 lần (median toàn cục + số mẫu/lớp), xem
# scripts/stage08_compute_train_stats.py. Phải chạy script đó trước khi bật server.
TRAIN_STATS_PATH = RQ3_ROOT / "data" / "train_stats.json"
with open(TRAIN_STATS_PATH, encoding="utf-8") as f:
    train_stats = json.load(f)

reliability_scorer = ReliabilityScorer(
    detector=detector,
    global_median=train_stats["global_median"],
    train_samples_per_class=train_stats["train_samples_per_class"],
    env_fingerprint_features=cfg["environment_fingerprint_features"],
    env_fingerprint_flag_threshold=cfg["environment_fingerprint_flag_threshold"],
    rare_class_min_train_samples=cfg["rare_class_min_train_samples"],
    faithfulness_k=cfg["faithfulness_proxy"]["k"],
)

# Hàng đợi giải thích bất đồng bộ (đúng kiến trúc bước "Vào hàng đợi" — xem app/explain_queue.py).
# /predict KHÔNG gọi SHAP trực tiếp nữa; chỉ đưa việc vào đây rồi trả lời ngay.
explain_queue = ExplainQueue(
    maxsize=cfg["api"]["max_explain_queue"],
    shap_explainer=shap_explainer,
    reliability_scorer=reliability_scorer,
    db_module=db,
    db_path=DB_PATH,
)

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

        # ---- Luật tạo cảnh báo: nhãn khác Benign thì tạo Alert NGAY --------------------
        # QUAN TRỌNG (đúng kiến trúc Làn B): tới đây là XONG phần API phải làm. KHÔNG
        # gọi SHAP ở đây — chỉ đưa việc vào hàng đợi rồi trả lời ngay, để "cảnh báo hiện
        # lên dashboard ngay, phần giải thích nối thêm vào khi tính xong" (tài liệu kiến
        # trúc, Làn B / bước "Vào hàng đợi"). Nếu hàng đợi đầy, giải thích bị bỏ nhưng
        # Alert vẫn đã được tạo và trả về — không mất cảnh báo.
        alert_id = None
        explanation_status = None
        if result["predicted_label"] != "Benign":
            alert_id = str(uuid.uuid4())
            db.insert_alert(
                conn, alert_id, flow_id,
                group_key=result["predicted_label"],  # chưa có IP/port để gộp theo cặp IP, dùng tạm nhãn dự đoán
                predicted_label=result["predicted_label"],
                created_at=now_iso(),
            )
            explanation_status = explain_queue.submit(alert_id, flow_id, result["predicted_label"], normalized)

        t_total_ms = (time.perf_counter() - t_start) * 1000
        db.insert_timing(conn, flow_id, "total", t_total_ms, now_iso())
    finally:
        conn.close()

    timing_ms = {
        "normalize": round(t_normalize_ms, 3),
        "predict": round(t_predict_ms, 3),
        "total": round(t_total_ms, 3),
    }

    return JSONResponse({
        "flow_id": flow_id,
        "predicted_label": result["predicted_label"],
        "probabilities": result["probabilities"],
        "model_version": result["model_version"],
        "is_alert": alert_id is not None,
        "alert_id": alert_id,
        # SHAP không còn tính ngay trong request này nữa (xem app/explain_queue.py) —
        # "queued" = đang xếp hàng tính nền, "dropped_queue_full" = hàng đợi đầy (bỏ
        # giải thích, GIỮ cảnh báo), None = Benign, không cần giải thích.
        "explanation_status": explanation_status,
        "timing_ms": timing_ms,
    })


@app.get("/explain_queue_status")
def explain_queue_status():
    """Chỉ để quan sát/debug: xem hàng đợi giải thích đang ở trạng thái nào."""
    return {
        "qsize": explain_queue.qsize(),
        "maxsize": explain_queue.maxsize,
        "n_queued": explain_queue.n_queued,
        "n_processed": explain_queue.n_processed,
        "n_dropped": explain_queue.n_dropped,
    }
